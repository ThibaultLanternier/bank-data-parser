import csv
from datetime import datetime
from pathlib import Path

from entities.transaction import transaction

OUTPUT_DIR = Path(__file__).parent.parent / "output"

FIELDNAMES = [
    "dateOperation",
    "dateValue",
    "label",
    "raw_label",
    "type",
    "credit_card_number",
    "payment_type",
    "category",
    "category_parent",
    "account_number",
    "account_label",
    "is_debit",
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
                    "label": t.label.get_label(),
                    "raw_label": t.label.raw_label,
                    "type": t.label.get_type().value,
                    "credit_card_number": t.label.get_credit_card_number(),
                    "payment_type": "CB" if t.label.get_credit_card_number() else "DEBIT",
                    "category": t.category.category,
                    "category_parent": t.category.parent_category,
                    "account_number": t.account.account_number,
                    "account_label": t.account.account_label,
                    "is_debit": t.amount < 0,
                    "amount": f"{t.amount:.2f}".replace(".", ","),
                })

        return output_path
