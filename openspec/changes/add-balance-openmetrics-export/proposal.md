# Proposal

## Why

The daily balance series is only available as a CSV file, which is hard to chart over several years and several accounts. Exporting it once to Prometheus lets Grafana show the balance of every account as a stacked curve, the bands adding up to the total balance.

## What Changes

- New `--openmetrics` flag on the `balance` command: on top of the CSV file, it writes the daily series as an OpenMetrics text file with timestamps, the input of `promtool tsdb create-blocks-from openmetrics` (Prometheus backfill).
- The file holds one gauge, `bank_account_balance_euros`, one series per account with the labels `account` (number) and `account_label`, one sample per day with a known end balance.
- Days with an unknown balance have no sample; the file covers the same range as the CSV (`--from` / `--to`, default the whole history).
- AGENTS.md documents the import (`promtool` command, block duration, Prometheus retention) and the Grafana query for the stacked curve.
- The CSV output and the printed summary are unchanged; without the flag the command behaves as today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-balance-history`: adds the OpenMetrics export of the daily series and the `--openmetrics` option of the `balance` command.

## Impact

- `src/services/`: a new writer of the daily series in OpenMetrics format, next to `BankBalanceToCSV`.
- `src/bilig-cli.py`: the `balance` command gets the `--openmetrics` flag.
- `src/output/`: a new `balance_<timestamp>.om` file (gitignored like the CSV outputs).
- No new dependency: the format is plain text. Importing into Prometheus (`promtool`) and Grafana are run by the user, outside the tool.
- Intended for a one-time export of the whole dataset: importing again data overlapping an earlier import is not handled.
