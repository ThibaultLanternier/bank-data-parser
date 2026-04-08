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