from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction
from services.bank_balance import BalanceConflict, BankBalance

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
