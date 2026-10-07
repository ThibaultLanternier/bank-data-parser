# bilig

CLI tool for extracting and processing bank transaction data from Boursobank CSV, OFX and QIF files.

## Run commands

- Extract transactions: `python src/bilig-cli.py extract [data/boursobank] [--file-type ofx|qif|csv]` (default `ofx`)
- Monthly report (income, expenses, transactions count, accounts): `python src/bilig-cli.py report [data/boursobank] [--file-type ofx|qif|csv]` (default `ofx`)
- Run tests: `pytest`
- Install dependencies: `poetry install`

## Project structure

- `src/bilig-cli.py` — CLI entry point (uses click)
- `src/entities/` — data classes: `transaction`, `Account`, `Category`, `Label`, `SourceType`
- `src/services/` — business logic: `CsvBankDataReader`, `OfxBankDataReader`, `QifBankDataReader`, `FileReader`, `FileRecorder`, `TransactionGrouper`
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

## Conventions

- Use `poetry run` to execute CLI and test commands
- Classes use PascalCase (`CsvBankDataReader`, `TransactionType`)
- Functions use snake_case (`get_label()`, `_parse_amount()`)
- `transaction` entity is lowercase (non-PEP8 intentional)
