"""
Unit tests for app/api/api_v1/endpoints/instructor_management/masters/utils.py

Pure helper functions (no DB, no HTTP) — 100% statement and branch coverage.

Coverage target: masters/utils.py (51 lines, ~0% previously)
Functions:
  - get_semester_age_group(spec_type) → str
  - can_teach_age_group(instructor_age_group, semester_age_group) → bool
  - get_allowed_age_groups(instructor_age_group) → list
"""

import pytest
from app.api.api_v1.endpoints.instructor_management.masters.utils import (
    get_semester_age_group,
    can_teach_age_group,
    get_allowed_age_groups,
)


# ── get_semester_age_group ────────────────────────────────────────────────────

class TestGetSemesterAgeGroup:
    """Maps LFA_PLAYER_* specialization to football age group string."""

    def test_pre_football(self):
        assert get_semester_age_group("LFA_PLAYER_PRE") == "PRE_FOOTBALL"

    def test_youth_football(self):
        assert get_semester_age_group("LFA_PLAYER_YOUTH") == "YOUTH_FOOTBALL"

    def test_amateur_football(self):
        assert get_semester_age_group("LFA_PLAYER_AMATEUR") == "AMATEUR_FOOTBALL"

    def test_pro_football(self):
        assert get_semester_age_group("LFA_PLAYER_PRO") == "PRO_FOOTBALL"

    def test_unknown_spec_returns_unknown(self):
        assert get_semester_age_group("GANCUJU") == "UNKNOWN"

    def test_empty_string_returns_unknown(self):
        assert get_semester_age_group("") == "UNKNOWN"

    def test_none_key_returns_unknown(self):
        # dict.get(None, "UNKNOWN") should also return "UNKNOWN"
        assert get_semester_age_group("LFA_COACH") == "UNKNOWN"

    def test_all_four_mappings_covered(self):
        specs = ["LFA_PLAYER_PRE", "LFA_PLAYER_YOUTH", "LFA_PLAYER_AMATEUR", "LFA_PLAYER_PRO"]
        expected = ["PRE_FOOTBALL", "YOUTH_FOOTBALL", "AMATEUR_FOOTBALL", "PRO_FOOTBALL"]
        for spec, exp in zip(specs, expected):
            assert get_semester_age_group(spec) == exp


# ── can_teach_age_group ───────────────────────────────────────────────────────

