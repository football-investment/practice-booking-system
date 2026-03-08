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
from unittest.mock import MagicMock, patch

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
            user_id=42, semester_id=99, db=db
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
            user_id=42, semester_id=1, db=db
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
            user_id=42, semester_id=1, db=db
        )
        assert result["has_conflict"] is False
        assert any("No future sessions" in w for w in result["warnings"])


# ===========================================================================
# _has_time_overlap — missing branch (session2.date_end = None)
# ===========================================================================

@pytest.mark.unit
class TestHasTimeOverlapAdditional:
    def test_session2_missing_date_end_returns_false(self):
        """session2.date_end=None → cannot determine → False."""
        s1 = _session(_dt(10), _dt(12))
        s2 = _session(_dt(10), None)   # same date, but missing end
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False


# ===========================================================================
# _has_travel_conflict — missing branches (session.date_end = None)
# ===========================================================================

@pytest.mark.unit
class TestHasTravelConflictAdditional:
    def test_session1_missing_date_end_returns_false(self):
        """session1.date_end=None → cannot determine → False."""
        s1 = _session(_dt(10), None)    # missing end
        s2 = _session(_dt(11), _dt(12))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is False

    def test_session2_missing_date_end_returns_false(self):
        """session2.date_end=None → cannot determine → False."""
        s1 = _session(_dt(10), _dt(11))
        s2 = _session(_dt(11, m=15), None)  # missing end
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is False


# ===========================================================================
# _get_session_location
# ===========================================================================

@pytest.mark.unit
class TestGetSessionLocation:
    def test_returns_location_name_from_session_location_field(self):
        """session.location truthy → returns dict with location_name."""
        session = MagicMock()
        session.location = "Keleti pálya"
        result = EnrollmentConflictService._get_session_location(session, _db())
        assert result == {"location_name": "Keleti pálya"}

    def test_uses_semester_location_id_when_session_location_empty(self):
        """session.location falsy → queries via semester.location_id."""
        session = MagicMock()
        session.location = None
        session.semester.location_id = 5

        location_obj = MagicMock()
        location_obj.name = "LFA Campus"
        location_obj.city = "Budapest"
        location_obj.id = 5

        db = _db()
        _q(db, first=location_obj)

        result = EnrollmentConflictService._get_session_location(session, db)
        assert result["location_name"] == "LFA Campus"
        assert result["location_city"] == "Budapest"
        assert result["location_id"] == 5

    def test_returns_none_when_no_location_available(self):
        """No session.location, no semester.location_id → None."""
        session = MagicMock()
        session.location = None
        session.semester = None
        result = EnrollmentConflictService._get_session_location(session, _db())
        assert result is None

    def test_returns_none_when_location_not_found_in_db(self):
        """semester.location_id set but DB query returns None → None."""
        session = MagicMock()
        session.location = None
        session.semester.location_id = 99

        db = _db()
        _q(db, first=None)  # location not found

        result = EnrollmentConflictService._get_session_location(session, db)
        assert result is None


# ===========================================================================
# validate_enrollment_request
# ===========================================================================

@pytest.mark.unit
class TestValidateEnrollmentRequest:
    def test_no_conflicts_returns_allowed_true(self):
        """No conflicts → allowed=True, empty conflicts/warnings/recommendations."""
        from unittest.mock import patch

        with patch.object(
            EnrollmentConflictService,
            "check_session_time_conflict",
            return_value={"has_conflict": False, "conflicts": [], "warnings": []}
        ):
            result = EnrollmentConflictService.validate_enrollment_request(
                user_id=42, semester_id=1, db=_db()
            )

        assert result["allowed"] is True
        assert result["conflicts"] == []
        assert result["recommendations"] == []

    def test_blocking_conflict_adds_warning(self):
        """blocking severity conflict → warning added to result."""
        from unittest.mock import patch

        conflicts = [{"conflict_type": "time_overlap", "severity": "blocking"}]
        with patch.object(
            EnrollmentConflictService,
            "check_session_time_conflict",
            return_value={"has_conflict": True, "conflicts": conflicts, "warnings": []}
        ):
            result = EnrollmentConflictService.validate_enrollment_request(
                user_id=42, semester_id=1, db=_db()
            )

        assert any("FIGYELMEZTETÉS" in w or "ütközés" in w for w in result["warnings"])

    def test_travel_conflict_adds_recommendation(self):
        """travel_time conflict → recommendation added."""
        from unittest.mock import patch

        conflicts = [{"conflict_type": "travel_time", "severity": "warning"}]
        with patch.object(
            EnrollmentConflictService,
            "check_session_time_conflict",
            return_value={"has_conflict": True, "conflicts": conflicts, "warnings": []}
        ):
            result = EnrollmentConflictService.validate_enrollment_request(
                user_id=42, semester_id=1, db=_db()
            )

        assert len(result["recommendations"]) > 0


