import re
import unicodedata
from enum import Enum


class GroupSource(Enum):
    DIRECT = "direct"  # the transaction label matches a pattern of the group
    CLUSTER = "cluster"  # inherited from the other transactions of its label cluster


def normalize_pattern(pattern: str) -> str:
    """Lowercase, accents stripped and whitespace collapsed, to compare with Label.get_normalized_label()."""
    s = unicodedata.normalize("NFD", pattern.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


class Group:
    def __init__(self, name: str, patterns: list[str]):
        self.name = name
        self.patterns = patterns
        self._normalized_patterns = [p for p in (normalize_pattern(p) for p in patterns) if p]

    def matches(self, normalized_label: str) -> bool:
        return any(p in normalized_label for p in self._normalized_patterns)
