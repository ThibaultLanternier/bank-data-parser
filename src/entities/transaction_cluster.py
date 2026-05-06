import logging

import numpy as np
from rapidfuzz import fuzz
from sklearn.cluster import DBSCAN
from entities.label import Label
from entities.transaction import Transaction

logger = logging.getLogger(__name__)

class TransactionCluster:
    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions

        self._index_by_label: dict[str, list[Transaction]] = {}
        for t in transactions:
            label = t.label.get_normalized_label()
            if label not in self._index_by_label:
                self._index_by_label[label] = []
            self._index_by_label[label].append(t)
    
    def _get_label(self, normalized_label: str) -> Label:
        return self._index_by_label[normalized_label][0].label

    def group_by_label(self) -> dict[str, 'TransactionCluster']:
        n = len(self._index_by_label.keys()) # Number of unique labels
        logger.info("Clustering %d unique labels", n)
        distance_matrix = np.zeros((n, n))
        
        normalized_labels = list(self._index_by_label.keys())

        for i in range(n):
            for j in range(i + 1, n):
                similarity = fuzz.token_sort_ratio(normalized_labels[i], normalized_labels[j]) / 100.0
                distance_matrix[i][j] = 1.0 - similarity
                distance_matrix[j][i] = 1.0 - similarity
                
        logger.info("Computed distance matrix for %d labels", n)
        db = DBSCAN(eps=0.2, min_samples=1, metric="precomputed")
        db.fit(distance_matrix)

        normalized_labels_clusters: dict[int, list[str]] = {}
        for idx, cluster_id in enumerate(db.labels_):
            if cluster_id not in normalized_labels_clusters:
                normalized_labels_clusters[cluster_id] = []
            normalized_labels_clusters[cluster_id].append(list(self._index_by_label.keys())[idx])

        logger.info("Formed %d clusters", len(normalized_labels_clusters))
        clusters: dict[str, TransactionCluster] = {}
        for cluster_id, normalized_labels in normalized_labels_clusters.items():
            cluster_transactions = []
            for normalized_label in normalized_labels:
                cluster_transactions.extend(self._index_by_label[normalized_label])
            clusters[f"cluster_{cluster_id}"] = TransactionCluster(cluster_transactions)
        
        return clusters
    
    def get_normalized_labels(self) -> str:
        return max(self._index_by_label, key=lambda k: len(self._index_by_label[k]))