import csv
from datetime import datetime
from pathlib import Path

import pandas as pd

from entities.transaction import Transaction

OUTPUT_DIR = Path(__file__).parent.parent / "output"

FIELDNAMES = [
    "id",
    "group_id",
    "date_operation",
    "date_value",
    "year",
    "month",
    "grouped_label",
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
    "is_internal",
    "is_large",
    "amount",
]


class FileRecorder:
    def write_csv(self, transactions: list[Transaction], filename: str | None = None) -> Path:
        if filename is None:
            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        output_path = OUTPUT_DIR / filename
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()
            for t in transactions:
                writer.writerow({
                    "id": t.id,
                    "group_id": t.group_id,
                    "date_operation": t.dateOperation.strftime("%Y-%m-%d"),
                    "date_value": t.dateValue.strftime("%Y-%m-%d"),
                    "year": t.dateOperation.year,
                    "month": t.dateOperation.month,
                    "grouped_label": t.grouped_label,
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
                    "is_internal": "INTERNAL" if t.is_internal else "",
                    "is_large": "LARGE" if t.is_large else "",
                    "amount": f"{t.amount:.2f}".replace(".", ","),
                })

        return output_path

    def write_parquet(self, transactions: list[Transaction], filename: str | None = None) -> Path:
        if filename is None:
            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"

        output_path = OUTPUT_DIR / filename
        rows = []
        for t in transactions:
            rows.append({
                "id": t.id,
                "group_id": t.group_id,
                "date_operation": t.dateOperation,
                "date_value": t.dateValue,
                "year": t.dateOperation.year,
                "month": t.dateOperation.month,
                "grouped_label": t.grouped_label,
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
                "is_internal": t.is_internal,
                "is_large": t.is_large,
                "amount": t.amount,
            })

        df = pd.DataFrame(rows)
        df.to_parquet(output_path, index=False)

        return output_path
