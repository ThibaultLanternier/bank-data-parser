# Proposal

## Why

Boursobank CSV exports have an account balance on every row, but the reader drops it, so there is no way to follow how each account balance changes over time. That balance can also tell whether the exported transactions are complete: if the balance moves by more than the transactions of a day, something is missing.

## What Changes

- The CSV reader keeps the account balance of each row (both the old `accountbalance` and the new second `Solde` columns), for the value date of the row.
- Transactions are grouped into day records: one per account, per day (operation date, 00:00) and per source file. A day record holds its transactions and its start and end of day balances, which are optional.
- A balance history takes the day records of all CSV files and:
  - deduplicates them per account and day: when several files have the same day, the version with more transactions wins;
  - resolves each day's end balance from the balances read for that value date, otherwise infers it from the previous day;
  - orders the days of each account and reports every gap, meaning a day whose start balance differs from the previous day's end balance, with the missing amount.
- OFX and QIF files have no balance per transaction and are not used for the balance history.

## Capabilities

### New Capabilities
- `account-balance-history`: day by day balance of each bank account built from the CSV exports, with deduplication across files and detection of gaps (missing transactions).

### Modified Capabilities

## Impact

- `src/services/csv_bank_data_reader.py`: reads the balance column instead of dropping it.
- `src/entities/transaction.py`: gets an optional balance (`None` for OFX and QIF).
- New entity for the day record and new service for the balance history in `src/entities/` and `src/services/`, with unit tests.
- No change to existing outputs (`extract`, `report`, `categorize`). A CLI command to show the history or the gaps is out of scope here.
