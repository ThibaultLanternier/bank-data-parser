import pytest

from services.groups_file import GroupsFile

COMMENTED = """\
# My groups
SALARY:
  - "acme corp"  # employer
ENERGY:
  - edf
"""


class TestLoad:
    def test_loads_groups_in_file_order(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")

        groups = GroupsFile(path).load()

        assert [(g.name, g.patterns) for g in groups] == [("SALARY", ["acme corp"]), ("ENERGY", ["edf"])]

    def test_missing_file_has_no_group(self, tmp_path):
        assert GroupsFile(tmp_path / "groups.yaml").load() == []

    def test_group_without_pattern_is_empty(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text("SALARY:\n", encoding="utf-8")

        assert [(g.name, g.patterns) for g in GroupsFile(path).load()] == [("SALARY", [])]

    def test_not_a_mapping_is_invalid(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text("- edf\n", encoding="utf-8")

        with pytest.raises(ValueError, match="groups.yaml"):
            GroupsFile(path).load()

    def test_group_not_a_list_of_strings_is_invalid(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text("ENERGY: edf\n", encoding="utf-8")

        with pytest.raises(ValueError, match="'ENERGY'"):
            GroupsFile(path).load()


class TestAddPattern:
    def test_creates_the_file(self, tmp_path):
        path = tmp_path / "data" / "groups.yaml"

        GroupsFile(path).add_pattern("ENERGY", "edf")

        assert [(g.name, g.patterns) for g in GroupsFile(path).load()] == [("ENERGY", ["edf"])]

    def test_appends_to_existing_group_and_keeps_comments(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")

        GroupsFile(path).add_pattern("SALARY", "other corp")

        content = path.read_text(encoding="utf-8")
        assert "# My groups" in content and "# employer" in content
        assert GroupsFile(path).load()[0].patterns == ["acme corp", "other corp"]

    def test_new_group_is_added_at_the_end(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")

        GroupsFile(path).add_pattern("SCHOOL", "lycee")

        assert [g.name for g in GroupsFile(path).load()] == ["SALARY", "ENERGY", "SCHOOL"]

    def test_existing_pattern_is_not_duplicated(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")

        GroupsFile(path).add_pattern("ENERGY", "edf")

        assert GroupsFile(path).load()[1].patterns == ["edf"]


class TestRemovePattern:
    def test_removes_the_pattern_and_keeps_comments(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")
        GroupsFile(path).add_pattern("SALARY", "other corp")

        GroupsFile(path).remove_pattern("SALARY", "other corp")

        assert GroupsFile(path).load()[0].patterns == ["acme corp"]
        assert "# employer" in path.read_text(encoding="utf-8")

    def test_removes_the_group_with_its_last_pattern(self, tmp_path):
        path = tmp_path / "groups.yaml"
        path.write_text(COMMENTED, encoding="utf-8")

        GroupsFile(path).remove_pattern("ENERGY", "edf")

        assert [g.name for g in GroupsFile(path).load()] == ["SALARY"]
