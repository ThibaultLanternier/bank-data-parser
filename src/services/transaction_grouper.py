from dataclasses import dataclass

from entities.transaction import Transaction


@dataclass
class MonthlySummary:
    year: int
    month: int
    total_income: float
    total_expenses: float  # positive value: sum of the absolute amounts of the debits
    transaction_count: int
    account_numbers: list[str]


class TransactionGrouper:
    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions

    def group_by_month(self) -> dict[int, list[MonthlySummary]]:
        """Summaries of the transactions per month (operation date), grouped by year, both in chronological order."""
        months: dict[tuple[int, int], list[Transaction]] = {}
        for t in self.transactions:
            months.setdefault((t.dateOperation.year, t.dateOperation.month), []).append(t)

        by_year: dict[int, list[MonthlySummary]] = {}
        for (year, month), transactions in sorted(months.items()):
            by_year.setdefault(year, []).append(self._summarize(year, month, transactions))
        return by_year

    @staticmethod
    def _summarize(year: int, month: int, transactions: list[Transaction]) -> MonthlySummary:
        return MonthlySummary(
            year=year,
            month=month,
            total_income=round(sum(t.amount for t in transactions if t.amount > 0), 2),
            total_expenses=round(-sum(t.amount for t in transactions if t.amount < 0), 2),
            transaction_count=len(transactions),
            account_numbers=sorted({t.account.account_number for t in transactions}),
        )
