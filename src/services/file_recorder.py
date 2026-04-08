import csv
from datetime import datetime
from pathlib import Path

from entities.transaction import transaction

OUTPUT_DIR = Path(__file__).parent.parent / "output"

FIELDNAMES = [
    "dateOperation",
    "dateValue",
    "label",
    "type",
    "category",
    "categoryParent",
    "accountNumber",
    "accountLabel",
    "amount",
]


class FileRecorder:
    def write_csv(self, transactions: list[transaction], filename: str | None = None) -> Path:
        if filename is None:
            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        output_path = OUTPUT_DIR / filename
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()
            for t in transactions:
                writer.writerow({
                    "dateOperation": t.dateOperation.strftime("%Y-%m-%d"),
                    "dateValue": t.dateValue.strftime("%Y-%m-%d"),
                    "label": t.label.raw_label,
                    "type": t.label.get_type().value,
                    "category": t.category.category,
                    "categoryParent": t.category.parent_category,
                    "accountNumber": t.account.account_number,
                    "accountLabel": t.account.account_label,
                    "amount": t.amount,
                })

        return output_path
