# balance

Personal balance sheet tracker. Set account balances as they change — assets and liabilities — and track your net worth over time. Update-in-place with full history preserved. SQLite-backed, pip-installable, zero dependencies beyond `click`.

## Install

```bash
pip install git+https://github.com/spinchange/balance
```

To update:

```bash
pip install --upgrade git+https://github.com/spinchange/balance
```

Or for local development:

```bash
pip install -e .
```

Requires Python 3.10+.

---

## Quick Start

```bash
# Set up accounts (type required on first use)
balance checking 5200 asset/cash
balance savings 12000 asset/cash
balance 401k 48000 asset/retirement
balance mortgage 284000 liability/mortgage
balance visa 1400 liability/credit

# View the full balance sheet
balance

# Update a balance (type not needed after first time)
balance checking 5450

# See net worth trend
balance trend 90
```

---

## Usage

### Setting Balances

```
balance ACCOUNT AMOUNT [type/category] [note]   set account balance
balance undo                                     remove last entry
```

Account names are lowercased automatically. On first use, `type/category` is required. After that, just provide the new amount.

```bash
balance checking 5200 asset/cash
balance savings 12000 asset/cash
balance brokerage 34000 asset/investment
balance 401k 48000 asset/retirement
balance home 420000 asset/property
balance car 18000 asset/vehicle
balance mortgage 284000 liability/mortgage
balance carloan 14500 liability/loan
balance visa 1400 liability/credit after groceries
```

When updating an existing account, the change from the previous balance is shown:

```
  checking             $5,450.00   +$250.00
```

### Account Types

| Type | Categories |
|------|------------|
| `asset` | `cash`, `investment`, `retirement`, `property`, `vehicle` |
| `liability` | `loan`, `credit`, `mortgage` |

### Viewing

```
balance                  full balance sheet (default)
balance sheet            full balance sheet
balance net              net worth one-liner
balance accounts         all accounts + last updated date
balance history ACCOUNT  every recorded balance for one account
balance trend [days]     net worth over time (default 90 days)
balance help             command reference
```

### Balance Sheet

```
  Balance Sheet - 2026-03-19
  ------------------------------------------------
  ASSETS
    checking             cash               $5,450.00
    savings              cash              $12,000.00
    brokerage            investment        $34,000.00
    401k                 retirement        $48,000.00
    home                 property         $420,000.00
  ------------------------------------------------
  Total Assets                            $519,450.00

  LIABILITIES
    mortgage             mortgage         $284,000.00
    visa                 credit             $1,400.00
  ------------------------------------------------
  Total Liabilities                       $285,400.00

  ------------------------------------------------
  NET WORTH                              +$234,050.00
```

### Net Worth Summary

```bash
balance net
```

```
  Net worth  +$234,050.00
  Assets     $519,450.00   Liabilities  $285,400.00
```

### Account History

```bash
balance history checking
```

```
  checking  (asset/cash)
  ------------------------------------------------
  2026-01-15    $4,800.00
  2026-02-01    $5,200.00
  2026-03-01    $5,200.00
  2026-03-19    $5,450.00

  trend  ._-#
```

### Net Worth Trend

```bash
balance trend 180
```

Shows net worth on every date where any balance was recorded, with an ASCII sparkline.

---

## Data

Everything is stored in `~/.balance/`:

```
~/.balance/
  balance.db    SQLite database (accounts + balances)
```

The database is a plain SQLite file — open it with any SQLite browser if you need to inspect or export data directly.

Schema:

```sql
accounts (id, name, type, category, created)
balances (id, account_id, amount, ts, date, note)
```

Every update is a new row in `balances` — no data is ever overwritten. `balance history` shows the full log; views always use the most recent balance per account.

---

## Workflow

Balance is designed for periodic updates — weekly, monthly, or whenever you check your accounts. It's not a transaction ledger. Just set the current balance and move on.

```bash
# Monthly check-in
balance checking 5450
balance savings 12200
balance 401k 49100
balance visa 820
balance net
balance trend
```

To remove a mistaken entry:

```bash
balance undo
```

---

## Examples

```bash
# First-time setup
balance checking 5200 asset/cash
balance savings 12000 asset/cash
balance 401k 48000 asset/retirement
balance brokerage 34000 asset/investment
balance home 420000 asset/property
balance mortgage 284000 liability/mortgage
balance visa 1400 liability/credit

# View everything
balance

# Monthly update
balance checking 5450
balance visa 820
balance 401k 49100
balance net

# Inspect one account
balance history 401k

# 6-month net worth trend
balance trend 180

# Fix a typo
balance undo
```

---

## License

MIT
