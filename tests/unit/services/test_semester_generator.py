"""Unit tests for app/api/api_v1/endpoints/semester_generator.py

Sprint P8 — Coverage target: ≥85% stmt, ≥75% branch

Covers:
- get_first_monday / get_last_sunday (pure date helpers)
- generate_monthly_semesters    (monthly cycle, gap-free Monday-Sunday)
- generate_quarterly_semesters  (quarterly cycle, gap-free)
- generate_semiannual_semesters (semi-annual, year wrap for Fall)
- generate_annual_semesters     (annual, Jul–Jun next year)
- generate_semesters endpoint   (async: 404/400/500/200 paths)
- get_available_templates       (async: list all templates)
"""

import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.api.api_v1.endpoints.semester_generator import (
    SemesterGenerationRequest,
    generate_annual_semesters,
    generate_monthly_semesters,
    generate_quarterly_semesters,
    generate_semiannual_semesters,
    generate_semesters,
    get_available_templates,
    get_first_monday,
    get_last_sunday,
)

_BASE = "app.api.api_v1.endpoints.semester_generator"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def _admin():
    u = MagicMock()
    u.id = 42
    return u


def _q(*, first=None, all_=None):
    q = MagicMock()
    for m in ("filter", "options", "order_by", "offset", "limit", "group_by", "join", "with_for_update"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    return q


def _seq_db(*qs):
    """n-th db.query() call returns qs[n]; safe fallback after exhaustion."""
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else _q()

    db = MagicMock()
    db.query.side_effect = _side
    return db


def _location(*, is_active=True, name="Budapest"):
    loc = MagicMock()
    loc.id = 1
    loc.name = name
    loc.is_active = is_active
    return loc


def _monthly_tmpl():
    return {
        "specialization": "LFA_PLAYER",
        "age_group": "PRE",
        "cycle_type": "monthly",
        "themes": [
            {"month": 1, "code": "M01", "theme": "New Year Challenge", "focus": "Focus Jan"},
            {"month": 2, "code": "M02", "theme": "Winter Heroes",      "focus": "Focus Feb"},
        ],
    }


def _quarterly_tmpl():
    return {
        "specialization": "LFA_PLAYER",
        "age_group": "YOUTH",
        "cycle_type": "quarterly",
        "themes": [
            {"quarter": 1, "code": "Q1", "months": [1, 2, 3], "theme": "Q1 Semester", "focus": "Q1 focus"},
            {"quarter": 2, "code": "Q2", "months": [4, 5, 6], "theme": "Q2 Semester", "focus": "Q2 focus"},
        ],
    }


def _semiannual_tmpl():
    return {
        "specialization": "LFA_PLAYER",
        "age_group": "AMATEUR",
        "cycle_type": "semi-annual",
        "themes": [
            {"code": "FALL",   "start_month": 9, "end_month": 2, "theme": "Fall Season",   "focus": "Fall focus"},
            {"code": "SPRING", "start_month": 3, "end_month": 8, "theme": "Spring Season", "focus": "Spring focus"},
        ],
    }


def _annual_tmpl():
    return {
        "specialization": "LFA_PLAYER",
        "age_group": "PRO",
        "cycle_type": "annual",
        "themes": [
            {"code": "SEASON", "start_month": 7, "end_month": 6, "theme": "Football Season", "focus": "Jul–Jun"},
        ],
    }


def _req(year=2024, spec="LFA_PLAYER", age_group="PRE", loc_id=1):
    return SemesterGenerationRequest(year=year, specialization=spec, age_group=age_group, location_id=loc_id)


# ===========================================================================
# TestGetFirstMonday
# ===========================================================================

class TestGetFirstMonday:
    def test_jan_2024_already_monday(self):
        # Jan 1, 2024 was a Monday
        result = get_first_monday(2024, 1)
        assert result == date(2024, 1, 1)
        assert result.weekday() == 0

    def test_march_2024_friday_start(self):
        # Mar 1, 2024 was Friday → first Monday = Mar 4
        result = get_first_monday(2024, 3)
        assert result == date(2024, 3, 4)
        assert result.weekday() == 0

    def test_december_2024_sunday_start(self):
        # Dec 1, 2024 was Sunday → first Monday = Dec 2
        result = get_first_monday(2024, 12)
        assert result == date(2024, 12, 2)
        assert result.weekday() == 0

    def test_february_2025_saturday_start(self):
        # Feb 1, 2025 was Saturday → first Monday = Feb 3
        result = get_first_monday(2025, 2)
        assert result == date(2025, 2, 3)
        assert result.weekday() == 0


# ===========================================================================
# TestGetLastSunday
# ===========================================================================

class TestGetLastSunday:
    def test_january_2024(self):
        # Jan 31, 2024 was Wednesday → last Sunday = Jan 28
        result = get_last_sunday(2024, 1)
        assert result == date(2024, 1, 28)
        assert result.weekday() == 6

    def test_december_uses_year_boundary(self):
        # Dec uses year+1 path; Dec 31, 2024 was Tuesday → last Sunday = Dec 29
        result = get_last_sunday(2024, 12)
        assert result == date(2024, 12, 29)
        assert result.weekday() == 6

    def test_march_2024_ends_on_sunday(self):
        # Mar 31, 2024 was itself a Sunday
        result = get_last_sunday(2024, 3)
        assert result == date(2024, 3, 31)
        assert result.weekday() == 6

    def test_february_2024_leap(self):
        # Feb 29, 2024 was Thursday → last Sunday = Feb 25
        result = get_last_sunday(2024, 2)
        assert result == date(2024, 2, 25)
        assert result.weekday() == 6


# ===========================================================================
# TestGenerateMonthly
# ===========================================================================

class TestGenerateMonthly:
    def test_generates_correct_count(self):
        db = MagicMock()
        result = generate_monthly_semesters(2024, _monthly_tmpl(), db)
        assert len(result) == 2

    def test_first_semester_starts_first_monday_of_month(self):
        db = MagicMock()
        result = generate_monthly_semesters(2024, _monthly_tmpl(), db)
        # Jan 2024: first Monday = Jan 1
        assert result[0].start_date == date(2024, 1, 1)
        assert result[0].start_date.weekday() == 0

    def test_second_semester_is_gap_free_and_monday(self):
        db = MagicMock()
        result = generate_monthly_semesters(2024, _monthly_tmpl(), db)
        first_end = result[0].end_date
        second_start = result[1].start_date
        # Gap-free: second starts right after first ends (possibly adjusted to Monday)
        assert second_start > first_end
        assert second_start.weekday() == 0

    def test_end_dates_are_sundays(self):
        db = MagicMock()
        result = generate_monthly_semesters(2024, _monthly_tmpl(), db)
        for sem in result:
            assert sem.end_date.weekday() == 6

    def test_code_format(self):
        db = MagicMock()
        result = generate_monthly_semesters(2024, _monthly_tmpl(), db)
        assert result[0].code == "2024/LFA_PLAYER_PRE_M01"
        assert result[1].code == "2024/LFA_PLAYER_PRE_M02"


# ===========================================================================
# TestGenerateQuarterly
# ===========================================================================

class TestGenerateQuarterly:
    def test_generates_correct_count(self):
        db = MagicMock()
        result = generate_quarterly_semesters(2024, _quarterly_tmpl(), db)
        assert len(result) == 2

    def test_first_starts_first_monday_of_q1_month(self):
        db = MagicMock()
        result = generate_quarterly_semesters(2024, _quarterly_tmpl(), db)
        # Q1 months=[1,2,3]; Jan 2024 first Monday = Jan 1
        assert result[0].start_date == date(2024, 1, 1)
        assert result[0].start_date.weekday() == 0

    def test_second_starts_gap_free_after_first(self):
        db = MagicMock()
        result = generate_quarterly_semesters(2024, _quarterly_tmpl(), db)
        first_end = result[0].end_date
        second_start = result[1].start_date
        assert second_start > first_end
        assert second_start.weekday() == 0

    def test_code_format(self):
        db = MagicMock()
        result = generate_quarterly_semesters(2024, _quarterly_tmpl(), db)
        assert result[0].code == "2024/LFA_PLAYER_YOUTH_Q1"

    def test_end_dates_are_sundays(self):
        db = MagicMock()
        result = generate_quarterly_semesters(2024, _quarterly_tmpl(), db)
        for sem in result:
            assert sem.end_date.weekday() == 6


# ===========================================================================
# TestGenerateSemiannual
# ===========================================================================

class TestGenerateSemiannual:
    def test_generates_two_semesters(self):
        db = MagicMock()
        result = generate_semiannual_semesters(2024, _semiannual_tmpl(), db)
        assert len(result) == 2

    def test_fall_starts_first_monday_of_september(self):
        db = MagicMock()
        result = generate_semiannual_semesters(2024, _semiannual_tmpl(), db)
        # Sep 2, 2024 was Monday → first Monday of Sep 2024 = Sep 2
        assert result[0].start_date == date(2024, 9, 2)
        assert result[0].start_date.weekday() == 0

    def test_fall_end_is_last_sunday_of_february_next_year(self):
        # Fall: start_month=9 > end_month=2 → end = get_last_sunday(year+1, 2)
        db = MagicMock()
        result = generate_semiannual_semesters(2024, _semiannual_tmpl(), db)
        assert result[0].end_date.year == 2025
        assert result[0].end_date.month == 2
        assert result[0].end_date.weekday() == 6

    def test_spring_starts_gap_free_after_fall(self):
        db = MagicMock()
        result = generate_semiannual_semesters(2024, _semiannual_tmpl(), db)
        fall_end = result[0].end_date
        spring_start = result[1].start_date
        assert spring_start > fall_end
        assert spring_start.weekday() == 0

    def test_spring_end_is_last_sunday_of_august_same_year(self):
        # Spring: start_month=3 < end_month=8 → end = get_last_sunday(year, 8)
        db = MagicMock()
        result = generate_semiannual_semesters(2024, _semiannual_tmpl(), db)
        assert result[1].end_date.year == 2024
        assert result[1].end_date.month == 8
        assert result[1].end_date.weekday() == 6


# ===========================================================================
# TestGenerateAnnual
# ===========================================================================

class TestGenerateAnnual:
    def test_generates_one_semester(self):
        db = MagicMock()
        result = generate_annual_semesters(2024, _annual_tmpl(), db)
        assert len(result) == 1

    def test_starts_first_monday_of_july(self):
        db = MagicMock()
        result = generate_annual_semesters(2024, _annual_tmpl(), db)
        # Jul 1, 2024 was Monday → first Monday = Jul 1
        assert result[0].start_date == date(2024, 7, 1)
        assert result[0].start_date.weekday() == 0

    def test_ends_last_sunday_of_june_next_year(self):
        db = MagicMock()
        result = generate_annual_semesters(2024, _annual_tmpl(), db)
        assert result[0].end_date.year == 2025
        assert result[0].end_date.month == 6
        assert result[0].end_date.weekday() == 6

    def test_code_format(self):
        db = MagicMock()
        result = generate_annual_semesters(2024, _annual_tmpl(), db)
        assert result[0].code == "2024/LFA_PLAYER_PRO_SEASON"

    def test_name_includes_both_years(self):
        db = MagicMock()
        result = generate_annual_semesters(2024, _annual_tmpl(), db)
        assert "2024/2025" in result[0].name


# ===========================================================================
# TestGenerateSemestersEndpoint
# ===========================================================================

class TestGenerateSemestersEndpoint:
    def test_404_location_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(Exception) as exc:
            _run(generate_semesters(_req(), db, _admin()))
        assert exc.value.status_code == 404

    def test_400_location_inactive(self):
        db = _seq_db(_q(first=_location(is_active=False)))
        with pytest.raises(Exception) as exc:
            _run(generate_semesters(_req(), db, _admin()))
        assert exc.value.status_code == 400
        assert "not active" in exc.value.detail.lower()

    def test_400_invalid_template_raises_value_error(self):
        db = _seq_db(_q(first=_location()))
        with patch(f"{_BASE}.get_template", side_effect=ValueError("No such template")):
            with pytest.raises(Exception) as exc:
                _run(generate_semesters(_req(spec="BOGUS", age_group="X"), db, _admin()))
        assert exc.value.status_code == 400
        assert "No such template" in exc.value.detail

    def test_400_existing_semesters_block_regeneration(self):
        existing = MagicMock()
        db = _seq_db(_q(first=_location()), _q(all_=[existing]))
        with patch(f"{_BASE}.get_template", return_value=_monthly_tmpl()):
            with pytest.raises(Exception) as exc:
                _run(generate_semesters(_req(), db, _admin()))
        assert exc.value.status_code == 400
        assert "already exist" in exc.value.detail.lower()

    def test_200_monthly_cycle_returns_correct_count(self):
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_monthly_tmpl()):
            result = _run(generate_semesters(_req(), db, _admin()))
        assert result.generated_count == 2
        assert len(result.semesters) == 2

    def test_200_quarterly_cycle(self):
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_quarterly_tmpl()):
            result = _run(generate_semesters(_req(age_group="YOUTH"), db, _admin()))
        assert result.generated_count == 2

    def test_200_semiannual_cycle(self):
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_semiannual_tmpl()):
            result = _run(generate_semesters(_req(age_group="AMATEUR"), db, _admin()))
        assert result.generated_count == 2

    def test_200_annual_cycle(self):
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_annual_tmpl()):
            result = _run(generate_semesters(_req(age_group="PRO"), db, _admin()))
        assert result.generated_count == 1

    def test_500_unknown_cycle_type(self):
        unknown_tmpl = {
            "specialization": "LFA_PLAYER",
            "age_group": "PRE",
            "cycle_type": "unknown",
            "themes": [],
        }
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=unknown_tmpl):
            with pytest.raises(Exception) as exc:
                _run(generate_semesters(_req(), db, _admin()))
        assert exc.value.status_code == 500
        assert "unknown" in exc.value.detail.lower()

    def test_response_message_contains_year_and_spec(self):
        db = _seq_db(_q(first=_location()), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_annual_tmpl()):
            result = _run(generate_semesters(_req(year=2025, spec="LFA_PLAYER", age_group="PRO"), db, _admin()))
        assert "2025" in result.message
        assert "LFA_PLAYER" in result.message

    def test_location_id_assigned_to_all_semesters(self):
        loc = _location()
        loc.id = 7
        db = _seq_db(_q(first=loc), _q(all_=[]))
        with patch(f"{_BASE}.get_template", return_value=_monthly_tmpl()):
            _run(generate_semesters(_req(loc_id=7), db, _admin()))
        # db.add() should have been called for each generated semester
        assert db.add.call_count == 2
        assert db.commit.called


# ===========================================================================
# TestGetAvailableTemplates
# ===========================================================================

class TestGetAvailableTemplates:
    def test_returns_available_templates_key(self):
        result = _run(get_available_templates(_admin()))
        assert "available_templates" in result

    def test_templates_list_is_non_empty(self):
        result = _run(get_available_templates(_admin()))
        templates = result["available_templates"]
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_each_template_has_required_fields(self):
        result = _run(get_available_templates(_admin()))
        for tmpl in result["available_templates"]:
            assert "specialization" in tmpl
            assert "age_group" in tmpl
            assert "cycle_type" in tmpl
            assert "semester_count" in tmpl

    def test_cycle_types_present(self):
        result = _run(get_available_templates(_admin()))
        cycle_types = {t["cycle_type"] for t in result["available_templates"]}
        assert "monthly" in cycle_types
        assert "quarterly" in cycle_types
