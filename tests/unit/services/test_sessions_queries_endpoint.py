"""
Unit tests for app/api/api_v1/endpoints/sessions/queries.py

Covers:
  list_sessions — service pipeline patched, role-based paths (admin/student-INTERNSHIP/
                  student-other/instructor), group_id filter, session_type filter,
                  specialization_filter=False skips SessionFilterService
  get_session_recommendations — delegates to filter_service.get_session_recommendations_summary
  get_session_bookings — session not found → 404, session found with no bookings → BookingList
  get_instructor_sessions — non-instructor → 403, instructor returns session list
  get_calendar_events — returns list of dicts with date_start/date_end

All four pipeline services (RoleSemesterFilterService, SessionFilterService,
SessionStatsAggregator, SessionResponseBuilder) are patched at the module level.

NOTE: FastAPI Query(default, ...) objects are NOT integers when calling directly —
      always pass page= and size= explicitly in all call sites.
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.sessions.queries import (
    get_calendar_events,
    get_instructor_sessions,
    get_session_bookings,
    get_session_recommendations,
    list_sessions,
)
from app.models.user import UserRole
from app.models.specialization import SpecializationType

_BASE = "app.api.api_v1.endpoints.sessions.queries"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _user(role=UserRole.STUDENT, spec=None, uid=99):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.specialization = spec
    return u


def _instructor_user(uid=42):
    u = MagicMock()
    u.id = uid
    role_mock = MagicMock()
    role_mock.value = "instructor"
    u.role = role_mock
    u.specialization = None
    return u


def _mock_q():
    """Fully chained query mock."""
    q = MagicMock()
    for m in ("filter", "join", "options", "order_by", "offset", "limit",
              "filter_by", "distinct", "with_for_update"):
        getattr(q, m).return_value = q
    q.count.return_value = 0
    q.all.return_value = []
    q.scalar.return_value = 0
    q.first.return_value = None
    return q


def _mock_db(q=None):
    db = MagicMock()
    if q is None:
        q = _mock_q()
    db.query.return_value = q
    return db, q


def _service_patches(q):
    """Return context manager patches for all 4 pipeline services."""
    rfs_cls = MagicMock()
    rfs_cls.return_value.apply_role_semester_filter.return_value = q

    sfs_cls = MagicMock()
    sfs_cls.return_value.apply_specialization_filter.return_value = q
    sfs_cls.return_value.get_relevant_sessions_for_user.return_value = []
    sfs_cls.return_value.get_session_recommendations_summary.return_value = {"summary": "ok"}

    sa_cls = MagicMock()
    sa_cls.return_value.fetch_stats.return_value = {}

    rb_cls = MagicMock()
    rb_response = MagicMock()
    rb_cls.return_value.build_response.return_value = rb_response

    return (
        patch(f"{_BASE}.RoleSemesterFilterService", rfs_cls),
        patch(f"{_BASE}.SessionFilterService", sfs_cls),
        patch(f"{_BASE}.SessionStatsAggregator", sa_cls),
        patch(f"{_BASE}.SessionResponseBuilder", rb_cls),
        rfs_cls, sfs_cls, sa_cls, rb_cls,
    )


# ──────────────────────────────────────────────────────────────────────────────
# list_sessions
# ──────────────────────────────────────────────────────────────────────────────

class TestListSessions:

    def test_admin_calls_all_four_services(self):
        user = _user(role=UserRole.ADMIN)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, page=1, size=50)
        rfs_cls.return_value.apply_role_semester_filter.assert_called_once()
        sa_cls.return_value.fetch_stats.assert_called_once()
        rb_cls.return_value.build_response.assert_called_once()

    def test_student_internship_uses_simple_ordering(self):
        user = _user(role=UserRole.STUDENT, spec=SpecializationType.INTERNSHIP)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, *_ = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, page=1, size=50)
        # INTERNSHIP path: SessionFilterService.get_relevant_sessions_for_user NOT called
        sfs_cls.return_value.get_relevant_sessions_for_user.assert_not_called()

    def test_student_non_internship_uses_intelligent_filtering(self):
        user = _user(role=UserRole.STUDENT)
        # Specialization is set but is NOT SpecializationType.INTERNSHIP
        # We need user.specialization != SpecializationType.INTERNSHIP → True
        # Use a MagicMock whose __eq__ returns False for INTERNSHIP
        spec_mock = MagicMock()
        spec_mock.__eq__ = MagicMock(return_value=False)
        user.specialization = spec_mock
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
        sfs_cls.return_value.get_relevant_sessions_for_user.return_value = []
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, page=1, size=50)
        rb_cls.return_value.build_response.assert_called_once()

    def test_specialization_filter_false_skips_sfs(self):
        user = _user(role=UserRole.ADMIN)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, specialization_filter=False, page=1, size=50)
        sfs_cls.return_value.apply_specialization_filter.assert_not_called()

    def test_group_id_filter_applied(self):
        user = _user(role=UserRole.ADMIN)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, *_ = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, group_id=7, page=1, size=50)
        # q.filter was called (for group_id)
        q.filter.assert_called()

    def test_session_type_filter_applied(self):
        user = _user(role=UserRole.ADMIN)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, *_ = _service_patches(q)
        from app.models.session import SessionType
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, session_type=SessionType.hybrid, page=1, size=50)
        q.filter.assert_called()

    def test_pagination_page_2(self):
        user = _user(role=UserRole.ADMIN)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, page=2, size=10)
        rb_cls.return_value.build_response.assert_called_once()
        call_args = rb_cls.return_value.build_response.call_args.args
        assert call_args[3] == 2   # page
        assert call_args[4] == 10  # size

    def test_instructor_uses_standard_ordering(self):
        user = _user(role=UserRole.INSTRUCTOR)
        db, q = _mock_db()
        p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
        with p_rfs, p_sfs, p_sa, p_rb:
            list_sessions(db=db, current_user=user, page=1, size=50)
        rb_cls.return_value.build_response.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# get_session_recommendations
# ──────────────────────────────────────────────────────────────────────────────

class TestGetSessionRecommendations:

    def test_calls_recommendations_summary(self):
        user = _user()
        db, q = _mock_db()
        sfs_cls = MagicMock()
        sfs_cls.return_value.get_session_recommendations_summary.return_value = {"score": 5}
        with patch(f"{_BASE}.SessionFilterService", sfs_cls):
            result = get_session_recommendations(db=db, current_user=user)
        sfs_cls.return_value.get_session_recommendations_summary.assert_called_once_with(user)
        assert result["user_profile"] == {"score": 5}

    def test_returns_message_key(self):
        user = _user()
        db, q = _mock_db()
        sfs_cls = MagicMock()
        sfs_cls.return_value.get_session_recommendations_summary.return_value = {}
        with patch(f"{_BASE}.SessionFilterService", sfs_cls):
            result = get_session_recommendations(db=db, current_user=user)
        assert "message" in result


# ──────────────────────────────────────────────────────────────────────────────
# get_session_bookings
# ──────────────────────────────────────────────────────────────────────────────

class TestGetSessionBookings:

    def test_session_not_found_raises_404(self):
        user = _user()
        db, q = _mock_db()
        q.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            get_session_bookings(session_id=999, db=db, current_user=user, page=1, size=50)
        assert exc_info.value.status_code == 404

    def test_session_found_empty_bookings_returns_booking_list(self):
        user = _user()
        db, q = _mock_db()
        session_mock = MagicMock()
        session_mock.id = 1

        call_count = [0]
        def _first():
            call_count[0] += 1
            if call_count[0] == 1:
                return session_mock  # First call: session exists
            return None
        q.first.side_effect = _first
        q.all.return_value = []
        q.count.return_value = 0

        result = get_session_bookings(session_id=1, db=db, current_user=user, page=1, size=50)
        assert result.total == 0
        assert result.bookings == []

    def test_session_found_returns_correct_pagination(self):
        user = _user()
        db, q = _mock_db()
        session_mock = MagicMock()
        q.first.return_value = session_mock
        q.count.return_value = 5
        q.all.return_value = []

        result = get_session_bookings(session_id=1, db=db, current_user=user, page=2, size=10)
        assert result.page == 2
        assert result.size == 10
        assert result.total == 5


# ──────────────────────────────────────────────────────────────────────────────
# get_instructor_sessions
# ──────────────────────────────────────────────────────────────────────────────

class TestGetInstructorSessions:

    def test_non_instructor_raises_403(self):
        user = MagicMock()
        user.id = 99
        role_mock = MagicMock()
        role_mock.value = "student"  # Not 'instructor' → 403
        user.role = role_mock
        db, q = _mock_db()
        with pytest.raises(HTTPException) as exc_info:
            get_instructor_sessions(db=db, current_user=user, page=1, size=50)
        assert exc_info.value.status_code == 403

    def test_instructor_returns_sessions_dict(self):
        user = _instructor_user()
        db, q = _mock_db()
        session_mock = MagicMock()
        session_mock.id = 1
        session_mock.title = "Test"
        session_mock.description = "Desc"
        session_mock.date_start = MagicMock()
        session_mock.date_start.isoformat.return_value = "2026-03-10T10:00:00"
        session_mock.date_end = MagicMock()
        session_mock.date_end.isoformat.return_value = "2026-03-10T12:00:00"
        session_mock.location = "Court 1"
        session_mock.capacity = 20
        session_mock.instructor_id = 42
        session_mock.level = "INTERMEDIATE"
        session_mock.sport_type = "FOOTBALL"
        session_mock.created_at = MagicMock()
        session_mock.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        q.all.return_value = [session_mock]
        q.count.return_value = 1
        q.scalar.return_value = 2  # booking count

        result = get_instructor_sessions(db=db, current_user=user, page=1, size=50)
        assert result["total"] == 1
        assert len(result["sessions"]) == 1
        assert result["sessions"][0]["title"] == "Test"

    def test_instructor_empty_sessions_returns_empty_list(self):
        user = _instructor_user()
        db, q = _mock_db()
        q.all.return_value = []
        q.count.return_value = 0

        result = get_instructor_sessions(db=db, current_user=user, page=1, size=50)
        assert result["sessions"] == []
        assert result["total"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# get_calendar_events
# ──────────────────────────────────────────────────────────────────────────────

class TestGetCalendarEvents:

    def test_empty_sessions_returns_empty_list(self):
        user = _user()
        db, q = _mock_db()
        q.all.return_value = []
        result = get_calendar_events(db=db, current_user=user)
        assert result == []

    def test_returns_formatted_calendar_events(self):
        user = _user()
        db, q = _mock_db()
        s = MagicMock()
        s.id = 5
        s.title = "Evening Training"
        s.description = "Skills session"
        s.date_start = MagicMock()
        s.date_start.isoformat.return_value = "2026-03-15T18:00:00"
        s.date_end = MagicMock()
        s.date_end.isoformat.return_value = "2026-03-15T20:00:00"
        s.session_type = MagicMock()
        s.session_type.value = "hybrid"
        s.location = "Field A"
        s.capacity = 25
        q.all.return_value = [s]

        result = get_calendar_events(db=db, current_user=user)
        assert len(result) == 1
        assert result[0]["id"] == 5
        assert result[0]["title"] == "Evening Training"
        assert result[0]["session_type"] == "hybrid"

    def test_none_dates_handled_gracefully(self):
        user = _user()
        db, q = _mock_db()
        s = MagicMock()
        s.id = 1
        s.title = "No Date Session"
        s.description = None
        s.date_start = None
        s.date_end = None
        s.session_type = MagicMock()
        s.session_type.value = "on_site"
        s.location = None
        s.capacity = 10
        q.all.return_value = [s]

        result = get_calendar_events(db=db, current_user=user)
        assert result[0]["date_start"] is None
        assert result[0]["date_end"] is None
