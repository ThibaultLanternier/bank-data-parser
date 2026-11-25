# Design

## Context

`BankBalance.get_daily_series(from, to)` already returns, per account, one `DayTransactions` per calendar day with `end_balance` set to `None` when unknown. `BankBalanceToCSV` (`src/services/bank_balance_to_csv.py`) turns it into the CSV file under `file_recorder.OUTPUT_DIR`. The OpenMetrics export is a second writer of that same series; the requirements are in `specs/account-balance-history/spec.md`.

The target consumer is `promtool tsdb create-blocks-from openmetrics <file> <data dir>`, then Grafana on top of Prometheus. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- A file that `promtool` imports as is, giving one stable series per account to stack in Grafana.
- Same range and same days as the CSV file of the same run.

**Non-Goals:**
- Other metrics (daily total, transaction count, inferred / gap / conflict flags): the CSV and the printed summary already cover data quality.
- Pushing to a live Prometheus (remote write, Pushgateway) or running `promtool`.
- Repeated imports overlapping earlier ones.

## Decisions

### A separate `BankBalanceToOpenMetrics` writer
New `src/services/bank_balance_to_openmetrics.py`, same shape as `BankBalanceToCSV`: `__init__(output_dir=None)` and `write_openmetrics(bank_balance, filename=None, date_from=None, date_to=None) -> Path`, default file name `balance_<YYYYmmdd_HHMMSS>.om` in `file_recorder.OUTPUT_DIR`.
- Alternative: a `format` parameter on `BankBalanceToCSV`. Rejected: the two outputs share nothing beyond the series, and the class name would lie.

### Opt-in `--openmetrics` flag, CSV always written
The command computes the series once per writer with the same `date_from` / `date_to`, so both files agree. Both output paths are printed.
- Alternative: `--format csv|openmetrics` replacing the CSV. Rejected: the CSV is cheap and remains the place to check data quality; a one-time export does not need a format switch.

### End balance sampled at 00:00 UTC of the next day
`end_balance` is by definition the balance at 00:00 the next day, so the sample time is `(day + 1 day)` at midnight UTC, as integer epoch seconds (OpenMetrics timestamps are in seconds).
- Alternative: Europe/Paris midnight. Rejected: the dates are naive and the shift (1-2 h) is invisible on a daily chart, while UTC avoids DST handling and keeps the output independent of the machine time zone.
- Alternative: start balance at the day's 00:00. Equivalent for continuous days, but loses the last day's end balance.

### One label value per account
Labels come from `bank_balance.get_account_label(account)`, not from each day record, so a label change between exports cannot split an account into two series (it would break the stack). Values are escaped for `\`, `"` and newline, as OpenMetrics requires. An account without label keeps `account_label=""`, so every series has the same label set.

### Plain text writing, no client library
The file is written by hand: one `HELP` / `TYPE` / `UNIT` header, then the samples account by account (series contiguous, timestamps increasing as returned by `get_daily_series`), then `# EOF`. Values use `f"{value:.2f}"` (dot decimal, unlike the French format of the CSV). `prometheus_client` cannot write historical timestamps and would be a dependency for ~40 lines.

## Risks / Trade-offs

- [Prometheus deletes the imported blocks at the next compaction with the default 15-day retention] → AGENTS.md documents running Prometheus with a retention longer than the history (e.g. `--storage.tsdb.retention.time=20y`).
- [`promtool` creates 2 h blocks by default, thousands of tiny blocks for years of daily data] → AGENTS.md documents `--max-block-duration=8760h` (or larger).
- [One sample per day is older than the 5-minute lookback: a plain query shows isolated points, and stacking needs a value at every step] → AGENTS.md gives the query `last_over_time(bank_account_balance_euros[1d])` with legend `{{account_label}} ({{account}})` and stacking set to Normal.
- [Unknown periods drop the account from the stack, the total dips] → Accepted, it is the honest picture; the command already prints the periods to export again.
- [Negative balances (overdraft, credit card) stack below zero] → Accepted; can be filtered on `account` in Grafana, no exporter change.
- [Large file for long histories] → A few accounts over ~10 years is ~ tens of thousands of lines, well within `promtool` limits.

## Migration Plan

None: new opt-in output, nothing changes without the flag.
