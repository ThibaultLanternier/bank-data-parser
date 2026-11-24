# Tasks

## 1. Daily series

- [x] 1.1 Keep `account_number -> account_label` in `BankBalance` from the kept days and expose `get_account_label(account)`; verify with a test in `src/tests/test_bank_balance.py` on two accounts
- [x] 1.2 Add `BankBalance.get_daily_series(date_from=None, date_to=None)` returning one `DayTransactions` per account and calendar day (bounds included, `None` bound = the account's first or last day with transactions), real days being the kept records and other days empty records; verify with tests for a weekend filled in, a given range inside the history, and two accounts with their own default ranges
- [x] 1.3 Set the balances of empty days: previous end balance as start and end when previous and next real days exist and no gap is reported on the next one, `None` otherwise (gap, unknown previous end, before the first day, after the last day); verify with tests for no gap, the 3.99 gap, an inferred next day, and a range extending before and after the history
- [x] 1.4 Describe the daily series in the "Balance history" section of `AGENTS.md` (filling rule, `None` inside gaps and outside the history); verify the section matches the specs

## 2. CSV export

- [x] 2.1 Make `BankBalanceToCSV.write_csv` take `date_from` / `date_to`, write `get_daily_series(date_from, date_to)`, take the label from `get_account_label` and leave `source_file` empty on days without transactions; verify with tests in `src/tests/test_bank_balance_to_csv.py` for a filled day (`0,00` total, count 0, balances carried), a day in a gap (empty balances), and the existing gap, inferred and conflict rows unchanged

## 3. CLI

- [x] 3.1 Add `--from` / `--to` (`YYYY-MM-DD`) to the `balance` command in `src/bilig-cli.py`, fail with a clear message when `--from` is after `--to`, pass the bounds to the CSV writer and keep the summary on the days with transactions; verify with CLI tests (click `CliRunner`) for a given range and an invalid range, or by running `poetry run python src/bilig-cli.py balance data/boursobank --from 2026-03-01 --to 2026-03-31` and checking the CSV holds March 2026 only
- [x] 3.2 Update the `balance` run command in `AGENTS.md` with `--from` / `--to` and the one-row-per-calendar-day output; verify it matches the CLI help

## 4. Integration check

- [x] 4.1 Run `poetry run python src/bilig-cli.py balance data/boursobank` and verify the CSV has one row per calendar day per account, carried balances across weekends, and empty balances on 2022-12-31 and 2023-01-01 of account …9727
- [x] 4.2 Run `poetry run pytest` and `make lint` and verify both pass

## 5. Missing data periods

- [x] 5.1 Add `BankBalance.get_missing_periods(date_from=None, date_to=None)` returning, per account with at least one, the runs of consecutive daily series days with an unknown end balance as `(first, last)`; verify with tests for a gap, a range beyond the history, two periods, a complete history, an unknown first day and a gap between consecutive days
- [x] 5.2 Print `Account: <account> missing data between <first> and <last>` for each period in the `balance` command, using `--from` / `--to`; verify with a CLI test, describe it in `AGENTS.md`, and check on `data/boursobank` that account …9727 reports 2022-12-31 to 2023-01-01 and 2026-04-01 to 2026-08-02
- [x] 5.3 Run `poetry run pytest` and `make lint` and verify both pass

## 6. Account label on day records

- [x] 6.1 Add `account_label` (default empty) to `DayTransactions`, set it in `from_transactions()` and on the filled days of the daily series, and make the CSV writer read it; verify with tests in `src/tests/test_day_transactions.py` and `src/tests/test_bank_balance.py`, `poetry run pytest` and `make lint`

## Workflow follow-up

- Open the PR against `develop`, with the lint fixes in the last commit.
- Archive the change with `/opsx:archive` once the PR is merged, syncing the `account-balance-history` spec.