# ===========================================================================
# get_user_schedule — default date range
# ===========================================================================

@pytest.mark.unit
class TestGetUserSchedule:
    def test_default_date_range_no_enrollments(self):
        """No start_date/end_date → defaults applied; no enrollments → empty result."""
        db = _db()
        _q(db, all_=[])  # no enrollments
        result = EnrollmentConflictService.get_user_schedule(user_id=42, db=db)
        assert result["enrollments"] == []
        assert result["total_sessions"] == 0
        assert "start" in result["date_range"]
        assert "end" in result["date_range"]

    def test_explicit_date_range_respected(self):
        """Explicit start/end_date → used directly, no default override."""
        from datetime import date
        db = _db()
        _q(db, all_=[])
        start = date(2026, 4, 1)
        end = date(2026, 6, 30)
        result = EnrollmentConflictService.get_user_schedule(
            user_id=42, start_date=start, end_date=end, db=db
        )
        assert result["date_range"]["start"] == "2026-04-01"
        assert result["date_range"]["end"] == "2026-06-30"


# ===========================================================================
# get_user_schedule — with enrollments and sessions (loop body branches)
# ===========================================================================

@pytest.mark.unit
class TestGetUserScheduleWithData:
    """
    Covers:
      L233: for enrollment in enrollments: → loop body entered (L234)
      L259: for session in sessions: → loop body entered (L260)
    """

    def _make_enrollment(self, semester_id=5):
        enrollment = MagicMock()
        enrollment.id = 10
        sem = MagicMock()
        sem.id = semester_id
        sem.name = "Test Semester"
        enrollment.semester = sem
        return enrollment

    def _make_session(self, session_id=1, dt_start=None, dt_end=None):
        s = MagicMock()
        s.id = session_id
        s.date_start = dt_start or datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        s.date_end = dt_end or datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
        s.location_id = None
        _ = s.location   # pre-warm
        return s

    def test_enrollment_with_sessions_loop_body_entered(self):
        """One enrollment with one session → loop bodies at L234 and L260 entered."""
        enrollment = self._make_enrollment()
        session = self._make_session()

        # Build a DB mock that returns data in sequence:
        #   query 1 (SemesterEnrollment): enrollments list
        #   query 2 (SessionModel): sessions list
        #   query 3 (Booking): user bookings (empty)
        calls = [0]
        def _make_q(first=None, all_=None):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.join.return_value = q
            q.first.return_value = first
            q.all.return_value = all_ if all_ is not None else []
            return q

        q_enrollments = _make_q(all_=[enrollment])
        q_sessions = _make_q(all_=[session])
        q_bookings = _make_q(all_=[])

        def _side(*args):
            idx = calls[0]; calls[0] += 1
            return [q_enrollments, q_sessions, q_bookings][idx] if idx < 3 else _make_q()
        db = MagicMock()
        db.query.side_effect = _side

        with patch("app.services.enrollment_conflict_service.EnrollmentConflictService._get_session_location", return_value="TestLocation"):
            result = EnrollmentConflictService.get_user_schedule(
                user_id=42, db=db
            )

        assert len(result["enrollments"]) == 1
        assert result["enrollments"][0]["semester_name"] == "Test Semester"

    def test_enrollment_with_no_sessions_skips_session_loop(self):
        """Enrollment with no sessions → L259 exits without entering loop body."""
        enrollment = self._make_enrollment()

        calls = [0]
        def _make_q(all_=None):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.join.return_value = q
            q.all.return_value = all_ if all_ is not None else []
            return q

        q_enrollments = _make_q(all_=[enrollment])
        q_sessions = _make_q(all_=[])     # no sessions
        q_bookings = _make_q(all_=[])

        def _side(*args):
            idx = calls[0]; calls[0] += 1
            return [q_enrollments, q_sessions, q_bookings][idx] if idx < 3 else _make_q()
        db = MagicMock()
        db.query.side_effect = _side

        result = EnrollmentConflictService.get_user_schedule(user_id=42, db=db)
        assert len(result["enrollments"]) == 1
        assert result["total_sessions"] == 0   # no sessions found for this enrollment


