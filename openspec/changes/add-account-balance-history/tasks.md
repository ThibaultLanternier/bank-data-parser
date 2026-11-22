# Tasks

## 1. Balance on transactions

- [x] 1.1 Add an optional `balance: float | None = None` to `Transaction` (`src/entities/transaction.py`), leaving OFX and QIF readers unchanged so they give `None`; verify the existing OFX and QIF reader tests still pass and a new assertion checks `balance is None` for an OFX transaction
- [x] 1.2 Parse the `accountbalance` key in `CsvBankDataReader._parse_row` with `_parse_amount` (comma or dot decimal, regular or non-breaking spaces), giving `None` for an empty value; verify with tests in `src/tests/test_csv_bank_data_reader.py` covering the old format (`258.29`), the new format (second `Solde`, `1 234,56`) and an empty balance
- [ ] 1.3 Document in the CSV format section of `AGENTS.md` that the balance column is kept as the account balance at the end of the row's value date; verify the section matches the reader behavior

## 2. Day records

- [ ] 2.1 Create `DayTransactions` in `src/entities/day_transactions.py` holding `account_number`, `start_date` (operation date at 00:00), `transactions`, `start_balance` / `end_balance` (`float | None`, default `None`), `is_inferred` (default `False`) and a `total` (sum rounded to the cent); verify with unit tests in `src/tests/test_day_transactions.py`
- [ ] 2.2 Add a builder function that groups transactions into `DayTransactions` by account number, operation date and `source_file`, keeping the read order; verify with tests for same-day transactions with different value dates, the same day in two files, and two accounts on the same day

## 3. Balance history: deduplication

- [ ] 3.1 Create `BankBalance` in `src/services/bank_balance.py` taking a list of `DayTransactions`, keeping one per `(account_number, start_date)`: most transactions wins, on a tie with different sorted amounts the first one read wins and a conflict `(account_number, start_date)` is recorded; verify with tests for partial re-export, identical days (no conflict) and tie with different content

## 4. Balance history: balances

- [ ] 4.1 Build the `(account_number, value date) -> balance` lookup from the kept records only (first balance kept, a warning logged on disagreement), then for each account sorted by date set `end_balance` from the lookup and `start_balance = end_balance - total`; verify with tests for a same-day balance and for a late-booked row whose balance goes to its value date, not its operation date
- [ ] 4.2 Infer the end balance from the previous day (`previous end + total`, `is_inferred=True`) when the lookup has no value for the day, and leave both balances unknown when there is no previous end; verify with tests for an inferred day and for a first day without balance

## 5. Balance history: gaps

- [ ] 5.1 Add `BalanceGap(account_number, previous_date, date, missing_amount)` and report one per consecutive pair whose later day is not inferred and whose `start_balance` differs from the previous `end_balance` to the cent; expose the ordered days per account, the gaps and the conflicts; verify with tests for a continuous history across a weekend, the 3.99 missing transaction, a missing period, and an inferred day that produces no gap
- [ ] 5.2 Add `DayTransactions` and `BankBalance` to the project structure in `AGENTS.md`, with a short "Balance history" section (operation date for transactions, value date for balances, deduplication rule, gap definition); verify the section matches the specs

## 6. Integration check

- [ ] 6.1 Read `data/boursobank` CSV files with `CsvBankDataReader`, build the day records and a `BankBalance` from a one-off `poetry run python` snippet (not committed), and verify it reports exactly two gaps on account …9727 (2023-01-02, +3.99, and 2026-08-03) and none elsewhere
- [ ] 6.2 Run `poetry run pytest` and `make lint` and verify both pass

## Workflow follow-up

- Open the PR against `develop`, with the lint fixes in the last commit.
- Archive the change with `/opsx:archive` once the PR is merged, syncing the `account-balance-history` spec.
