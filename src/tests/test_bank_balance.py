from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction
from services.bank_balance import BalanceConflict, BalanceGap, BankBalance

ACCOUNT = Account("00001", "Main Account")


def _transaction(
    amount: float,
    date: str = "2026-09-07",
    value_date: str | None = None,
    balance: float | None = None,
    source_file: str = "export.csv",
) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    value_day = datetime.strptime(value_date, "%Y-%m-%d") if value_date else day
    return Transaction(
        day,
        value_day,
        Label("Label | LABEL"),
        Category("misc"),
        ACCOUNT,
        amount,
        source_file=source_file,
        balance=balance,
    )


def _day(*amounts: float, date: str = "2026-09-07", source_file: str = "export.csv") -> DayTransactions:
    transactions = [_transaction(a, date=date, source_file=source_file) for a in amounts]
    return DayTransactions(ACCOUNT.account_number, datetime.strptime(date, "%Y-%m-%d"), transactions)


class TestDeduplication:
    def test_day_with_more_transactions_wins(self):
        partial = _day(-10.0, -20.0, -30.0, source_file="a.csv")
        full = _day(-10.0, -20.0, -30.0, -40.0, -50.0, source_file="b.csv")

        days = BankBalance([partial, full]).get_days()

        assert days["00001"] == [full]

    def test_larger_day_wins_whatever_the_read_order(self):
        full = _day(-10.0, -20.0, -30.0, -40.0, -50.0, source_file="a.csv")
        partial = _day(-10.0, -20.0, -30.0, source_file="b.csv")

        days = BankBalance([full, partial]).get_days()

        assert days["00001"] == [full]

    def test_identical_days_keep_one_without_conflict(self):
        first = _day(-10.0, -20.0, source_file="a.csv")
        second = _day(-20.0, -10.0, source_file="b.csv")

        balance = BankBalance([first, second])

        assert balance.get_days()["00001"] == [first]
        assert balance.conflicts == []

    def test_tie_with_different_content_keeps_first_and_reports_conflict(self):
        first = _day(-10.0, -20.0, -30.0, -40.0, source_file="a.csv")
        second = _day(-10.0, -20.0, -30.0, -99.0, source_file="b.csv")

        balance = BankBalance([first, second])

        assert balance.get_days()["00001"] == [first]
        assert balance.conflicts == [BalanceConflict("00001", datetime(2026, 9, 7))]

    def test_days_ordered_by_date(self):
        later = _day(-10.0, date="2026-09-08")
        earlier = _day(-20.0, date="2026-09-07")

        days = BankBalance([later, earlier]).get_days()

        assert [d.start_date for d in days["00001"]] == [datetime(2026, 9, 7), datetime(2026, 9, 8)]


def _days(transactions: list[Transaction]) -> list[DayTransactions]:
    return DayTransactions.from_transactions(transactions)


class TestBalances:
    def test_balance_from_the_same_day(self):
        day = _days([_transaction(-1000.0, balance=15395.57), _transaction(-200.0, balance=15395.57)])

        [result] = BankBalance(day).get_days()["00001"]

        assert result.end_balance == 15395.57
        assert result.start_balance == 16595.57
        assert not result.is_inferred

    def test_late_booked_balance_goes_to_its_value_date(self):
        transactions = [
            _transaction(-50.0, date="2026-09-05", balance=16837.64),
            _transaction(60.0, date="2026-09-07", value_date="2026-09-05", balance=16837.64),
            _transaction(-80.0, date="2026-09-07", balance=16817.64),
        ]

        days = BankBalance(_days(transactions)).get_days()["00001"]

        assert [(d.start_date.day, d.end_balance, d.start_balance) for d in days] == [
            (5, 16837.64, 16887.64),
            (7, 16817.64, 16837.64),
        ]

    def test_late_booked_balance_ignored_when_value_date_has_no_transactions(self):
        transactions = [
            _transaction(-50.0, date="2026-09-04", balance=16777.64),
            _transaction(60.0, date="2026-09-07", value_date="2026-09-05", balance=16777.64),
            _transaction(-100.0, date="2026-09-07", value_date="2026-09-05", balance=16777.64),
        ]

        days = BankBalance(_days(transactions)).get_days()["00001"]

        assert [(d.start_date.day, d.end_balance, d.is_inferred) for d in days] == [
            (4, 16777.64, False),
            (7, 16737.64, True),
        ]

    def test_discarded_version_gives_no_balance(self):
        partial = _days([_transaction(-10.0, source_file="a.csv", balance=999.0)])
        full = _days([_transaction(-10.0, source_file="b.csv"), _transaction(-20.0, source_file="b.csv")])

        [result] = BankBalance(partial + full).get_days()["00001"]

        assert result.end_balance is None


