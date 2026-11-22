# Spec Delta

## Purpose

Follow the balance of each bank account day by day from the CSV exports, and detect the periods where the exported transactions do not explain how the balance moved.

## ADDED Requirements

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
