import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.source_type import SourceType
from entities.transaction import Transaction
from services.bank_data_reader import BankDataReader

logger = logging.getLogger(__name__)

# Bank statements (STMTRS) and credit card statements (CCSTMTRS)
_STATEMENT_TAGS = ("STMTRS", "CCSTMTRS")
_ACCOUNT_TAGS = ("BANKACCTFROM", "CCACCTFROM")


class OfxBankDataReader(BankDataReader):
    """Reads OFX 2.x (XML) files as described in the OFX Banking Specification."""

    def read(self, paths: list[Path]) -> list[Transaction]:
        transactions = []
        for path in paths:
            transactions.extend(self._read_file(path))
        logger.info("Read %d transactions from %d files", len(transactions), len(paths))
        return transactions

    def _read_file(self, path: Path) -> list[Transaction]:
        logger.debug("Reading file: %s", path)
        root = ET.parse(path).getroot()
        transactions = []
        for tag in _STATEMENT_TAGS:
            for statement in root.iter(tag):
                account = self._parse_account(statement)
                for stmttrn in statement.iter("STMTTRN"):
                    transactions.append(self._parse_transaction(stmttrn, account, path))
        return transactions

    def _parse_account(self, statement: ET.Element) -> Account:
        for tag in _ACCOUNT_TAGS:
            account_from = statement.find(tag)
            if account_from is not None:
                account_id = self._get_text(account_from, "ACCTID")
                # OFX does not provide an account label, the account id is used instead
                return Account(account_id, account_id)
        raise ValueError("No account information found in OFX statement")

    def _parse_transaction(self, stmttrn: ET.Element, account: Account, path: Path) -> Transaction:
        date_posted = self._parse_date(self._get_text(stmttrn, "DTPOSTED"))
        if date_posted is None:
            raise ValueError("Invalid or missing DTPOSTED in OFX transaction")

        name = self._get_text(stmttrn, "NAME")
        memo = self._get_text(stmttrn, "MEMO")
        raw_label = f"{name} {memo}".strip()

        return Transaction(
            dateOperation=self._parse_date(self._get_text(stmttrn, "DTUSER")) or date_posted,
            dateValue=self._parse_date(self._get_text(stmttrn, "DTAVAIL")) or date_posted,
            # Same "label | raw label" layout as the CSV export, so Label can detect
            # the transaction type and the credit card number
            label=Label(f"{raw_label} | {raw_label}"),
            # OFX has no category
            category=Category(""),
            account=account,
            amount=float(self._get_text(stmttrn, "TRNAMT").replace(",", ".")),
            source_type=SourceType.OFX,
            source_file=path.name,
            bank_transaction_id=self._get_text(stmttrn, "FITID") or None,
            bank_transaction_type=self._get_text(stmttrn, "TRNTYPE") or None,
        )

    def _get_text(self, element: ET.Element, tag: str) -> str:
        child = element.find(tag)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    def _parse_date(self, value: str) -> datetime | None:
        # OFX dates are YYYYMMDD[HHMMSS[.XXX][[gmt offset:tz name]]], only the day is kept
        try:
            return datetime.strptime(value[:8], "%Y%m%d")
        except ValueError:
            # Some banks (e.g. Boursobank) fill DTUSER with invalid values
            return None
