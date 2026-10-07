from datetime import datetime

import pytest

from entities.label import TransactionType
from entities.source_type import SourceType
from services.ofx_bank_data_reader import OfxBankDataReader

OFX_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<?OFX OFXHEADER="200" VERSION="220" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE" ?>
<OFX><BANKMSGSRSV1><STMTTRNRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS><CURDEF>EUR</CURDEF>
<BANKACCTFROM><BANKID>abc</BANKID><ACCTID>00040079727</ACCTID><ACCTTYPE>CHECKINGS</ACCTTYPE></BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN><DTPOSTED>20261002</DTPOSTED><TRNTYPE>DEBIT</TRNTYPE><TRNAMT>-92.72</TRNAMT><FITID>fit1</FITID><NAME>CARTE 01/10/26 LIDL 2652 CB*6863</NAME><DTUSER>40797230</DTUSER></STMTTRN>
<STMTTRN><DTPOSTED>20261001120000.000[+1:CET]</DTPOSTED><TRNTYPE>CREDIT</TRNTYPE><TRNAMT>3000.00</TRNAMT><FITID>fit2</FITID><NAME>VIR SEPA M. DUPONT &amp; FILS</NAME><DTUSER>20260930</DTUSER><DTAVAIL>20261003</DTAVAIL></STMTTRN>
<DTSTART>20260901</DTSTART><DTEND>20261002</DTEND></BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1>
<CREDITCARDMSGSRSV1><CCSTMTTRNRS><CCSTMTRS><CURDEF>EUR</CURDEF>
<CCACCTFROM><ACCTID>4970XXXX6863</ACCTID></CCACCTFROM>
<BANKTRANLIST><STMTTRN><DTPOSTED>20260915</DTPOSTED><TRNTYPE>POS</TRNTYPE><TRNAMT>-14,99</TRNAMT><FITID>fit3</FITID><NAME>NETFLIX</NAME><MEMO>STREAMING</MEMO></STMTTRN></BANKTRANLIST>
</CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1></OFX>
"""


@pytest.fixture
def transactions(tmp_path):
    path = tmp_path / "export.ofx"
    path.write_text(OFX_CONTENT, encoding="utf-8")
    return OfxBankDataReader().read([path])


class TestOfxBankDataReader:
    def test_reads_all_statements(self, transactions):
        assert len(transactions) == 3

    def test_parses_card_transaction(self, transactions):
        t = transactions[0]
        assert t.amount == -92.72
        assert t.account.account_number == "00040079727"
        assert t.account.account_label == "00040079727"
        assert t.label.get_label() == "lidl"
        assert t.label.get_type() == TransactionType.CARD
        assert t.label.get_credit_card_number() == "*6863"
        assert t.category.category == ""

    def test_invalid_dtuser_falls_back_to_dtposted(self, transactions):
        t = transactions[0]
        assert t.dateOperation == datetime(2026, 10, 2)
        assert t.dateValue == datetime(2026, 10, 2)

    def test_uses_dtuser_and_dtavail_when_valid(self, transactions):
        t = transactions[1]
        assert t.dateOperation == datetime(2026, 9, 30)
        assert t.dateValue == datetime(2026, 10, 3)

    def test_unescapes_xml_entities(self, transactions):
        assert transactions[1].label.get_label() == "m. dupont & fils"
        assert transactions[1].label.get_type() == TransactionType.VIR_SEPA

    def test_sets_source_and_ofx_fields(self, transactions):
        t = transactions[1]
        assert t.source_type == SourceType.OFX
        assert t.source_file == "export.ofx"
        assert t.bank_transaction_id == "fit2"
        assert t.bank_transaction_type == "CREDIT"

    def test_reads_credit_card_statement(self, transactions):
        t = transactions[2]
        assert t.account.account_number == "4970XXXX6863"
        assert t.amount == -14.99
        assert t.label.get_label() == "netflix streaming"
        assert t.bank_transaction_type == "POS"

    def test_raises_on_missing_dtposted(self, tmp_path):
        path = tmp_path / "bad.ofx"
        path.write_text(
            "<OFX><STMTRS><BANKACCTFROM><ACCTID>1</ACCTID></BANKACCTFROM>"
            "<STMTTRN><TRNAMT>1.00</TRNAMT></STMTTRN></STMTRS></OFX>",
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            OfxBankDataReader().read([path])
