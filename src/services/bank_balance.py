import logging
from dataclasses import dataclass
from datetime import datetime

from entities.day_transactions import DayTransactions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalanceConflict:
    """Two versions of the same day with as many transactions but different amounts."""

    account_number: str
    date: datetime


class BankBalance:
    """Day by day balance of each account, built from the day records of all CSV files."""

    def __init__(self, day_transactions: list[DayTransactions]):
        self.conflicts: list[BalanceConflict] = []
        self._days = self._deduplicate(day_transactions)

    def get_days(self) -> dict[str, list[DayTransactions]]:
        """Kept day records per account number, ordered by date."""
        by_account: dict[str, list[DayTransactions]] = {}
        for day in self._days.values():
            by_account.setdefault(day.account_number, []).append(day)
        return {account: sorted(days, key=lambda d: d.start_date) for account, days in by_account.items()}

    def _deduplicate(self, day_transactions: list[DayTransactions]) -> dict[tuple[str, datetime], DayTransactions]:
        kept: dict[tuple[str, datetime], DayTransactions] = {}
        for day in day_transactions:
            key = (day.account_number, day.start_date)
            current = kept.get(key)
            if current is None or len(day.transactions) > len(current.transactions):
                kept[key] = day
            elif len(day.transactions) == len(current.transactions) and _amounts(day) != _amounts(current):
                # Same size, different content: keep the first one read and report it
                conflict = BalanceConflict(*key)
                if conflict not in self.conflicts:
                    logger.warning("Conflicting versions of %s on %s", key[0], key[1].date())
                    self.conflicts.append(conflict)
        return kept


def _amounts(day: DayTransactions) -> list[float]:
    return sorted(round(t.amount, 2) for t in day.transactions)
