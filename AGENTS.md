# bilig

CLI tool for extracting and processing bank transaction data from Boursobank CSV and QIF files.

## Run commands

- Extract transactions: `python src/bilig-cli.py extract [data/boursobank]`
- Run tests: `pytest`
- Install dependencies: `poetry install`

## Project structure

- `src/bilig-cli.py` — CLI entry point (uses click)
- `src/entities/` — data classes: `transaction`, `Account`, `Category`, `Label`, `SourceType`
- `src/services/` — business logic: `CsvBankDataReader`, `QIFBankDataReader`, `FileReader`, `FileRecorder`
- `src/output/` — generated CSV files (gitignored)

## CSV format

- Input: semicolon-delimited, UTF-8-sig encoding
- French number format: spaces as thousands separator, comma as decimal
- Date format: `%Y-%m-%d`
- Pipe-separated label parts (raw label before `|`, normalized after)

## QIF format

- `!Type:Bank` sections, records terminated by `^`
- Dates are day first (`dd/mm/yyyy`), amounts use `.` as decimal separator
- No account information unless an `!Account` block is present (falls back to `UNKNOWN`)
- Payee (`P`) is used for both label parts (`payee | payee`)

## Conventions

- Use `poetry run` to execute CLI and test commands
- Classes use PascalCase (`CsvBankDataReader`, `TransactionType`)
- Functions use snake_case (`get_label()`, `_parse_amount()`)
- `transaction` entity is lowercase (non-PEP8 intentional)
