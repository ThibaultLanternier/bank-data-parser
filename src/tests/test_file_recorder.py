import csv
from datetime import datetime

import pandas as pd
import pytest

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.source_type import SourceType
from entities.transaction import Transaction
from services import file_recorder
from services.file_recorder import FileRecorder


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    monkeypatch.setattr(file_recorder, "OUTPUT_DIR", tmp_path)
    return FileRecorder()


@pytest.fixture
def transactions():
    return [
        Transaction(
            dateOperation=datetime(2026, 10, 1),
            dateValue=datetime(2026, 10, 2),
            label=Label("CARTE 01/10/26 LIDL CB*6863 | CARTE 01/10/26 LIDL CB*6863"),
            category=Category(""),
            account=Account("123", "123"),
            amount=-10.5,
            source_type=SourceType.OFX,
            source_file="export.ofx",
            bank_transaction_id="fit1",
            bank_transaction_type="DEBIT",
        ),
        Transaction(
            dateOperation=datetime(2026, 10, 1),
            dateValue=datetime(2026, 10, 1),
            label=Label("Lidl | CARTE LIDL"),
            category=Category("Alimentation", "Courses"),
            account=Account("123", "Compte"),
            amount=-3.0,
        ),
    ]


class TestFileRecorder:
    def test_write_csv_includes_source_columns(self, recorder, transactions):
        path = recorder.write_csv(transactions, "out.csv")

        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        assert rows[0]["source_type"] == "OFX"
        assert rows[0]["source_file"] == "export.ofx"
        assert rows[0]["bank_transaction_id"] == "fit1"
        assert rows[0]["bank_transaction_type"] == "DEBIT"
        assert rows[1]["source_type"] == ""
        assert rows[1]["bank_transaction_id"] == ""

    def test_write_parquet_includes_source_columns(self, recorder, transactions):
        df = pd.read_parquet(recorder.write_parquet(transactions, "out.parquet"))

        assert df["source_type"][0] == "OFX"
        assert df["bank_transaction_type"][0] == "DEBIT"
        assert df["source_type"].isna()[1]
        assert df["bank_transaction_type"].isna()[1]
