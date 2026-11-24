# Proposal

## Why

The balance history only holds the days with transactions, so weekends, holidays and periods without exports are missing, and the export cannot be charted or compared as a continuous series. Filling the days in makes the balance readable day by day, and leaving the unexplained periods empty keeps the discrepancies visible instead of hiding them.

## What Changes

- The balance history can produce a continuous daily series per account between two dates: one entry per calendar day, whether or not it has transactions.
- A day without transactions between two days that follow each other without a gap carries the previous end balance (start and end balances equal to it).
- A day without transactions inside a gap, before the account's first day or after its last day has no balance (empty, not a sentinel value).
- The `balance` command gets optional `--from` and `--to` dates (`YYYY-MM-DD`); without them each account goes from its own first to its last day with transactions.
- **BREAKING**: the balance CSV export becomes the daily series: one row per account and calendar day of the range instead of one row per day with transactions. Filled rows have a transaction count of 0 and an empty source file; real days can still be told apart with `transaction_count`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-balance-history`: adds the daily series requirement, the `--from` / `--to` options of the balance command, and changes the CSV export to one row per calendar day.

## Impact

- `src/services/bank_balance.py`: new daily series method, account labels kept per account.
- `src/services/bank_balance_to_csv.py`: writes the daily series, no longer reads the first transaction of a day for the account label.
- `src/bilig-cli.py`: `balance` command gets `--from` / `--to`.
- Tests in `src/tests/test_bank_balance.py` and `src/tests/test_bank_balance_to_csv.py`; `AGENTS.md` run commands and balance history section.
- Anyone reading the balance CSV gets more rows, including rows with empty balances.
