from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.group import Group, GroupSource
from entities.label import Label
from entities.transaction import Transaction
from entities.transaction_cluster import TransactionCluster
from services.group_matcher import ClusterStatus, GroupMatcher

ENERGY = Group("ENERGY", ["edf"])
SUBSCRIPTIONS = Group("SUBSCRIPTIONS", ["amazon prime"])
SHOPPING = Group("SHOPPING", ["amazon"])


def _transaction(label: str, amount: float = -10.0) -> Transaction:
    day = datetime(2024, 1, 1)
    return Transaction(day, day, Label(f"{label} | {label.upper()}"), Category("misc"), Account("00001", "Main"), amount)


class TestMatch:
    def test_returns_group_having_a_pattern_in_the_label(self):
        assert GroupMatcher([ENERGY]).match(Label("Edf Particuliers | PRLV SEPA EDF PARTICULIERS")) is ENERGY

    def test_returns_none_without_match(self):
        assert GroupMatcher([ENERGY]).match(Label("Engie | PRLV SEPA ENGIE")) is None

    def test_first_group_in_file_order_wins(self):
        assert GroupMatcher([SUBSCRIPTIONS, SHOPPING]).match(Label("amazon prime")) is SUBSCRIPTIONS

    def test_file_order_wins_over_pattern_specificity(self):
        assert GroupMatcher([SHOPPING, SUBSCRIPTIONS]).match(Label("amazon prime")) is SHOPPING


class TestAssign:
    def test_unanimous_cluster_is_inherited(self):
        direct = _transaction("edf particuliers")
        variant = _transaction("e d f clients part")

        result = GroupMatcher([ENERGY]).assign({"c": TransactionCluster([direct, variant])})

        assert result["c"].status == ClusterStatus.GROUPED
        assert (direct.group, direct.group_source) == (ENERGY, GroupSource.DIRECT)
        assert (variant.group, variant.group_source) == (ENERGY, GroupSource.CLUSTER)

    def test_cluster_without_direct_match_is_ungrouped(self):
        t = _transaction("engie")

        result = GroupMatcher([ENERGY]).assign({"c": TransactionCluster([t])})

        assert result["c"].status == ClusterStatus.UNGROUPED
        assert t.group is None and t.group_source is None

    def test_conflicting_cluster_keeps_direct_matches_and_is_not_inherited(self):
        prime = _transaction("amazon prime")
        mktp = _transaction("amazon mktp")
        other = _transaction("amzn eu")

        result = GroupMatcher([SUBSCRIPTIONS, SHOPPING]).assign({"c": TransactionCluster([mktp, prime, other])})

        assert result["c"].status == ClusterStatus.CONFLICT
        assert result["c"].groups == [SUBSCRIPTIONS, SHOPPING]
        assert (prime.group, prime.group_source) == (SUBSCRIPTIONS, GroupSource.DIRECT)
        assert (mktp.group, mktp.group_source) == (SHOPPING, GroupSource.DIRECT)
        assert other.group is None and other.group_source is None

    def test_previous_assignment_is_replaced(self):
        t = _transaction("engie")
        t.group, t.group_source = ENERGY, GroupSource.DIRECT

        GroupMatcher([]).assign({"c": TransactionCluster([t])})

        assert t.group is None and t.group_source is None
