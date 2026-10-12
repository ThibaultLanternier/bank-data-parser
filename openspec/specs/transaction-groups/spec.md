# transaction-groups Specification

## Purpose

Lets users define their own transaction groups (salary, school, investment...) in an editable YAML file and assigns one of these groups to each transaction based on its label.

## Requirements

### Requirement: Groups file format
The groups file SHALL be a YAML mapping whose keys are group names and whose values are lists of string patterns. The order of groups and of patterns in the file SHALL be preserved and used as matching priority.

#### Scenario: Valid groups file
- **WHEN** the groups file contains `SALARY: ["acme corp"]` followed by `ENERGY: ["edf"]`
- **THEN** two groups are loaded, `SALARY` then `ENERGY`, each with its patterns

#### Scenario: Missing groups file
- **WHEN** the groups file does not exist
- **THEN** no group is defined and every transaction is left without a group, without error

#### Scenario: Invalid groups file
- **WHEN** the groups file is not a mapping of names to lists of strings
- **THEN** the command fails with an error naming the groups file and the invalid entry

### Requirement: Substring matching on normalized label
A pattern SHALL match a transaction when the pattern, lowercased and stripped of accents, is a substring of the transaction's normalized label. Empty patterns SHALL never match.

#### Scenario: Case and accent insensitive match
- **WHEN** a pattern is `"Électricité EDF"` and the normalized label is `"electricite edf particuliers"`
- **THEN** the pattern matches

#### Scenario: No match
- **WHEN** no pattern of any group is a substring of the normalized label
- **THEN** the transaction has no direct match

### Requirement: First group in file order wins
When patterns of several groups match the same transaction, the transaction SHALL be directly matched to the first of these groups in file order.

#### Scenario: More specific group listed first
- **WHEN** `SUBSCRIPTIONS: ["amazon prime"]` is listed before `SHOPPING: ["amazon"]` and the normalized label is `"amazon prime"`
- **THEN** the transaction is directly matched to `SUBSCRIPTIONS`

### Requirement: Direct match takes precedence
A transaction with a direct match SHALL get that group with source `direct`, whatever the other transactions of its cluster match.

#### Scenario: Direct match inside a mixed cluster
- **WHEN** a transaction directly matches `SHOPPING` and other transactions of its cluster directly match `SUBSCRIPTIONS`
- **THEN** the transaction gets group `SHOPPING` with source `direct`

### Requirement: Group inheritance within a cluster
A transaction without a direct match SHALL inherit, with source `cluster`, the group of its label cluster when all direct matches of that cluster designate one single group.

#### Scenario: Unanimous cluster
- **WHEN** a cluster holds `"edf particuliers"` (matched by `ENERGY`) and `"edf clients part"` (no direct match)
- **THEN** the `"edf clients part"` transactions get group `ENERGY` with source `cluster`

#### Scenario: Cluster without any direct match
- **WHEN** no transaction of a cluster has a direct match
- **THEN** every transaction of the cluster is left without a group

### Requirement: Conflicting clusters are not inherited
When the direct matches of a cluster designate more than one group, the cluster SHALL be a conflict and its transactions without a direct match SHALL be left without a group.

#### Scenario: Ambiguous cluster
- **WHEN** a cluster holds transactions matched by `SUBSCRIPTIONS`, transactions matched by `SHOPPING` and `"amazon eu"` transactions with no direct match
- **THEN** the `"amazon eu"` transactions have no group and no group source

### Requirement: Group columns in extract output
The extract CSV and parquet outputs SHALL contain a `group` column with the group name (empty when none) and a `group_source` column with `direct`, `cluster` or empty. Existing columns SHALL remain unchanged.

#### Scenario: Extract with groups file
- **WHEN** `extract` runs with a groups file matching some transactions
- **THEN** matched rows have `group` and `group_source` filled and other rows have both empty

#### Scenario: Custom groups file location
- **WHEN** `extract` runs with `--groups other.yaml`
- **THEN** groups are read from `other.yaml` instead of the default `data/groups.yaml`
