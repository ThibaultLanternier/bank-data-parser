from datetime import datetime

import pytest

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from services.categorize_session import Action, CategorizeSession
from services.group_matcher import ClusterStatus
from services.groups_file import GroupsFile
from services.transaction_enhancer import TransactionEnhancer


MAIN = Account("00001", "Main")
SAVINGS = Account("00002", "Savings")


def _transaction(label: str, amount: float, day: int = 1, account: Account = MAIN) -> Transaction:
    date = datetime(2024, 1, day)
    return Transaction(date, date, Label(f"{label} | {label.upper()}"), Category(""), account, amount)


def _transfer(amount: float, day: int) -> list[Transaction]:
    """Offsetting pair between the two accounts, marked internal by the enhancer."""
    return [
        _transaction("Vir Sepa Livret A", -amount, day),
        _transaction("Vir Sepa Livret A", amount, day, SAVINGS),
    ]


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

    def test_internal_only_cluster_is_not_reviewed(self, transactions, groups_path):
        session = _session(transactions + _transfer(1000.0, 15) + _transfer(1000.0, 16), groups_path)

        assert all("livret" not in r.label for r in session.queue())

    def test_cluster_with_ungrouped_external_transaction_is_reviewed(self, transactions, groups_path):
        leftover = _transaction("Vir Sepa Livret A", -10.0, 20)
        session = _session(transactions + _transfer(1000.0, 15) + [leftover], groups_path)

        [review] = [r for r in session.queue() if "livret" in r.label]
        assert len(review.cluster.transactions) == 3

    def test_orders_clusters_by_external_amount_only(self, transactions, groups_path):
        leftover = _transaction("Vir Sepa Livret A", -10.0, 20)
        labels = [r.label for r in _session(transactions + _transfer(1000.0, 15) + [leftover], groups_path).queue()]

        assert labels.index("livret a") > labels.index("amazon mktp fr")


class TestProgress:
    def test_counts_grouped_transactions_and_remaining_clusters(self, transactions, groups_path):
        progress = _session(transactions, groups_path, "ENERGY:\n  - edf\n").progress()

        assert (progress.grouped_transactions, progress.total_transactions) == (2, 7)
        assert progress.remaining == 3
        assert progress.grouped_share == pytest.approx(2 / 7)

    def test_ignores_internal_transactions(self, groups_path):
        transactions = [
            _transaction("Edf Particuliers", -80.0, 5),
            _transaction("Edf Particulier", -81.0, 6),
            _transaction("Acme Corp Salaire", 3000.0, 28),
            _transaction("Boulangerie Paul", -5.0, 3),
            *_transfer(1000.0, 15),
            *_transfer(500.0, 16),
            *_transfer(200.0, 17),
        ]
        progress = _session(transactions, groups_path, "ENERGY:\n  - edf\n").progress()

        assert (progress.grouped_transactions, progress.total_transactions) == (2, 4)
        assert progress.grouped_share == pytest.approx(0.5)


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


class ScriptedUi:
    """Answers the prompts from a list, None when the script is exhausted (like Ctrl+C)."""

    def __init__(self, answers: list):
        self.answers = list(answers)
        self.shown: list[str] = []
        self.messages: list[str] = []
        self.previews = []

    def _next(self):
        return self.answers.pop(0) if self.answers else None

    def show_cluster(self, review, progress):
        self.shown.append(review.label)

    def ask_action(self, can_undo):
        return self._next()

    def ask_pattern(self, default):
        answer = self._next()
        return default if answer == "" else answer

    def show_preview(self, preview):
        self.previews.append(preview)

    def ask_group(self, group_names):
        return self._next()

    def confirm_shadowed(self, shadowing):
        return self._next()

    def show_message(self, message):
        self.messages.append(message)


def _groups(groups_path) -> list[tuple[str, list[str]]]:
    return [(g.name, g.patterns) for g in GroupsFile(groups_path).load()]


class TestRun:
    def test_assigns_new_group_with_proposed_pattern(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        ui = ScriptedUi([Action.ASSIGN, "", "SALARY", Action.QUIT])

        assignments = session.run(ui)

        assert _groups(groups_path) == [("SALARY", ["acme corp salaire"])]
        assert [(a.group_name, a.pattern) for a in assignments] == [("SALARY", "acme corp salaire")]
        assert ui.shown[1] != "acme corp salaire"

    def test_assigns_to_existing_group_with_edited_pattern(self, transactions, groups_path):
        session = _session(transactions, groups_path, "# mine\nSALARY:\n  - other\n")
        ui = ScriptedUi([Action.ASSIGN, "acme", "SALARY"])

        session.run(ui)

        assert _groups(groups_path) == [("SALARY", ["other", "acme"])]
        assert "# mine" in groups_path.read_text(encoding="utf-8")
        assert (ui.previews[0].inside, ui.previews[0].outside) == (1, 0)

    def test_new_pattern_also_groups_later_clusters(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        ui = ScriptedUi([Action.SKIP, Action.ASSIGN, "edf", "ENERGY", Action.ASSIGN, "a", "ALL", Action.QUIT])

        session.run(ui)

        assert "boulangerie paul" not in ui.shown

    def test_skip_leaves_file_unchanged_and_moves_on(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        ui = ScriptedUi([Action.SKIP, Action.QUIT])

        session.run(ui)

        assert not groups_path.exists()
        assert ui.shown[0] != ui.shown[1]

    def test_undo_removes_pattern_and_presents_cluster_again(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        ui = ScriptedUi([Action.ASSIGN, "", "SALARY", Action.UNDO, Action.QUIT])

        assignments = session.run(ui)

        assert _groups(groups_path) == []
        assert assignments == []
        assert ui.shown[0] == ui.shown[2] == "acme corp salaire"

    def test_undo_keeps_pattern_that_was_already_in_the_file(self, transactions, groups_path):
        session = _session(transactions, groups_path, "FR:\n  - amazon mktp fr\nDE:\n  - amazon mktp de\n")
        ui = ScriptedUi([Action.ASSIGN, "amazon mktp fr", "FR", Action.UNDO, Action.QUIT])

        session.run(ui)

        assert ("FR", ["amazon mktp fr"]) in _groups(groups_path)

    def test_shadowed_pattern_is_not_saved_when_not_confirmed(self, transactions, groups_path):
        session = _session(transactions, groups_path, "ENERGY:\n  - edf\n")
        ui = ScriptedUi([Action.ASSIGN, "edf particuliers", "BILLS", False, Action.QUIT])

        session.run(ui)

        assert _groups(groups_path) == [("ENERGY", ["edf"])]

    def test_quit_by_ctrl_c_keeps_saved_assignments(self, transactions, groups_path):
        session = _session(transactions, groups_path)
        ui = ScriptedUi([Action.ASSIGN, "", "SALARY", Action.ASSIGN, ""])

        assignments = session.run(ui)

        assert len(assignments) == 1
        assert _groups(groups_path) == [("SALARY", ["acme corp salaire"])]

    def test_stops_when_nothing_is_left_to_review(self, transactions, groups_path):
        session = _session(transactions, groups_path, "ALL:\n  - a\n  - edf\n  - paul\n")
        ui = ScriptedUi([])

        session.run(ui)

        assert ui.shown == []
        assert ui.messages == ["No cluster left to review."]
