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


@dataclass(frozen=True)
class BalanceGap:
    """The balance moved by more than the transactions between two consecutive days: transactions are missing."""

    account_number: str
    previous_date: datetime
    date: datetime
    missing_amount: float  # start balance of the day minus end balance of the previous day


class BankBalance:
    """Day by day balance of each account, built from the day records of all CSV files."""

    def __init__(self, day_transactions: list[DayTransactions]):
        self.conflicts: list[BalanceConflict] = []
        self._days = self._deduplicate(day_transactions)
        self._resolve_balances()
        self.gaps = self._find_gaps()

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

    def _resolve_balances(self) -> None:
        balances = self._balances_by_value_date()
        for account, days in self.get_days().items():
            previous_end: float | None = None
            for day in days:
                day.end_balance = balances.get((account, day.start_date))
                day.is_inferred = False
                if day.end_balance is None and previous_end is not None:
                    # No transaction gives this day's balance: carry the previous one over
                    day.end_balance = round(previous_end + day.total, 2)
                    day.is_inferred = True
                day.start_balance = None if day.end_balance is None else round(day.end_balance - day.total, 2)
                previous_end = day.end_balance

    def _find_gaps(self) -> list[BalanceGap]:
        gaps = []
        for account, days in self.get_days().items():
            for previous, day in zip(days, days[1:]):
                # An inferred day is built from the previous one and cannot reveal a gap
                if day.is_inferred or day.start_balance is None or previous.end_balance is None:
                    continue
                missing = round(day.start_balance - previous.end_balance, 2)
                if missing != 0:
                    gaps.append(BalanceGap(account, previous.start_date, day.start_date, missing))
        return gaps

    def _balances_by_value_date(self) -> dict[tuple[str, datetime], float]:
        # The balance of a transaction is the account balance at the end of its value date,
        # so a late-booked transaction gives the balance of an earlier day.
        # Only kept records are used: a discarded version never supplies a balance.
        balances: dict[tuple[str, datetime], float] = {}
        for day in self._days.values():
            for t in day.transactions:
                if t.balance is None:
                    continue
                key = (day.account_number, _midnight(t.dateValue))
                balance = round(t.balance, 2)
                if key not in balances:
                    balances[key] = balance
                elif balances[key] != balance:
                    logger.warning(
                        "Conflicting balances for %s on %s, keeping %.2f", key[0], key[1].date(), balances[key]
                    )
        return balances


def _midnight(date: datetime) -> datetime:
    return date.replace(hour=0, minute=0, second=0, microsecond=0)


def _amounts(day: DayTransactions) -> list[float]:
    return sorted(round(t.amount, 2) for t in day.transactions)
