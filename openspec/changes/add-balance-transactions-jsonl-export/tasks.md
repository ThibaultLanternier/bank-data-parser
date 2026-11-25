# Tasks

## 1. Bank label

- [x] 1.1 Add `Label.get_bank_label()` returning the part after `|` (the whole label without `|`) with spaces trimmed and collapsed; verify with tests in `src/tests/test_label.py` for a `suggested | bank` label, a label without `|` and a label with repeated spaces, run with `poetry run pytest`

## 2. JSON lines writer

- [x] 2.1 Add `BankBalanceTransactionsToJsonl` in `src/services/bank_balance_transactions_to_jsonl.py` writing one line per transaction of the daily series, keys in the spec order, `ensure_ascii=False`, ordered by account then `date_value` (stable); verify with `src/tests/test_bank_balance_transactions_to_jsonl.py` covering the exact line of a card payment, `null` balance, non ASCII label, ordering across accounts and days, no line for filled days, and only the kept day record of overlapping files
- [x] 2.2 Compute the export `id` (account, operation date, value date, amount with 2 decimals, bank label, occurrence index); verify with tests: identical payments of a day get different ids, the same transaction from two files or with another suggested label or other spacing gets the same id and the same line
- [x] 2.3 Honour `date_from` / `date_to` and the default `balance_<timestamp>.jsonl` name in `file_recorder.OUTPUT_DIR`; verify with tests on a range and on the default path
- [ ] 2.4 Add `*.jsonl` to `src/output/.gitignore` and `BankBalanceTransactionsToJsonl` to the AGENTS.md services list; verify `git check-ignore src/output/x.jsonl` matches and the existing `*.csv`, `*.parquet`, `*.om` patterns still do

## 3. Balance command

- [ ] 3.1 Write the JSON lines file with `--openmetrics` in `src/bilig-cli.py` (same range, path printed) and update the flag help text; verify with `src/tests/test_bilig_cli.py` tests: flag given (three files and paths), flag with `--from` / `--to`, flag not given (no `.jsonl` file)
- [ ] 3.2 Document in AGENTS.md the JSON lines file (fields, id, timestamp), the Alloy pipeline (`local.file_match`, `loki.source.file`, `loki.process` with `stage.json`, `stage.timestamp` RFC3339, `stage.labels` account, `stage.label_drop` filename), the Loki limits (`reject_old_samples: false`, retention) and the old gap limitation; verify the documented options match `poetry run python src/bilig-cli.py balance --help`

## 4. Integration check

- [ ] 4.1 Run `poetry run python src/bilig-cli.py balance data/boursobank --openmetrics` on the real data; verify every line parses as JSON, ids are unique, timestamps increase per account, and running it twice gives byte-identical `.jsonl` files
- [ ] 4.2 Run `make lint` and `poetry run pytest`; verify both are clean

## Workflow follow-up

- Archive `add-balance-openmetrics-export` before or with this change so the main spec holds the OpenMetrics requirements.
- Open the PR against `develop` with a reference to its issue.
- Archive this change after review.
