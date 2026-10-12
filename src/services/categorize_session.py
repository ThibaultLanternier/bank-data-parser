from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from entities.group import Group
from entities.transaction import Transaction
from entities.transaction_cluster import TransactionCluster
from services.group_matcher import ClusterMatch, GroupMatcher
from services.groups_file import GroupsFile
from services.transaction_enhancer import TransactionEnhancer


@dataclass
class ClusterReview:
    cluster_id: str
    cluster: TransactionCluster
    match: ClusterMatch

    @property
    def total_amount(self) -> float:
        return sum(t.amount for t in self.cluster.transactions)

    @property
    def external_absolute_amount(self) -> float:
        """Total absolute amount of the transactions that are not transfers between accounts."""
        return sum(abs(t.amount) for t in self.cluster.transactions if not t.is_internal)

    @property
    def label(self) -> str:
        return self.cluster.get_normalized_labels()

    @property
    def periodicity(self) -> int | None:
        return self.cluster.transactions[0].periodicity

    def recent_transactions(self, count: int) -> list[Transaction]:
        return sorted(self.cluster.transactions, key=lambda t: t.dateOperation, reverse=True)[:count]


@dataclass
class Progress:
    reviewed: int  # clusters answered or skipped during the session
    remaining: int  # clusters still to review
    grouped_transactions: int  # external transactions only, internal ones need no group
    total_transactions: int

    @property
    def grouped_share(self) -> float:
        return self.grouped_transactions / self.total_transactions if self.total_transactions else 0.0


@dataclass
class PatternPreview:
    inside: int  # transactions of the reviewed cluster matched by the pattern
    outside: int  # transactions of the other clusters matched by the pattern


@dataclass
class Assignment:
    cluster_id: str
    group_name: str
    pattern: str
    added: bool  # False when the pattern was already in the group: undo leaves the file unchanged


class Action(Enum):
    ASSIGN = "assign"
    SKIP = "skip"
    UNDO = "undo"
    QUIT = "quit"


class CategorizeUi(Protocol):
    """User interaction of the session, a None answer means the user quits (e.g. Ctrl+C)."""

    def show_cluster(self, review: ClusterReview, progress: Progress) -> None: ...

    def ask_action(self, can_undo: bool) -> Action | None: ...

    def ask_pattern(self, default: str) -> str | None: ...

    def show_preview(self, preview: PatternPreview) -> None: ...

    def ask_group(self, group_names: list[str]) -> str | None: ...

    def confirm_shadowed(self, shadowing: list[Group]) -> bool | None: ...

    def show_message(self, message: str) -> None: ...


