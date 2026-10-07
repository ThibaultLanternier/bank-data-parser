# bilig

CLI tool for extracting and processing bank transaction data from Boursobank CSV and OFX files.

## Run commands

- Extract transactions: `python src/bilig-cli.py extract [data/boursobank]`
- Run tests: `pytest`
- Install dependencies: `poetry install`

## Project structure

- `src/bilig-cli.py` — CLI entry point (uses click)
- `src/entities/` — data classes: `transaction`, `Account`, `Category`, `Label`, `SourceType`
- `src/services/` — business logic: `CsvBankDataReader`, `OfxBankDataReader`, `FileReader`, `FileRecorder`
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
- No category nor account label in OFX: category is empty, account label is the `ACCTID`
- Boursobank fills `DTUSER` with invalid values: falls back to `DTPOSTED`

## Conventions

- Use `poetry run` to execute CLI and test commands
- Classes use PascalCase (`CsvBankDataReader`, `TransactionType`)
- Functions use snake_case (`get_label()`, `_parse_amount()`)
- `transaction` entity is lowercase (non-PEP8 intentional)
