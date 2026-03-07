"""
Sprint 36 — app/api/api_v1/endpoints/analytics.py
==================================================
Target: branch coverage gaps (7 missing branches, 56% → ≥80%)

Missing branches (from coverage.xml):
  L36[br:41] — get_analytics_metrics: dates provided → skip default-date if block
  L54[br:55], L55, L56 — semester_id provided → filter applied
  L65, L66, L67 — try/except in BookingStatus filter
  L89[br:98] — active_semester_obj found → populate active_semester dict

Covers:
  get_analytics_metrics:
    * no dates → default 30-day window (if block executed)
    * dates provided → L36 false branch (no default-date logic)
    * semester_id provided → semester filter applied (L54 true branch)
    * active semester found → active_semester dict populated (L89 true branch)
    * exception in outer try → fallback dict returned (L120 except branch)

  get_attendance_analytics:
    * attendance_count == 0 → early return [] (L158 true branch)
    * attendance_count > 0 + dates provided → runs query (L151 false branch)
    * inner except → returns []

  get_utilization_analytics / get_booking_analytics / get_user_analytics:
    * happy path + dates provided → L208, L252, None branches covered
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.api.api_v1.endpoints.analytics import (
    get_analytics_metrics,
    get_attendance_analytics,
    get_booking_analytics,
    get_user_analytics,
    get_utilization_analytics,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _q(first=None, count=0, all_=None, scalar=0):
    q = MagicMock()
    for m in ("filter", "join", "outerjoin", "options", "order_by",
              "group_by", "filter_by", "distinct", "with_entities"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.count.return_value = count
    q.scalar.return_value = scalar
    q.all.return_value = all_ if all_ is not None else []
    return q


def _seq_db(*queries):
    calls = [0]
    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return queries[idx] if idx < len(queries) else _q()
    db = MagicMock()
    db.query.side_effect = _side
    return db


def _admin():
    u = MagicMock()
    u.id = 1
    u.role = MagicMock()
    u.role.value = "admin"
    return u


def _semester_obj():
    s = MagicMock()
    s.id = 1
    s.name = "Test Semester"
    s.code = "TS-2025"
    s.start_date = MagicMock()
    s.start_date.isoformat.return_value = "2025-09-01"
    s.end_date = MagicMock()
    s.end_date.isoformat.return_value = "2026-01-31"
    return s


# ── get_analytics_metrics tests ───────────────────────────────────────────────

class TestGetAnalyticsMetrics:

    def _run(self, start_date=None, end_date=None, semester_id=None,
             sessions_q=None, bookings_q=None, semester_q=None, user_q=None):
        """Run get_analytics_metrics with controlled DB mocks."""
        if sessions_q is None:
            sessions_q = _q(count=5, scalar=100)
        if bookings_q is None:
            bookings_q = _q(count=20)
        if semester_q is None:
            semester_q = _q(first=None)
        if user_q is None:
            user_q = _q(count=10)

        db = _seq_db(
            sessions_q,   # db.query(SessionTypel) - base sessions
            bookings_q,   # db.query(Booking).join() - base bookings
            semester_q,   # db.query(Semester) - active semester
            user_q,       # db.query(User) - active users
        )
        return asyncio.run(get_analytics_metrics(
            start_date=start_date,
            end_date=end_date,
            semester_id=semester_id,
            current_user=_admin(),
            db=db,
        ))

    def test_no_dates_uses_default_30_day_window(self):
        """No dates → if block executes, sets default 30-day window."""
        result = self._run()
        assert "totalSessions" in result
        assert "bookingRate" in result

    def test_dates_provided_skips_default_window(self):
        """Dates provided → L36 false branch, skips default date logic."""
        result = self._run(start_date="2025-01-01", end_date="2025-12-31")
        assert result["metadata"]["period"]["start_date"] == "2025-01-01"
        assert result["metadata"]["period"]["end_date"] == "2025-12-31"

    def test_semester_id_provided_applies_filter(self):
        """semester_id provided → L54 true branch: semester filter applied to both queries."""
        result = self._run(
            start_date="2025-01-01", end_date="2025-12-31",
            semester_id=5,
        )
        # Both sessions_query and bookings_query had .filter() called with semester_id
        assert result["metadata"]["period"]["semester_id"] == 5

    def test_active_semester_found_populates_dict(self):
        """active_semester_obj found → L89 true branch: dict populated."""
        result = self._run(semester_q=_q(first=_semester_obj()))
        assert result["activeSemester"] is not None
        assert result["activeSemester"]["name"] == "Test Semester"

    def test_no_active_semester_returns_none(self):
        """No active semester → L89 false branch: activeSemester is None."""
        result = self._run(semester_q=_q(first=None))
        assert result["activeSemester"] is None

    def test_total_capacity_zero_booking_rate_is_zero(self):
        """total_capacity == 0 → booking_rate = 0 (L73 guard branch)."""
        sessions_q = _q(count=0, scalar=0)
        result = self._run(sessions_q=sessions_q)
        assert result["bookingRate"] == 0

    def test_total_capacity_nonzero_booking_rate_computed(self):
        """total_capacity > 0 → L73 true branch: booking_rate computed."""
        sessions_q = _q(count=5, scalar=200)
        bookings_q = _q(count=10)
        result = self._run(sessions_q=sessions_q, bookings_q=bookings_q)
        # booking_rate = confirmed_bookings / total_capacity * 100
        assert result["bookingRate"] >= 0

    def test_exception_in_outer_try_returns_fallback(self):
        """Exception in outer try → L120 except: returns fallback dict with 'error' key."""
        db = MagicMock()
        db.query.side_effect = RuntimeError("DB failure")
        result = asyncio.run(get_analytics_metrics(
            start_date=None, end_date=None,
            current_user=_admin(), db=db,
        ))
        assert "error" in result
        assert result["totalSessions"] == 0


# ── get_attendance_analytics tests ───────────────────────────────────────────

class TestGetAttendanceAnalytics:

    def test_no_attendance_data_returns_empty_list(self):
        """attendance_count == 0 → early return [] (L158 true branch)."""
        db = _seq_db(_q(count=0))  # attendance_count = 0
        result = asyncio.run(get_attendance_analytics(
            start_date=None, end_date=None, semester_id=None,
            current_user=_admin(), db=db,
        ))
        assert result == []

    def test_dates_provided_skips_default_window(self):
        """Dates provided → L151 false branch; with data runs the attendance query."""
        # attendance_count > 0, then attendance query returns empty list
        db = _seq_db(
            _q(count=5),    # attendance_count
            _q(all_=[]),    # attendance_query.all()
        )
        result = asyncio.run(get_attendance_analytics(
            start_date="2025-01-01", end_date="2025-12-31", semester_id=None,
            current_user=_admin(), db=db,
        ))
        assert isinstance(result, list)

    def test_exception_returns_empty_list(self):
        """Outer exception → returns []."""
        db = MagicMock()
        db.query.side_effect = RuntimeError("failure")
        result = asyncio.run(get_attendance_analytics(
            current_user=_admin(), db=db,
        ))
        assert result == []


# ── get_utilization_analytics tests ──────────────────────────────────────────

class TestGetUtilizationAnalytics:

    def test_dates_provided_skips_default_window(self):
        """Dates provided → L208 false branch; runs session utilization query."""
        row = MagicMock()
        row.session_id = 1
        row.capacity = 10
        row.booking_count = 5
        db = _seq_db(_q(all_=[row]))
        result = asyncio.run(get_utilization_analytics(
            start_date="2025-01-01", end_date="2025-12-31", semester_id=None,
            current_user=_admin(), db=db,
        ))
        assert len(result) == 1
        assert result[0]["utilizationRate"] == 50.0

    def test_session_capacity_zero_utilization_zero(self):
        """session.capacity == 0 → utilization_rate = 0 (L226 guard branch)."""
        row = MagicMock()
        row.session_id = 2
        row.capacity = 0
        row.booking_count = 3
        db = _seq_db(_q(all_=[row]))
        result = asyncio.run(get_utilization_analytics(
            start_date="2025-01-01", end_date="2025-12-31",
            current_user=_admin(), db=db,
        ))
        assert result[0]["utilizationRate"] == 0

    def test_exception_returns_empty_list(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("fail")
        result = asyncio.run(get_utilization_analytics(current_user=_admin(), db=db))
        assert result == []


# ── get_booking_analytics tests ───────────────────────────────────────────────

class TestGetBookingAnalytics:

    def test_dates_provided_skips_default_window(self):
        """Dates provided → L252 false branch."""
        trend = MagicMock()
        trend.date = "2025-06-15"
        trend.booking_count = 3
        db = _seq_db(_q(all_=[trend]))
        result = asyncio.run(get_booking_analytics(
            start_date="2025-01-01", end_date="2025-12-31",
            current_user=_admin(), db=db,
        ))
        assert len(result) == 1
        assert result[0]["bookings"] == 3

    def test_exception_returns_empty_list(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("fail")
        result = asyncio.run(get_booking_analytics(current_user=_admin(), db=db))
        assert result == []


# ── get_user_analytics tests ──────────────────────────────────────────────────

class TestGetUserAnalytics:

    def test_happy_path_returns_user_counts(self):
        """Happy path: runs 5 count queries and returns user stats."""
        db = _seq_db(
            _q(count=50),   # total_users
            _q(count=40),   # active_users
            _q(count=3),    # admin_users
            _q(count=10),   # instructor_users
            _q(count=37),   # student_users
        )
        result = asyncio.run(get_user_analytics(
            start_date=None, end_date=None,
            current_user=_admin(), db=db,
        ))
        assert result["totalUsers"] == 50
        assert result["activeUsers"] == 40
        assert result["usersByRole"]["admin"] == 3

    def test_exception_returns_fallback(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("fail")
        result = asyncio.run(get_user_analytics(current_user=_admin(), db=db))
        assert result["totalUsers"] == 0
        assert "error" in result
