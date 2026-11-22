from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction

ACCOUNT = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings Account")


def _transaction(
    amount: float,
    date: str = "2026-09-07",
    value_date: str | None = None,
    account: Account = ACCOUNT,
    source_file: str = "export.csv",
) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    value_day = datetime.strptime(value_date, "%Y-%m-%d") if value_date else day
    return Transaction(
        day, value_day, Label("Label | LABEL"), Category("misc"), account, amount, source_file=source_file
    )


class TestDayTransactions:
    def test_holds_account_day_and_transactions(self):
        transactions = [_transaction(-10.0), _transaction(25.0)]

        day = DayTransactions("00001", datetime(2026, 9, 7), transactions)

        assert day.account_number == "00001"
        assert day.start_date == datetime(2026, 9, 7, 0, 0, 0)
        assert day.transactions == transactions

    def test_balances_unknown_by_default(self):
        day = DayTransactions("00001", datetime(2026, 9, 7), [_transaction(-10.0)])

        assert day.start_balance is None
        assert day.end_balance is None
        assert not day.is_inferred

    def test_total_is_rounded_to_the_cent(self):
        day = DayTransactions("00001", datetime(2026, 9, 7), [_transaction(0.1), _transaction(0.2)])

        assert day.total == 0.3

    def test_total_of_mixed_amounts(self):
        day = DayTransactions("00001", datetime(2026, 9, 7), [_transaction(2950.0), _transaction(-868.5)])

        assert day.total == pytest.approx(2081.5)


class TestFromTransactions:
    def test_same_day_with_different_value_dates(self):
        transactions = [
            _transaction(-10.0),
            _transaction(60.0, value_date="2026-09-05"),
            _transaction(-5.0, value_date="2026-09-08"),
        ]

        days = DayTransactions.from_transactions(transactions)

        assert len(days) == 1
        assert days[0].account_number == "00001"
        assert days[0].start_date == datetime(2026, 9, 7)
        assert days[0].transactions == transactions

    def test_same_day_in_two_files(self):
        first = _transaction(-10.0, source_file="a.csv")
        second = _transaction(-10.0, source_file="b.csv")

        days = DayTransactions.from_transactions([first, second])

        assert [d.transactions for d in days] == [[first], [second]]

    def test_one_record_per_account(self):
        main = _transaction(-10.0)
        savings = _transaction(10.0, account=SAVINGS)

        days = DayTransactions.from_transactions([main, savings])

        assert [(d.account_number, d.transactions) for d in days] == [("00001", [main]), ("00002", [savings])]

    def test_one_record_per_day_in_read_order(self):
        later = _transaction(-10.0, date="2026-09-08")
        earlier = _transaction(-20.0, date="2026-09-07")

        days = DayTransactions.from_transactions([later, earlier])

        assert [d.start_date for d in days] == [datetime(2026, 9, 8), datetime(2026, 9, 7)]
