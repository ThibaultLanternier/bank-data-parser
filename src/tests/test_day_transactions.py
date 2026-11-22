from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction

ACCOUNT = Account("00001", "Main Account")


def _transaction(amount: float) -> Transaction:
    day = datetime(2026, 9, 7)
    return Transaction(day, day, Label("Label | LABEL"), Category("misc"), ACCOUNT, amount)


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
