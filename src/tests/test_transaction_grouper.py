from datetime import date, datetime

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from services.transaction_grouper import MonthlySummary, TransactionGrouper

MAIN = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings Account")


def _transaction(date: str, amount: float, account: Account = MAIN, is_internal: bool = False) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    t = Transaction(day, day, Label("Label | LABEL"), Category("misc"), account, amount)
    t.is_internal = is_internal
    return t


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
            2024: [
                MonthlySummary(2024, 1, date(2024, 1, 5), date(2024, 1, 26), 3000.3, 100.0, 0, 5, ["00001", "00002"]),
            ],
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
                MonthlySummary(2024, 2, date(2024, 2, 1), date(2024, 2, 1), 30.0, 0, 0, 1, ["00001"]),
                MonthlySummary(2024, 12, date(2024, 12, 1), date(2024, 12, 31), 0, 60.0, 0, 2, ["00001", "00002"]),
            ],
            2025: [MonthlySummary(2025, 1, date(2025, 1, 3), date(2025, 1, 3), 0, 10.0, 0, 1, ["00001"])],
        }

    def test_excludes_transfers_from_income_and_expenses(self):
        transactions = [
            _transaction("2024-03-01", 2000.0),
            _transaction("2024-03-02", -50.0),
            _transaction("2024-03-05", -500.0, is_internal=True),
            _transaction("2024-03-05", 500.0, SAVINGS, is_internal=True),
            _transaction("2024-03-20", -200.0, SAVINGS, is_internal=True),
            _transaction("2024-03-20", 200.0, is_internal=True),
        ]

        assert TransactionGrouper(transactions).group_by_month() == {
            2024: [
                MonthlySummary(2024, 3, date(2024, 3, 1), date(2024, 3, 20), 2000.0, 50.0, 700.0, 6, ["00001", "00002"]),
            ],
        }
