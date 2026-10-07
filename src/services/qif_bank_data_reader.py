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

UNKNOWN_ACCOUNT = Account("UNKNOWN", "UNKNOWN")

# QIF section types holding plain cash-flow transactions (investment, category, class
# and memorized sections use a different record layout and are skipped)
_SUPPORTED_TYPES = {"bank", "cash", "ccard", "oth a", "oth l"}

# QIF dates are locale dependent: Boursobank exports them day first ("02/10/2026"),
# Quicken may use an apostrophe before a 2-digit year ("02/10'26")
_DATE_FORMATS = ["%d/%m/%Y", "%d/%m/%y"]


class QIFBankDataReader(BankDataReader):
    def __init__(self, account: Account | None = None):
        self._default_account = account or UNKNOWN_ACCOUNT

    def read(self, paths: list[Path]) -> list[Transaction]:
        transactions = []
        for path in paths:
            transactions.extend(self._read_file(path))
        logger.info("Read %d transactions from %d files", len(transactions), len(paths))
        return transactions

    def _read_file(self, path: Path) -> list[Transaction]:
        logger.debug("Reading file: %s", path)
        transactions = []
        account = self._default_account
        section: str | None = None
        record: dict[str, str] = {}

        with open(path, encoding="utf-8-sig") as f:
            for raw_line in f:
                line = raw_line.rstrip("\r\n")
                if not line.strip():
                    continue

                if line.startswith("!"):
                    section = self._parse_header(line)
                    record = {}
                    continue

                if line.startswith("^"):
                    if section == "account":
                        account = self._parse_account(record)
                    elif section in _SUPPORTED_TYPES:
                        transaction = self._parse_record(record, account, path)
                        if transaction is not None:
                            transactions.append(transaction)
                    record = {}
                    continue

                code, value = line[0], line[1:].strip()
                # Keep the first occurrence: split lines (S, E, $) are not handled
                record.setdefault(code, value)

        return transactions

    def _parse_header(self, line: str) -> str | None:
        header = line[1:].strip().lower()
        if header == "account":
            return "account"
        if header.startswith("type:"):
            section = header[len("type:"):].strip()
            if section not in _SUPPORTED_TYPES:
                logger.debug("Skipping unsupported QIF section: %s", line)
            return section
        # !Option / !Clear headers do not change the current section
        return None

    def _parse_account(self, record: dict[str, str]) -> Account:
        name = record.get("N", "")
        if not name:
            return self._default_account
        return Account(name, record.get("D", name))

    def _parse_record(self, record: dict[str, str], account: Account, path: Path) -> Transaction | None:
        if "D" not in record or ("T" not in record and "U" not in record):
            logger.warning("Skipping incomplete QIF record in %s: %s", path, record)
            return None

        date = self._parse_date(record["D"])
        payee = record.get("P") or record.get("M", "")

        return Transaction(
            dateOperation=date,
            dateValue=date,
            # QIF only provides the raw label: use it for both parts so that
            # Label type and credit card detection keep working
            label=Label(f"{payee} | {payee}"),
            category=self._parse_category(record.get("L", "")),
            account=account,
            amount=self._parse_amount(record.get("T") or record["U"]),
            source_type=SourceType.QIF,
            source_file=path,
            memo=record.get("M", ""),
            check_number=record.get("N", ""),
            cleared_status=record.get("C", ""),
        )

    def _parse_date(self, value: str) -> datetime:
        normalized = value.replace("'", "/").replace(" ", "0")
        for date_format in _DATE_FORMATS:
            try:
                return datetime.strptime(normalized, date_format)
            except ValueError:
                continue
        raise ValueError(f"Unsupported QIF date format: {value!r}")

    def _parse_category(self, value: str) -> Category:
        # "Parent:Sub/Class": the class part is not a category
        category = value.split("/", 1)[0].strip()
        if ":" in category:
            parent, sub = category.rsplit(":", 1)
            return Category(sub.strip(), parent.strip())
        return Category(category)

    def _parse_amount(self, value: str) -> float:
        # Handles "-1,234.56" as well as a comma decimal separator "-1234,56"
        value = value.replace("\xa0", "").replace(" ", "")
        if "," in value and "." not in value:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")
        return float(value)
