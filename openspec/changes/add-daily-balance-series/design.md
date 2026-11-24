# Design

## Context

`BankBalance` keeps one `DayTransactions` per account and day with transactions (`get_days()`), resolves their start and end balances, then reports `gaps` (on the later day of the pair) and `conflicts`. `BankBalanceToCSV` writes `get_days()` and reads `day.transactions[0]` for the account label and source file, which fails on a day without transactions. The `balance` CLI summary is built from `get_days()`.

## Goals / Non-Goals

**Goals:**
- One `DayTransactions` per account and calendar day of a range, built from the resolved history without changing it.
- Filled days that can be written and charted like real days.

**Non-Goals:**
- No change to deduplication, balance resolution, inference or gap detection.
- No interpolation and no sentinel value: an unknown balance is `None`.
- No flag telling a day inside a gap from a day outside the history: both have no balance.
- `--from` / `--to` do not filter the printed conflicts and gaps, only the series and the CSV.

## Decisions

### `get_daily_series(date_from=None, date_to=None) -> dict[str, list[DayTransactions]]`
Same shape as `get_days()`, so the CSV writer keeps its loop. Real days are the kept `DayTransactions` objects themselves (not copies), filled days are new `DayTransactions(account, day, [])` with `start_balance` / `end_balance` set and `is_inferred=False`. Bounds are dates at 00:00, both included; a `None` bound falls back to the account's first or last day with transactions. A range entirely before or after an account's history is not special-cased: every calendar day of the range is returned, all with `None` balances. Alternative considered: one account per call (`get_daily_series(account, ...)`), rejected to stay consistent with `get_days()`.

### Filling rule
For a calendar day without a real day: find the previous real day `p` and the next real day `n` of the account (bisect on the sorted dates). The balance is `p.end_balance` when both exist and no gap is reported on `n.start_date`; otherwise `None`. A gap on `n` is looked up in a `{(account, date)}` set built from `self.gaps`, so the rule matches gap detection exactly (an inferred `n` never has a gap, so the previous end is carried; an unknown `p.end_balance` carries `None`).

Alternative considered: carrying the previous end balance after the last day, rejected because nothing tells that no transaction happened after the last export.

### Account label
`BankBalance` keeps `account_number -> account_label` from the first transaction of the kept days, exposed as `get_account_label(account)`. The CSV writer uses it for every row and writes `source_file` only when the day has transactions.

### CSV writer and CLI
`BankBalanceToCSV.write_csv(bank_balance, filename=None, date_from=None, date_to=None)` writes `get_daily_series(date_from, date_to)`; `gap` and `conflict` lookups are unchanged and naturally empty on filled days. The `balance` command adds `--from` / `--to` as `click.DateTime(formats=["%Y-%m-%d"])`, raises `click.BadParameter` when `--from` is after `--to`, keeps the summary on `get_days()` and passes the bounds to the writer.

## Risks / Trade-offs

- [Breaking CSV: many more rows, some with empty balances] → `transaction_count` 0 identifies filled rows; documented in `AGENTS.md`.
- [Real days are shared objects: a caller mutating a series day mutates the history] → the series is read-only by convention, as `get_days()` already is.
- [Large range with old data: one row per day per account] → a few thousand rows per account over years, negligible.
