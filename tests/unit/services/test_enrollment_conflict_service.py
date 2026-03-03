"""
Unit tests for app/services/enrollment_conflict_service.py

Covers:
  Pure static methods (no DB):
    _has_time_overlap      — no date_start, different dates, same date overlap, no overlap
    _has_travel_conflict   — no date_start, different dates, same location, no location, gap < buffer, gap >= buffer
    _calculate_time_gap    — start > end (positive gap), start < end (next-day wrap), same time
    _get_enrollment_type   — ACADEMY_SEASON, TOURNAMENT, MINI_SEASON, OTHER

  check_session_time_conflict (early return paths):
    semester not found → warning + return
    no existing enrollments → return (no conflicts)
    no future target sessions → warning + return
"""
import pytest
from datetime import datetime, date, time, timedelta, timezone
from unittest.mock import MagicMock

from app.services.enrollment_conflict_service import EnrollmentConflictService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(h, m=0, day=1):
    """datetime on 2026-06-01 at h:m."""
    return datetime(2026, 6, day, h, m, tzinfo=timezone.utc)


def _session(start_dt, end_dt):
    s = MagicMock()
    s.date_start = start_dt
    s.date_end = end_dt
    return s


def _db():
    return MagicMock()


def _q(db, first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    db.query.return_value = q
    return q


def _multi_q(db, specs):
    mocks = []
    for spec in specs:
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = spec.get("first")
        q.all.return_value = spec.get("all_", [])
        mocks.append(q)
    db.query.side_effect = mocks
    return mocks


# ===========================================================================
# _has_time_overlap
# ===========================================================================

@pytest.mark.unit
class TestHasTimeOverlap:
    def test_no_date_start_returns_false(self):
        s1 = _session(None, None)
        s2 = _session(_dt(10), _dt(11))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False

    def test_different_dates_returns_false(self):
        s1 = _session(_dt(10, day=1), _dt(11, day=1))
        s2 = _session(_dt(10, day=2), _dt(11, day=2))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False

    def test_same_date_overlap_returns_true(self):
        # s1: 10:00-12:00, s2: 11:00-13:00 — overlap from 11:00-12:00
        s1 = _session(_dt(10), _dt(12))
        s2 = _session(_dt(11), _dt(13))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is True

    def test_same_date_no_overlap_returns_false(self):
        # s1: 08:00-09:00, s2: 10:00-11:00 — no overlap
        s1 = _session(_dt(8), _dt(9))
        s2 = _session(_dt(10), _dt(11))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False

    def test_adjacent_sessions_no_overlap(self):
        # s1 ends exactly when s2 starts — no overlap (strict <)
        s1 = _session(_dt(8), _dt(10))
        s2 = _session(_dt(10), _dt(12))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False

    def test_session1_missing_date_end_returns_false(self):
        s1 = _session(_dt(10), None)  # missing date_end
        s2 = _session(_dt(10), _dt(12))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False


# ===========================================================================
# _calculate_time_gap
# ===========================================================================

@pytest.mark.unit
class TestCalculateTimeGap:
    def test_gap_between_end_and_start(self):
        # end at 10:00, start at 10:30 → gap = 30 min
        end_t = time(10, 0)
        start_t = time(10, 30)
        result = EnrollmentConflictService._calculate_time_gap(end_t, start_t)
        assert result == 30

    def test_start_before_end_wraps_to_next_day(self):
        # end at 22:00, start at 01:00 (next day) → gap = 3 hours = 180 min
        end_t = time(22, 0)
        start_t = time(1, 0)
        result = EnrollmentConflictService._calculate_time_gap(end_t, start_t)
        assert result == 180

    def test_same_time_zero_gap(self):
        t = time(12, 0)
        result = EnrollmentConflictService._calculate_time_gap(t, t)
        assert result == 0


# ===========================================================================
# _has_travel_conflict
# ===========================================================================

@pytest.mark.unit
class TestHasTravelConflict:
    def test_no_date_start_returns_false(self):
        s1 = _session(None, None)
        s2 = _session(_dt(10), _dt(11))
        assert EnrollmentConflictService._has_travel_conflict(s1, None, s2, None) is False

    def test_different_dates_returns_false(self):
        s1 = _session(_dt(10, day=1), _dt(11, day=1))
        s2 = _session(_dt(10, day=2), _dt(11, day=2))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is False

    def test_no_location_returns_false(self):
        s1 = _session(_dt(10), _dt(11))
        s2 = _session(_dt(11, m=15), _dt(12))
        assert EnrollmentConflictService._has_travel_conflict(s1, None, s2, None) is False

    def test_same_location_returns_false(self):
        s1 = _session(_dt(10), _dt(11))
        s2 = _session(_dt(11, m=15), _dt(12))
        loc = {"location_id": 1}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc, s2, loc) is False

    def test_travel_conflict_within_buffer(self):
        # s1 ends 10:00, s2 starts 10:20 — gap 20 min < 30 min buffer → conflict
        s1 = _session(_dt(9), _dt(10))
        s2 = _session(_dt(10, 20), _dt(11, 20))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is True

    def test_no_travel_conflict_outside_buffer(self):
        # s1 ends 10:00, s2 starts 11:00 — gap 60 min >= 30 min buffer → no conflict
        s1 = _session(_dt(9), _dt(10))
        s2 = _session(_dt(11), _dt(12))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is False


