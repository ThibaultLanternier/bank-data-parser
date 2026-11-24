# bilig

CLI tool for extracting and processing bank transaction data from Boursobank CSV, OFX and QIF files.

## Run commands

- Extract transactions: `python src/bilig-cli.py extract [data/boursobank] [--file-type ofx|qif|csv] [--groups data/groups.yaml]` (default `ofx`)
- Monthly report (first and last date, income, expenses, transfers between accounts, transactions count, accounts): `python src/bilig-cli.py report [data/boursobank] [--file-type ofx|qif|csv]` (default `ofx`)
- Assign groups interactively: `python src/bilig-cli.py categorize [data/boursobank] [--file-type ofx|qif|csv] [--groups data/groups.yaml]` reviews the clusters with ungrouped transactions (largest total amount first), internal transactions (transfers between accounts) are never asked about but are shown tagged `[internal]` in the reviewed clusters, asks a pattern (pre-filled with the cluster label) and a group (autocomplete, new name creates it); each answer is saved immediately, skip / undo / quit (or Ctrl+C) available
- Balance history: `python src/bilig-cli.py balance [data/boursobank] [--from YYYY-MM-DD] [--to YYYY-MM-DD]` reads the CSV files only (the only ones with a balance), prints per account the days with transactions, the inferred days, the conflicts and the gaps (whole history), and writes the daily series to `src/output/balance_<timestamp>.csv` (`BankBalanceToCSV`): one row per account and calendar day from `--from` to `--to` (default: each account's first and last day with transactions), days without transactions having a `transaction_count` of 0 and empty balances when unknown
- Run tests: `pytest`
- Lint: `make lint` (ruff, configured in `pyproject.toml`, fixes what it can)
- Install dependencies: `poetry install`

## Project structure

- `src/bilig-cli.py` — CLI entry point (uses click)
- `src/entities/` — data classes: `transaction`, `Account`, `Category`, `DayTransactions`, `Group`, `Label`, `SourceType`
- `src/services/` — business logic: `CsvBankDataReader`, `OfxBankDataReader`, `QifBankDataReader`, `FileReader`, `FileRecorder`, `TransactionGrouper`, `GroupsFile`, `GroupMatcher`, `CategorizeSession`, `BankBalance`, `BankBalanceToCSV`
- `src/output/` — generated CSV files (gitignored)

## CSV format

- Input: semicolon-delimited, UTF-8-sig encoding
- French number format: spaces as thousands separator, comma as decimal
- Date format: `%Y-%m-%d`
- Pipe-separated label parts (raw label before `|`, normalized after)
- Account balance (`accountbalance` in the old format, second `Solde` in the new one) is kept in `transaction.balance`: the account balance at the end of the row's value date (00:00 the next day), `None` when empty. OFX and QIF transactions have no balance

## OFX format

- OFX 2.x (XML) only, parsed with `xml.etree.ElementTree`; OFX 1.x (SGML) is not supported
- Bank (`STMTRS`) and credit card (`CCSTMTRS`) statements are read
- `NAME` (+ `MEMO`) is turned into a `Label` as `"<name> | <name>"` to reuse CSV label parsing
- `FITID` / `TRNTYPE` are stored in `bank_transaction_id` / `bank_transaction_type`
- Duplicates (same `ACCTID` + `FITID`, e.g. overlapping exports) are removed, first occurrence is kept; transactions without `FITID` are never deduplicated
- No category nor account label in OFX: category is empty, account label is the `ACCTID`
- Boursobank fills `DTUSER` with invalid values: falls back to `DTPOSTED`

## QIF format

- Only non-investment sections are read (`!Type:Bank`, `Cash`, `CCard`, `Oth A`, `Oth L`)
- Dates are read as `DD/MM/YYYY` (Boursobank), `DD/MM/YY` and `DD/MM'YY` are also accepted
- UTF-8 encoding, falls back to windows-1252
- `P` (+ `M`) is turned into a `Label` as `"<payee> | <payee>"`, same as OFX
- `L` is the category, `Parent:Sub` is split into parent and category
- `N` (check / reference number) is stored in `bank_transaction_id`
- Only the first value of a field is kept, split lines (`S`, `E`, `$`) are ignored
- No value date in QIF: value date is the transaction date
- Account comes from the `!Account` header `N` field, otherwise the file name (without extension)

## Balance history

- Built from CSV files only (OFX and QIF have no balance per transaction), from the reader output and not the enhanced list, whose deduplication by id would merge identical rows of a day
- `DayTransactions.from_transactions()` makes one day record per account, operation date (00:00) and source file
- `BankBalance` keeps one day record per account and day: the one with the most transactions wins; a tie with different amounts keeps the first one read and is reported in `conflicts`
- End of day balance: the balance of a kept transaction whose value date is that day (a late-booked transaction gives the balance of an earlier day); otherwise previous end + the day's transactions, flagged `is_inferred`; unknown when there is no previous end. Start balance = end - the day's transactions. Compared to the cent
- `gaps`: a `BalanceGap` (account, previous day, day, missing amount) when a non-inferred day starts at a different balance than the previous day ended, meaning transactions are missing. Days without transactions are not gaps
- `get_daily_series(from, to)`: one `DayTransactions` per account and calendar day, bounds included (default: the account's first and last day with transactions). Days with transactions are the kept records; a day without transactions is an empty record whose start and end balances are the previous end balance when the next day with transactions has no gap, `None` inside a gap, after an unknown balance, before the first day or after the last day

## Groups

- User groups (`SALARY`, `SCHOOL`...) live in `data/groups.yaml` (gitignored, `--groups` to use another file), unrelated to the bank `Category`
- YAML mapping of group name to a list of label patterns:

  ```yaml
  # first matching group wins: put specific patterns first
  SUBSCRIPTIONS:
    - amazon prime
  SHOPPING:
    - amazon
  ```

- A pattern matches when it is a substring of `Label.get_normalized_label()` (case and accent insensitive)
- Matching is per label cluster: a direct match always wins; transactions without direct match inherit the group only when all direct matches of the cluster agree, otherwise the cluster is a conflict and nothing is inherited
- Output columns `group` and `group_source` (`direct`, `cluster` or empty)
- Missing file means no group; the file is written in round-trip mode (comments and order kept)

## Conventions

- Use `poetry run` to execute CLI and test commands
- Classes use PascalCase (`CsvBankDataReader`, `TransactionType`)
- Functions use snake_case (`get_label()`, `_parse_amount()`)
- `transaction` entity is lowercase (non-PEP8 intentional)
