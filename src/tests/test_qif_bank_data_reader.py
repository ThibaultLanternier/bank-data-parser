from datetime import datetime

import pytest

from entities.account import Account
from entities.label import TransactionType
from entities.source_type import SourceType
from services.qif_bank_data_reader import UNKNOWN_ACCOUNT, QIFBankDataReader

QIF_CONTENT = """!Type:Bank
D02/10/2026
T-8.00
PCARTE 01/10/26 SURF SHOP CB*1234
LRestaurants, bars, discothèques…
^
D02/10/2026
T3,000.00
PVIR SEPA JOHN DOE
LRevenus placement immobiliers
^
D14/09/2026
T-120.00
PCHQ. N.0000001
N0000001
MBirthday gift
CX
LChèques
^
"""


@pytest.fixture
def qif_file(tmp_path):
    path = tmp_path / "export.qif"
    path.write_text(QIF_CONTENT, encoding="utf-8")
    return path


class TestRead:
    def test_reads_all_transactions(self, qif_file):
        transactions = QIFBankDataReader().read([qif_file])
        assert len(transactions) == 3

    def test_reads_multiple_files(self, qif_file, tmp_path):
        other = tmp_path / "other.qif"
        other.write_text(QIF_CONTENT, encoding="utf-8")
        assert len(QIFBankDataReader().read([qif_file, other])) == 6

    def test_card_transaction(self, qif_file):
        t = QIFBankDataReader().read([qif_file])[0]
        assert t.dateOperation == datetime(2026, 10, 2)
        assert t.dateValue == datetime(2026, 10, 2)
        assert t.amount == -8.00
        assert t.category.category == "Restaurants, bars, discothèques…"
        assert t.category.parent_category is None
        assert t.label.get_label() == "surf shop"
        assert t.label.get_type() == TransactionType.CARD
        assert t.label.get_credit_card_number() == "*1234"

    def test_amount_with_thousands_separator(self, qif_file):
        t = QIFBankDataReader().read([qif_file])[1]
        assert t.amount == 3000.00
        assert t.label.get_type() == TransactionType.VIR_SEPA

    def test_optional_fields(self, qif_file):
        t = QIFBankDataReader().read([qif_file])[2]
        assert t.memo == "Birthday gift"
        assert t.check_number == "0000001"
        assert t.cleared_status == "X"
        assert t.label.get_type() == TransactionType.CHQ

    def test_source(self, qif_file):
        t = QIFBankDataReader().read([qif_file])[0]
        assert t.source_type == SourceType.QIF
        assert t.source_file == qif_file

    def test_default_account_is_unknown(self, qif_file):
        t = QIFBankDataReader().read([qif_file])[0]
        assert t.account is UNKNOWN_ACCOUNT

    def test_provided_account(self, qif_file):
        account = Account("00012345678", "Compte courant")
        t = QIFBankDataReader(account).read([qif_file])[0]
        assert t.account is account

    def test_account_header(self, tmp_path):
        path = tmp_path / "account.qif"
        path.write_text(
            "!Account\nNChecking\nDMain account\nTBank\n^\n"
            "!Type:Bank\nD01/09/2026\nT-1.30\nPCARTE 28/08/26 BAKERY CB*1234\n^\n",
            encoding="utf-8",
        )
        t = QIFBankDataReader().read([path])[0]
        assert t.account.account_number == "Checking"
        assert t.account.account_label == "Main account"

    def test_skips_unsupported_sections(self, tmp_path):
        path = tmp_path / "mixed.qif"
        path.write_text(
            "!Type:Cat\nNFood\nE\n^\n"
            "!Type:Bank\nD01/09/2026\nT-1.30\nPBAKERY\n^\n",
            encoding="utf-8",
        )
        assert len(QIFBankDataReader().read([path])) == 1

    def test_skips_incomplete_record(self, tmp_path):
        path = tmp_path / "incomplete.qif"
        path.write_text("!Type:Bank\nPNO DATE\nT-1.00\n^\n", encoding="utf-8")
        assert QIFBankDataReader().read([path]) == []

    def test_crlf_line_endings(self, tmp_path):
        path = tmp_path / "crlf.qif"
        path.write_bytes(QIF_CONTENT.replace("\n", "\r\n").encode("utf-8"))
        assert len(QIFBankDataReader().read([path])) == 3


class TestParseDate:
    @pytest.mark.parametrize("value", ["02/10/2026", "02/10/26", "02/10'26", " 2/10'26"])
    def test_supported_formats(self, value):
        assert QIFBankDataReader()._parse_date(value) == datetime(2026, 10, 2)

    def test_unsupported_format(self):
        with pytest.raises(ValueError):
            QIFBankDataReader()._parse_date("2026.10.02")


class TestParseAmount:
    @pytest.mark.parametrize("value,expected", [
        ("-8.00", -8.0),
        ("3000.00", 3000.0),
        ("-1,234.56", -1234.56),
        ("-1234,56", -1234.56),
        ("1 234.56", 1234.56),
    ])
    def test_amounts(self, value, expected):
        assert QIFBankDataReader()._parse_amount(value) == expected


class TestParseCategory:
    def test_simple(self):
        category = QIFBankDataReader()._parse_category("Alimentation")
        assert category.category == "Alimentation"
        assert category.parent_category is None

    def test_sub_category(self):
        category = QIFBankDataReader()._parse_category("Auto:Fuel")
        assert category.category == "Fuel"
        assert category.parent_category == "Auto"

    def test_class_is_removed(self):
        category = QIFBankDataReader()._parse_category("Auto:Fuel/Business")
        assert category.category == "Fuel"
        assert category.parent_category == "Auto"
