from entities.group import Group, normalize_pattern


class TestNormalizePattern:
    def test_lowercases_and_strips_accents(self):
        assert normalize_pattern("Électricité  EDF ") == "electricite edf"


class TestGroupMatches:
    def test_matches_substring_of_normalized_label(self):
        assert Group("ENERGY", ["edf"]).matches("edf particuliers")

    def test_match_is_case_and_accent_insensitive(self):
        assert Group("ENERGY", ["Électricité EDF"]).matches("electricite edf particuliers")

    def test_matches_when_any_pattern_matches(self):
        assert Group("ENERGY", ["engie", "edf"]).matches("edf particuliers")

    def test_does_not_match_when_no_pattern_is_a_substring(self):
        assert not Group("ENERGY", ["engie"]).matches("edf particuliers")

    def test_empty_pattern_never_matches(self):
        assert not Group("ENERGY", ["", "  "]).matches("edf particuliers")
