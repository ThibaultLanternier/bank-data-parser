# Proposal

## Why

Transactions can be clustered by similar labels, but there is no way to say what they are for (salary, school, investment, real estate...). The bank category is empty for OFX, the default format, and uses the bank's vocabulary anyway. Users need their own groups, kept in a file they can edit, and a fast way to assign them without writing every rule by hand.

## What Changes

- New user-defined **groups** (e.g. `SALARY`, `SCHOOL`, `INVESTMENT`, `REAL_ESTATE`) defined in a YAML file that maps each group name to a list of label patterns.
- A pattern matches a transaction when it is a substring of the transaction's normalized label (case and accent insensitive); the first matching group in file order wins.
- Groups are assigned per label cluster: a transaction's own match always wins, and unmatched transactions of a cluster inherit the group only when all direct matches of that cluster agree on a single group. Clusters with diverging direct matches are conflicts and nothing is inherited.
- The extract output (CSV and parquet) gets two new columns: `group` and `group_source` (`direct`, `cluster` or empty).
- New interactive `categorize` command: it walks through the clusters that have no group or a conflict, largest total amount first, shows their transactions, and asks for a group with autocomplete (existing groups or a new one) and an editable pattern pre-filled from the cluster label. Each answer is saved to the YAML file immediately.
- New dependencies: a comment-preserving YAML library and an interactive prompt library.
- Out of scope: per-group breakdown in `report`, amount or sign based rules, regex patterns, group hierarchy. The existing bank `Category` is left unchanged.

## Capabilities

### New Capabilities
- `transaction-groups`: definition of user groups in a YAML file and assignment of a group to each transaction (substring matching, cluster inheritance, conflicts, output columns).
- `group-categorization-cli`: interactive command that helps the user build the groups file by labelling clusters of transactions.

### Modified Capabilities

## Impact

- `src/entities/`: new `Group` entity; `transaction` gets `group` and `group_source` attributes.
- `src/services/`: new groups file loader/writer and group matcher; `TransactionEnhancer` assigns groups after clustering; `FileRecorder` writes the new columns.
- `src/bilig-cli.py`: new `categorize` command; `extract` gets a `--groups` option for the groups file (default `data/groups.yaml`).
- `pyproject.toml`: adds `ruamel.yaml` and `questionary`.
- `AGENTS.md` / `README.md`: document the groups file format and the new command.
- Output CSV gains two columns; existing columns are unchanged.
