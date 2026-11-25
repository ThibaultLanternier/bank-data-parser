# Spec Delta

## ADDED Requirements

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
