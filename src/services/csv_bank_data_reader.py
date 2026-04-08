import csv
from datetime import datetime
from pathlib import Path

from entities.account import Account
from services.bank_data_reader import BankDataReader
from entities.category import Category
from entities.label import Label
from entities.transaction import transaction


class CsvBankDataReader(BankDataReader):
    def read(self, paths: list[Path]) -> list[transaction]:
        transactions = []
        for path in paths:
            transactions.extend(self._read_file(path))
        return transactions

    def _read_file(self, path: Path) -> list[transaction]:
        transactions = []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                transactions.append(self._parse_row(row))
        return transactions

    def _parse_row(self, row: dict) -> transaction:
        return transaction(
            dateOperation=datetime.strptime(row["dateOp"], "%Y-%m-%d"),
            dateValue=datetime.strptime(row["dateVal"], "%Y-%m-%d"),
            label=Label(row["label"]),
            category=Category(row["category"], row["categoryParent"]),
            account=Account(row["accountNum"], row["accountLabel"]),
            amount=self._parse_amount(row["amount"]),
        )

    def _parse_amount(self, value: str) -> float:
        # Handles French number format: "1 100,00" or "-1,95"
        # The thousands separator may be a regular or non-breaking space
        return float(value.replace("\xa0", "").replace(" ", "").replace(",", "."))
