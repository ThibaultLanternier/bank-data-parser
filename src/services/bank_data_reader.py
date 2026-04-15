from abc import ABC, abstractmethod
from pathlib import Path

from entities.transaction import Transaction


class BankDataReader(ABC):
    @abstractmethod
    def read(self, paths: list[Path]) -> list[Transaction]:
        pass
