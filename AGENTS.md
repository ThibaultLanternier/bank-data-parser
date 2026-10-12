# bilig

CLI tool for extracting and processing bank transaction data from Boursobank CSV, OFX and QIF files.

## Run commands

- Extract transactions: `python src/bilig-cli.py extract [data/boursobank] [--file-type ofx|qif|csv] [--groups data/groups.yaml]` (default `ofx`)
- Monthly report (first and last date, income, expenses, transfers between accounts, transactions count, accounts): `python src/bilig-cli.py report [data/boursobank] [--file-type ofx|qif|csv]` (default `ofx`)
- Assign groups interactively: `python src/bilig-cli.py categorize [data/boursobank] [--file-type ofx|qif|csv] [--groups data/groups.yaml]` reviews the clusters with ungrouped transactions (largest total amount first), asks a pattern (pre-filled with the cluster label) and a group (autocomplete, new name creates it); each answer is saved immediately, skip / undo / quit (or Ctrl+C) available
- Run tests: `pytest`
- Lint: `make lint` (ruff, configured in `pyproject.toml`, fixes what it can)
- Install dependencies: `poetry install`

## Project structure

- `src/bilig-cli.py` — CLI entry point (uses click)
- `src/entities/` — data classes: `transaction`, `Account`, `Category`, `Group`, `Label`, `SourceType`
- `src/services/` — business logic: `CsvBankDataReader`, `OfxBankDataReader`, `QifBankDataReader`, `FileReader`, `FileRecorder`, `TransactionGrouper`, `GroupsFile`, `GroupMatcher`, `CategorizeSession`
- `src/output/` — generated CSV files (gitignored)

## CSV format

- Input: semicolon-delimited, UTF-8-sig encoding
- French number format: spaces as thousands separator, comma as decimal
- Date format: `%Y-%m-%d`
- Pipe-separated label parts (raw label before `|`, normalized after)

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
