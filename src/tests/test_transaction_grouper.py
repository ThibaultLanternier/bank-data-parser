from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from services.transaction_grouper import MonthlySummary, TransactionGrouper

MAIN = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings Account")


def _transaction(date: str, amount: float, account: Account = MAIN) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    return Transaction(day, day, Label("Label | LABEL"), Category("misc"), account, amount)


class TestTransactionGrouper:
    def test_empty_list_gives_empty_report(self):
        assert TransactionGrouper([]).group_by_month() == {}

    def test_summarizes_each_month(self):
        transactions = [
            _transaction("2024-01-05", 3000.0),
            _transaction("2024-01-10", -92.72),
            _transaction("2024-01-20", -7.28, SAVINGS),
            _transaction("2024-01-25", 0.1, SAVINGS),
            _transaction("2024-01-26", 0.2, SAVINGS),
        ]

        assert TransactionGrouper(transactions).group_by_month() == {
            2024: [MonthlySummary(2024, 1, 3000.3, 100.0, 5, ["00001", "00002"])],
        }

    def test_groups_months_by_year_in_chronological_order(self):
        transactions = [
            _transaction("2025-01-03", -10.0),
            _transaction("2024-12-31", -20.0),
            _transaction("2024-02-01", 30.0),
            _transaction("2024-12-01", -40.0, SAVINGS),
        ]

        assert TransactionGrouper(transactions).group_by_month() == {
            2024: [
                MonthlySummary(2024, 2, 30.0, 0, 1, ["00001"]),
                MonthlySummary(2024, 12, 0, 60.0, 2, ["00001", "00002"]),
            ],
            2025: [MonthlySummary(2025, 1, 0, 10.0, 1, ["00001"])],
        }
