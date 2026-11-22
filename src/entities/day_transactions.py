from datetime import datetime

from entities.transaction import Transaction


class DayTransactions:
    """Transactions of one account booked on one day (operation date), read from one file."""

    def __init__(self, account_number: str, start_date: datetime, transactions: list[Transaction]):
        self.account_number = account_number
        self.start_date = start_date  # operation date at 00:00
        self.transactions = transactions
        self.start_balance: float | None = None
        self.end_balance: float | None = None  # account balance at 00:00 the next day
        self.is_inferred = False  # end balance computed from the previous day, not read from the bank

    @property
    def total(self) -> float:
        return round(sum(t.amount for t in self.transactions), 2)

    @staticmethod
    def from_transactions(transactions: list[Transaction]) -> list["DayTransactions"]:
        """One record per account, operation date and source file, in read order."""
        by_key: dict[tuple[str, datetime, str], list[Transaction]] = {}
        for t in transactions:
            day = t.dateOperation.replace(hour=0, minute=0, second=0, microsecond=0)
            by_key.setdefault((t.account.account_number, day, t.source_file), []).append(t)
        return [DayTransactions(account, day, day_transactions) for (account, day, _), day_transactions in by_key.items()]
