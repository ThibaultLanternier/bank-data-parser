from datetime import datetime

from entities.source_type import SourceType
from services.csv_bank_data_reader import CsvBankDataReader

CSV_CONTENT = (
    "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance\n"
    "2025-02-11;2025-02-12;Carte 11/02/25 Uniqlo Opera Cb*6863 | CARTE 11/02/25 Uniqlo Opera CB*6863;"
    "Vêtements;Shopping;uniqlo;-1 100,50;;00040079727;BoursoBank;1000\n"
)


def _write_csv(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8-sig")
    return path


class TestCsvBankDataReader:
    def test_reads_transaction(self, tmp_path):
        transactions = CsvBankDataReader().read([_write_csv(tmp_path)])

        assert len(transactions) == 1
        t = transactions[0]
        assert t.dateOperation == datetime(2025, 2, 11)
        assert t.dateValue == datetime(2025, 2, 12)
        assert t.amount == -1100.50
        assert t.account.account_number == "00040079727"
        assert t.category.category == "Vêtements"
        assert t.label.get_label() == "uniqlo opera"

    def test_sets_source_metadata(self, tmp_path):
        t = CsvBankDataReader().read([_write_csv(tmp_path)])[0]

        assert t.source_type == SourceType.CSV
        assert t.source_file == "export.csv"
        assert t.bank_transaction_id is None
        assert t.bank_transaction_type is None