# ===========================================================================
# check_session_time_conflict — with sessions and no booking conflicts (L103 loop)
# ===========================================================================

@pytest.mark.unit
class TestCheckSessionTimeConflictWithSessions:
    """
    Covers L97 False branch (target_sessions non-empty → enters for loop).
    Uses empty existing_bookings so the inner for-booking loop isn't needed.
    """

    def test_sessions_present_no_bookings_no_conflict(self):
        """
        target_sessions non-empty + existing_bookings empty for each session →
        L97 False branch (proceeds to for loop), L103 loop body entered,
        inner booking loop (L122) not entered → result has no conflicts.
        """
        from datetime import date as date_cls
        semester = MagicMock()
        semester.id = 5
        semester.name = "Target Sem"

        enrollment = MagicMock()
        enrollment.semester.sessions = []   # no existing sessions to match

        target_session = MagicMock()
        target_session.id = 1
        target_session.date_start = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        target_session.date_end = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

        calls = [0]
        def _make_q(first=None, all_=None):
            q = MagicMock()
            q.filter.return_value = q
            q.join.return_value = q
            q.all.return_value = all_ if all_ is not None else []
            q.first.return_value = first
            return q

        q_semester = _make_q(first=semester)
        q_enrollments = _make_q(all_=[enrollment])
        q_target_sessions = _make_q(all_=[target_session])
        q_bookings = _make_q(all_=[])   # no bookings for this target_session

        def _side(*args):
            idx = calls[0]; calls[0] += 1
            qs = [q_semester, q_enrollments, q_target_sessions, q_bookings]
            return qs[idx] if idx < len(qs) else _make_q()
        db = MagicMock()
        db.query.side_effect = _side

        with patch("app.services.enrollment_conflict_service.EnrollmentConflictService._get_session_location", return_value=None):
            result = EnrollmentConflictService.check_session_time_conflict(
                user_id=42, semester_id=5, db=db
            )

        assert result["has_conflict"] is False
        assert result["conflicts"] == []


# ===========================================================================
# Targeted mutation-killing tests (Sprint 46)
# ===========================================================================

class TestGetEnrollmentTypeMutantTargets:
    """
    Kill XX-string mutants on the MINI_SEASON branch spec list (line 357).
    mutmut wraps individual list items to "XX...XX"; tests must use those exact values.
    Killed mutants: 890 (YOUTH→XX), 891 (AMATEUR→XX), 892 (PRO→XX)
    """

    def _semester(self, spec_value, code="SEM-001"):
        sem = MagicMock()
        sem.specialization_type = spec_value
        sem.code = code
        return sem

    def test_lfa_player_youth_is_mini_season(self):
        sem = self._semester("LFA_PLAYER_YOUTH", code="SEM-2026")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "MINI_SEASON"

    def test_lfa_player_amateur_is_mini_season(self):
        sem = self._semester("LFA_PLAYER_AMATEUR", code="SEM-2026")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "MINI_SEASON"

    def test_lfa_player_pro_is_mini_season(self):
        sem = self._semester("LFA_PLAYER_PRO", code="SEM-2026")
        assert EnrollmentConflictService._get_enrollment_type(sem) == "MINI_SEASON"


