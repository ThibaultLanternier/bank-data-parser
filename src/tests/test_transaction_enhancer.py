from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.group import Group, GroupSource
from entities.label import Label
from entities.transaction import Transaction
from services.transaction_enhancer import TransactionEnhancer

MAIN = Account("00001", "Main Account")
SAVINGS = Account("00002", "Savings Account")


def _transaction(date: str, amount: float, account: Account = MAIN, label: str = "Label") -> Transaction:
    day = datetime.strptime(date, "%Y-%m-%d")
    return Transaction(day, day, Label(f"{label} | {label.upper()}"), Category("misc"), account, amount)


class TestMarkInternalTransactions:
    def test_flags_offsetting_transactions_between_accounts(self):
        debit = _transaction("2024-01-05", -500.0)
        credit = _transaction("2024-01-05", 500.0, SAVINGS)

        TransactionEnhancer([debit, credit]).mark_internal_transactions()

        assert debit.is_internal and credit.is_internal

    def test_ignores_offsetting_transactions_on_same_account(self):
        debit = _transaction("2024-01-05", -500.0)
        refund = _transaction("2024-01-05", 500.0)

        TransactionEnhancer([debit, refund]).mark_internal_transactions()

        assert not debit.is_internal and not refund.is_internal

    def test_ignores_offsetting_transactions_on_different_days(self):
        debit = _transaction("2024-01-05", -500.0)
        credit = _transaction("2024-01-06", 500.0, SAVINGS)

        TransactionEnhancer([debit, credit]).mark_internal_transactions()

        assert not debit.is_internal and not credit.is_internal


ENERGY = Group("ENERGY", ["edf particuliers"])
SHOPPING_FR = Group("SHOPPING_FR", ["amazon mktp fr"])
SHOPPING_DE = Group("SHOPPING_DE", ["amazon mktp de"])


def _by_label(transactions: list[Transaction]) -> dict[str, tuple[str | None, GroupSource | None]]:
    return {t.label.get_normalized_label(): (t.group.name if t.group else None, t.group_source) for t in transactions}


class TestAssignGroups:
    def test_direct_and_inherited_groups(self):
        transactions = [
            _transaction("2024-01-05", -80.0, label="Edf Particuliers"),
            _transaction("2024-02-05", -81.0, label="Edf Particulier"),
        ]

        enhanced = TransactionEnhancer(transactions, [ENERGY]).get_enhanced_list()

        assert _by_label(enhanced) == {
            "edf particuliers": ("ENERGY", GroupSource.DIRECT),
            "edf particulier": ("ENERGY", GroupSource.CLUSTER),
        }

    def test_conflicting_cluster_is_not_inherited(self):
        transactions = [
            _transaction("2024-01-05", -8.0, label="Amazon Mktp Fr"),
            _transaction("2024-01-06", -30.0, label="Amazon Mktp De"),
            _transaction("2024-01-07", -12.0, label="Amazon Mktp It"),
        ]

        enhancer = TransactionEnhancer(transactions, [SHOPPING_FR, SHOPPING_DE])
        enhanced = enhancer.get_enhanced_list()

        assert len(enhancer.clusters) == 1
        assert _by_label(enhanced) == {
            "amazon mktp fr": ("SHOPPING_FR", GroupSource.DIRECT),
            "amazon mktp de": ("SHOPPING_DE", GroupSource.DIRECT),
            "amazon mktp it": (None, None),
        }

    def test_no_groups_leaves_transactions_without_group(self):
        transactions = [_transaction("2024-01-05", -80.0, label="Edf Particuliers")]
        enhanced = TransactionEnhancer(transactions).get_enhanced_list()

        assert _by_label(enhanced) == {"edf particuliers": (None, None)}

    def test_assign_groups_again_replaces_previous_assignment(self):
        enhancer = TransactionEnhancer([_transaction("2024-01-05", -80.0, label="Edf Particuliers")], [ENERGY])
        enhanced = enhancer.get_enhanced_list()

        enhancer.assign_groups([])

        assert _by_label(enhanced) == {"edf particuliers": (None, None)}
