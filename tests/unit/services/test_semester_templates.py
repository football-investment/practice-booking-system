"""
Unit tests for semester_templates module

Covers:
- get_first_monday: finds first Monday, handles month where day 1 is already Monday
- get_last_sunday: finds last Sunday, December edge case (year roll-over)
- get_template: happy path, missing key raises ValueError
- SEMESTER_TEMPLATES registry: all 8 defined keys are present

DB-free: pure date arithmetic + dict lookup.
"""
import pytest
from datetime import datetime

from app.services.semester_templates import (
    get_first_monday,
    get_last_sunday,
    get_template,
    SEMESTER_TEMPLATES,
)


# ─── get_first_monday ─────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetFirstMonday:

    def test_first_monday_when_first_is_monday(self):
        # Jan 1 2024 is a Monday
        result = get_first_monday(2024, 1)
        assert result == datetime(2024, 1, 1)
        assert result.weekday() == 0  # Monday = 0

    def test_first_monday_when_first_is_tuesday(self):
        # Feb 1 2022 is Tuesday → first Monday is Feb 7
        result = get_first_monday(2022, 2)
        assert result.weekday() == 0
        assert result.day == 7

    def test_first_monday_when_first_is_sunday(self):
        # Sept 1 2024 is Sunday → first Monday is Sept 2
        result = get_first_monday(2024, 9)
        assert result.weekday() == 0
        assert result.day == 2

    def test_first_monday_always_in_correct_month(self):
        for month in range(1, 13):
            result = get_first_monday(2025, month)
            assert result.month == month
            assert result.weekday() == 0
            assert result.day <= 7  # First Monday always within first 7 days


# ─── get_last_sunday ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetLastSunday:

    def test_last_sunday_is_weekday_6(self):
        result = get_last_sunday(2025, 3)  # March 2025
        assert result.weekday() == 6  # Sunday = 6

    def test_last_sunday_of_december_year_rollover(self):
        # December: uses year+1/Jan to find last day of December
        result = get_last_sunday(2025, 12)
        assert result.month == 12
        assert result.weekday() == 6

    def test_last_sunday_of_january(self):
        result = get_last_sunday(2025, 1)
        assert result.month == 1
        assert result.weekday() == 6

    def test_last_sunday_is_within_last_7_days_of_month(self):
        import calendar
        for month in range(1, 13):
            result = get_last_sunday(2025, month)
            _, last_day = calendar.monthrange(2025, month)
            assert result.day >= last_day - 6
            assert result.day <= last_day

    def test_last_sunday_different_month_from_december_boundary(self):
        # December 2024: last Sunday must be in December, not January
        result = get_last_sunday(2024, 12)
        assert result.year == 2024
        assert result.month == 12


# ─── get_template ─────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetTemplate:

    def test_lfa_player_pre_template_exists(self):
        t = get_template("LFA_PLAYER", "PRE")
        assert t["specialization"] == "LFA_PLAYER"
        assert t["age_group"] == "PRE"

    def test_lfa_player_youth_template_quarterly(self):
        t = get_template("LFA_PLAYER", "YOUTH")
        assert t["cycle_type"] == "quarterly"

    def test_lfa_player_amateur_template_has_cost(self):
        t = get_template("LFA_PLAYER", "AMATEUR")
        assert "cost_credits" in t

    def test_lfa_player_pro_template_has_cost(self):
        t = get_template("LFA_PLAYER", "PRO")
        assert "cost_credits" in t

    def test_academy_pre_template_annual(self):
        t = get_template("LFA_PLAYER_PRE_ACADEMY", "PRE")
        assert t["cycle_type"] == "academy_annual"
        assert t.get("enrollment_lock") is True

    def test_academy_youth_template_center_required(self):
        t = get_template("LFA_PLAYER_YOUTH_ACADEMY", "YOUTH")
        assert t.get("requires_center") is True

    def test_missing_specialization_raises_value_error(self):
        with pytest.raises(ValueError, match="No template found"):
            get_template("GANCUJU", "PRE")

    def test_missing_age_group_raises_value_error(self):
        with pytest.raises(ValueError, match="No template found"):
            get_template("LFA_PLAYER", "MASTERS")

    def test_both_missing_raises_value_error(self):
        with pytest.raises(ValueError):
            get_template("UNKNOWN_SPEC", "UNKNOWN_AGE")


# ─── SEMESTER_TEMPLATES registry ──────────────────────────────────────────────

@pytest.mark.unit
class TestSemesterTemplatesRegistry:

    EXPECTED_KEYS = [
        ("LFA_PLAYER", "PRE"),
        ("LFA_PLAYER", "YOUTH"),
        ("LFA_PLAYER", "AMATEUR"),
        ("LFA_PLAYER", "PRO"),
        ("LFA_PLAYER_PRE_ACADEMY", "PRE"),
        ("LFA_PLAYER_YOUTH_ACADEMY", "YOUTH"),
        ("LFA_PLAYER_AMATEUR_ACADEMY", "AMATEUR"),
        ("LFA_PLAYER_PRO_ACADEMY", "PRO"),
    ]

    def test_all_expected_keys_present(self):
        for key in self.EXPECTED_KEYS:
            assert key in SEMESTER_TEMPLATES, f"Missing template key: {key}"

    def test_all_templates_have_required_fields(self):
        for key, template in SEMESTER_TEMPLATES.items():
            assert "specialization" in template, f"Missing 'specialization' in {key}"
            assert "age_group" in template, f"Missing 'age_group' in {key}"
            assert "cycle_type" in template, f"Missing 'cycle_type' in {key}"
