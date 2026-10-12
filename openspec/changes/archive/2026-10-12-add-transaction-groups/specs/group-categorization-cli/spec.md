# Spec Delta

## Purpose

Interactive command that helps the user build and grow the groups file by reviewing clusters of similar transactions and assigning each one a group.

## ADDED Requirements

### Requirement: Categorize command
The CLI SHALL provide a `categorize` command taking the same input path and `--file-type` options as `extract`, plus a `--groups` option for the groups file (default `data/groups.yaml`). It SHALL read, enhance and group the transactions before starting the interactive session.

#### Scenario: Start a session
- **WHEN** the user runs `bilig categorize data/boursobank`
- **THEN** transactions are read and matched against `data/groups.yaml` and the first cluster to review is shown

#### Scenario: Groups file created on first answer
- **WHEN** `data/groups.yaml` does not exist and the user assigns a group to a cluster
- **THEN** the file is created with that group and pattern

### Requirement: Clusters to review and their order
The session SHALL only present clusters that have no grouped transaction or that are conflicts, ordered by decreasing total absolute amount. It SHALL show the progress (position, remaining clusters, share of transactions grouped).

#### Scenario: Fully grouped clusters are skipped
- **WHEN** every transaction of a cluster has a group
- **THEN** that cluster is not presented

#### Scenario: Conflict cluster is presented
- **WHEN** a cluster is a conflict
- **THEN** it is presented and flagged as a conflict with the groups that compete

#### Scenario: Nothing left to review
- **WHEN** no cluster needs review
- **THEN** the command says so and exits successfully

### Requirement: Cluster display
For each presented cluster the session SHALL show its label, transaction count, total amount, detected periodicity when available, and its most recent transactions (date, label, amount).

#### Scenario: Periodic cluster
- **WHEN** the cluster has a detected periodicity of 30 days
- **THEN** the periodicity is shown with the cluster summary

### Requirement: Pattern proposal and preview
The session SHALL propose an editable pattern pre-filled with the cluster's most frequent normalized label, and before saving SHALL show how many transactions the pattern matches inside and outside the cluster.

#### Scenario: Pattern too broad
- **WHEN** the user edits the pattern to `"edf"` and it also matches transactions of other clusters
- **THEN** the number of transactions matched outside the cluster is shown before the group is chosen

#### Scenario: Pattern shadowed by an earlier group
- **WHEN** the pattern would be assigned to a group but an earlier group in the file already matches the same transactions
- **THEN** the user is warned that the new pattern would not take effect for those transactions

### Requirement: Group selection with autocomplete
The session SHALL ask for the group with autocompletion over the existing group names and SHALL accept a new name, which creates a new group.

#### Scenario: Existing group
- **WHEN** the user types `SAL` and selects `SALARY`
- **THEN** the pattern is appended to the `SALARY` patterns

#### Scenario: New group
- **WHEN** the user enters a name that is not an existing group
- **THEN** a new group with that name and the pattern is added at the end of the groups file

### Requirement: Immediate save preserving the file
Each assignment SHALL be written to the groups file immediately, keeping existing comments, group order and pattern order, and the cluster states SHALL be recomputed so the following clusters reflect the new pattern.

#### Scenario: Hand-written comments kept
- **WHEN** the groups file contains comments and the user assigns a group
- **THEN** the comments are still present in the saved file

#### Scenario: Pattern covers later clusters
- **WHEN** a new pattern also groups transactions of a cluster not yet reviewed
- **THEN** that cluster is no longer presented if all its transactions now have a group

### Requirement: Session controls
The user SHALL be able to skip a cluster, undo the last assignment (removing its pattern from the file), and quit at any time without losing saved assignments.

#### Scenario: Skip
- **WHEN** the user skips a cluster
- **THEN** the next cluster is shown and the groups file is unchanged

#### Scenario: Undo
- **WHEN** the user undoes after assigning a pattern
- **THEN** the pattern is removed from the groups file and the cluster is presented again

#### Scenario: Quit
- **WHEN** the user quits or presses Ctrl+C
- **THEN** the command exits with a summary of the assignments made, and all of them are in the groups file
