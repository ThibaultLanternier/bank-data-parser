import hashlib
from datetime import datetime
from pathlib import Path

from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.source_type import SourceType


class Transaction:
    def __init__(
            self, 
            dateOperation: datetime,
            dateValue: datetime, 
            label: Label,
            category: Category,
            account: Account,
            amount: float,
            source_type: SourceType | None = None,
            source_file: Path | None = None
        ):
        self.dateOperation = dateOperation
        self.dateValue = dateValue
        self.label = label
        self.category = category
        self.account = account
        self.amount = amount
        self.source_type = source_type
        self.source_file = source_file
        self.is_internal = False
        self.is_large = False
        self.grouped_label: str = ""
        self.cluster_id: str = ""
        self.periodicity: int | None = None
        self.periodicity_confidence: float | None = None

    @property
    def id(self) -> str:
        data = f"{self.account.account_number}||{self.amount}||{self.dateOperation.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    @property
    def group_id(self) -> str:
        data = f"||{abs(self.amount)}||{self.dateOperation.strftime('%Y-%m-%d')}"
        return hashlib.md5(data.encode()).hexdigest()