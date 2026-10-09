# Design

## Context

- `Label.get_normalized_label()` already lowercases, strips accents, dates, card numbers, bank keywords (`VIR`, `PRLV`, `SEPA`...) and numbers. Matching reuses it as is.
- `TransactionEnhancer.get_enhanced_list()` runs: internal transfers, large transactions, then `TransactionCluster.group_by_label()` (DBSCAN, `eps=0.2`, `min_samples=1` on `token_sort_ratio`) and periodicity, setting `cluster_id` and `grouped_label` on each transaction.
- Cluster ids are positional (`cluster_<n>`) and change between runs, so nothing persistent can refer to them.
- On the latest real extract: 2090 transactions, 596 clusters, top 50 clusters = 55% of transactions.
- `Category` is filled by readers and only passed through to the output; it is not touched.
- `group` already appears in names with other meanings (`transaction.group_id`, `TransactionGrouper`, `TransactionEnhancer.by_group`); the new concept keeps the name `Group` by user decision and is always referred to as `group` / `Group` attributes, never `group_id`.

## Goals / Non-Goals

**Goals:**
- Group matching is a pure, unit-testable service independent of the interactive layer.
- The interactive command reuses the same matching code as `extract`, so what the user sees during the session is what `extract` produces.

**Non-Goals:**
- Changing the clustering algorithm or its parameters.
- Renaming the existing `group_id` / `TransactionGrouper`.
- Testing the interactive prompts end to end; the session loop is kept thin and the logic it calls is tested.

## Decisions

### Entities
- `entities/group.py`: `Group(name: str, patterns: list[str])` with `matches(normalized_label) -> bool`. Patterns are normalized once (lowercase + accent stripping, same `unicodedata` NFD approach as `Label`) at construction.
- `GroupSource` enum (`DIRECT`, `CLUSTER`) in the same module.
- `transaction` gets `group: Group | None = None` and `group_source: GroupSource | None = None`, like `is_internal` / `cluster_id`.

### Services
- `services/groups_file.py` — `GroupsFile(path)`: `load() -> list[Group]`, `add_pattern(group_name, pattern)`, `remove_pattern(group_name, pattern)`. Uses `ruamel.yaml` round-trip mode so comments and order survive writes. Missing file → empty list; `add_pattern` creates it. Removing the last pattern of a group removes the group (keeps undo of a new group clean). Validation errors raise a `ValueError` with the file path and offending key; the CLI turns it into a `click.ClickException`.
- `services/group_matcher.py` — `GroupMatcher(groups)`:
  - `match(label) -> Group | None`: first group in order whose pattern matches the normalized label.
  - `assign(clusters: dict[str, TransactionCluster])`: for each cluster, sets direct matches, collects the set of directly matched groups; if exactly one, unmatched transactions inherit with `CLUSTER`; returns per-cluster status (`grouped`, `partial`, `ungrouped`, `conflict`) for the CLI.
- `TransactionEnhancer.__init__` takes an optional `groups: list[Group]` (default empty, so existing callers and tests are unchanged). `get_enhanced_list()` calls `GroupMatcher(groups).assign(clusters)` right after clustering and periodicity. As with `cluster_id`, the group fields are copied onto `self._by_id[t.id]`, since `by_id` deduplicates transactions and may hold a different object than the cluster. The clusters dict is kept on the enhancer (`self.clusters`) so `categorize` can reuse it instead of clustering twice.

### Ordering and recomputation in `categorize`
- The session clusters once. After each assignment it reloads the groups and re-runs `GroupMatcher.assign` on the same clusters (cheap: substring checks over ~2k labels), then picks the next cluster needing review (`ungrouped` or `conflict`, or `partial` with ungrouped transactions — i.e. any cluster with at least one transaction without group), sorted by decreasing `sum(abs(amount))`.
- Clustering is done on all transactions, not only ungrouped ones, so inheritance in `categorize` matches `extract` exactly.

### Pattern proposal
- Default pattern: `cluster.get_normalized_labels()` (most frequent normalized label). Editable via a text prompt.
- Preview: count of transactions matched inside / outside the cluster by the raw pattern; shadowing check: for transactions the pattern matches, whether `GroupMatcher.match` already returns an earlier group different from the chosen one.

### Prompt library: `questionary`
- `questionary.autocomplete` for the group (choices = existing group names, free text allowed → new group), `questionary.text` with default for the pattern, `questionary.select`/key for skip / undo / quit.
- Alternatives: `click.prompt(type=Choice)` has no autocomplete; InquirerPy is similar but less maintained; Textual is a full TUI, too heavy for a prompt loop.
- The session logic lives in `services/categorize_session.py` with the prompt functions injected, so it can be unit tested with scripted answers.

### YAML library: `ruamel.yaml`
- Round-trip mode keeps comments and key order, needed because the file is both hand-edited and tool-written. PyYAML would drop comments on every save.

### Default file location: `data/groups.yaml`
- Patterns contain personal merchant names. `data/` sits next to the bank exports; `data/groups.yaml` is added to `.gitignore` so it is not committed by accident. `--groups` overrides it on `extract` and `categorize`.

### Output columns
- `FileRecorder` appends `group` (group name or `""`) and `group_source` (`direct`, `cluster` or `""`) after `grouped_label`, in CSV and parquet.

## Risks / Trade-offs

- [DBSCAN with `min_samples=1` chains labels, so a cluster can contain unrelated merchants and inheritance spreads a group too far] → direct matches always win, conflicts are not inherited, and `group_source=cluster` lets the user audit inherited rows in the output.
- [New data can merge or split clusters, changing inherited groups between runs] → accepted; direct patterns are stable, and re-running `categorize` surfaces new conflicts.
- [Short substring patterns (`"edf"`) can match unrelated labels] → the outside-cluster match count is shown before saving.
- [Interactive layer hard to test] → thin prompt adapter, session logic tested with injected answers.
- [Two new dependencies] → both small and pure Python.

## Migration Plan

- No migration: without a groups file every transaction has no group and the output only gains two empty columns.