class CategorizeSession:
    """Interactive labelling of the clusters of enhanced transactions, answers are saved in the groups file."""

    def __init__(self, enhancer: TransactionEnhancer, groups_file: GroupsFile):
        self.enhancer = enhancer  # get_enhanced_list() already called: clusters are computed
        self.groups_file = groups_file
        self.groups = groups_file.load()
        self._skipped: set[str] = set()
        self._reviewed = 0
        self.assignments: list[Assignment] = []
        self.enhancer.assign_groups(self.groups)

    def queue(self) -> list[ClusterReview]:
        """Clusters with at least one external transaction without group, not skipped, largest external amount first.

        Internal transactions (transfers between accounts) need no group: they are never asked about."""
        reviews = [
            ClusterReview(cluster_id, cluster, self.enhancer.cluster_matches[cluster_id])
            for cluster_id, cluster in self.enhancer.clusters.items()
            if cluster_id not in self._skipped
            and any(t.group is None and not t.is_internal for t in cluster.transactions)
        ]
        return sorted(reviews, key=lambda r: r.external_absolute_amount, reverse=True)

    def progress(self) -> Progress:
        transactions = [
            t for cluster in self.enhancer.clusters.values() for t in cluster.transactions if not t.is_internal
        ]
        return Progress(
            reviewed=self._reviewed,
            remaining=len(self.queue()),
            grouped_transactions=sum(1 for t in transactions if t.group is not None),
            total_transactions=len(transactions),
        )

    @staticmethod
    def proposed_pattern(review: ClusterReview) -> str:
        """Most frequent normalized label of the cluster."""
        return review.label

    def preview(self, review: ClusterReview, pattern: str) -> PatternPreview:
        matcher = Group("", [pattern])
        inside = sum(1 for t in review.cluster.transactions if matcher.matches(t.label.get_normalized_label()))
        total = sum(
            1
            for cluster in self.enhancer.clusters.values()
            for t in cluster.transactions
            if matcher.matches(t.label.get_normalized_label())
        )
        return PatternPreview(inside, total - inside)

    def shadowing_groups(self, pattern: str, group_name: str) -> list[Group]:
        """Groups listed before group_name (all groups when it is new) already matching transactions of the pattern."""
        names = [g.name for g in self.groups]
        earlier = self.groups[: names.index(group_name)] if group_name in names else self.groups
        matcher = Group("", [pattern])
        earlier_matcher = GroupMatcher(earlier)
        shadowing: list[Group] = []
        for cluster in self.enhancer.clusters.values():
            for t in cluster.transactions:
                if not matcher.matches(t.label.get_normalized_label()):
                    continue
                group = earlier_matcher.match(t.label)
                if group is not None and group not in shadowing:
                    shadowing.append(group)
        return sorted(shadowing, key=self.groups.index)

    def assign(self, review: ClusterReview, group_name: str, pattern: str) -> Assignment:
        """Save the pattern in the group and assign the groups again to all the clusters."""
        existing = next((g for g in self.groups if g.name == group_name), None)
        added = existing is None or pattern not in existing.patterns
        assignment = Assignment(review.cluster_id, group_name, pattern, added)
        self.groups_file.add_pattern(group_name, pattern)
        self.assignments.append(assignment)
        self._reviewed += 1
        self._reload()
        return assignment

    def undo(self) -> Assignment | None:
        """Remove the pattern of the last assignment from the groups file."""
        if not self.assignments:
            return None
        assignment = self.assignments.pop()
        if assignment.added:
            self.groups_file.remove_pattern(assignment.group_name, assignment.pattern)
        self._reviewed -= 1
        self._reload()
        return assignment

    def skip(self, review: ClusterReview) -> None:
        self._skipped.add(review.cluster_id)
        self._reviewed += 1

    def run(self, ui: CategorizeUi) -> list[Assignment]:
        """Review the clusters until none is left or the user quits, return the assignments kept."""
        next_cluster_id: str | None = None
        while True:
            queue = self.queue()
            if not queue:
                ui.show_message("No cluster left to review.")
                break
            review = next((r for r in queue if r.cluster_id == next_cluster_id), queue[0])
            next_cluster_id = None
            ui.show_cluster(review, self.progress())

            action = ui.ask_action(can_undo=bool(self.assignments))
            if action is None or action == Action.QUIT:
                break
            if action == Action.SKIP:
                self.skip(review)
                continue
            if action == Action.UNDO:
                undone = self.undo()
                if undone is None:
                    ui.show_message("Nothing to undo.")
                else:
                    ui.show_message(f"Removed {undone.pattern!r} from {undone.group_name}.")
                    next_cluster_id = undone.cluster_id
                continue

            pattern = ui.ask_pattern(self.proposed_pattern(review))
            if pattern is None:
                break
            pattern = pattern.strip()
            if not pattern:
                continue
            ui.show_preview(self.preview(review, pattern))

            group_name = ui.ask_group([g.name for g in self.groups])
            if group_name is None:
                break
            group_name = group_name.strip()
            if not group_name:
                continue

            shadowing = self.shadowing_groups(pattern, group_name)
            if shadowing:
                confirmed = ui.confirm_shadowed(shadowing)
                if confirmed is None:
                    break
                if not confirmed:
                    continue

            self.assign(review, group_name, pattern)
        return self.assignments

    def _reload(self) -> None:
        self.groups = self.groups_file.load()
        self.enhancer.assign_groups(self.groups)
