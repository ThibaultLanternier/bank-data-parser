import pytest
from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from entities.transaction_cluster import TransactionCluster


@pytest.fixture
def cluster() -> TransactionCluster:
    account = Account("00001", "Main Account")
    category = Category("misc")
    date = datetime(2024, 1, 1)

    transactions = [
        Transaction(datetime(2024,1,1), date, Label("Ech Pret:80363000600232370909 | ECH PRET:80363000600232370909"), category, account, 150.0),
        Transaction(datetime(2024,1,2), date, Label("Ech Pret:80363000600232370912 | ECH PRET:80363000600232370912"), category, account, 250.0),
        Transaction(datetime(2024,1,3), date, Label("Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE"), category, account, -100.0),
        Transaction(datetime(2024,1,4), date, Label("Prlv Sepa Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE"), category, account, -100.0),
    ]

    return TransactionCluster(transactions)


@pytest.fixture
def monthly_cluster() -> TransactionCluster:
    account = Account("00001", "Main Account")
    category = Category("misc")
    ref = datetime(2024, 1, 1)
    raw = [
        ("2022-01-07", -9.99),  ("2022-02-09", -10.99), ("2022-03-08", -10.99),
        ("2022-04-07", -10.99), ("2022-05-09", -10.99), ("2022-06-09", -10.99),
        ("2022-07-07", -10.99), ("2022-08-09", -10.99), ("2022-09-07", -10.99),
        ("2022-10-07", -10.99), ("2022-11-08", -10.99), ("2022-12-07", -10.99),
        ("2023-01-10", -10.99), ("2023-02-07", -17.99), ("2023-03-07", -17.99),
        ("2023-04-05", -17.99), ("2023-05-05", -17.99), ("2023-06-06", -17.99),
        ("2023-07-05", -17.99), ("2023-08-07", -17.99), ("2023-09-05", -17.99),
        ("2023-10-05", -17.99), ("2023-11-07", -17.99), ("2023-12-05", -17.99),
        ("2024-01-05", -17.99), ("2024-02-06", -19.99), ("2024-03-05", -19.99),
        ("2024-04-05", -19.99), ("2024-05-07", -19.99), ("2024-06-05", -19.99),
        ("2024-07-05", -19.99), ("2024-08-06", -19.99), ("2024-09-05", -19.99),
        ("2024-10-07", -19.99), ("2024-11-05", -19.99), ("2024-12-05", -19.99),
        ("2025-01-07", -19.99), ("2025-02-05", -19.99), ("2025-03-05", -19.99),
        ("2025-04-07", -19.99), ("2025-05-06", -19.99), ("2025-06-05", -19.99),
        ("2025-07-07", -19.99), ("2025-08-05", -19.99), ("2025-09-05", -19.99),
        ("2025-10-07", -19.99), ("2025-11-05", -19.99), ("2025-12-05", -19.99),
        ("2026-01-06", -19.99), ("2026-02-05", -19.99), ("2026-03-05", -19.99),
    ]
    transactions = [
        Transaction(datetime.strptime(d, "%Y-%m-%d"), ref, Label("Netflix"), category, account, amt)
        for d, amt in raw
    ]
    return TransactionCluster(transactions)


@pytest.fixture
def noisy_monthly_cluster() -> TransactionCluster:
    account = Account("00001", "Main Account")
    category = Category("misc")
    ref = datetime(2024, 1, 1)
    raw = [
        ("2026-03-05", -110), ("2026-02-05", -110), ("2026-01-05", -110),
        ("2025-10-22", 84.01), ("2025-09-05", -132), ("2025-08-05", -132),
        ("2025-07-07", -132), ("2025-06-05", -132), ("2025-05-05", -132),
        ("2025-04-07", -132), ("2025-03-05", -132), ("2025-02-05", -132),
        ("2025-01-07", -132), ("2024-12-05", -77.45), ("2024-11-05", -77.39),
        ("2024-09-05", -130), ("2024-08-07", -130), ("2024-07-05", -130),
        ("2024-06-05", -130), ("2024-05-06", -130), ("2024-04-05", -130),
        ("2024-03-05", -130), ("2024-02-05", -130), ("2024-01-05", -130),
        ("2023-11-07", -104.22), ("2023-09-05", -110), ("2023-08-07", -110),
        ("2023-07-05", -110), ("2023-06-06", -110), ("2023-05-05", -110),
        ("2023-04-05", -110), ("2023-03-07", -110), ("2023-02-06", -110),
        ("2023-01-05", -110), ("2022-10-20", 661.93), ("2022-09-06", -90),
        ("2022-08-05", -90), ("2022-07-05", -90), ("2022-06-06", -90),
        ("2022-05-05", -90), ("2022-04-05", -90), ("2022-03-07", -90),
        ("2022-02-07", -90), ("2022-01-05", -90),
    ]
    transactions = [
        Transaction(datetime.strptime(d, "%Y-%m-%d"), ref, Label("Gym"), category, account, amt)
        for d, amt in raw
    ]
    return TransactionCluster(transactions)


class TestTransactionCluster:
    def test_group_transactions(self, cluster: TransactionCluster):
        clusters = list(cluster.group_by_label().values())
        
        assert clusters[0].transactions == [cluster.transactions[0], cluster.transactions[1]]
        assert clusters[1].transactions == [cluster.transactions[2], cluster.transactions[3]]

        assert clusters[0].get_normalized_labels() == "ech pret:80363000600232370909"
        assert clusters[1].get_normalized_labels() == "direction generale des finance"

    def test_get_autocorrelation_peak_monthly(self, monthly_cluster: TransactionCluster):
        result = monthly_cluster.get_autocorrelation_peak()

        assert result is not None
        lag, corr = result
        assert lag == 29
        assert corr == pytest.approx(0.24, abs=1e-2)

    def test_get_autocorrelation_peak_noisy_returns_none(self, noisy_monthly_cluster: TransactionCluster):
        # Amounts vary widely (90, 110, 130, 132 + outliers like 661.93).
        # After filtering to ±5% of the mean, only 9 transactions remain (< 12 threshold).
        assert noisy_monthly_cluster.get_autocorrelation_peak() is None