class TestCanTeachAgeGroup:
    """
    LFA_COACH hierarchy:
    PRE_FOOTBALL   → can teach [PRE]
    YOUTH_FOOTBALL → can teach [PRE, YOUTH]
    AMATEUR_FOOTBALL → can teach [PRE, YOUTH, AMATEUR]
    PRO_FOOTBALL   → can teach ALL
    """

    # ── PRE_FOOTBALL instructor (Level 2 — can only teach PRE) ──────────────

    def test_pre_instructor_teaches_pre(self):
        assert can_teach_age_group("PRE_FOOTBALL", "PRE_FOOTBALL") is True

    def test_pre_instructor_cannot_teach_youth(self):
        assert can_teach_age_group("PRE_FOOTBALL", "YOUTH_FOOTBALL") is False

    def test_pre_instructor_cannot_teach_amateur(self):
        assert can_teach_age_group("PRE_FOOTBALL", "AMATEUR_FOOTBALL") is False

    def test_pre_instructor_cannot_teach_pro(self):
        assert can_teach_age_group("PRE_FOOTBALL", "PRO_FOOTBALL") is False

    # ── YOUTH_FOOTBALL instructor (Level 4 — can teach PRE + YOUTH) ─────────

    def test_youth_instructor_teaches_pre(self):
        assert can_teach_age_group("YOUTH_FOOTBALL", "PRE_FOOTBALL") is True

    def test_youth_instructor_teaches_youth(self):
        assert can_teach_age_group("YOUTH_FOOTBALL", "YOUTH_FOOTBALL") is True

    def test_youth_instructor_cannot_teach_amateur(self):
        assert can_teach_age_group("YOUTH_FOOTBALL", "AMATEUR_FOOTBALL") is False

    def test_youth_instructor_cannot_teach_pro(self):
        assert can_teach_age_group("YOUTH_FOOTBALL", "PRO_FOOTBALL") is False

    # ── AMATEUR_FOOTBALL instructor (Level 6 — can teach PRE + YOUTH + AMATEUR) ─

    def test_amateur_instructor_teaches_pre(self):
        assert can_teach_age_group("AMATEUR_FOOTBALL", "PRE_FOOTBALL") is True

    def test_amateur_instructor_teaches_youth(self):
        assert can_teach_age_group("AMATEUR_FOOTBALL", "YOUTH_FOOTBALL") is True

    def test_amateur_instructor_teaches_amateur(self):
        assert can_teach_age_group("AMATEUR_FOOTBALL", "AMATEUR_FOOTBALL") is True

    def test_amateur_instructor_cannot_teach_pro(self):
        assert can_teach_age_group("AMATEUR_FOOTBALL", "PRO_FOOTBALL") is False

    # ── PRO_FOOTBALL instructor (Level 8 — can teach ALL) ───────────────────

    def test_pro_instructor_teaches_pre(self):
        assert can_teach_age_group("PRO_FOOTBALL", "PRE_FOOTBALL") is True

    def test_pro_instructor_teaches_youth(self):
        assert can_teach_age_group("PRO_FOOTBALL", "YOUTH_FOOTBALL") is True

    def test_pro_instructor_teaches_amateur(self):
        assert can_teach_age_group("PRO_FOOTBALL", "AMATEUR_FOOTBALL") is True

    def test_pro_instructor_teaches_pro(self):
        assert can_teach_age_group("PRO_FOOTBALL", "PRO_FOOTBALL") is True

    # ── Unknown instructor age group ─────────────────────────────────────────

    def test_unknown_instructor_age_group_returns_false(self):
        assert can_teach_age_group("UNKNOWN", "PRE_FOOTBALL") is False

    def test_empty_instructor_age_group_returns_false(self):
        assert can_teach_age_group("", "PRE_FOOTBALL") is False


# ── get_allowed_age_groups ────────────────────────────────────────────────────

class TestGetAllowedAgeGroups:
    """Returns short-form list of teachable age groups."""

    def test_pre_instructor_allowed_groups(self):
        assert get_allowed_age_groups("PRE_FOOTBALL") == ["PRE"]

    def test_youth_instructor_allowed_groups(self):
        result = get_allowed_age_groups("YOUTH_FOOTBALL")
        assert result == ["PRE", "YOUTH"]

    def test_amateur_instructor_allowed_groups(self):
        result = get_allowed_age_groups("AMATEUR_FOOTBALL")
        assert result == ["PRE", "YOUTH", "AMATEUR"]

    def test_pro_instructor_allowed_groups(self):
        result = get_allowed_age_groups("PRO_FOOTBALL")
        assert result == ["PRE", "YOUTH", "AMATEUR", "PRO"]

    def test_unknown_instructor_returns_empty_list(self):
        assert get_allowed_age_groups("UNKNOWN") == []

    def test_empty_string_returns_empty_list(self):
        assert get_allowed_age_groups("") == []

    def test_hierarchy_is_cumulative(self):
        """Each level includes all levels below it."""
        pre = get_allowed_age_groups("PRE_FOOTBALL")
        youth = get_allowed_age_groups("YOUTH_FOOTBALL")
        amateur = get_allowed_age_groups("AMATEUR_FOOTBALL")
        pro = get_allowed_age_groups("PRO_FOOTBALL")

        assert set(pre).issubset(set(youth))
        assert set(youth).issubset(set(amateur))
        assert set(amateur).issubset(set(pro))

    def test_pro_includes_all_four_groups(self):
        groups = get_allowed_age_groups("PRO_FOOTBALL")
        assert len(groups) == 4
        assert "PRE" in groups
        assert "YOUTH" in groups
        assert "AMATEUR" in groups
        assert "PRO" in groups
