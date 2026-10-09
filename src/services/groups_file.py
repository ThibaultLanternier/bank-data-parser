from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from entities.group import Group


class GroupsFile:
    """YAML file mapping each group name to its list of label patterns, file order is the matching priority.

    Writes keep the comments and the order of the file (round-trip mode)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def load(self) -> list[Group]:
        """Groups of the file in file order, empty when the file does not exist."""
        return [Group(name, list(patterns)) for name, patterns in self._read().items()]

    def add_pattern(self, group_name: str, pattern: str) -> None:
        """Append the pattern to the group, the group is added at the end of the file when new."""
        data = self._read()
        if group_name in data:
            if pattern not in data[group_name]:
                data[group_name].append(pattern)
        else:
            data[group_name] = CommentedSeq([pattern])
        self._write(data)

    def remove_pattern(self, group_name: str, pattern: str) -> None:
        """Remove the pattern from the group, the group is removed with its last pattern."""
        data = self._read()
        patterns = data.get(group_name)
        if not patterns or pattern not in patterns:
            return
        patterns.remove(pattern)
        if not patterns:
            del data[group_name]
        self._write(data)

    def _read(self) -> CommentedMap:
        if not self.path.exists():
            return CommentedMap()
        with self.path.open(encoding="utf-8") as f:
            data = self._yaml.load(f)
        if data is None:
            return CommentedMap()
        if not isinstance(data, CommentedMap):
            raise ValueError(f"Invalid groups file {self.path}: expected a mapping of group names to lists of patterns")
        for name, patterns in data.items():
            if patterns is None:
                data[name] = CommentedSeq()
            elif not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise ValueError(f"Invalid groups file {self.path}: group {name!r} must be a list of strings")
        return data

    def _write(self, data: CommentedMap) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            self._yaml.dump(data, f)
