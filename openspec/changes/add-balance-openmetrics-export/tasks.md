# Tasks

## 1. OpenMetrics writer

- [ ] 1.1 Add `BankBalanceToOpenMetrics` in `src/services/bank_balance_to_openmetrics.py` writing the `HELP` / `TYPE` / `UNIT` header, one series per account labelled `account` and `account_label` (from `get_account_label`), samples ordered by time, and `# EOF`; verify with `src/tests/test_bank_balance_to_openmetrics.py` covering the header, the series order and the exact sample lines, run with `poetry run pytest`
- [ ] 1.2 Write one sample per day with a known end balance, value with two decimals and a dot, timestamp at 00:00 UTC of the next day in seconds, no sample for unknown balances; verify with tests for a known day (`1523.45 1704153600`), a filled day, the days of a gap left out and a negative balance
- [ ] 1.3 Escape `\`, `"` and newline in label values and keep `account_label=""` for an account without label; verify with tests on a label holding a quote and a backslash and on an account without label
- [ ] 1.4 Honour `date_from` / `date_to` and the default `balance_<timestamp>.om` name in `file_recorder.OUTPUT_DIR`; verify with tests on a range and on the default path
- [ ] 1.5 Add `BankBalanceToOpenMetrics` to the services list in AGENTS.md and verify it reads as written

## 2. Balance command option

- [ ] 2.1 Add the `--openmetrics` flag to the `balance` command in `src/bilig-cli.py`, writing the OpenMetrics file with the same range as the CSV and printing its path; verify with `src/tests/test_bilig_cli.py` tests: flag given (both files written, both paths printed), flag with `--from` / `--to`, flag not given (no `.om` file)
- [ ] 2.2 Document the flag in the AGENTS.md balance command, plus the import (`promtool tsdb create-blocks-from openmetrics --max-block-duration=8760h <file> <data dir>`, Prometheus retention longer than the history) and the Grafana stacked panel (`last_over_time(bank_account_balance_euros[1d])`, legend `{{account_label}} ({{account}})`, stack Normal); verify the documented command line matches `poetry run python src/bilig-cli.py balance --help`

## 3. Integration check

- [ ] 3.1 Run `poetry run python src/bilig-cli.py balance data/boursobank --openmetrics` on the real data and, if `promtool` is available, `promtool tsdb create-blocks-from openmetrics --max-block-duration=8760h <file> <tmp dir>`; verify the import succeeds without errors, otherwise check the file ends with `# EOF` and timestamps increase per series
- [ ] 3.2 Run `make lint` and `poetry run pytest`; verify both are clean

## Workflow follow-up

- Open the PR against `develop`.
- Archive the change after review, syncing the `account-balance-history` spec.
