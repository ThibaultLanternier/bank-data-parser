# Design

## Context

See proposal.md (Why) and specs/account-balance-history/spec.md for the requirements.

The CSV reader already maps the balance column (`accountbalance`, or the second `Solde` renamed `accountbalance`) and then drops it. `Transaction` has no balance field. `TransactionEnhancer` deduplicates transactions by `Transaction.id` (account + amount + operation date), which merges two legitimate identical rows of the same day.

The design rests on findings from the current exports (12 CSV files, 10,382 rows, 8 accounts, 2019 to 2026):

- **The balance belongs to the value date.** Grouped by value date, every account and day has exactly one balance. Grouped by operation date, 60 days have rows with different balances.
- **The balance follows operation dates.** It is the balance after every operation booked up to the end of its value date. A late-booked row (operation 09-07, value 09-05) carries the end balance of 09-05, which excludes its own amount.
- **Which combination the chain check supports:**

  | transactions summed by | balance read by | chain ok | gaps |
  |---|---|---|---|
  | value date | value date | 1450 | 166 |
  | operation date | any row of the day | 1505 | 51 |
  | operation date | value date | 1527 | 2 |

  The 2 remaining gaps are real: 3.99 missing at the end of 2022, and April to July 2026 not exported.
- 106 rows are late-booked (value date before operation date), 1 has a later value date. 27 days of operations have no row with that value date.
- The current files never overlap: no account and day appears in two files.

## Goals / Non-Goals

**Goals:**
- A balance history per account that can be trusted day by day, with every gap reported with its amount.
- Deduplication at day level, so overlapping re-exports can be added safely.

**Non-Goals:**
- Reconciling OFX or QIF data: they carry no balance per transaction. OFX `LEDGERBAL` (one statement balance) is left for later.
- A CLI command, report or chart. This change provides the model the follow-up builds on.
- Fixing gaps or guessing which transaction is missing.

## Decisions

### Balance stored on the transaction, for its value date
`Transaction` gets an optional `balance: float | None`. The CSV reader parses it with the existing `_parse_amount` and an empty value gives `None`. OFX and QIF readers leave it `None`.
- *Alternative:* the reader builds day records directly. Rejected: it couples parsing with the model, and a day's end balance can come from a row of another day (late-booked row), even in another file.

### `DayTransactions` entity, one per account, operation day and source file
`DayTransactions(account_number, start_date, transactions)` where `start_date` is the operation date at 00:00, plus `end_balance: float | None`, `start_balance: float | None` and `is_inferred: bool`, set by the balance history. Records are built per source file (`Transaction.source_file`) so the versions of the same day from two files stay separate until deduplication.
- *Alternative:* group by value date, as first considered. Rejected: 166 false gaps (see table).

### `BankBalance` service owns deduplication, balances and gaps
`BankBalance(day_transactions)`:
1. **Deduplicate.** Group by `(account_number, start_date)` and keep the record with the most transactions. On a tie with different amounts (compared as sorted amounts), keep the first one read and add a conflict.
2. **Look up balances.** Build a lookup `(account_number, value date) -> balance` from the transactions of the kept records only, so a discarded version never supplies a balance.
3. **Chain.** For each account, sort the days. For each day:
   - its end balance is the lookup for its own date when one exists;
   - otherwise it is inferred as `previous end + sum` (`is_inferred=True`), or unknown when there is no previous end;
   - `start = end - sum`.
4. **Report gaps.** For each pair of consecutive days where the later end balance is not inferred, compare `start(next)` with `end(previous)`. A mismatch becomes a `BalanceGap(account_number, previous_date, date, missing_amount)`.

It exposes the ordered days per account, the gaps and the conflicts.
- *Alternative:* `DayTransactions` reads its balance from its own rows. Rejected: the 27 days whose balance only appears on other days' late rows would lose it.

### The balance of a late-booked row is used for its value date only
With the lookup keyed by value date, a late row's balance lands on its value date. When that date has no operations (a weekend), the balance is not used: the last operation day before it carries the same balance, from its own rows.

### Amounts compared to the cent
Sums and balances are rounded to 2 decimals before comparing, so float noise never becomes a gap. Moving to `Decimal` would touch every reader and is out of scope.

### Built from the reader output, not the enhanced list
`BankBalance` takes transactions straight from `CsvBankDataReader`. `TransactionEnhancer`'s id deduplication would merge identical rows of a day, break the sums and create false gaps.

## Risks / Trade-offs

- [A newer export has fewer rows for a day, for example a cancelled pending card payment] → the stale version wins. The balance chain shows it as a gap next to the day, which makes the problem visible.
- [Two transactions of an account share a value date but disagree on the balance] → never seen in the current data. Keep the first balance and log a warning, rather than adding a reported type nobody needs yet.
- [The first day of an account has no previous day] → its start balance is computed and no gap can be reported before it.
- [Boursobank changes the meaning of the balance column] → the chain check would show many gaps at once, so a format change can't go unnoticed.

## Open Questions

- How the history and gaps are shown (CLI command, CSV output, chart) is left to a follow-up change. It does not affect this model.
