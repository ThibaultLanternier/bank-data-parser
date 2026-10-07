from datetime import datetime

import pytest

from entities.label import TransactionType
from services.csv_bank_data_reader import CsvBankDataReader

OLD_FORMAT = (
    "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance\n"
    '2026-03-31;2026-03-31;"M | CARTE 30/03/26 M H CB*5252";"Restaurants, bars, discothèques…";"Loisirs et sorties";"maison hector";-7,90;;00040811579;"BOURSORAMA ESSENTIEL - Clément";258.29\n'
    '2026-03-30;2026-03-30;"Boulangerie Rt | CARTE 27/03/26 BOULANGERIE RT CB*5252";Alimentation;"Vie quotidienne";"boulangerie rt";-1 104,95;;00040811579;"BOURSORAMA ESSENTIEL - Clément";266.19\n'
)

NEW_FORMAT = (
    '"Date Opération";"Date Valeur";Libellé;"Libellé Suggéré";Catégorie;"Catégorie Parente";Solde;Commentaire;"Numéro Compte";"Libellé Compte";Solde;Pointage\n'
    '2026-10-02;2026-10-01;"CARTE 01/10/26 ZEPHYR SURF CB*3657";"Zephyr Surf";"Restaurants, bars, discothèques…";"Loisirs et sorties";-8,00;;00040079727;"BoursoBank (joint)";13853.59;Non\n'
    '2026-10-02;2026-10-02;"CARTE 01/10/26 MIGNON CAFE CB*3657";"Mignon Café";"Restaurants, bars, discothèques…";"Loisirs et sorties";-1 126,00;;00040079727;"BoursoBank (joint)";13853.59;Non\n'
    '2026-10-02;2026-10-02;"VIR SEPA SOMEONE";"";"Non catégorisé";"Non catégorisé";2,70;;00040079727;"BoursoBank (joint)";13853.59;Non\n'
)


def _write(tmp_path, content: str):
    path = tmp_path / "export.csv"
    path.write_text(content, encoding="utf-8-sig")
    return path


class TestOldFormat:
    def test_reads_all_rows(self, tmp_path):
        transactions = CsvBankDataReader().read([_write(tmp_path, OLD_FORMAT)])
        assert len(transactions) == 2

    def test_parses_fields(self, tmp_path):
        t = CsvBankDataReader().read([_write(tmp_path, OLD_FORMAT)])[0]
        assert t.dateOperation == datetime(2026, 3, 31)
        assert t.amount == pytest.approx(-7.90)
        assert t.label.get_label() == "m"
        assert t.label.get_type() == TransactionType.CARD
        assert t.label.get_credit_card_number() == "*5252"
        assert t.category.category == "Restaurants, bars, discothèques…"
        assert t.category.parent_category == "Loisirs et sorties"
        assert t.account.account_number == "00040811579"
        assert t.account.account_label == "BOURSORAMA ESSENTIEL - Clément"

    def test_parses_thousands_separator(self, tmp_path):
        t = CsvBankDataReader().read([_write(tmp_path, OLD_FORMAT)])[1]
        assert t.amount == pytest.approx(-1104.95)


class TestNewFormat:
    def test_reads_all_rows(self, tmp_path):
        transactions = CsvBankDataReader().read([_write(tmp_path, NEW_FORMAT)])
        assert len(transactions) == 3

    def test_parses_fields(self, tmp_path):
        t = CsvBankDataReader().read([_write(tmp_path, NEW_FORMAT)])[0]
        assert t.dateOperation == datetime(2026, 10, 2)
        assert t.dateValue == datetime(2026, 10, 1)
        assert t.label.get_label() == "zephyr surf"
        assert t.label.get_type() == TransactionType.CARD
        assert t.label.get_credit_card_number() == "*3657"
        assert t.category.category == "Restaurants, bars, discothèques…"
        assert t.category.parent_category == "Loisirs et sorties"
        assert t.account.account_number == "00040079727"
        assert t.account.account_label == "BoursoBank (joint)"

    def test_amount_uses_first_solde_column(self, tmp_path):
        transactions = CsvBankDataReader().read([_write(tmp_path, NEW_FORMAT)])
        assert transactions[0].amount == pytest.approx(-8.00)
        assert transactions[1].amount == pytest.approx(-1126.00)

    def test_empty_suggested_label_falls_back_to_raw_label(self, tmp_path):
        t = CsvBankDataReader().read([_write(tmp_path, NEW_FORMAT)])[2]
        assert t.label.get_label() == "someone"
        assert t.label.get_type() == TransactionType.VIR_SEPA


def test_reads_mixed_formats(tmp_path):
    old_path = tmp_path / "old.csv"
    new_path = tmp_path / "new.csv"
    old_path.write_text(OLD_FORMAT, encoding="utf-8-sig")
    new_path.write_text(NEW_FORMAT, encoding="utf-8-sig")
    transactions = CsvBankDataReader().read([old_path, new_path])
    assert len(transactions) == 5
