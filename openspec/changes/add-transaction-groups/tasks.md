# Tasks

## 1. Setup

- [x] 1.1 Add `ruamel.yaml` and `questionary` with `poetry add` and verify `poetry run python -c "import ruamel.yaml, questionary"` succeeds
- [x] 1.2 Add `data/groups.yaml` to `.gitignore` and verify with `git check-ignore data/groups.yaml`

## 2. Group entity and matching

- [x] 2.1 Create `src/entities/group.py` with `Group(name, patterns)`, pattern normalization (lowercase, accents stripped), `matches(normalized_label)` and the `GroupSource` enum; verify with `src/tests/test_group.py` (case/accent insensitive match, no match, empty pattern never matches)
- [x] 2.2 Add `group` and `group_source` attributes (default `None`) to `transaction`; verify existing tests still pass with `poetry run pytest`
- [x] 2.3 Create `src/services/group_matcher.py` with `match(label)` (first group in file order wins) and `assign(clusters)` (direct match wins, unanimous inheritance with `cluster` source, conflicts not inherited, per-cluster status); verify with `src/tests/test_group_matcher.py` covering every scenario of the `transaction-groups` matching requirements

## 3. Groups file

- [x] 3.1 Create `src/services/groups_file.py` with `GroupsFile.load()` (missing file → empty list, invalid content → `ValueError` naming file and entry); verify with `src/tests/test_groups_file.py` using `tmp_path`
- [x] 3.2 Add `add_pattern` (creates file and group when needed, new group appended at the end) and `remove_pattern` (removes the group when its last pattern goes), preserving comments and order; verify with tests that write a commented file, modify it and check comments and order are kept

## 4. Extract integration

- [x] 4.1 Make `TransactionEnhancer` accept optional `groups`, run `GroupMatcher.assign` after clustering, copy group fields onto `by_id` transactions and keep the clusters on the enhancer; verify with new cases in `src/tests/test_transaction_enhancer.py` (direct, inherited, conflict, no groups)
- [x] 4.2 Add `group` and `group_source` columns to `FileRecorder` CSV and parquet output; verify with `src/tests/test_file_recorder.py` (filled and empty values, existing columns unchanged)
- [x] 4.3 Add the `--groups` option (default `data/groups.yaml`) to `extract`, turning file errors into a `click.ClickException`; verify with `src/tests/test_bilig_cli.py` (custom file, missing file, invalid file) and a manual `poetry run python src/bilig-cli.py extract` run
- [x] 4.4 Document the groups file format, matching rules and the new output columns in `AGENTS.md` and `README.md`; verify the documented example file loads with `GroupsFile.load()`

## 5. Categorize session

- [ ] 5.1 Create `src/services/categorize_session.py` with the review queue (clusters with ungrouped transactions or conflicts, sorted by decreasing total absolute amount) and progress figures; verify with `src/tests/test_categorize_session.py`
- [ ] 5.2 Add pattern proposal (most frequent normalized label), inside/outside match counts and shadowing detection; verify with unit tests on a small cluster set
- [ ] 5.3 Add the session loop with injected prompt functions: assign to existing or new group, skip, undo (removes pattern, cluster presented again), quit with summary, save and recompute after each answer; verify with tests driving scripted answers against a `tmp_path` groups file

## 6. Categorize command

- [ ] 6.1 Add the `categorize` command to `src/bilig-cli.py` (input path, `--file-type`, `--groups`) wiring `questionary` prompts (autocomplete for groups, text with default for pattern) and cluster display (label, count, total, periodicity, recent transactions); handle Ctrl+C as quit; verify with a `test_bilig_cli.py` test that runs it with no cluster to review, and a manual session on `data/boursobank`
- [ ] 6.2 Document the `categorize` command in `AGENTS.md` (run commands) and `README.md`; verify the documented command runs as written

## 7. Integration check

- [ ] 7.1 Run a real session: categorize a few clusters, then run `extract` and verify the CSV `group` / `group_source` columns match the session, and that the full `poetry run pytest` suite is green
