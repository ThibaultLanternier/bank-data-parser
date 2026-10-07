from datetime import datetime

import pytest

from entities.label import TransactionType
from entities.source_type import SourceType
from services.qif_bank_data_reader import QifBankDataReader

QIF_CONTENT = """!Type:Bank
D02/10/2026
T-92.72
PCARTE 01/10/26 LIDL 2652 CB*6863
LAlimentation
^
D01/10/2026
T3,000.00
PVIR SEPA M. DUPONT
MLOYER OCTOBRE
N1234
LRevenus:Revenus placement immobiliers
^
D30/09/2026
T-14,99
PCARTE 30/09/26 Multimédia CB*6863
LNon catégorisé
^
"""


@pytest.fixture
def transactions(tmp_path):
    path = tmp_path / "export.qif"
    path.write_text(QIF_CONTENT, encoding="utf-8")
    return QifBankDataReader().read([path])


class TestQifBankDataReader:
    def test_reads_all_transactions(self, transactions):
        assert len(transactions) == 3

    def test_parses_card_transaction(self, transactions):
        t = transactions[0]
        assert t.dateOperation == datetime(2026, 10, 2)
        assert t.dateValue == datetime(2026, 10, 2)
        assert t.amount == -92.72
        assert t.label.get_label() == "lidl"
        assert t.label.get_type() == TransactionType.CARD
        assert t.label.get_credit_card_number() == "*6863"
        assert t.category.category == "Alimentation"
        assert t.category.parent_category is None

    def test_uses_file_name_as_account(self, transactions):
        assert transactions[0].account.account_number == "export"
        assert transactions[0].account.account_label == "export"

    def test_parses_memo_number_and_parent_category(self, transactions):
        t = transactions[1]
        assert t.amount == 3000.0
        assert t.label.get_label() == "m. dupont loyer octobre"
        assert t.label.get_type() == TransactionType.VIR_SEPA
        assert t.bank_transaction_id == "1234"
        assert t.category.category == "Revenus placement immobiliers"
        assert t.category.parent_category == "Revenus"

    def test_parses_comma_decimal_and_accents(self, transactions):
        t = transactions[2]
        assert t.amount == -14.99
        assert t.label.get_label() == "multimédia"
        assert t.category.category == "Non catégorisé"

    def test_sets_source_fields(self, transactions):
        t = transactions[0]
        assert t.source_type == SourceType.QIF
        assert t.source_file == "export.qif"
        assert t.bank_transaction_id is None
        assert t.bank_transaction_type is None

    def test_uses_account_header_and_skips_other_sections(self, tmp_path):
        path = tmp_path / "quicken.qif"
        path.write_text(
            "!Type:Cat\nNAlimentation\nE\n^\n"
            "!Account\nNCompte courant\nTBank\n^\n"
            "!Type:Bank\nD01/10/26\nU-1.00\nPTEST\nSFood\n$-0.50\nSOther\n$-0.50\n^\n",
            encoding="cp1252",
        )
        transactions = QifBankDataReader().read([path])
        assert len(transactions) == 1
        assert transactions[0].account.account_number == "Compte courant"
        assert transactions[0].dateOperation == datetime(2026, 10, 1)
        assert transactions[0].amount == -1.0

    def test_reads_windows_1252_files(self, tmp_path):
        path = tmp_path / "latin.qif"
        path.write_text("!Type:Bank\nD01/10/2026\nT-1.00\nPCAFÉ\n^\n", encoding="cp1252")
        assert QifBankDataReader().read([path])[0].label.get_label() == "café"

    def test_raises_on_invalid_date(self, tmp_path):
        path = tmp_path / "bad.qif"
        path.write_text("!Type:Bank\nD2026-13-45\nT1.00\n^\n", encoding="utf-8")
        with pytest.raises(ValueError):
            QifBankDataReader().read([path])
