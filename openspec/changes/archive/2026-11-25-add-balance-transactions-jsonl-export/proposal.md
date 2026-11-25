# Proposal

## Why

The OpenMetrics export puts the balance curve in Grafana, but not the transactions that move it. Exporting the transactions as JSON lines lets Alloy load them into Loki, to list and search them next to the balance curve, without duplicating them when an export is imported again.

## What Changes

- With `--openmetrics`, the `balance` command also writes `src/output/balance_<timestamp>.jsonl`: one JSON object per line for each transaction of the kept day records of the `--from` / `--to` range.
- Each line has a stable `id` (account, operation date, value date, amount, bank label and the occurrence index among identical rows of the day) and a `timestamp` that is the value date at 00:00 UTC (RFC 3339).
- Each line is deterministic: same transaction, same bytes, whatever the source file or the export time, so that Loki drops identical entries on re-import.
- The `--openmetrics` help text mentions the transactions file; `*.jsonl` outputs are gitignored.
- AGENTS.md documents the Alloy pipeline (with the `filename` label dropped), the Loki limits for history, and the limit on filling old gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-balance-history`: adds the JSON lines export of the transactions of the balance history and its writing with the `--openmetrics` option.

## Impact

- `src/services/`: a new writer of the balance history transactions as JSON lines, next to `BankBalanceToOpenMetrics`.
- `src/bilig-cli.py`: the `balance` command writes the JSON lines file when `--openmetrics` is given.
- `src/output/.gitignore`: ignores `*.jsonl`.
- No new dependency (standard `json` module). Alloy and Loki are run by the user, outside the tool.
- Depends on the `add-balance-openmetrics-export` change (merged, not archived yet): its requirements must be synced to the main spec before or with this one.
- The existing `Transaction.id` (used by `TransactionEnhancer`) is unchanged; the export uses its own id.
