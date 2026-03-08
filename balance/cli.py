"""balance - personal balance sheet tracker"""

import sqlite3
import click
from datetime import datetime, date, timedelta
from pathlib import Path

# --- DB ----------------------------------------------------------------------

DB_DIR  = Path.home() / ".balance"
DB_PATH = DB_DIR / "balance.db"

COMMANDS = {"sheet", "net", "history", "trend", "accounts", "undo", "help"}


def get_db() -> sqlite3.Connection:
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL UNIQUE,
            type     TEXT NOT NULL,
            category TEXT,
            created  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS balances (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            amount     REAL NOT NULL,
            ts         TEXT NOT NULL,
            date       TEXT NOT NULL,
            note       TEXT
        );
    """)
    conn.commit()
    return conn


# --- Helpers -----------------------------------------------------------------

def fmt(n: float) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}${abs(n):,.2f}"


def hr(n: int = 46) -> str:
    return "  " + "-" * n


def sparkline(values: list[float]) -> str:
    if not values:
        return ""
    bars = list("._,-=+*#")
    mn, mx = min(values), max(values)
    if mx == mn:
        return "#" * len(values)
    return "".join(bars[int((v - mn) / (mx - mn) * 7)] for v in values)


def get_account(conn: sqlite3.Connection, name: str):
    return conn.execute(
        "SELECT id, name, type, category FROM accounts WHERE name=?",
        (name,),
    ).fetchone()


def get_latest_balance(conn: sqlite3.Connection, account_id: int) -> float | None:
    row = conn.execute(
        "SELECT amount FROM balances WHERE account_id=? ORDER BY ts DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    return row[0] if row else None


def net_worth_on(conn: sqlite3.Connection, on_date: str) -> tuple[float, float]:
    """Return (total_assets, total_liabilities) using latest balances as of on_date."""
    accounts = conn.execute("SELECT id, type FROM accounts").fetchall()
    assets, liabilities = 0.0, 0.0
    for acc_id, acc_type in accounts:
        row = conn.execute(
            "SELECT amount FROM balances WHERE account_id=? AND date<=? ORDER BY ts DESC LIMIT 1",
            (acc_id, on_date),
        ).fetchone()
        if row:
            if acc_type == "asset":
                assets += row[0]
            else:
                liabilities += row[0]
    return assets, liabilities


# --- Entry -------------------------------------------------------------------

def set_balance(name: str, amount: float, type_cat: str | None, note: str | None):
    name_key = name.lower()
    now = datetime.now()
    ts  = now.strftime("%Y-%m-%dT%H:%M:%S")
    d   = now.strftime("%Y-%m-%d")

    with get_db() as conn:
        account = get_account(conn, name_key)
        is_new  = account is None

        if is_new:
            if not type_cat:
                click.echo(f"  New account '{name_key}' - specify type:")
                click.echo("    asset/cash  asset/investment  asset/retirement  asset/property")
                click.echo("    liability/loan  liability/credit  liability/mortgage")
                return
            parts    = type_cat.split("/", 1)
            acc_type = parts[0].lower()
            category = parts[1].lower() if len(parts) > 1 else None
            if acc_type not in ("asset", "liability"):
                click.echo(f"  Type must be 'asset' or 'liability', got: '{acc_type}'")
                return
            conn.execute(
                "INSERT INTO accounts (name, type, category, created) VALUES (?,?,?,?)",
                (name_key, acc_type, category, ts),
            )
            account = get_account(conn, name_key)

        prev = get_latest_balance(conn, account[0])

        conn.execute(
            "INSERT INTO balances (account_id, amount, ts, date, note) VALUES (?,?,?,?,?)",
            (account[0], amount, ts, d, note or None),
        )

    if is_new:
        tc = f"{account[2]}/{account[3]}" if account[3] else account[2]
        click.echo(f"  New account: {name_key}  ({tc})")

    if prev is not None:
        diff = amount - prev
        sign = "+" if diff >= 0 else ""
        click.echo(f"  {name_key:<20} {fmt(amount)}   {sign}{fmt(diff)}")
    else:
        click.echo(f"  {name_key:<20} {fmt(amount)}")


# --- Views -------------------------------------------------------------------

def _sheet():
    today = date.today().isoformat()
    with get_db() as conn:
        accounts = conn.execute(
            "SELECT id, name, type, category FROM accounts ORDER BY type DESC, category, name"
        ).fetchall()

        if not accounts:
            click.echo("\n  No accounts yet.")
            click.echo("  try:  balance checking 5200 asset/cash\n")
            return

        rows = []
        for acc_id, name, acc_type, category in accounts:
            amount = get_latest_balance(conn, acc_id)
            if amount is not None:
                rows.append((name, acc_type, category or "", amount))

    if not rows:
        click.echo("\n  No balances recorded yet.\n")
        return

    assets      = [(n, c, a) for n, t, c, a in rows if t == "asset"]
    liabilities = [(n, c, a) for n, t, c, a in rows if t == "liability"]
    total_a     = sum(a for _, _, a in assets)
    total_l     = sum(a for _, _, a in liabilities)
    net         = total_a - total_l

    click.echo(f"\n  Balance Sheet - {today}")
    click.echo(hr())

    if assets:
        click.echo("  ASSETS")
        for name, cat, amt in assets:
            click.echo(f"    {name:<20} {cat:<16} {fmt(amt):>12}")
        click.echo(hr())
        click.echo(f"  {'Total Assets':<37} {fmt(total_a):>12}")

    if liabilities:
        click.echo()
        click.echo("  LIABILITIES")
        for name, cat, amt in liabilities:
            click.echo(f"    {name:<20} {cat:<16} {fmt(amt):>12}")
        click.echo(hr())
        click.echo(f"  {'Total Liabilities':<37} {fmt(total_l):>12}")

    click.echo(hr())
    sign = "+" if net >= 0 else ""
    click.echo(f"  {'NET WORTH':<37} {sign}{fmt(net):>12}")
    click.echo()


def _net():
    today = date.today().isoformat()
    with get_db() as conn:
        assets, liabilities = net_worth_on(conn, today)
    net  = assets - liabilities
    sign = "+" if net >= 0 else ""
    click.echo(f"\n  Net worth  {sign}{fmt(net)}")
    click.echo(f"  Assets     {fmt(assets)}   Liabilities  {fmt(liabilities)}")
    click.echo()


def _history(rest: tuple):
    if not rest:
        click.echo("  Usage: balance history ACCOUNT")
        return
    name = rest[0].lower()
    with get_db() as conn:
        account = get_account(conn, name)
        if not account:
            click.echo(f"  Unknown account: {name}")
            return
        rows = conn.execute(
            "SELECT date, amount, note FROM balances WHERE account_id=? ORDER BY ts",
            (account[0],),
        ).fetchall()

    if not rows:
        click.echo(f"\n  No balances recorded for {name}.\n")
        return

    values = [r[1] for r in rows]
    tc     = f"{account[2]}/{account[3]}" if account[3] else account[2]

    click.echo(f"\n  {name}  ({tc})")
    click.echo(hr())
    for d, amt, note in rows:
        n_str = f"  {note}" if note else ""
        click.echo(f"  {d}   {fmt(amt):>12}{n_str}")
    click.echo()
    click.echo(f"  trend  {sparkline(values)}")
    click.echo()


def _trend(rest: tuple):
    days   = int(rest[0]) if rest and rest[0].isdigit() else 90
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    with get_db() as conn:
        dates = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT date FROM balances WHERE date>=? ORDER BY date",
                (cutoff,),
            ).fetchall()
        ]
        if not dates:
            click.echo(f"\n  No data in last {days} days.\n")
            return

        net_worths = []
        for d in dates:
            assets, liabilities = net_worth_on(conn, d)
            net_worths.append((d, assets - liabilities))

    values = [nw for _, nw in net_worths]
    click.echo(f"\n  Net worth trend - last {days} days")
    click.echo(hr())
    click.echo(f"  trend  {sparkline(values)}")
    click.echo()
    for d, nw in net_worths:
        sign = "+" if nw >= 0 else ""
        click.echo(f"  {d}   {sign}{fmt(nw):>12}")
    click.echo()


def _accounts():
    today = date.today().isoformat()
    with get_db() as conn:
        accounts = conn.execute(
            "SELECT id, name, type, category FROM accounts ORDER BY type DESC, category, name"
        ).fetchall()

    if not accounts:
        click.echo("\n  No accounts yet.\n")
        return

    click.echo("\n  Accounts")
    click.echo(hr())
    for acc_id, name, acc_type, category in accounts:
        with get_db() as conn:
            row = conn.execute(
                "SELECT amount, date FROM balances WHERE account_id=? ORDER BY ts DESC LIMIT 1",
                (acc_id,),
            ).fetchone()
        tc     = f"{acc_type}/{category}" if category else acc_type
        amt    = fmt(row[0]) if row else "—"
        last   = row[1] if row else "never"
        click.echo(f"  {name:<20} {tc:<22} {amt:>12}   updated {last}")
    click.echo()


def _undo():
    with get_db() as conn:
        row = conn.execute(
            "SELECT b.id, a.name, b.amount, b.ts FROM balances b "
            "JOIN accounts a ON a.id = b.account_id ORDER BY b.ts DESC LIMIT 1"
        ).fetchone()
        if not row:
            click.echo("  Nothing to undo.")
            return
        b_id, name, amount, ts = row
        conn.execute("DELETE FROM balances WHERE id=?", (b_id,))
    click.echo(f"  Removed: {name} {fmt(amount)} @ {ts[:16]}")


def _help():
    click.echo("""
  balance - personal balance sheet tracker
  ------------------------------------------------
  LOGGING
    balance ACCOUNT AMOUNT [type/category] [note]   set account balance
    balance undo                                     remove last entry

    On first use, type/category is required:
      asset/cash  asset/investment  asset/retirement
      asset/property  asset/vehicle
      liability/loan  liability/credit  liability/mortgage

  VIEWING
    balance                  full balance sheet
    balance sheet            full balance sheet
    balance net              net worth summary
    balance accounts         all accounts + last updated
    balance history ACCOUNT  balance history for one account
    balance trend [days]     net worth over time (default 90d)
    balance help             this message

  EXAMPLES
    balance checking 5200 asset/cash
    balance savings 12000 asset/cash
    balance 401k 48000 asset/retirement
    balance mortgage 284000 liability/mortgage
    balance visa 1400 liability/credit after groceries
    balance checking 5450
    balance sheet
    balance history checking
    balance trend 180
""")


# --- Entry point -------------------------------------------------------------

@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def balance(args):
    """Personal balance sheet tracker."""
    if not args:
        _sheet()
        return

    subcmd = args[0].lower()

    if subcmd == "sheet":
        _sheet()
    elif subcmd == "net":
        _net()
    elif subcmd == "history":
        _history(args[1:])
    elif subcmd == "trend":
        _trend(args[1:])
    elif subcmd == "accounts":
        _accounts()
    elif subcmd == "undo":
        _undo()
    elif subcmd == "help":
        _help()
    else:
        # balance ACCOUNT AMOUNT [type/cat] [note...]
        if len(args) < 2:
            click.echo("  Usage: balance ACCOUNT AMOUNT [type/category] [note]")
            return
        try:
            amount = float(args[1])
        except ValueError:
            click.echo(f"  Expected a number for amount, got: '{args[1]}'")
            return

        # third arg is type/category if it contains / or is asset/liability
        type_cat = None
        note_start = 2
        if len(args) > 2:
            third = args[2]
            if "/" in third or third.lower() in ("asset", "liability"):
                type_cat   = third
                note_start = 3

        note = " ".join(args[note_start:]) or None
        set_balance(args[0], amount, type_cat, note)
