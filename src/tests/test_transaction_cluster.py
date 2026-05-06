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


class TestTransactionCluster:
    def test_group_transactions(self, cluster: TransactionCluster):
        clusters = list(cluster.group_by_label().values())
        
        assert clusters[0].transactions == [cluster.transactions[0], cluster.transactions[1]]
        assert clusters[1].transactions == [cluster.transactions[2], cluster.transactions[3]]

        assert clusters[0].get_normalized_labels() == "ech pret:80363000600232370909"
        assert clusters[1].get_normalized_labels() == "direction generale des finance"