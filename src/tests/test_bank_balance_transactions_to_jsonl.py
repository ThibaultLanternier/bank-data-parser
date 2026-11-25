import hashlib
import json
from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction
from services import file_recorder
from services.bank_balance import BankBalance
from services.bank_balance_transactions_to_jsonl import BankBalanceTransactionsToJsonl

MAIN = Account("00001", "Main")
SAVINGS = Account("00002", "Savings")
CARD_LABEL = "Boulangerie | CARTE 01/01/24 BOULANGERIE"


def _transaction(
    amount: float,
    date: str,
    value_date: str | None = None,
    label: str = CARD_LABEL,
    balance: float | None = None,
    account: Account = MAIN,
    source_file: str = "a.csv",
    category: Category | None = None,
) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    value_day = datetime.strptime(value_date, "%Y-%m-%d") if value_date else day
    return Transaction(
        day, value_day, Label(label), category or Category("Alimentation", "Vie quotidienne"), account, amount,
        source_file=source_file, balance=balance,
    )


def _bank_balance(transactions: list[Transaction]) -> BankBalance:
    return BankBalance(DayTransactions.from_transactions(transactions))


def _write(bank_balance: BankBalance, tmp_path, name="balance.jsonl", **kwargs):
    return BankBalanceTransactionsToJsonl(tmp_path).write_jsonl(bank_balance, name, **kwargs)


def _records(bank_balance: BankBalance, tmp_path, **kwargs) -> list[dict]:
    return [json.loads(line) for line in _write(bank_balance, tmp_path, **kwargs).read_text("utf-8").splitlines()]


class TestTransactionLines:
    def test_line_of_a_card_payment(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-12.5, "2024-01-01", "2024-01-02", balance=1523.45)])

        [line] = _write(bank_balance, tmp_path).read_text("utf-8").splitlines()

        expected_id = hashlib.md5(
            "00001||2024-01-01T00:00:00||2024-01-02T00:00:00||-12.50||carte 01/01/24 boulangerie||0".encode()
        ).hexdigest()
        assert line == json.dumps({
            "id": expected_id,
            "timestamp": "2024-01-02T00:00:00Z",
            "date_value": "2024-01-02",
            "date_operation": "2024-01-01",
            "account": "00001",
            "account_label": "Main",
            "amount": -12.5,
            "label": "carte 01/01/24 boulangerie",
            "normalized_label": "boulangerie",
            "category": "Alimentation",
            "parent_category": "Vie quotidienne",
            "balance": 1523.45,
        }, ensure_ascii=False)

    def test_missing_values_are_null(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-1.0, "2024-01-01", category=Category(""))])

        [record] = _records(bank_balance, tmp_path)

        assert (record["balance"], record["category"], record["parent_category"]) == (None, None, None)

    def test_non_ascii_characters_kept(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-1.0, "2024-01-01", label="Café | CARTE CAFÉ")])

        assert "carte café" in _write(bank_balance, tmp_path).read_text("utf-8")

    def test_ordered_by_account_then_value_date(self, tmp_path):
        bank_balance = _bank_balance([
            _transaction(-1.0, "2024-01-05", account=SAVINGS),
            _transaction(-2.0, "2024-01-05"),
            _transaction(-3.0, "2024-01-02", value_date="2024-01-03"),
            _transaction(-4.0, "2024-01-02"),
        ])

        records = _records(bank_balance, tmp_path)

        assert [(r["account"], r["amount"]) for r in records] == [
            ("00001", -4.0), ("00001", -3.0), ("00001", -2.0), ("00002", -1.0),
        ]

    def test_filled_days_give_no_line(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-1.0, "2024-01-02"), _transaction(-2.0, "2024-01-05")])

        assert [r["date_operation"] for r in _records(bank_balance, tmp_path)] == ["2024-01-02", "2024-01-05"]

    def test_overlapping_files_give_the_kept_day_record_only(self, tmp_path):
        day = [_transaction(-1.0, "2024-01-02"), _transaction(-2.0, "2024-01-02"), _transaction(-3.0, "2024-01-02")]
        again = [_transaction(t.amount, "2024-01-02", source_file="b.csv") for t in day]

        assert len(_records(_bank_balance(day + again), tmp_path)) == 3


class TestExportId:
    def test_identical_payments_of_a_day_get_different_ids(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-2.5, "2024-01-02"), _transaction(-2.5, "2024-01-02")])

        first, second = _records(bank_balance, tmp_path)

        assert first["id"] != second["id"]

    def test_same_transaction_from_two_files_gives_the_same_line(self, tmp_path):
        from_a = _write(_bank_balance([_transaction(-2.5, "2024-01-02")]), tmp_path, "a.jsonl")
        from_b = _write(_bank_balance([_transaction(-2.5, "2024-01-02", source_file="b.csv")]), tmp_path, "b.jsonl")

        assert from_a.read_bytes() == from_b.read_bytes()

    def test_suggested_label_and_spacing_do_not_change_the_id(self, tmp_path):
        before = _bank_balance([_transaction(-2.5, "2024-01-02", label="Boul | CARTE  BOULANGERIE")])
        after = _bank_balance([_transaction(-2.5, "2024-01-02", label="Paul | CARTE BOULANGERIE ")])

        assert _records(before, tmp_path)[0]["id"] == _records(after, tmp_path)[0]["id"]


class TestOutput:
    def test_writes_the_given_range(self, tmp_path):
        bank_balance = _bank_balance([
            _transaction(-1.0, "2024-01-01"),
            _transaction(-2.0, "2024-01-02"),
            _transaction(-3.0, "2024-01-03"),
        ])

        records = _records(bank_balance, tmp_path, date_from=datetime(2024, 1, 2), date_to=datetime(2024, 1, 2))

        assert [r["amount"] for r in records] == [-2.0]

    def test_defaults_to_output_dir_with_timestamped_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_recorder, "OUTPUT_DIR", tmp_path)

        path = BankBalanceTransactionsToJsonl().write_jsonl(_bank_balance([_transaction(-1.0, "2024-01-01")]))

        assert path.parent == tmp_path
        assert path.name.startswith("balance_") and path.suffix == ".jsonl"
