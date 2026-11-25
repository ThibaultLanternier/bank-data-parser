# Spec Delta

## ADDED Requirements

### Requirement: Balance history transactions JSON lines export
The transactions of the kept day records of the daily series SHALL be written as a UTF-8 JSON lines file, one JSON object per transaction and per line, ordered by account then timestamp, then read order. Days without transactions SHALL give no line.

#### Scenario: Transactions of the series
- **WHEN** account A has 2 transactions on 2024-01-02 and 1 on 2024-01-05, with no transaction in between
- **THEN** the file has 3 lines for account A, in timestamp order

#### Scenario: Overlapping exports
- **WHEN** two CSV files hold the same 3 transactions of account A on 2024-01-02
- **THEN** the file has 3 lines for that day, those of the day record kept

#### Scenario: Several accounts
- **WHEN** accounts 00001 and 00002 both have transactions
- **THEN** all lines of account 00001 come before those of account 00002

### Requirement: Transaction line content
Each line SHALL hold, in this order, `id`, `timestamp`, `date_value`, `date_operation`, `account`, `account_label`, `amount`, `label`, `normalized_label`, `category`, `parent_category` and `balance`. `timestamp` SHALL be the value date at 00:00 UTC in RFC 3339, dates SHALL be `YYYY-MM-DD`, `amount` and `balance` JSON numbers, `label` the bank label. Missing values SHALL be `null`. A line SHALL hold nothing that depends on the source file or on the export time.

#### Scenario: Line of a card payment
- **WHEN** account 00001 `Main` has a -12.50 transaction booked 2024-01-01, value date 2024-01-02, bank label `carte 01/01/24 boulangerie`, balance 1523.45
- **THEN** its line has `"timestamp": "2024-01-02T00:00:00Z"`, `"date_value": "2024-01-02"`, `"date_operation": "2024-01-01"`, `"account": "00001"`, `"account_label": "Main"`, `"amount": -12.5`, `"label": "carte 01/01/24 boulangerie"` and `"balance": 1523.45`

#### Scenario: No balance
- **WHEN** a transaction has no balance
- **THEN** its line has `"balance": null`

#### Scenario: Same transaction from two files
- **WHEN** the same transaction is exported once from file `a.csv` and once from file `b.csv`
- **THEN** both exports give the exact same line

#### Scenario: Non ASCII characters
- **WHEN** a label holds `é`
- **THEN** the line holds `é` as is, not an escape sequence

### Requirement: Transaction id
The `id` SHALL be the MD5 hex digest of the account number, the operation date, the value date, the amount, the bank label (the part after `|`, or the whole label without `|`, spaces trimmed and collapsed) and the occurrence index of the transaction among the transactions of its day record sharing all these values, starting at 0. The suggested label SHALL NOT be part of the id.

#### Scenario: Identical payments on the same day
- **WHEN** account A has two -2.50 transactions on 2024-01-02 with the same value date and bank label
- **THEN** they have two different ids, the first one read with occurrence index 0, the second one with 1

#### Scenario: Same transaction in another export
- **WHEN** the same transaction is read from two exports
- **THEN** it has the same id in both

#### Scenario: Suggested label changed
- **WHEN** two exports of a transaction have the same bank label but different suggested labels
- **THEN** it has the same id in both

#### Scenario: Spacing of the bank label
- **WHEN** two exports of a transaction differ only by the spaces of the bank label
- **THEN** it has the same id in both

### Requirement: Transactions export with the OpenMetrics option
With the `--openmetrics` flag, the `balance` command SHALL also write the transactions of the `--from` / `--to` range as a JSON lines file next to the CSV and OpenMetrics files, and print its path. Without the flag, no JSON lines file SHALL be written.

#### Scenario: Flag given
- **WHEN** the user runs `bilig balance data/boursobank --openmetrics`
- **THEN** the CSV, OpenMetrics and JSON lines files are written and their paths printed

#### Scenario: Flag with a range
- **WHEN** the user runs `bilig balance data/boursobank --openmetrics --from 2026-03-01 --to 2026-03-31`
- **THEN** the JSON lines file holds the transactions of the day records of March 2026 only (by operation date)

#### Scenario: Flag not given
- **WHEN** the user runs `bilig balance data/boursobank`
- **THEN** no JSON lines file is written
