from datetime import datetime

from entities.source_type import SourceType
from services.csv_bank_data_reader import CsvBankDataReader

CSV_CONTENT = (
    "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance\n"
    "2025-02-11;2025-02-12;Carte 11/02/25 Uniqlo Opera Cb*6863 | CARTE 11/02/25 UNIQLO OPERA CB*6863;"
    "Vêtements;Achats;uniqlo;-1 100,50;;00012345678;Compte courant;1000,00\n"
)


class TestCsvBankDataReader:
    def test_read_sets_source(self, tmp_path):
        path = tmp_path / "export.csv"
        path.write_text(CSV_CONTENT, encoding="utf-8-sig")

        transactions = CsvBankDataReader().read([path])

        assert len(transactions) == 1
        t = transactions[0]
        assert t.source_type == SourceType.CSV
        assert t.source_file == path
        assert t.amount == -1100.50
        assert t.dateOperation == datetime(2025, 2, 11)
        assert t.dateValue == datetime(2025, 2, 12)
        assert t.account.account_number == "00012345678"
