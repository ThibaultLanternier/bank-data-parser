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
