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

    def get_autocorrelation_peak(self) -> tuple[int, float] | None:
        """Returns (lag_days, correlation) for the strongest periodic signal, or None if insufficient data."""
        if len(self.transactions) < 12:
            return None

        dates = [t.dateOperation for t in self.transactions]
        min_date = min(dates)
        n_days = (max(dates) - min_date).days + 1

        if n_days < 2:
            return None

        amounts = np.array([abs(t.amount) for t in self.transactions])
        mean_amount = amounts.mean()
        if mean_amount == 0:
            return None
        filtered = [t for t in self.transactions if abs(abs(t.amount) - mean_amount) / mean_amount <= 0.05]
        if len(filtered) < 12:
            return None

        series = np.zeros(n_days)
        for t in filtered:
            series[(t.dateOperation - min_date).days] += abs(t.amount)

        std = series.std()
        if std == 0:
            return None

        series_norm = (series - series.mean()) / std

        max_lag = min(365, n_days - 1)
        # np.correlate full mode: center at index n_days-1, positive lags follow
        autocorr = np.correlate(series_norm, series_norm, mode="full") / n_days
        lags_autocorr = autocorr[n_days : n_days + max_lag]  # lags 1..max_lag

        noise_mean = lags_autocorr.mean()
        noise_std = lags_autocorr.std()
        significance_threshold = noise_mean + 2 * noise_std

        local_max_window = 3
        for i in range(max_lag):
            corr = lags_autocorr[i]
            if corr < significance_threshold:
                continue
            window = lags_autocorr[max(0, i - local_max_window): i + local_max_window + 1]
            if corr == window.max():
                return i + 1, float(corr)

        return None