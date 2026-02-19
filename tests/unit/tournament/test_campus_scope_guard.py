"""
Unit tests — Campus-scope guard (_assert_campus_scope)

Verifies that the backend enforces single-campus scope for instructors
and allows unrestricted multi-campus access for admins.

All tests are DB-free: the guard function only inspects the current_user
object and the campus_ids / campus_schedule_overrides arguments.

Test matrix:
  ADMIN:
    G-01  campus_ids=[]           → allowed
    G-02  campus_ids=[1, 2, 3]    → allowed (multi-campus OK for admin)
    G-03  overrides={1: ..., 2: ..} → allowed
    G-04  campus_ids=None          → allowed

  INSTRUCTOR:
    G-05  campus_ids=None          → allowed
    G-06  campus_ids=[]            → allowed
    G-07  campus_ids=[42]          → allowed (single campus OK)
    G-08  campus_ids=[42, 99]      → 403 FORBIDDEN
    G-09  campus_ids=[1, 2, 3]     → 403 FORBIDDEN
    G-10  overrides={'42': {...}}  → allowed (single override OK)
    G-11  overrides={'42': {...}, '99': {...}} → 403 FORBIDDEN
    G-12  campus_ids=[42, 99] + overrides={'42': {...}} → 403 on campus_ids (first check)
"""

import pytest
from types import SimpleNamespace
from fastapi import HTTPException

# We test the guard function directly — no endpoint / DB needed.
from app.api.api_v1.endpoints.tournaments.generate_sessions import _assert_campus_scope
from app.models.user import UserRole


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _user(role: UserRole) -> SimpleNamespace:
    return SimpleNamespace(id=1, email="test@lfa.com", role=role)


ADMIN      = _user(UserRole.ADMIN)
INSTRUCTOR = _user(UserRole.INSTRUCTOR)


# ─── Admin tests ──────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestCampusScopeGuardAdmin:
    """Admin users bypass all campus-count restrictions."""

    def test_admin_no_campus_ids(self):
        """G-01: admin + campus_ids=None → no exception"""
        _assert_campus_scope(ADMIN, campus_ids=None, campus_schedule_overrides=None)

    def test_admin_empty_campus_ids(self):
        """G-02a: admin + campus_ids=[] → no exception"""
        _assert_campus_scope(ADMIN, campus_ids=[], campus_schedule_overrides=None)

    def test_admin_multi_campus_ids(self):
        """G-02b: admin + campus_ids=[1,2,3] → no exception"""
        _assert_campus_scope(ADMIN, campus_ids=[1, 2, 3], campus_schedule_overrides=None)

    def test_admin_multi_overrides(self):
        """G-03: admin + 2 campus overrides → no exception"""
        overrides = {"1": {"parallel_fields": 2}, "2": {"parallel_fields": 3}}
        _assert_campus_scope(ADMIN, campus_ids=None, campus_schedule_overrides=overrides)

    def test_admin_combined_multi(self):
        """G-04: admin + campus_ids=[1,2] + 2 overrides → no exception"""
        overrides = {"1": {}, "2": {}}
        _assert_campus_scope(ADMIN, campus_ids=[1, 2], campus_schedule_overrides=overrides)


# ─── Instructor tests ─────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestCampusScopeGuardInstructor:
    """Instructors are restricted to a single campus."""

    def test_instructor_no_campus_ids(self):
        """G-05: instructor + campus_ids=None → allowed"""
        _assert_campus_scope(INSTRUCTOR, campus_ids=None, campus_schedule_overrides=None)

    def test_instructor_empty_campus_ids(self):
        """G-06: instructor + campus_ids=[] → allowed"""
        _assert_campus_scope(INSTRUCTOR, campus_ids=[], campus_schedule_overrides=None)

    def test_instructor_single_campus(self):
        """G-07: instructor + campus_ids=[42] → allowed"""
        _assert_campus_scope(INSTRUCTOR, campus_ids=[42], campus_schedule_overrides=None)

    def test_instructor_two_campuses_raises_403(self):
        """G-08: instructor + campus_ids=[42, 99] → HTTP 403"""
        with pytest.raises(HTTPException) as exc_info:
            _assert_campus_scope(INSTRUCTOR, campus_ids=[42, 99], campus_schedule_overrides=None)
        assert exc_info.value.status_code == 403
        assert "single campus" in exc_info.value.detail.lower()

    def test_instructor_three_campuses_raises_403(self):
        """G-09: instructor + campus_ids=[1,2,3] → HTTP 403"""
        with pytest.raises(HTTPException) as exc_info:
            _assert_campus_scope(INSTRUCTOR, campus_ids=[1, 2, 3], campus_schedule_overrides=None)
        assert exc_info.value.status_code == 403

    def test_instructor_single_override_allowed(self):
        """G-10: instructor + 1 override entry → allowed"""
        overrides = {"42": {"parallel_fields": 2}}
        _assert_campus_scope(INSTRUCTOR, campus_ids=None, campus_schedule_overrides=overrides)

    def test_instructor_two_overrides_raises_403(self):
        """G-11: instructor + 2 override entries → HTTP 403"""
        overrides = {"42": {"parallel_fields": 2}, "99": {"parallel_fields": 3}}
        with pytest.raises(HTTPException) as exc_info:
            _assert_campus_scope(INSTRUCTOR, campus_ids=None, campus_schedule_overrides=overrides)
        assert exc_info.value.status_code == 403
        assert "single campus" in exc_info.value.detail.lower()

    def test_instructor_campus_ids_checked_before_overrides(self):
        """G-12: campus_ids check fires first (before overrides check)"""
        overrides = {"42": {}}  # only 1 override — would pass on its own
        with pytest.raises(HTTPException) as exc_info:
            _assert_campus_scope(
                INSTRUCTOR,
                campus_ids=[42, 99],           # ← triggers first
                campus_schedule_overrides=overrides,
            )
        assert exc_info.value.status_code == 403
        # Error message must reference campus_ids (not overrides)
        assert "campus" in exc_info.value.detail.lower()
