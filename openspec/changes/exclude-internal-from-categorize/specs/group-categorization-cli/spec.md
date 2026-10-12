# Spec Delta

## MODIFIED Requirements

### Requirement: Clusters to review and their order
The session SHALL only present clusters that have at least one external (not internal) transaction without a group, ordered by decreasing total absolute amount of their external transactions. Internal transactions, transfers between the user's accounts, SHALL be ignored when selecting and ordering clusters. It SHALL show the progress (position, remaining clusters, share of external transactions grouped).

#### Scenario: Fully grouped clusters are skipped
- **WHEN** every transaction of a cluster has a group
- **THEN** that cluster is not presented

#### Scenario: Conflict cluster is presented
- **WHEN** a cluster is a conflict
- **THEN** it is presented and flagged as a conflict with the groups that compete

#### Scenario: Nothing left to review
- **WHEN** no cluster needs review
- **THEN** the command says so and exits successfully

#### Scenario: Internal-only cluster is skipped
- **WHEN** every transaction of a cluster without a group is internal
- **THEN** that cluster is not presented

#### Scenario: Cluster with an external transaction left is presented
- **WHEN** a cluster holds internal transactions and one external transaction, none of them grouped
- **THEN** that cluster is presented

#### Scenario: Order ignores internal amounts
- **WHEN** cluster A holds internal transactions of 1000 and an external transaction of 10, and cluster B an external transaction of 50, none grouped
- **THEN** cluster B is presented before cluster A

#### Scenario: Progress ignores internal transactions
- **WHEN** there are 4 external transactions, 2 of them grouped, and 6 internal transactions without group
- **THEN** the share of transactions grouped is 50%

### Requirement: Cluster display
For each presented cluster the session SHALL show its label, transaction count, total amount, detected periodicity when available, and its most recent transactions (date, label, amount), internal transactions included and tagged `[internal]`.

#### Scenario: Periodic cluster
- **WHEN** the cluster has a detected periodicity of 30 days
- **THEN** the periodicity is shown with the cluster summary

#### Scenario: Internal transaction tagged
- **WHEN** a presented cluster holds an internal transaction among its most recent transactions
- **THEN** that transaction is listed with an `[internal]` tag
