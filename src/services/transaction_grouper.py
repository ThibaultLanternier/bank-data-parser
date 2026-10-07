from dataclasses import dataclass
from datetime import date

from entities.transaction import Transaction


@dataclass
class MonthlySummary:
    year: int
    month: int
    first_date: date  # operation date of the first transaction of the month
    last_date: date  # operation date of the last transaction of the month
    total_income: float  # transfers between accounts excluded
    total_expenses: float  # transfers between accounts excluded, positive sum of the debits
    total_transfers: float  # credit side of the transfers between accounts
    transaction_count: int
    account_numbers: list[str]


class TransactionGrouper:
    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions

    def group_by_month(self) -> dict[int, list[MonthlySummary]]:
        """Summaries of the transactions per month (operation date), grouped by year, in chronological order."""
        months: dict[tuple[int, int], list[Transaction]] = {}
        for t in self.transactions:
            months.setdefault((t.dateOperation.year, t.dateOperation.month), []).append(t)

        by_year: dict[int, list[MonthlySummary]] = {}
        for (year, month), transactions in sorted(months.items()):
            by_year.setdefault(year, []).append(self._summarize(year, month, transactions))
        return by_year

    @staticmethod
    def _summarize(year: int, month: int, transactions: list[Transaction]) -> MonthlySummary:
        external = [t for t in transactions if not t.is_internal]
        dates = [t.dateOperation.date() for t in transactions]
        return MonthlySummary(
            year=year,
            month=month,
            first_date=min(dates),
            last_date=max(dates),
            total_income=round(sum(t.amount for t in external if t.amount > 0), 2),
            total_expenses=round(-sum(t.amount for t in external if t.amount < 0), 2),
            total_transfers=round(sum(t.amount for t in transactions if t.is_internal and t.amount > 0), 2),
            transaction_count=len(transactions),
            account_numbers=sorted({t.account.account_number for t in transactions}),
        )