class TestHasTimeOverlapMutantTargets:
    """
    Kill operator-mutation survivors in _has_time_overlap (line 404) and
    @staticmethod removal mutant (line 407).

    Killed mutants:
      922: s1.date_start < s2.date_end  →  <=  (reverse-adjacent: s2 ends when s1 starts)
      925: @staticmethod removed from _has_time_overlap (instance call injects self → TypeError)
    """

    def test_reverse_adjacent_no_overlap(self):
        # s2: 08:00-10:00, s1: 10:00-12:00  → s2.date_end == s1.date_start → no overlap
        # Mutant (<= instead of <): s1.date_start <= s2.date_end → 10:00 <= 10:00 True AND
        #   s2.date_start < s1.date_end → 08:00 < 12:00 True → would wrongly return True
        s1 = _session(_dt(10), _dt(12))
        s2 = _session(_dt(8), _dt(10))
        assert EnrollmentConflictService._has_time_overlap(s1, s2) is False

    def test_instance_call_preserves_staticmethod_behaviour(self):
        # Calling via instance on the original code works fine.
        # With @staticmethod removed, Python injects self as first arg → TypeError.
        s1 = _session(_dt(10), _dt(12))
        s2 = _session(_dt(11), _dt(13))
        result = EnrollmentConflictService()._has_time_overlap(s1, s2)
        assert result is True


class TestHasTravelConflictMutantTargets:
    """
    Kill or→and mutant (line 424) and boundary mutants on `0 <= min_gap < BUFFER` (line 444).

    Killed mutants:
      942: `not location1 or not location2`  →  `not location1 and not location2`
           (only one location None still triggers early-return with `or`, not with `and`)
      951: 0 <= min_gap  →  1 <= min_gap  (gap=0 is conflict, but 1<=0 is False)
      952: 0 <= min_gap  →  0 < min_gap   (gap=0 is conflict, but 0<0 is False)
      953: min_gap < 30  →  min_gap <= 30 (gap=30 is NOT a conflict, but <=30 is True)
    """

    def test_one_location_none_other_present_returns_false(self):
        # Only location2 provided, location1 is None.
        # Original `or`: True OR False = True → returns False (correct)
        # Mutant `and`: True AND False = False → proceeds → None.get() → AttributeError
        s1 = _session(_dt(10), _dt(11))
        s2 = _session(_dt(11, m=15), _dt(12))
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, None, s2, loc2) is False

    def test_zero_minute_gap_different_locations_is_conflict(self):
        # s1: 09:00-10:00, s2: 10:00-11:00 — gap = 0 min, different locations → conflict
        # Original: 0 <= 0 < 30 → True (conflict)
        # Mutant 951 (1<=): 1 <= 0 → False (no conflict) — WRONG
        # Mutant 952 (0<):  0 < 0 → False (no conflict) — WRONG
        s1 = _session(_dt(9), _dt(10))
        s2 = _session(_dt(10), _dt(11))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is True

    def test_exactly_30_minute_gap_is_not_conflict(self):
        # s1: 09:00-10:00, s2: 10:30-11:30 — gap = 30 min → NOT a conflict (strict <30)
        # Mutant 953 (<=30): 0 <= 30 <= 30 → True (conflict) — WRONG
        s1 = _session(_dt(9), _dt(10))
        s2 = _session(_dt(10, 30), _dt(11, 30))
        loc1 = {"location_id": 1}
        loc2 = {"location_id": 2}
        assert EnrollmentConflictService._has_travel_conflict(s1, loc1, s2, loc2) is False


class TestCalculateTimeGapMutantTargets:
    """
    Kill @staticmethod removal mutant on _calculate_time_gap (line 446).
    Killed mutant: 954 (@staticmethod removed → instance call injects self → TypeError)
    """

    def test_instance_call_preserves_staticmethod_behaviour(self):
        from datetime import time as time_cls
        result = EnrollmentConflictService()._calculate_time_gap(
            time_cls(10, 0), time_cls(11, 30)
        )
        assert result == 90
