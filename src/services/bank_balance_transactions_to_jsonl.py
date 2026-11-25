import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from entities.transaction import Transaction
from services import file_recorder
from services.bank_balance import BankBalance


def _day(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


def _id_values(t: Transaction) -> tuple[str, ...]:
    # The suggested label is left out: the bank's enrichment can change between exports
    return (
        t.account.account_number,
        t.dateOperation.isoformat(),
        t.dateValue.isoformat(),
        f"{t.amount:.2f}",
        t.label.get_bank_label(),
    )


def _export_ids(transactions: list[Transaction]) -> list[str]:
    """Stable ids of the transactions of a day record, identical rows told apart by their occurrence index."""
    seen: Counter[tuple[str, ...]] = Counter()
    ids = []
    for t in transactions:
        values = _id_values(t)
        data = "||".join([*values, str(seen[values])])
        seen[values] += 1
        ids.append(hashlib.md5(data.encode()).hexdigest())
    return ids


class BankBalanceTransactionsToJsonl:
    """Write the transactions of a BankBalance as JSON lines, one per transaction, to import into Loki with Alloy."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir

    def write_jsonl(
        self,
        bank_balance: BankBalance,
        filename: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Path:
        if filename is None:
            filename = f"balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        output_path = (self.output_dir or file_recorder.OUTPUT_DIR) / filename

        lines = []
        for account, days in sorted(bank_balance.get_daily_series(date_from, date_to).items()):
            account_label = bank_balance.get_account_label(account) or None
            records = [
                (t, export_id) for day in days for t, export_id in zip(day.transactions, _export_ids(day.transactions))
            ]
            # Stable sort: each Loki stream is written in time order, ties in read order
            for t, export_id in sorted(records, key=lambda r: r[0].dateValue):
                record = {
                    "id": export_id,
                    "timestamp": t.dateValue.strftime("%Y-%m-%dT00:00:00Z"),
                    "date_value": _day(t.dateValue),
                    "date_operation": _day(t.dateOperation),
                    "account": account,
                    "account_label": account_label,
                    "amount": t.amount,
                    "label": t.label.get_bank_label(),
                    "normalized_label": t.label.get_normalized_label(),
                    "category": t.category.category or None,
                    "parent_category": t.category.parent_category or None,
                    "balance": t.balance,
                }
                # Nothing from the source file nor the export time: the same transaction gives the same line
                lines.append(json.dumps(record, ensure_ascii=False))

        output_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
        return output_path
