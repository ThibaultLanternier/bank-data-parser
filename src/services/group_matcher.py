from dataclasses import dataclass, field
from enum import Enum

from entities.group import Group, GroupSource
from entities.label import Label
from entities.transaction_cluster import TransactionCluster


class ClusterStatus(Enum):
    GROUPED = "grouped"  # one single group, every transaction has it
    UNGROUPED = "ungrouped"  # no transaction matches any group
    CONFLICT = "conflict"  # direct matches designate several groups, nothing is inherited


@dataclass
class ClusterMatch:
    status: ClusterStatus
    groups: list[Group] = field(default_factory=list)  # groups directly matched in the cluster, in file order


class GroupMatcher:
    def __init__(self, groups: list[Group]):
        self.groups = groups

    def match(self, label: Label) -> Group | None:
        """First group, in file order, having a pattern in the normalized label."""
        normalized_label = label.get_normalized_label()
        return next((g for g in self.groups if g.matches(normalized_label)), None)

    def assign(self, clusters: dict[str, TransactionCluster]) -> dict[str, ClusterMatch]:
        """Set group and group source of the transactions of each cluster, previous values are replaced.

        A direct match always wins. Transactions without direct match inherit the group of their
        cluster only when all its direct matches designate one single group."""
        return {cluster_id: self._assign_cluster(cluster) for cluster_id, cluster in clusters.items()}

    def _assign_cluster(self, cluster: TransactionCluster) -> ClusterMatch:
        unmatched = []
        matched_groups: list[Group] = []
        for t in cluster.transactions:
            t.group = self.match(t.label)
            t.group_source = GroupSource.DIRECT if t.group else None
            if t.group is None:
                unmatched.append(t)
            elif t.group not in matched_groups:
                matched_groups.append(t.group)

        matched_groups.sort(key=self.groups.index)
        if not matched_groups:
            return ClusterMatch(ClusterStatus.UNGROUPED)
        if len(matched_groups) > 1:
            return ClusterMatch(ClusterStatus.CONFLICT, matched_groups)

        for t in unmatched:
            t.group = matched_groups[0]
            t.group_source = GroupSource.CLUSTER
        return ClusterMatch(ClusterStatus.GROUPED, matched_groups)
