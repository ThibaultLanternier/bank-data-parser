# Spec Delta

## ADDED Requirements

### Requirement: Daily series range
The balance history SHALL produce, for each account, one day per calendar day between a start and an end date, both included. A day with transactions SHALL be the kept day record, a day without transactions SHALL have no transactions and a total of zero. Without a start date, an account SHALL start at its first day with transactions; without an end date, it SHALL end at its last day with transactions.

#### Scenario: Weekend filled in
- **WHEN** account A has transactions on Friday 2026-09-04 and Monday 2026-09-07 and no dates are given
- **THEN** the series of account A has 4 days, from 2026-09-04 to 2026-09-07, Saturday and Sunday without transactions

#### Scenario: Range given
- **WHEN** account A has transactions from 2026-01-05 to 2026-06-30 and the range is 2026-03-01 to 2026-03-31
- **THEN** the series of account A has the 31 days of March 2026 only

#### Scenario: Each account its own range
- **WHEN** no dates are given, account A has transactions from 2025-01-02 and account B from 2026-02-10
- **THEN** the series of account A starts on 2025-01-02 and the series of account B on 2026-02-10

### Requirement: Balance of days without transactions
A day without transactions between two days with transactions SHALL have its start and end balances equal to the previous day's end balance, unless a gap is reported on the next day with transactions; then, and when the previous end balance is unknown, both balances SHALL be unknown. A day without transactions before the account's first day or after its last day with transactions SHALL have unknown balances.

#### Scenario: No gap
- **WHEN** Friday ends at 1000.00, Monday starts at 1000.00 and no gap is reported
- **THEN** Saturday and Sunday start and end at 1000.00

#### Scenario: Gap
- **WHEN** 2022-12-30 ends at 10105.11 and a gap is reported on 2023-01-02, which starts at 10109.10
- **THEN** 2022-12-31 and 2023-01-01 have unknown start and end balances

#### Scenario: Next day inferred
- **WHEN** Friday ends at 1000.00 and Monday's end balance is inferred
- **THEN** Saturday and Sunday start and end at 1000.00

#### Scenario: Outside the history
- **WHEN** the range starts 3 days before the first day of account A and ends 5 days after its last day
- **THEN** these 8 days have unknown start and end balances

### Requirement: Missing data periods
The balance history SHALL report, for each account, the periods of consecutive days of its daily series whose end balance is unknown, each as a first and a last day, both included, in date order; an account without such a day SHALL not be reported. The `balance` command SHALL print each period as `Account: <account number> missing data between <first day> and <last day>`, for the range given by `--from` and `--to`.

#### Scenario: Gap between two days
- **WHEN** account A has a gap reported on 2023-01-02, the previous day with transactions being 2022-12-30
- **THEN** account A is missing data between 2022-12-31 and 2023-01-01

#### Scenario: Range beyond the history
- **WHEN** the range is 2026-01-01 to 2026-12-31 and the days of account A with transactions go from 2026-01-01 to 2026-11-30 without gap
- **THEN** account A is missing data between 2026-12-01 and 2026-12-31

#### Scenario: Several periods
- **WHEN** account A has two gaps
- **THEN** both periods are reported for account A, the earliest first

#### Scenario: Complete history
- **WHEN** every day of account B's series has a known end balance
- **THEN** account B is not reported

#### Scenario: Unknown balance on days with transactions
- **WHEN** the first day of account A with transactions has an unknown balance, and so has the next day without transactions
- **THEN** both days are in the same missing data period

#### Scenario: Gap between consecutive days
- **WHEN** a gap is reported on Tuesday and Monday has transactions
- **THEN** no missing data period is reported for it, the gap itself being printed

## MODIFIED Requirements

### Requirement: Balance command
The CLI SHALL provide a `balance` command taking an input path (default `data/boursobank`) and optional `--from` and `--to` dates (`YYYY-MM-DD`) bounding the daily series. It SHALL read the CSV files of that path only, build the balance history, print for each account the first and last day, the number of inferred days and of days without balance, then each conflict and each gap with its missing amount, and write the daily series as a CSV file. The printed summary SHALL count the days with transactions only. It SHALL fail when no CSV transaction is found or when `--from` is after `--to`.

#### Scenario: History with a gap
- **WHEN** the user runs `bilig balance data/boursobank` and the CSV files miss a 3.99 transaction between 2022-12-30 and 2023-01-02
- **THEN** the gap between 2022-12-30 and 2023-01-02 is printed with 3,99 € missing, and the path of the written CSV file is printed

#### Scenario: Only CSV files are read
- **WHEN** the input path holds OFX and QIF files but no CSV file
- **THEN** the command fails saying no transactions were found in CSV files

#### Scenario: Range given
- **WHEN** the user runs `bilig balance data/boursobank --from 2026-03-01 --to 2026-03-31`
- **THEN** the written CSV file holds, for each account, the 31 days of March 2026 only

#### Scenario: Invalid range
- **WHEN** the user runs `bilig balance --from 2026-04-01 --to 2026-03-01`
- **THEN** the command fails saying the start date is after the end date

#### Scenario: Summary ignores filled days
- **WHEN** account A has 10 days with transactions spread over 20 calendar days
- **THEN** the summary prints 10 days for account A, and filled days are not counted as days without balance

### Requirement: Balance history CSV export
The balance history SHALL be written as a semicolon-delimited UTF-8 CSV file with one row per account and day of the daily series, ordered by account then date, with the columns `account_number`, `account_label`, `date`, `start_balance`, `total`, `end_balance`, `transaction_count`, `is_inferred`, `gap`, `conflict` and `source_file`. Amounts SHALL use a comma as decimal separator and unknown balances SHALL be empty. A day without transactions SHALL have the account label, a `total` of `0,00`, a `transaction_count` of 0 and empty `is_inferred`, `gap`, `conflict` and `source_file`.

#### Scenario: Day with a gap
- **WHEN** 2023-01-02 starts at 10109.10 while 2022-12-30 ended at 10105.11
- **THEN** the 2023-01-02 row has `start_balance` `10109,10` and `gap` `3,99`, and the 2022-12-30 row has an empty `gap`

#### Scenario: Inferred day
- **WHEN** a day's end balance is inferred
- **THEN** its row has `INFERRED` in `is_inferred`

#### Scenario: Conflicting day
- **WHEN** two files have a different version of the same day with as many transactions
- **THEN** the kept day's row has `CONFLICT` in `conflict` and the `source_file` of the version kept

#### Scenario: Filled day
- **WHEN** Saturday has no transaction and Friday ended at 1000.00 with no gap before Monday
- **THEN** the Saturday row has the account label, `start_balance` and `end_balance` `1000,00`, `total` `0,00`, `transaction_count` 0 and an empty `source_file`

#### Scenario: Day in a gap
- **WHEN** 2022-12-31 has no transaction and a gap is reported on 2023-01-02
- **THEN** the 2022-12-31 row has empty `start_balance` and `end_balance`
