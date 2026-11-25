from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.day_transactions import DayTransactions
from entities.label import Label
from entities.transaction import Transaction
from services import file_recorder
from services.bank_balance import BankBalance
from services.bank_balance_to_openmetrics import BankBalanceToOpenMetrics

MAIN = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings")

HEADER = [
    "# HELP bank_account_balance_euros Account balance at the end of the day",
    "# TYPE bank_account_balance_euros gauge",
    "# UNIT bank_account_balance_euros euros",
]
MAIN_SERIES = 'bank_account_balance_euros{account="00001",account_label="Main Account"}'


def _transaction(
    amount: float, date: str, balance: float | None = None, value_date: str | None = None, account: Account = MAIN
) -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    value_day = datetime.strptime(value_date, "%Y-%m-%d") if value_date else day
    return Transaction(
        day, value_day, Label("Label | LABEL"), Category("misc"), account, amount, source_file="a.csv", balance=balance
    )


def _bank_balance(transactions: list[Transaction]) -> BankBalance:
    return BankBalance(DayTransactions.from_transactions(transactions))


def _lines(bank_balance: BankBalance, tmp_path, **kwargs) -> list[str]:
    path = BankBalanceToOpenMetrics(tmp_path).write_openmetrics(bank_balance, "balance.om", **kwargs)
    return path.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def bank_balance():
    # 2022-12-31 and 2023-01-01 are in a gap, 2023-01-03 is inferred
    return _bank_balance([
        _transaction(-77.97, "2022-12-30", balance=10105.11),
        _transaction(2950.0, "2023-01-02", balance=12190.6),
        _transaction(-868.5, "2023-01-02", balance=12190.6),
        _transaction(-10.0, "2023-01-03", value_date="2023-01-01", balance=10105.11),
    ])


class TestBankBalanceToOpenMetrics:
    def test_writes_header_samples_and_eof(self, tmp_path, bank_balance):
        assert _lines(bank_balance, tmp_path) == HEADER + [
            f"{MAIN_SERIES} 10105.11 1672444800",
            f"{MAIN_SERIES} 12190.60 1672704000",
            f"{MAIN_SERIES} 12180.60 1672790400",
            "# EOF",
        ]

    def test_samples_end_balance_at_next_day_midnight_utc(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-10.0, "2024-01-01", balance=1523.45)])

        assert _lines(bank_balance, tmp_path)[3] == f"{MAIN_SERIES} 1523.45 1704153600"

    def test_filled_day_gives_a_sample(self, tmp_path):
        bank_balance = _bank_balance([
            _transaction(-10.0, "2026-09-04", balance=1000.0),
            _transaction(-25.0, "2026-09-07", balance=975.0),
        ])

        assert _lines(bank_balance, tmp_path)[3:7] == [
            f"{MAIN_SERIES} 1000.00 1788566400",
            f"{MAIN_SERIES} 1000.00 1788652800",
            f"{MAIN_SERIES} 1000.00 1788739200",
            f"{MAIN_SERIES} 975.00 1788825600",
        ]

    def test_unknown_balance_gives_no_sample(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-10.0, "2026-09-07")])

        assert _lines(bank_balance, tmp_path) == HEADER + ["# EOF"]

    def test_negative_balance(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-300.0, "2024-01-01", balance=-250.3)])

        assert _lines(bank_balance, tmp_path)[3] == f"{MAIN_SERIES} -250.30 1704153600"

    def test_one_series_per_account_ordered_by_account(self, tmp_path):
        bank_balance = _bank_balance([
            _transaction(-10.0, "2024-01-01", balance=500.0, account=SAVINGS),
            _transaction(-10.0, "2024-01-01", balance=1523.45),
        ])

        assert _lines(bank_balance, tmp_path)[3:5] == [
            f"{MAIN_SERIES} 1523.45 1704153600",
            'bank_account_balance_euros{account="00002",account_label="Savings"} 500.00 1704153600',
        ]

    def test_same_label_for_all_samples_of_an_account(self, tmp_path):
        bank_balance = _bank_balance([
            _transaction(-10.0, "2024-01-01", balance=100.0, account=Account("00001", "Old name")),
            _transaction(-10.0, "2024-01-02", balance=90.0, account=Account("00001", "New name")),
        ])

        labels = {line.split(" ")[0] for line in _lines(bank_balance, tmp_path)[3:-1]}

        assert len(labels) == 1

    def test_escapes_label_values(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-10.0, "2024-01-01", balance=1.0, account=Account("1", 'A "B" \\C'))])

        assert _lines(bank_balance, tmp_path)[3] == (
            'bank_account_balance_euros{account="1",account_label="A \\"B\\" \\\\C"} 1.00 1704153600'
        )

    def test_account_without_label(self, tmp_path):
        bank_balance = _bank_balance([_transaction(-10.0, "2024-01-01", balance=1.0, account=Account("1", ""))])

        assert _lines(bank_balance, tmp_path)[3] == 'bank_account_balance_euros{account="1",account_label=""} 1.00 1704153600'

    def test_writes_the_given_range(self, tmp_path, bank_balance):
        lines = _lines(bank_balance, tmp_path, date_from=datetime(2023, 1, 1), date_to=datetime(2023, 1, 2))

        assert lines == HEADER + [f"{MAIN_SERIES} 12190.60 1672704000", "# EOF"]

    def test_defaults_to_output_dir_with_timestamped_name(self, tmp_path, monkeypatch, bank_balance):
        monkeypatch.setattr(file_recorder, "OUTPUT_DIR", tmp_path)

        path = BankBalanceToOpenMetrics().write_openmetrics(bank_balance)

        assert path.parent == tmp_path
        assert path.name.startswith("balance_") and path.suffix == ".om"
