# Tasks

## 1. Review queue ignores internal transactions

- [x] 1.1 In `CategorizeSession.queue()` (`src/services/categorize_session.py`), present a cluster only when it has a transaction with `group is None and not is_internal`; verify with new tests in `src/tests/test_categorize_session.py` that an internal-only cluster is not queued and that a cluster with internal transactions plus one ungrouped external transaction is queued
- [x] 1.2 Order the queue by the total absolute amount of the external transactions of each cluster (e.g. a `ClusterReview` property used as sort key, keeping `total_amount` for display unchanged); verify with a test where a cluster of large internal transfers plus a small external one comes after a cluster with a larger external amount
- [x] 1.3 Count only external transactions in `CategorizeSession.progress()` (`grouped_transactions` and `total_transactions`); verify with a test giving 50% for 2 grouped out of 4 external transactions plus ungrouped internal ones
- [x] 1.4 Check that the existing tests of `src/tests/test_categorize_session.py` (no internal transactions) still pass unchanged with `poetry run pytest src/tests/test_categorize_session.py`

## 2. Internal transactions tagged in the cluster display

- [ ] 2.1 In `QuestionaryUi.show_cluster()` (`src/bilig-cli.py`), append an `[internal]` tag to the lines of internal transactions; verify with a test in `src/tests/test_bilig_cli.py` that calls `show_cluster()` on a cluster holding an internal transaction and checks the tag in the captured output (`capsys`)

## 3. Documentation and checks

- [ ] 3.1 Update the `categorize` line of `AGENTS.md` to say that internal transactions (transfers between accounts) are not asked about but are shown tagged `[internal]` in the presented clusters; verify by reading the updated line
- [ ] 3.2 Run the full test suite with `poetry run pytest` and verify it is all green
- [ ] 3.3 Run `poetry run python src/bilig-cli.py categorize` on real data and verify that clusters made only of transfers between own accounts are not presented

## Workflow follow-up

- Run the linter and commit its changes last, then open the PR against `develop` with `Fixes #<ISSUE_ID>` if an issue exists.
- Archive the change once merged.
