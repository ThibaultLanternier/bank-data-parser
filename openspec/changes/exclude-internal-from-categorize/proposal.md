# Proposal

## Why

The `categorize` session asks the user about clusters made of transfers between their own accounts (e.g. `VIR SEPA vers LIVRET A`). These internal transactions are not income nor expenses and do not need a group, yet they are often large and come first in the review queue, and they keep the "grouped" progress from reaching 100%.

## What Changes

- The `categorize` review queue ignores internal transactions (`is_internal`): a cluster is presented only when at least one of its **external** transactions has no group. Clusters made only of internal transactions are never presented.
- The queue order (decreasing total absolute amount) is computed on the external transactions of each cluster.
- The progress ("share of transactions grouped") counts external transactions only.
- In a presented cluster, internal transactions are still listed, tagged `[internal]`, since internal detection is a heuristic and can be wrong.
- Unchanged: clustering, group matching (internal transactions keep their cluster, periodicity and can still get a group from a pattern), the `extract` output, and the pattern preview counts (which include internal transactions, as patterns apply to them).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `group-categorization-cli`: the clusters to review, their order, the progress and the cluster display take internal transactions into account.

## Impact

- `src/services/categorize_session.py`: `CategorizeSession.queue()`, `progress()`, `ClusterReview` ordering amount.
- `src/bilig-cli.py`: `QuestionaryUi.show_cluster()` tags internal transactions.
- Tests: `src/tests/test_categorize_session.py`, `src/tests/test_bilig_cli.py`.
- `AGENTS.md`: `categorize` description.
- No new dependency, no change to the groups file nor to the output files.