class TestInferredBalances:
    def test_day_without_balance_is_inferred_from_previous_day(self):
        transactions = [
            _transaction(-10.0, date="2025-07-11", balance=1000.0),
            _transaction(-30.0, date="2025-07-14", value_date="2025-07-11", balance=1000.0),
            _transaction(-20.0, date="2025-07-14", value_date="2025-07-12", balance=1000.0),
        ]

        days = BankBalance(_days(transactions)).get_days()["00001"]

        assert days[1].end_balance == 950.0
        assert days[1].start_balance == 1000.0
        assert days[1].is_inferred

    def test_next_day_balance_read_again_after_inferred_day(self):
        transactions = [
            _transaction(-10.0, date="2025-07-11", balance=1000.0),
            _transaction(-50.0, date="2025-07-14", value_date="2025-07-11", balance=1000.0),
            _transaction(-5.0, date="2025-07-15", balance=945.0),
        ]

        days = BankBalance(_days(transactions)).get_days()["00001"]

        assert [(d.end_balance, d.start_balance, d.is_inferred) for d in days] == [
            (1000.0, 1010.0, False),
            (950.0, 1000.0, True),
            (945.0, 950.0, False),
        ]

    def test_first_day_without_balance_stays_unknown(self):
        transactions = [
            _transaction(-10.0, date="2025-07-14", value_date="2025-07-11", balance=1000.0),
            _transaction(-5.0, date="2025-07-15", balance=985.0),
        ]

        days = BankBalance(_days(transactions)).get_days()["00001"]

        assert (days[0].end_balance, days[0].start_balance, days[0].is_inferred) == (None, None, False)
        assert (days[1].end_balance, days[1].start_balance) == (985.0, 990.0)


class TestGaps:
    def test_continuous_history_across_a_weekend(self):
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            _transaction(-25.0, date="2026-09-07", balance=975.0),
        ]

        assert BankBalance(_days(transactions)).gaps == []

    def test_missing_transaction(self):
        transactions = [
            _transaction(-77.97, date="2022-12-30", balance=10105.11),
            _transaction(2950.0, date="2023-01-02", balance=12190.6),
            _transaction(-868.5, date="2023-01-02", balance=12190.6),
        ]

        gaps = BankBalance(_days(transactions)).gaps

        assert gaps == [BalanceGap("00001", datetime(2022, 12, 30), datetime(2023, 1, 2), 3.99)]

    def test_missing_period(self):
        transactions = [
            _transaction(-10.0, date="2026-03-31", balance=5000.0),
            _transaction(-20.0, date="2026-08-03", balance=14869.44),
        ]

        gaps = BankBalance(_days(transactions)).gaps

        assert gaps == [BalanceGap("00001", datetime(2026, 3, 31), datetime(2026, 8, 3), 9889.44)]

    def test_inferred_day_is_not_a_gap_and_is_compared_with_the_next_day(self):
        transactions = [
            _transaction(-10.0, date="2025-07-11", balance=1000.0),
            _transaction(-50.0, date="2025-07-14", value_date="2025-07-11", balance=1000.0),
            _transaction(-5.0, date="2025-07-15", balance=940.0),
        ]

        gaps = BankBalance(_days(transactions)).gaps

        assert gaps == [BalanceGap("00001", datetime(2025, 7, 14), datetime(2025, 7, 15), -5.0)]

    def test_gaps_are_per_account(self):
        savings = Account("00002", "Savings Account")
        other = _transaction(10.0, date="2026-09-05", balance=500.0)
        other.account = savings
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            other,
            _transaction(-25.0, date="2026-09-07", balance=975.0),
        ]

        assert BankBalance(_days(transactions)).gaps == []


