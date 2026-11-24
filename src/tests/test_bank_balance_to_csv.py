import csv
from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction
from services import file_recorder
from services.bank_balance import BankBalance
from services.bank_balance_to_csv import FIELDNAMES, BankBalanceToCSV

ACCOUNT = Account("00001", "Main Account")


def _transaction(
    amount: float, date: str, balance: float | None = None, value_date: str | None = None, source_file="a.csv"
) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    value_day = datetime.strptime(value_date, "%Y-%m-%d") if value_date else day
    return Transaction(
        day, value_day, Label("Label | LABEL"), Category("misc"), ACCOUNT, amount,
        source_file=source_file, balance=balance,
    )


def _read(path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


@pytest.fixture
def bank_balance():
    transactions = [
        _transaction(-77.97, "2022-12-30", balance=10105.11),
        _transaction(2950.0, "2023-01-02", balance=12190.6),
        _transaction(-868.5, "2023-01-02", balance=12190.6),
        _transaction(-10.0, "2023-01-03", value_date="2023-01-01", balance=10105.11),
    ]
    return BankBalance(DayTransactions.from_transactions(transactions))


class TestBankBalanceToCSV:
    def test_writes_one_row_per_calendar_day(self, tmp_path, bank_balance):
        path = BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv")

        rows = _read(path)

        assert path == tmp_path / "balance.csv"
        assert list(rows[0]) == FIELDNAMES
        assert [r["date"] for r in rows] == ["2022-12-30", "2022-12-31", "2023-01-01", "2023-01-02", "2023-01-03"]

    def test_writes_balances_in_french_format(self, tmp_path, bank_balance):
        rows = _read(BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv"))

        assert rows[3]["start_balance"] == "10109,10"
        assert rows[3]["total"] == "2081,50"
        assert rows[3]["end_balance"] == "12190,60"
        assert rows[3]["transaction_count"] == "2"
        assert rows[3]["account_number"] == "00001"
        assert rows[3]["account_label"] == "Main Account"
        assert rows[3]["source_file"] == "a.csv"

    def test_flags_gap_on_the_day_it_is_found(self, tmp_path, bank_balance):
        rows = _read(BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv"))

        assert [r["gap"] for r in rows] == ["", "", "", "3,99", ""]

    def test_flags_inferred_day(self, tmp_path, bank_balance):
        rows = _read(BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv"))

        assert [r["is_inferred"] for r in rows] == ["", "", "", "", "INFERRED"]
        assert rows[4]["end_balance"] == "12180,60"

    def test_flags_conflict(self, tmp_path):
        first = DayTransactions.from_transactions([_transaction(-10.0, "2026-09-07", source_file="a.csv")])
        second = DayTransactions.from_transactions([_transaction(-20.0, "2026-09-07", source_file="b.csv")])

        rows = _read(BankBalanceToCSV(tmp_path).write_csv(BankBalance(first + second), "balance.csv"))

        assert [(r["conflict"], r["source_file"], r["end_balance"]) for r in rows] == [("CONFLICT", "a.csv", "")]

    def test_filled_day_carries_previous_end_balance(self, tmp_path):
        transactions = [
            _transaction(-10.0, "2026-09-04", balance=1000.0),
            _transaction(-25.0, "2026-09-07", balance=975.0),
        ]
        bank_balance = BankBalance(DayTransactions.from_transactions(transactions))

        rows = _read(BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv"))

        saturday = rows[1]
        assert saturday["date"] == "2026-09-05"
        assert saturday["account_number"] == "00001"
        assert saturday["account_label"] == "Main Account"
        assert (saturday["start_balance"], saturday["end_balance"], saturday["total"]) == ("1000,00", "1000,00", "0,00")
        assert saturday["transaction_count"] == "0"
        assert [saturday[c] for c in ("is_inferred", "gap", "conflict", "source_file")] == ["", "", "", ""]

    def test_day_in_a_gap_has_empty_balances(self, tmp_path, bank_balance):
        rows = _read(BankBalanceToCSV(tmp_path).write_csv(bank_balance, "balance.csv"))

        assert [(r["date"], r["start_balance"], r["end_balance"]) for r in rows[1:3]] == [
            ("2022-12-31", "", ""),
            ("2023-01-01", "", ""),
        ]

    def test_writes_the_given_range(self, tmp_path, bank_balance):
        path = BankBalanceToCSV(tmp_path).write_csv(
            bank_balance, "balance.csv", date_from=datetime(2022, 12, 29), date_to=datetime(2023, 1, 1)
        )

        rows = _read(path)

        assert [r["date"] for r in rows] == ["2022-12-29", "2022-12-30", "2022-12-31", "2023-01-01"]
        assert rows[0]["end_balance"] == ""

    def test_defaults_to_output_dir_with_timestamped_name(self, tmp_path, monkeypatch, bank_balance):
        monkeypatch.setattr(file_recorder, "OUTPUT_DIR", tmp_path)

        path = BankBalanceToCSV().write_csv(bank_balance)

        assert path.parent == tmp_path
        assert path.name.startswith("balance_") and path.suffix == ".csv"
