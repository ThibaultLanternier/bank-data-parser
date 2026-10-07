import logging
from datetime import datetime
from pathlib import Path

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.source_type import SourceType
from entities.transaction import Transaction
from services.bank_data_reader import BankDataReader

logger = logging.getLogger(__name__)

# Non-investment transaction lists: bank, cash, credit card, other asset/liability
_TRANSACTION_TYPES = ("bank", "cash", "ccard", "oth a", "oth l")

# QIF has no standard date format, Boursobank exports DD/MM/YYYY
_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%d/%m'%y")


class QifBankDataReader(BankDataReader):
    """Reads QIF (Quicken Interchange Format) files."""

    def read(self, paths: list[Path]) -> list[Transaction]:
        transactions = []
        for path in paths:
            transactions.extend(self._read_file(path))
        logger.info("Read %d transactions from %d files", len(transactions), len(paths))
        return transactions

    def _read_file(self, path: Path) -> list[Transaction]:
        logger.debug("Reading file: %s", path)
        # QIF exported by Quicken is usually windows-1252, Boursobank exports UTF-8
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = path.read_text(encoding="cp1252")

        # QIF has no account information unless an !Account header is present,
        # the file name is used instead
        account = Account(path.stem, path.stem)
        section = ""
        transactions = []
        for record in self._parse_records(content):
            if "!" in record:
                section = record["!"].lower()
            elif section == "account":
                name = record.get("N")
                if name:
                    account = Account(name, name)
            elif section in _TRANSACTION_TYPES:
                transactions.append(self._parse_transaction(record, account, path))
        return transactions

    def _parse_records(self, content: str) -> list[dict[str, str]]:
        # Each line starts with a one character field code, records end with "^".
        # Only the first value of a field is kept (split lines repeat S, E and $ codes)
        records = []
        record: dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("!"):
                header = line[1:]
                # "!Type:Bank" switches section, "!Account" announces account records
                key, _, value = header.partition(":")
                if key.lower() == "type":
                    records.append({"!": value.strip()})
                elif key.lower() == "account":
                    records.append({"!": "account"})
                elif key.lower() == "clear":
                    continue
                else:
                    records.append({"!": header})
                continue
            if line == "^":
                records.append(record)
                record = {}
                continue
            record.setdefault(line[0], line[1:].strip())
        if record:
            records.append(record)
        return records

    def _parse_transaction(self, record: dict[str, str], account: Account, path: Path) -> Transaction:
        date = self._parse_date(record.get("D", ""))
        if date is None:
            raise ValueError(f"Invalid or missing date in QIF transaction: {record}")

        amount = record.get("T") or record.get("U")
        if not amount:
            raise ValueError(f"Missing amount in QIF transaction: {record}")

        payee = record.get("P", "")
        memo = record.get("M", "")
        raw_label = f"{payee} {memo}".strip()

        return Transaction(
            dateOperation=date,
            # QIF has no value date
            dateValue=date,
            # Same "label | raw label" layout as the CSV export, so Label can detect
            # the transaction type and the credit card number
            label=Label(f"{raw_label} | {raw_label}"),
            category=self._parse_category(record.get("L", "")),
            account=account,
            amount=self._parse_amount(amount),
            source_type=SourceType.QIF,
            source_file=path.name,
            # QIF "N" field holds the check number or a reference
            bank_transaction_id=record.get("N") or None,
        )

    def _parse_category(self, value: str) -> Category:
        # "Parent:Sub/Class", transfers are written "[Account]"
        value = value.split("/", 1)[0].strip()
        if ":" in value:
            parent, category = value.rsplit(":", 1)
            return Category(category.strip(), parent.strip())
        return Category(value)

    def _parse_amount(self, value: str) -> float:
        value = value.replace("\xa0", "").replace(" ", "")
        if "," in value and "." in value:
            # "1,000.00": comma is the thousands separator
            value = value.replace(",", "")
        return float(value.replace(",", "."))

    def _parse_date(self, value: str) -> datetime | None:
        value = value.replace(" ", "")
        for date_format in _DATE_FORMATS:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
        return None