def _on_account(transaction: Transaction, account: Account) -> Transaction:
    transaction.account = account
    return transaction


def _series(transactions: list[Transaction], date_from: str | None = None, date_to: str | None = None):
    bounds = [datetime.strptime(d, "%Y-%m-%d") if d else None for d in (date_from, date_to)]
    return BankBalance(_days(transactions)).get_daily_series(*bounds)


class TestAccountLabel:
    def test_label_kept_per_account(self):
        savings = Account("00002", "Savings Account")
        transactions = [_transaction(-10.0), _on_account(_transaction(10.0), savings)]

        balance = BankBalance(_days(transactions))

        assert balance.get_account_label("00001") == "Main Account"
        assert balance.get_account_label("00002") == "Savings Account"


class TestDailySeriesRange:
    def test_weekend_filled_in(self):
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            _transaction(-25.0, date="2026-09-07", balance=975.0),
        ]

        days = _series(transactions)["00001"]

        assert [d.start_date.day for d in days] == [4, 5, 6, 7]
        assert [len(d.transactions) for d in days] == [1, 0, 0, 1]
        assert [d.total for d in days] == [-10.0, 0, 0, -25.0]

    def test_days_with_transactions_are_the_kept_records(self):
        transactions = [_transaction(-10.0, date="2026-09-04"), _transaction(-25.0, date="2026-09-07")]
        balance = BankBalance(_days(transactions))

        days = balance.get_daily_series()["00001"]

        assert days[0] is balance.get_days()["00001"][0]
        assert days[3] is balance.get_days()["00001"][1]

    def test_days_without_transactions_hold_the_account_label(self):
        transactions = [_transaction(-10.0, date="2026-09-04"), _transaction(-25.0, date="2026-09-07")]

        days = _series(transactions, "2026-09-01", "2026-09-10")["00001"]

        assert {d.account_label for d in days} == {"Main Account"}

    def test_range_given_inside_the_history(self):
        transactions = [_transaction(-10.0, date="2026-01-05"), _transaction(-25.0, date="2026-06-30")]

        days = _series(transactions, "2026-03-01", "2026-03-31")["00001"]

        assert len(days) == 31
        assert (days[0].start_date, days[-1].start_date) == (datetime(2026, 3, 1), datetime(2026, 3, 31))

    def test_each_account_its_own_range(self):
        savings = Account("00002", "Savings Account")
        transactions = [
            _transaction(-10.0, date="2025-01-02"),
            _transaction(-10.0, date="2026-02-12"),
            _on_account(_transaction(10.0, date="2026-02-10"), savings),
            _on_account(_transaction(10.0, date="2026-02-12"), savings),
        ]

        series = _series(transactions)

        assert series["00001"][0].start_date == datetime(2025, 1, 2)
        assert series["00002"][0].start_date == datetime(2026, 2, 10)
        assert len(series["00002"]) == 3


