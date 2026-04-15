import re
import unicodedata
from collections import defaultdict

import numpy as np
from rapidfuzz import fuzz
from sklearn.cluster import DBSCAN

from entities.transaction import Transaction


class TransactionEnhancer:
    def __init__(self, transactions: list[Transaction]):
        self._transactions = transactions
        self._by_id: dict[str, Transaction] = {t.id: t for t in transactions}
        self._by_group: dict[str, list[Transaction]] = defaultdict(list)
        for t in transactions:
            self._by_group[t.group_id].append(t)

    @property
    def by_id(self) -> dict[str, Transaction]:
        return self._by_id

    @property
    def by_group(self) -> dict[str, list[Transaction]]:
        return self._by_group

    def get_enhanced_list(self) -> list[Transaction]:
        offsetting_pairs = self._find_offsetting_pairs()
        for t1, t2 in offsetting_pairs:
            self._by_id[t1.id].is_internal = True
            self._by_id[t2.id].is_internal = True
        
        large_transactions = self._find_large_transactions()
        for t in large_transactions:
            self._by_id[t.id].is_large = True

        self._group_labels()

        return list(self._by_id.values())

    def _find_offsetting_pairs(self) -> list[tuple[Transaction, Transaction]]:
        pairs = []
        for group_id, group_transactions in self._by_group.items():
            if len(group_transactions) < 2:
                continue
            pairs.extend(self._find_pairs_in_group(group_transactions))
        return pairs
    
    def _find_large_transactions(self, threshold: float = 10000.0) -> list[Transaction]:
        return [t for t in self._by_id.values() if abs(t.amount) >= threshold]

    def _group_labels(self) -> None:
        def normalize(s: str) -> str:
            s = s.lower()
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            s = re.sub(r'[._\-]', ' ', s)
            s = re.sub(r'\b(com|www|inc|llc|ab)\b', '', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s

        seen: dict[str, None] = {}
        for t in self._transactions:
            lbl = t.label.get_label()
            if lbl not in seen:
                seen[lbl] = None
        unique_labels = list(seen.keys())

        if not unique_labels:
            return

        normalized = [normalize(l) for l in unique_labels]
        n = len(normalized)

        distance_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                similarity = fuzz.token_sort_ratio(normalized[i], normalized[j]) / 100.0
                distance_matrix[i][j] = 1.0 - similarity
                distance_matrix[j][i] = 1.0 - similarity

        db = DBSCAN(eps=0.25, min_samples=1, metric="precomputed")
        db.fit(distance_matrix)

        cluster_first: dict[int, str] = {}
        for idx, cluster_id in enumerate(db.labels_):
            if cluster_id not in cluster_first:
                cluster_first[cluster_id] = unique_labels[idx]

        label_to_grouped = {lbl: cluster_first[db.labels_[idx]] for idx, lbl in enumerate(unique_labels)}

        for t in self._transactions:
            lbl = t.label.get_label()
            self._by_id[t.id].grouped_label = label_to_grouped.get(lbl, lbl)

    def _find_pairs_in_group(self, group: list[Transaction]) -> list[tuple[Transaction, Transaction]]:
        pairs = []
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                t1, t2 = group[i], group[j]
                if t1.amount + t2.amount == 0 and t1.account.account_number != t2.account.account_number:
                    pairs.append((t1, t2))
        return pairs
