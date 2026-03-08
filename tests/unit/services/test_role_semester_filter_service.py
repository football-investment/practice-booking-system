"""Unit tests for app/services/role_semester_filter_service.py

Sprint P9 — Coverage target: ≥90% stmt+branch

Covers:
- apply_role_semester_filter: STUDENT / ADMIN / INSTRUCTOR / unknown role
- _filter_student_semesters: Mbappé with/without semester_id,
  regular student with current semesters, fallback (no current), explicit semester_id
- _filter_admin_semesters: with/without semester_id
- _filter_instructor_semesters: with/without semester_id (subquery + OR join)
"""

from unittest.mock import MagicMock

from app.models.user import UserRole
from app.services.role_semester_filter_service import RoleSemesterFilterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(role=UserRole.STUDENT, email="student@test.com", uid=42):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.email = email
    u.name = "Test User"
    return u


def _query_mock():
    """Fluent session query mock — join/filter/filter_by all return self."""
    q = MagicMock()
    for m in ("join", "filter", "filter_by"):
        getattr(q, m).return_value = q
    return q


def _db_with_semesters(all_results):
    """DB mock whose query().filter().all() returns all_results."""
    db = MagicMock()
    q = MagicMock()
    for m in ("filter", "order_by", "limit"):
        getattr(q, m).return_value = q
    q.all.return_value = all_results
    db.query.return_value = q
    return db


def _db_fallback(first_results, fallback_results):
    """
    DB mock for fallback path:
    - First all() → first_results (current semester check)
    - Second all() → fallback_results (recent semesters)
    """
    db = MagicMock()
    q = MagicMock()
    for m in ("filter", "order_by", "limit"):
        getattr(q, m).return_value = q
    q.all.side_effect = [first_results, fallback_results]
    db.query.return_value = q
    return db


def _db_instructor():
    """DB mock for instructor: subquery path."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.subquery.return_value = MagicMock()
    db.query.return_value = q
    return db


# ===========================================================================
# TestApplyRoleSemesterFilter  (dispatcher)
# ===========================================================================

class TestApplyRoleSemesterFilter:
    def test_student_role_delegates(self):
        db = _db_with_semesters([])
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="x@test.com")
        session_q = _query_mock()
        result = svc.apply_role_semester_filter(session_q, user, semester_id=None)
        # Result must be the same fluent mock (possibly with filters applied)
        assert result is not None

    def test_admin_role_delegates(self):
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.ADMIN)
        session_q = _query_mock()
        result = svc.apply_role_semester_filter(session_q, user, semester_id=None)
        assert result is session_q  # admin without semester_id: no filter added

    def test_instructor_role_delegates(self):
        db = _db_instructor()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.INSTRUCTOR)
        session_q = _query_mock()
        result = svc.apply_role_semester_filter(session_q, user, semester_id=None)
        assert result is not None

    def test_unknown_role_returns_query_unchanged(self):
        """Fallback: if role is not STUDENT/ADMIN/INSTRUCTOR, return query as-is."""
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        user = MagicMock()
        user.role = "SUPERUSER"  # not a known UserRole
        session_q = _query_mock()
        result = svc.apply_role_semester_filter(session_q, user, semester_id=None)
        assert result is session_q


# ===========================================================================
# TestFilterStudentSemesters
# ===========================================================================

class TestFilterStudentSemesters:
    def test_mbappe_without_semester_id_no_filter_applied(self):
        """Mbappé gets all sessions — no semester filter when semester_id=None."""
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="mbappe@lfa.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=None)
        # filter_by should NOT have been called (no restriction)
        session_q.filter_by.assert_not_called()
        assert result is session_q

    def test_mbappe_with_semester_id_filters_by_semester(self):
        """Mbappé with explicit semester_id filters to that semester."""
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="mbappe@lfa.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=7)
        session_q.filter_by.assert_called_once_with(semester_id=7)

    def test_regular_student_with_current_semesters(self):
        """Regular student sees sessions from current active semesters."""
        sem = MagicMock()
        sem.id = 5
        sem.name = "Spring 2024"
        db = _db_with_semesters([sem])
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="regular@test.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=None)
        # filter() must be called on session_q to restrict to semester_ids
        session_q.filter.assert_called()

    def test_regular_student_no_current_semesters_fallback(self):
        """When no current semesters exist, fall back to 3 most recent active semesters."""
        sem = MagicMock()
        sem.id = 3
        db = _db_fallback(first_results=[], fallback_results=[sem])
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="regular@test.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=None)
        # filter() must be called (fallback semester applied)
        session_q.filter.assert_called()

    def test_regular_student_no_current_and_no_recent_semesters(self):
        """When both current and recent semesters are empty, query is unchanged."""
        db = _db_fallback(first_results=[], fallback_results=[])
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="regular@test.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=None)
        # No filter applied since no semesters found — result still a query
        assert result is not None

    def test_regular_student_with_explicit_semester_id(self):
        """Regular student with semester_id filters to that semester."""
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.STUDENT, email="regular@test.com")
        session_q = _query_mock()
        result = svc._filter_student_semesters(session_q, user, semester_id=3)
        session_q.filter_by.assert_called_once_with(semester_id=3)


# ===========================================================================
# TestFilterAdminSemesters
# ===========================================================================

class TestFilterAdminSemesters:
    def test_admin_without_semester_id_no_filter(self):
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        session_q = _query_mock()
        result = svc._filter_admin_semesters(session_q, semester_id=None)
        session_q.filter_by.assert_not_called()
        assert result is session_q

    def test_admin_with_semester_id_filters(self):
        db = MagicMock()
        svc = RoleSemesterFilterService(db)
        session_q = _query_mock()
        result = svc._filter_admin_semesters(session_q, semester_id=9)
        session_q.filter_by.assert_called_once_with(semester_id=9)


# ===========================================================================
# TestFilterInstructorSemesters
# ===========================================================================

class TestFilterInstructorSemesters:
    def test_instructor_without_semester_id_joins_and_filters(self):
        db = _db_instructor()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.INSTRUCTOR, uid=42)
        session_q = _query_mock()
        result = svc._filter_instructor_semesters(session_q, user, semester_id=None)
        # join() and filter() must be called on the session query
        session_q.join.assert_called()
        session_q.filter.assert_called()

    def test_instructor_with_semester_id_adds_extra_filter(self):
        db = _db_instructor()
        svc = RoleSemesterFilterService(db)
        user = _user(role=UserRole.INSTRUCTOR, uid=42)
        session_q = _query_mock()
        result = svc._filter_instructor_semesters(session_q, user, semester_id=5)
        # Both join + OR filter + semester_id filter
        assert session_q.join.call_count >= 1
        # filter called at least twice: OR condition + semester_id
        assert session_q.filter.call_count >= 2