class TestDailySeriesBalances:
    def test_no_gap_carries_previous_end_balance(self):
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            _transaction(-25.0, date="2026-09-07", balance=975.0),
        ]

        days = _series(transactions)["00001"]

        assert [(d.start_balance, d.end_balance, d.is_inferred) for d in days[1:3]] == [
            (1000.0, 1000.0, False),
            (1000.0, 1000.0, False),
        ]

    def test_gap_leaves_balances_unknown(self):
        transactions = [
            _transaction(-77.97, date="2022-12-30", balance=10105.11),
            _transaction(2950.0, date="2023-01-02", balance=12190.6),
            _transaction(-868.5, date="2023-01-02", balance=12190.6),
        ]

        days = _series(transactions)["00001"]

        assert [(d.start_date.day, d.start_balance, d.end_balance) for d in days[1:3]] == [
            (31, None, None),
            (1, None, None),
        ]

    def test_inferred_next_day_carries_previous_end_balance(self):
        transactions = [
            _transaction(-10.0, date="2025-07-11", balance=1000.0),
            _transaction(-50.0, date="2025-07-14", value_date="2025-07-11", balance=1000.0),
        ]

        days = _series(transactions)["00001"]

        assert days[-1].is_inferred
        assert [(d.start_balance, d.end_balance) for d in days[1:3]] == [(1000.0, 1000.0), (1000.0, 1000.0)]

    def test_unknown_previous_end_balance_stays_unknown(self):
        transactions = [_transaction(-10.0, date="2025-07-11"), _transaction(-5.0, date="2025-07-14")]

        days = _series(transactions)["00001"]

        assert [(d.start_balance, d.end_balance) for d in days[1:3]] == [(None, None), (None, None)]

    def test_outside_the_history_is_unknown(self):
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            _transaction(-25.0, date="2026-09-07", balance=975.0),
        ]

        days = _series(transactions, "2026-09-01", "2026-09-12")["00001"]

        outside = days[:3] + days[-5:]
        assert len(days) == 12
        assert all(d.transactions == [] and (d.start_balance, d.end_balance) == (None, None) for d in outside)


def _missing(transactions: list[Transaction], date_from: str | None = None, date_to: str | None = None):
    bounds = [datetime.strptime(d, "%Y-%m-%d") if d else None for d in (date_from, date_to)]
    return BankBalance(_days(transactions)).get_missing_periods(*bounds)


class TestMissingPeriods:
    def test_gap_between_two_days(self):
        transactions = [
            _transaction(-77.97, date="2022-12-30", balance=10105.11),
            _transaction(2950.0, date="2023-01-02", balance=12190.6),
            _transaction(-868.5, date="2023-01-02", balance=12190.6),
        ]

        assert _missing(transactions) == {"00001": [(datetime(2022, 12, 31), datetime(2023, 1, 1))]}

    def test_range_beyond_the_history(self):
        transactions = [
            _transaction(-10.0, date="2026-01-01", balance=1000.0),
            _transaction(-25.0, date="2026-11-30", balance=975.0),
        ]

        periods = _missing(transactions, "2026-01-01", "2026-12-31")

        assert periods == {"00001": [(datetime(2026, 12, 1), datetime(2026, 12, 31))]}

    def test_several_periods_earliest_first(self):
        transactions = [
            _transaction(-10.0, date="2026-03-02", balance=1000.0),
            _transaction(-10.0, date="2026-03-05", balance=995.0),
            _transaction(-10.0, date="2026-03-09", balance=980.0),
        ]

        assert _missing(transactions) == {
            "00001": [
                (datetime(2026, 3, 3), datetime(2026, 3, 4)),
                (datetime(2026, 3, 6), datetime(2026, 3, 8)),
            ]
        }

    def test_complete_history_is_not_reported(self):
        savings = Account("00002", "Savings Account")
        transactions = [
            _transaction(-10.0, date="2026-09-04", balance=1000.0),
            _transaction(-25.0, date="2026-09-07", balance=975.0),
            _on_account(_transaction(10.0, date="2026-09-04", balance=500.0), savings),
            _on_account(_transaction(10.0, date="2026-09-06", balance=400.0), savings),
        ]

        assert list(_missing(transactions)) == ["00002"]

    def test_unknown_first_day_joins_the_next_days(self):
        transactions = [
            _transaction(-10.0, date="2025-07-11", value_date="2025-07-10", balance=1000.0),
            _transaction(-5.0, date="2025-07-14", balance=985.0),
        ]

        assert _missing(transactions) == {"00001": [(datetime(2025, 7, 11), datetime(2025, 7, 13))]}

    def test_gap_between_consecutive_days_is_not_a_missing_period(self):
        transactions = [
            _transaction(-10.0, date="2026-09-07", balance=1000.0),
            _transaction(-10.0, date="2026-09-08", balance=995.0),
        ]

        balance = BankBalance(_days(transactions))

        assert len(balance.gaps) == 1
        assert balance.get_missing_periods() == {}
