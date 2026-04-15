import hashlib
from datetime import datetime

from entities.account import Account
from entities.category import Category
from entities.label import Label


class transaction:
    def __init__(
            self, 
            dateOperation: datetime,
            dateValue: datetime, 
            label: Label,
            category: Category,
            account: Account,
            amount: float
        ):
        self.dateOperation = dateOperation
        self.dateValue = dateValue
        self.label = label
        self.category = category
        self.account = account
        self.amount = amount
        self.is_internal = False
        self.is_large = False

    @property
    def id(self) -> str:
        data = f"{self.account.account_number}||{self.amount}||{self.dateOperation.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    @property
    def group_id(self) -> str:
        data = f"||{abs(self.amount)}||{self.dateOperation.strftime('%Y-%m-%d')}"
        return hashlib.md5(data.encode()).hexdigest()