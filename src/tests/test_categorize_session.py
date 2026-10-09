from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from services.categorize_session import CategorizeSession
from services.group_matcher import ClusterStatus
from services.groups_file import GroupsFile
from services.transaction_enhancer import TransactionEnhancer


def _transaction(label: str, amount: float, day: int = 1) -> Transaction:
    date = datetime(2024, 1, day)
    return Transaction(date, date, Label(f"{label} | {label.upper()}"), Category(""), Account("00001", "Main"), amount)


@pytest.fixture
def transactions() -> list[Transaction]:
    return [
        _transaction("Edf Particuliers", -80.0, 5),
        _transaction("Edf Particulier", -81.0, 6),
        _transaction("Acme Corp Salaire", 3000.0, 28),
        _transaction("Boulangerie Paul", -5.0, 3),
        _transaction("Amazon Mktp Fr", -30.0, 10),
        _transaction("Amazon Mktp De", -20.0, 11),
        _transaction("Amazon Mktp It", -10.0, 12),
    ]


@pytest.fixture
def groups_path(tmp_path):
    return tmp_path / "groups.yaml"


def _session(transactions, groups_path, content: str | None = None) -> CategorizeSession:
    if content is not None:
        groups_path.write_text(content, encoding="utf-8")
    enhancer = TransactionEnhancer(transactions)
    enhancer.get_enhanced_list()
    return CategorizeSession(enhancer, GroupsFile(groups_path))


class TestQueue:
    def test_orders_clusters_by_decreasing_total_absolute_amount(self, transactions, groups_path):
        labels = [r.label for r in _session(transactions, groups_path).queue()]

        assert labels[0] == "acme corp salaire"
        assert labels[1] == "edf particuliers" or labels[1] == "edf particulier"
        assert labels[-1] == "boulangerie paul"

    def test_fully_grouped_clusters_are_not_reviewed(self, transactions, groups_path):
        session = _session(transactions, groups_path, "ENERGY:\n  - edf particuliers\n")

        assert all("edf" not in r.label for r in session.queue())

    def test_conflict_cluster_is_reviewed(self, transactions, groups_path):
        session = _session(transactions, groups_path, "FR:\n  - amazon mktp fr\nDE:\n  - amazon mktp de\n")

        [conflict] = [r for r in session.queue() if r.match.status == ClusterStatus.CONFLICT]
        assert [g.name for g in conflict.match.groups] == ["FR", "DE"]


class TestProgress:
    def test_counts_grouped_transactions_and_remaining_clusters(self, transactions, groups_path):
        progress = _session(transactions, groups_path, "ENERGY:\n  - edf\n").progress()

        assert (progress.grouped_transactions, progress.total_transactions) == (2, 7)
        assert progress.remaining == 3
        assert progress.grouped_share == pytest.approx(2 / 7)


class TestPatternProposal:
    def test_proposes_most_frequent_normalized_label(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        review = session.queue()[0]

        assert session.proposed_pattern(review) == "acme corp salaire"

    def test_preview_counts_matches_inside_and_outside_the_cluster(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        [amazon] = [r for r in session.queue() if r.label.startswith("amazon")]

        preview = session.preview(amazon, "amazon mktp fr")
        broad = session.preview(amazon, "a")

        assert (preview.inside, preview.outside) == (1, 0)
        assert (broad.inside, broad.outside) == (3, 4)

    def test_new_group_is_shadowed_by_existing_groups(self, transactions, groups_path):
        session = _session(transactions, groups_path, "ENERGY:\n  - edf\n")

        assert [g.name for g in session.shadowing_groups("edf particuliers", "BILLS")] == ["ENERGY"]

    def test_existing_group_is_shadowed_only_by_earlier_groups(self, transactions, groups_path):
        session = _session(transactions, groups_path, "FIRST:\n  - edf\nBILLS:\n  - x\nLAST:\n  - acme\n")

        assert [g.name for g in session.shadowing_groups("edf", "BILLS")] == ["FIRST"]
        assert session.shadowing_groups("acme", "BILLS") == []
