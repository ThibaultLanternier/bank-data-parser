# Design

## Context

`BankBalance.get_daily_series(from, to)` returns per account one `DayTransactions` per calendar day; days with transactions are the kept day records (already deduplicated across overlapping files), filled days have no transactions. `BankBalanceToOpenMetrics` (`src/services/bank_balance_to_openmetrics.py`) writes the balances of that series with `--openmetrics`. The JSON lines export is a third writer of the same series, for Loki through Alloy. Requirements are in `specs/account-balance-history/spec.md`; motivation in proposal.md.

`Label.raw_label` is `"<suggested> | <bank label>"` lowercased (the new CSV format rebuilds it from `Libellé Suggéré` and `Libellé`); `Label._get_label_part(1)` returns the bank label, or the whole label when there is no `|`. `Transaction.id` hashes only account, amount and operation date, so identical payments of a day collide; it is used by `TransactionEnhancer` and stays unchanged.

## Goals / Non-Goals

**Goals:**
- Lines that Alloy can parse with `stage.json` + `stage.timestamp` (RFC 3339) without custom formats.
- Byte-identical lines for the same transaction across exports, so that Loki drops re-imported entries.
- Same days as the CSV and OpenMetrics files of the same run.

**Non-Goals:**
- Pushing to Loki (push API, `logcli`): Alloy reads the file.
- Choosing Loki stream labels: done in the Alloy config, the file has none.
- Groups, clusters or internal transfer flags: the `balance` command does not compute them.
- Changing `Transaction.id`.

## Decisions

### A separate `BankBalanceTransactionsToJsonl` writer
New `src/services/bank_balance_transactions_to_jsonl.py`, same shape as the other writers: `__init__(output_dir=None)`, `write_jsonl(bank_balance, filename=None, date_from=None, date_to=None) -> Path`, default name `balance_<YYYYmmdd_HHMMSS>.jsonl` in `file_recorder.OUTPUT_DIR`. It iterates `get_daily_series(from, to)` and takes `day.transactions`, so the range and the deduplication are those of the series.
- Alternative: export from the reader output. Rejected: overlapping files would give duplicate rows, and the range would differ from the other files.

### Export id computed by the writer
`md5("||".join([account, date_operation isoformat, date_value isoformat, amount, bank label, index]))`, the bank label being `" ".join(label._get_label_part(1).split())`, the index counting earlier transactions of the same day record with the same five values. A public `Label.get_bank_label()` wraps `_get_label_part(1)` to avoid using a private method from the service. The amount is formatted with `f"{amount:.2f}"` so that `-12.5` and `-12.50` hash the same.
- Alternative: change `Transaction.id`. Rejected: `TransactionEnhancer` and the other commands rely on its current merging behavior.
- Alternative: include the suggested label. Rejected: Boursobank's enrichment can change between exports and would create new ids.

### Deterministic lines
`json.dumps(record, ensure_ascii=False, separators=(", ", ": "))` with keys inserted in the spec order (dicts keep insertion order), floats as JSON numbers, `None` as `null`. No `source_file`, no export time. Lines sorted by account (sorted keys of the series), then by `date_value`, ties kept in series order (stable sort), so each Loki stream is written in time order.

### Timestamp at value date 00:00 UTC
`timestamp = date_value` at midnight with `tzinfo=UTC`, formatted `%Y-%m-%dT%H:%M:%SZ`. Same UTC convention as the OpenMetrics samples, so a transaction and the balance it moves line up in Grafana (the end balance sample of a day is at 00:00 the next day).

### Written with `--openmetrics`
The `balance` command writes the JSON lines file right after the OpenMetrics file with the same range and prints `Transactions output written to <path>.`. The flag keeps its name (just merged); its help text becomes "Also write the end of day balances as an OpenMetrics file and the transactions as JSON lines, to import into Prometheus and Loki".

## Risks / Trade-offs

- [Alloy's `loki.source.file` adds a `filename` label: each export is a new stream and Loki keeps duplicates] → AGENTS.md shows the pipeline with `stage.label_drop { values = ["filename"] }`.
- [Loki rejects entries older than a week by default] → AGENTS.md documents `limits_config.reject_old_samples: false` and a retention longer than the history.
- [Loki rejects entries far behind the newest entry of a stream: a later export filling an old gap is refused] → Documented; import into an empty Loki to rebuild the history.
- [Old and new CSV formats could write the bank label of the same transaction differently, giving two ids] → Unverified: the current data has no transaction exported in both formats. Spacing differences are absorbed; check on the next export overlapping an older one.
- [Two genuinely identical rows booked in different order in two exports] → Identical rows are interchangeable, the occurrence index gives the same set of ids.
- [`balance` lines carry balances and labels, personal data] → The file is written under `src/output/`, gitignored with `*.jsonl`.

## Migration Plan

None: new file written only with `--openmetrics`.

## Open Questions

- Do the old and new CSV formats give the same bank label for one transaction? Answered by the first export overlapping an older one; changes neither the spec nor the tasks unless they differ.
