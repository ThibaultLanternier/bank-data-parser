# account-balance-history Specification

## Purpose

Follow the balance of each bank account day by day from the CSV exports, and detect the periods where the exported transactions do not explain how the balance moved.

## Requirements

### Requirement: Balance read from CSV exports
The CSV reader SHALL keep the account balance of each row, read from the `accountbalance` column (old format) or the second `Solde` column (new format), in the same number format as amounts. The balance of a row SHALL be the account balance at the end of the row's value date (00:00 the next day). A row with an empty balance, and every OFX or QIF transaction, SHALL have no balance.

#### Scenario: New format balance
- **WHEN** a new format row has `-12,50` in the first `Solde` column and `1 234,56` in the second one
- **THEN** the transaction amount is -12.50 and its balance is 1234.56

#### Scenario: Old format balance
- **WHEN** an old format row has `1234,56` in `accountbalance`
- **THEN** the transaction balance is 1234.56

#### Scenario: No balance
- **WHEN** a transaction is read from an OFX file, or from a CSV row with an empty balance
- **THEN** it has no balance

### Requirement: Day records
Transactions SHALL be grouped into day records, one per account number, per day and per source file. The day of a transaction SHALL be its operation date, the day record starting at 00:00 of that date. A day record SHALL hold the account number, its start date, its transactions and optional start and end of day balances.

#### Scenario: Transactions of the same day
- **WHEN** a file holds three transactions of account A with operation date 2026-09-07, whatever their value dates
- **THEN** they form one day record for account A starting 2026-09-07 00:00

#### Scenario: Same day in two files
- **WHEN** two files both hold transactions of account A on 2026-09-07
- **THEN** each file gives its own day record for that day

#### Scenario: Different accounts
- **WHEN** a file holds transactions of accounts A and B on the same day
- **THEN** there is one day record per account

### Requirement: Deduplication across files
The balance history SHALL take the day records of all CSV files and keep one day record per account and day. When several day records share the same account and day, the one with the most transactions SHALL be kept. When they have the same number of transactions but different amounts, the first one read SHALL be kept and the conflict SHALL be reported.

#### Scenario: Partial day re-exported
- **WHEN** one file has 3 transactions of account A on 2026-09-07 and another file has 5
- **THEN** the day record with 5 transactions is kept

#### Scenario: Identical day in two files
- **WHEN** two files have the same transactions of account A on 2026-09-07
- **THEN** one day record is kept and no conflict is reported

#### Scenario: Tie with different content
- **WHEN** two files have 4 transactions each for account A on 2026-09-07 with different amounts
- **THEN** the first day record read is kept and a conflict is reported for account A on 2026-09-07

### Requirement: End and start of day balances
After deduplication, the end of day balance of a day SHALL be the balance of a kept transaction of the same account whose value date is that day, whichever day record holds it. The start of day balance SHALL be the end balance minus the sum of the day's transactions. Balances SHALL be compared to the cent.

#### Scenario: Balance from the same day
- **WHEN** a transaction on 2026-09-07 has value date 2026-09-07 and balance 15395.57, and the day's transactions sum to -1200.00
- **THEN** the day's end balance is 15395.57 and its start balance is 16595.57

#### Scenario: Balance from a late-booked transaction
- **WHEN** a transaction with operation date 2026-09-07 has value date 2026-09-05 and balance 16777.64
- **THEN** 16777.64 is the end balance of the day 2026-09-05 (or of the last day before it when 2026-09-05 has no transactions), not of 2026-09-07

### Requirement: Inferred balances
When no kept transaction of the account has a day's date as value date, the end balance of that day SHALL be inferred as the previous day's end balance plus the day's transactions, and marked as inferred. When there is no previous end balance, the end and start balances SHALL stay unknown.

#### Scenario: First day without any balance
- **WHEN** the first day of account A has no transaction with its date as value date
- **THEN** its end and start balances are unknown

#### Scenario: Day without any balance
- **WHEN** no kept transaction has value date 2025-07-14, the previous day ends at 1000.00 and the 2025-07-14 transactions sum to -50.00
- **THEN** the end balance of 2025-07-14 is 950.00, marked as inferred

### Requirement: Gap detection
The balance history SHALL order the days of each account by date and report a gap when a day's end balance is not inferred and its start balance differs from the previous day's end balance. A gap SHALL give the account, the previous day, the day and the missing amount (start balance minus previous end balance). Days without transactions SHALL NOT be gaps by themselves.

#### Scenario: Continuous history
- **WHEN** Friday ends at 1000.00 and Monday, the next day with transactions, starts at 1000.00
- **THEN** no gap is reported

