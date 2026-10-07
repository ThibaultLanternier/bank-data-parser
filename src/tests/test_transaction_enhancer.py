from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from services.transaction_enhancer import TransactionEnhancer

MAIN = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings Account")


def _transaction(date: str, amount: float, account: Account = MAIN) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    return Transaction(day, day, Label("Label | LABEL"), Category("misc"), account, amount)


class TestMarkInternalTransactions:
    def test_flags_offsetting_transactions_between_accounts(self):
        debit = _transaction("2024-01-05", -500.0)
        credit = _transaction("2024-01-05", 500.0, SAVINGS)

        TransactionEnhancer([debit, credit]).mark_internal_transactions()

        assert debit.is_internal and credit.is_internal

    def test_ignores_offsetting_transactions_on_same_account(self):
        debit = _transaction("2024-01-05", -500.0)
        refund = _transaction("2024-01-05", 500.0)

        TransactionEnhancer([debit, refund]).mark_internal_transactions()

        assert not debit.is_internal and not refund.is_internal

    def test_ignores_offsetting_transactions_on_different_days(self):
        debit = _transaction("2024-01-05", -500.0)
        credit = _transaction("2024-01-06", 500.0, SAVINGS)

        TransactionEnhancer([debit, credit]).mark_internal_transactions()

        assert not debit.is_internal and not credit.is_internal
