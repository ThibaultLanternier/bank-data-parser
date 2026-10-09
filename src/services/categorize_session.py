from dataclasses import dataclass

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
    def total_absolute_amount(self) -> float:
        return sum(abs(t.amount) for t in self.cluster.transactions)

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
    grouped_transactions: int
    total_transactions: int

    @property
    def grouped_share(self) -> float:
        return self.grouped_transactions / self.total_transactions if self.total_transactions else 0.0


@dataclass
class PatternPreview:
    inside: int  # transactions of the reviewed cluster matched by the pattern
    outside: int  # transactions of the other clusters matched by the pattern


class CategorizeSession:
    """Interactive labelling of the clusters of enhanced transactions, answers are saved in the groups file."""

    def __init__(self, enhancer: TransactionEnhancer, groups_file: GroupsFile):
        self.enhancer = enhancer  # get_enhanced_list() already called: clusters are computed
        self.groups_file = groups_file
        self.groups = groups_file.load()
        self._skipped: set[str] = set()
        self._reviewed = 0
        self.enhancer.assign_groups(self.groups)

    def queue(self) -> list[ClusterReview]:
        """Clusters with at least one transaction without group, not skipped, largest total absolute amount first."""
        reviews = [
            ClusterReview(cluster_id, cluster, self.enhancer.cluster_matches[cluster_id])
            for cluster_id, cluster in self.enhancer.clusters.items()
            if cluster_id not in self._skipped and any(t.group is None for t in cluster.transactions)
        ]
        return sorted(reviews, key=lambda r: r.total_absolute_amount, reverse=True)

    def progress(self) -> Progress:
        transactions = [t for cluster in self.enhancer.clusters.values() for t in cluster.transactions]
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