#### Scenario: Missing transaction
- **WHEN** 2022-12-30 ends at 10105.11 and 2023-01-02 starts at 10109.10
- **THEN** a gap is reported between 2022-12-30 and 2023-01-02 with a missing amount of 3.99

#### Scenario: Missing period
- **WHEN** the files of account A cover up to 2026-03-31 and again from 2026-08-03, and the balances do not match
- **THEN** a gap is reported between 2026-03-31 and 2026-08-03

#### Scenario: Inferred day
- **WHEN** a day's end balance is inferred
- **THEN** no gap is reported for that day, and the next day is compared with the inferred end balance

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
The balance history SHALL report, for each account, the periods of consecutive days of its daily series whose end balance is unknown, each as a first and a last day, both included, in date order; an account without such a day SHALL not be reported. The `balance` command SHALL print each period as `Account: <account label> (<account number>) missing data between <first day> and <last day>`, or with the account number alone when the account has no label, for the range given by `--from` and `--to`.

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

#### Scenario: Printed with the account label
- **WHEN** account 00040079727, labelled `Compte courant`, is missing data between 2022-12-31 and 2023-01-01
- **THEN** the `balance` command prints `Account: Compte courant (00040079727) missing data between 2022-12-31 and 2023-01-01`

#### Scenario: Gap between consecutive days
- **WHEN** a gap is reported on Tuesday and Monday has transactions
- **THEN** no missing data period is reported for it, the gap itself being printed

### Requirement: Balance history OpenMetrics export
The daily series SHALL be written as an OpenMetrics text file holding one gauge family `bank_account_balance_euros`, with `HELP`, `TYPE` and `UNIT` lines, ended by `# EOF`. Each account SHALL be one series labelled `account` (the account number) and `account_label`, the same label for all its samples. The series SHALL be ordered by account, their samples by increasing time.

#### Scenario: Metric family
- **WHEN** the daily series of two accounts is exported
- **THEN** the file starts with `# HELP bank_account_balance_euros`, `# TYPE bank_account_balance_euros gauge` and `# UNIT bank_account_balance_euros euros` lines, holds the samples of the first account then those of the second one, and ends with `# EOF`

#### Scenario: Series labels
- **WHEN** account 00040079727 is labelled `Compte courant`
- **THEN** each of its samples is `bank_account_balance_euros{account="00040079727",account_label="Compte courant"}`

#### Scenario: Account without label
- **WHEN** an account has no label
- **THEN** its samples have an empty `account_label`

#### Scenario: Label with special characters
- **WHEN** an account label holds a double quote or a backslash
- **THEN** it is escaped as `\"` or `\\` in the label value

### Requirement: OpenMetrics balance samples
Each day of an account's daily series with a known end balance SHALL give one sample: the end balance with a dot as decimal separator and two decimals, timestamped in seconds at 00:00 UTC of the next day. A day with an unknown end balance SHALL give no sample, never a zero or NaN value.

#### Scenario: Known balance
- **WHEN** account A ends 2024-01-01 at 1523.45
- **THEN** its series has the sample `1523.45 1704153600` (2024-01-02 00:00 UTC)

#### Scenario: Filled day
- **WHEN** Saturday has no transaction and starts and ends at 1000.00
- **THEN** Saturday gives a `1000.00` sample like the days with transactions

#### Scenario: Unknown balance
- **WHEN** 2022-12-31 and 2023-01-01 have unknown balances because of a gap reported on 2023-01-02
- **THEN** the series has no sample for these two days and goes on with 2023-01-02

#### Scenario: Negative balance
- **WHEN** an account ends a day at -250.30
- **THEN** its sample value is `-250.30`

### Requirement: OpenMetrics option of the balance command
The `balance` command SHALL accept an `--openmetrics` flag. With it, the command SHALL also write the daily series of the `--from` / `--to` range as an OpenMetrics file next to the CSV file and print its path. Without it, no OpenMetrics file SHALL be written and the command SHALL behave as before.

#### Scenario: Flag given
- **WHEN** the user runs `bilig balance data/boursobank --openmetrics`
- **THEN** the CSV file and an OpenMetrics file covering the whole history are written, and both paths are printed

#### Scenario: Flag with a range
- **WHEN** the user runs `bilig balance data/boursobank --openmetrics --from 2026-03-01 --to 2026-03-31`
- **THEN** the OpenMetrics file only holds samples for the days of March 2026

#### Scenario: Flag not given
- **WHEN** the user runs `bilig balance data/boursobank`
- **THEN** only the CSV file is written
