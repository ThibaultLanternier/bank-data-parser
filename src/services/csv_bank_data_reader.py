import csv
import logging
from datetime import datetime
from pathlib import Path

from entities.account import Account
from services.bank_data_reader import BankDataReader
from entities.category import Category
from entities.label import Label
from entities.source_type import SourceType
from entities.transaction import Transaction

logger = logging.getLogger(__name__)

# Headers used by the newer Boursobank export format, mapped to the internal keys.
# "Solde" appears twice: the first occurrence is the transaction amount,
# the second one is the account balance.
_NEW_FORMAT_HEADERS = {
    "Date Opération": "dateOp",
    "Date Valeur": "dateVal",
    "Libellé": "rawLabel",
    "Libellé Suggéré": "suggestedLabel",
    "Catégorie": "category",
    "Catégorie Parente": "categoryParent",
    "Commentaire": "comment",
    "Numéro Compte": "accountNum",
    "Libellé Compte": "accountLabel",
    "Pointage": "pointage",
}
_DUPLICATED_SOLDE_HEADERS = ["amount", "accountbalance"]


class CsvBankDataReader(BankDataReader):
    def read(self, paths: list[Path]) -> list[Transaction]:
        transactions = []
        for path in paths:
            transactions.extend(self._read_file(path))
        logger.info("Read %d transactions from %d files", len(transactions), len(paths))
        return transactions

    def _read_file(self, path: Path) -> list[Transaction]:
        logger.debug("Reading file: %s", path)
        transactions = []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader, None)
            if header is None:
                return transactions
            fieldnames = self._normalize_header(header)
            for values in reader:
                if not values:
                    continue
                transactions.append(self._parse_row(dict(zip(fieldnames, values)), path))
        return transactions

    def _normalize_header(self, header: list[str]) -> list[str]:
        if "dateOp" in header:
            return header

        logger.debug("Detected new Boursobank CSV format")
        solde_keys = iter(_DUPLICATED_SOLDE_HEADERS)
        fieldnames = []
        for column in header:
            if column == "Solde":
                fieldnames.append(next(solde_keys, column))
            else:
                fieldnames.append(_NEW_FORMAT_HEADERS.get(column, column))
        return fieldnames

    def _parse_row(self, row: dict, path: Path) -> Transaction:
        return Transaction(
            dateOperation=datetime.strptime(row["dateOp"], "%Y-%m-%d"),
            dateValue=datetime.strptime(row["dateVal"], "%Y-%m-%d"),
            label=Label(self._get_raw_label(row)),
            category=Category(row["category"], row["categoryParent"]),
            account=Account(row["accountNum"], row["accountLabel"]),
            amount=self._parse_amount(row["amount"]),
            source_type=SourceType.CSV,
            source_file=path.name,
        )

    def _get_raw_label(self, row: dict) -> str:
        if "label" in row:
            return row["label"]

        # New format splits the label in two columns: rebuild the
        # "suggested | raw" form expected by Label
        raw_label = row["rawLabel"]
        suggested_label = row.get("suggestedLabel") or raw_label
        return f"{suggested_label} | {raw_label}"

    def _parse_amount(self, value: str) -> float:
        # Handles French number format: "1 100,00" or "-1,95"
        # The thousands separator may be a regular or non-breaking space
        return float(value.replace("\xa0", "").replace(" ", "").replace(",", "."))
