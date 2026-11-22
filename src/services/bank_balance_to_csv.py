import csv
from datetime import datetime
from pathlib import Path

from services import file_recorder
from services.bank_balance import BankBalance

FIELDNAMES = [
    "account_number",
    "account_label",
    "date",
    "start_balance",
    "total",
    "end_balance",
    "transaction_count",
    "is_inferred",
    "gap",
    "conflict",
    "source_file",
]


def _format(value: float | None) -> str:
    # Comma as decimal, like the other CSV outputs
    return "" if value is None else f"{value:.2f}".replace(".", ",")


class BankBalanceToCSV:
    """Write the kept days of a BankBalance, one row per account and day, to analyze and debug the history."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir

    def write_csv(self, bank_balance: BankBalance, filename: str | None = None) -> Path:
        if filename is None:
            filename = f"balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = (self.output_dir or file_recorder.OUTPUT_DIR) / filename

        # Gaps are reported on the day that starts at an unexpected balance
        gaps = {(g.account_number, g.date): g.missing_amount for g in bank_balance.gaps}
        conflicts = {(c.account_number, c.date) for c in bank_balance.conflicts}

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()
            for account, days in bank_balance.get_days().items():
                for day in days:
                    key = (account, day.start_date)
                    writer.writerow({
                        "account_number": account,
                        "account_label": day.transactions[0].account.account_label,
                        "date": day.start_date.strftime("%Y-%m-%d"),
                        "start_balance": _format(day.start_balance),
                        "total": _format(day.total),
                        "end_balance": _format(day.end_balance),
                        "transaction_count": len(day.transactions),
                        "is_inferred": "INFERRED" if day.is_inferred else "",
                        "gap": _format(gaps.get(key)),
                        "conflict": "CONFLICT" if key in conflicts else "",
                        "source_file": day.transactions[0].source_file,
                    })

        return output_path