# ===========================================================================
# _get_enrollment_type
# ===========================================================================

@pytest.mark.unit
class TestGetEnrollmentType:
    def _semester(self, spec_value, code="SEM-001"):
        sem = MagicMock()
        sem.specialization_type = spec_value  # string, no .value attr
        sem.code = code
        return sem

    def test_academy_season_lfa_player_pre_academy(self):
        sem = self._semester("LFA_PLAYER_PRE_ACADEMY")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "ACADEMY_SEASON"

    def test_academy_season_lfa_player_youth_academy(self):
        sem = self._semester("LFA_PLAYER_YOUTH_ACADEMY")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "ACADEMY_SEASON"

    def test_tournament_by_code_prefix(self):
        sem = self._semester("LFA_PLAYER_PRE", code="TOURN-2026-01")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "TOURNAMENT"

    def test_mini_season_without_tourn_prefix(self):
        sem = self._semester("LFA_PLAYER_PRE", code="SEM-2026-01")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "MINI_SEASON"

    def test_other_specialization_type(self):
        sem = self._semester("UNKNOWN_SPEC")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "OTHER"

    def test_lfa_football_player_mini_season(self):
        sem = self._semester("LFA_FOOTBALL_PLAYER", code="SEM-2026")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "MINI_SEASON"


# ===========================================================================
# check_session_time_conflict — early return paths
# ===========================================================================

@pytest.mark.unit
class TestCheckSessionTimeConflictEarlyReturns:
    def test_semester_not_found_returns_warning(self):
        db = _db()
        _q(db, first=None)  # semester not found
        result = EnrollmentConflictService.check_session_time_conflict(
            user_id=1, semester_id=99, db=db
        )
        assert result["has_conflict"] is False
        assert len(result["warnings"]) > 0
        assert "not found" in result["warnings"][0]

    def test_no_existing_enrollments_returns_no_conflicts(self):
        db = _db()
        semester = MagicMock()
        _multi_q(db, [
            {"first": semester},  # semester found
            {"all_": []},          # no existing enrollments
        ])
        result = EnrollmentConflictService.check_session_time_conflict(
            user_id=1, semester_id=1, db=db
        )
        assert result["has_conflict"] is False
        assert result["conflicts"] == []

    def test_no_future_sessions_returns_warning(self):
        db = _db()
        semester = MagicMock()
        enrollment = MagicMock()
        _multi_q(db, [
            {"first": semester},       # semester found
            {"all_": [enrollment]},    # existing enrollments found
            {"all_": []},              # no future sessions in target semester
        ])
        result = EnrollmentConflictService.check_session_time_conflict(
            user_id=1, semester_id=1, db=db
        )
        assert result["has_conflict"] is False
        assert any("No future sessions" in w for w in result["warnings"])
