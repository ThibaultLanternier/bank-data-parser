from collections import defaultdict

from entities.transaction import transaction


class TransactionEnhancer:
    def __init__(self, transactions: list[transaction]):
        self._transactions = transactions
        self._by_id: dict[str, transaction] = {t.id: t for t in transactions}
        self._by_group: dict[str, list[transaction]] = defaultdict(list)
        for t in transactions:
            self._by_group[t.group_id].append(t)

    @property
    def by_id(self) -> dict[str, transaction]:
        return self._by_id

    @property
    def by_group(self) -> dict[str, list[transaction]]:
        return self._by_group

    def get_enhanced_list(self) -> list[transaction]:
        offsetting_pairs = self._find_offsetting_pairs()
        for t1, t2 in offsetting_pairs:
            self._by_id[t1.id].is_internal = True
            self._by_id[t2.id].is_internal = True
        
        large_transactions = self._find_large_transactions()
        for t in large_transactions:
            self._by_id[t.id].is_large = True

        return list(self._by_id.values())

    def _find_offsetting_pairs(self) -> list[tuple[transaction, transaction]]:
        pairs = []
        for group_id, group_transactions in self._by_group.items():
            if len(group_transactions) < 2:
                continue
            pairs.extend(self._find_pairs_in_group(group_transactions))
        return pairs
    
    def _find_large_transactions(self, threshold: float = 10000.0) -> list[transaction]:
        return [t for t in self._by_id.values() if abs(t.amount) >= threshold]

    def _find_pairs_in_group(self, group: list[transaction]) -> list[tuple[transaction, transaction]]:
        pairs = []
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                t1, t2 = group[i], group[j]
                if t1.amount + t2.amount == 0 and t1.account.account_number != t2.account.account_number:
                    pairs.append((t1, t2))
        return pairs
