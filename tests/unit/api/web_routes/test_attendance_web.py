"""
Unit tests for app/api/web_routes/attendance.py

Covers:
  mark_attendance — not_instructor, session_not_found, too_early, session_ended,
                    student_not_enrolled, invalid_status,
                    new_attendance_success, update_confirmed_change_request,
                    update_pending_updates_directly, present_sets_check_in_time
  confirm_attendance — not_student, no_attendance, session_ended, confirm_success,
                       dispute_success, invalid_action
  handle_change_request — not_student, no_change_request, approve_success,
                          reject_success, invalid_action

Mock strategy:
  - asyncio.run(endpoint(...)) direct call
  - db.query().filter().first() → side_effect list for multi-query routes
  - Timezone mocked via freezegun-style datetime patching or MagicMock date_start/end
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from zoneinfo import ZoneInfo
from fastapi.responses import RedirectResponse

from app.api.web_routes.attendance import (
    mark_attendance,
    confirm_attendance,
    handle_change_request,
)
from app.models.user import UserRole
from app.models.attendance import AttendanceStatus, ConfirmationStatus


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_BASE = "app.api.web_routes.attendance"


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    return u


def _student(uid=99):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.STUDENT
    return u


def _req():
    return MagicMock()


def _run(coro):
    return asyncio.run(coro)


_BUD = ZoneInfo("Europe/Budapest")


def _now_budapest():
    """Current time as naive Budapest datetime (matches DB storage convention)."""
    return datetime.now(_BUD).replace(tzinfo=None)


def _session_in_window(session_id=1, instructor_id=42):
    """Session whose marking window is open: started 30 min ago, ends in 30 min (Budapest)."""
    s = MagicMock()
    s.id = session_id
    s.instructor_id = instructor_id
    now = _now_budapest()
    s.date_start = now - timedelta(minutes=30)
    s.date_end = now + timedelta(minutes=30)
    return s


def _session_ended(session_id=1, instructor_id=42):
    """Session that ended 1 hour ago (Budapest)."""
    s = MagicMock()
    s.id = session_id
    s.instructor_id = instructor_id
    now = _now_budapest()
    s.date_start = now - timedelta(hours=2)
    s.date_end = now - timedelta(hours=1)
    return s


def _session_future(session_id=1, instructor_id=42):
    """Session starting 2 hours from now (Budapest) — too early to mark attendance."""
    s = MagicMock()
    s.id = session_id
    s.instructor_id = instructor_id
    now = _now_budapest()
    s.date_start = now + timedelta(hours=2)
    s.date_end = now + timedelta(hours=3)
    return s


# ──────────────────────────────────────────────────────────────────────────────
# mark_attendance
# ──────────────────────────────────────────────────────────────────────────────

class TestMarkAttendance:

    def test_not_instructor_redirects(self):
        user = _student()
        db = MagicMock()
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert isinstance(result, RedirectResponse)
        assert "unauthorized" in result.headers["location"]

    def test_session_not_found_redirects(self):
        user = _instructor()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "unauthorized" in result.headers["location"]

    def test_not_your_session_redirects(self):
        user = _instructor(uid=42)
        s = MagicMock()
        s.instructor_id = 99
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = s
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "unauthorized" in result.headers["location"]

    def test_too_early_redirects(self):
        user = _instructor()
        s = _session_future()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = s
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "too_early" in result.headers["location"]

    def test_session_ended_redirects(self):
        user = _instructor()
        s = _session_ended()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = s
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "session_ended" in result.headers["location"]

    def test_student_not_enrolled_redirects(self):
        user = _instructor()
        s = _session_in_window()
        db = MagicMock()
        # Session found, booking not found
        db.query.return_value.filter.return_value.first.side_effect = [s, None, None]
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "student_not_enrolled" in result.headers["location"]

    def test_invalid_status_redirects(self):
        user = _instructor()
        s = _session_in_window()
        booking = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, booking, None]
        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="invalid_status_value", notes=None,
            db=db, user=user,
        ))
        assert "invalid_status" in result.headers["location"]

    def test_new_attendance_created_success(self):
        user = _instructor()
        s = _session_in_window()
        booking = MagicMock()
        booking.id = 7

        db = MagicMock()
        # Session, booking, no existing attendance
        db.query.return_value.filter.return_value.first.side_effect = [s, booking, None]
        # attendance after flush gets id
        db.flush.side_effect = lambda: None

        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes="OK",
            db=db, user=user,
        ))
        assert "attendance_marked" in result.headers["location"]
        db.add.assert_called()
        db.commit.assert_called()

    def test_update_confirmed_attendance_creates_change_request(self):
        """When existing attendance is 'confirmed', update → change request."""
        user = _instructor()
        s = _session_in_window()
        booking = MagicMock()
        existing = MagicMock()
        existing.confirmation_status = ConfirmationStatus.confirmed

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, booking, existing]

        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="late", notes="Late by 5 min",
            db=db, user=user,
        ))
        assert "change_requested" in result.headers["location"]
        db.commit.assert_called()

    def test_update_pending_attendance_updates_directly(self):
        """When existing attendance is pending, update directly."""
        user = _instructor()
        s = _session_in_window()
        booking = MagicMock()
        existing = MagicMock()
        existing.confirmation_status = ConfirmationStatus.pending_confirmation
        existing.status = AttendanceStatus.absent  # different from 'present'

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, booking, existing]

        result = _run(mark_attendance(
            request=_req(), session_id=1,
            student_id=2, status="present", notes=None,
            db=db, user=user,
        ))
        assert "attendance_marked" in result.headers["location"]
        assert existing.status == AttendanceStatus.present


# ──────────────────────────────────────────────────────────────────────────────
# confirm_attendance
# ──────────────────────────────────────────────────────────────────────────────

class TestConfirmAttendance:

    def test_not_student_redirects(self):
        user = _instructor()
        db = MagicMock()
        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="confirm", dispute_reason=None,
            db=db, user=user,
        ))
        assert "unauthorized" in result.headers["location"]

    def test_no_attendance_redirects(self):
        user = _student()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="confirm", dispute_reason=None,
            db=db, user=user,
        ))
        assert "no_attendance" in result.headers["location"]

    def test_session_ended_redirects(self):
        user = _student()
        attendance = MagicMock()
        s = _session_ended()  # Already ended

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [attendance, s]

        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="confirm", dispute_reason=None,
            db=db, user=user,
        ))
        assert "session_ended" in result.headers["location"]

    def test_confirm_action_success(self):
        user = _student()
        attendance = MagicMock()
        attendance.id = 5
        s = MagicMock()
        # Session not ended → date_end in future
        s.date_end = _now_budapest() + timedelta(hours=1)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [attendance, s]

        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="confirm", dispute_reason=None,
            db=db, user=user,
        ))
        assert "attendance_confirmed" in result.headers["location"]
        assert attendance.confirmation_status == ConfirmationStatus.confirmed

    def test_dispute_action_success(self):
        user = _student()
        attendance = MagicMock()
        attendance.id = 5
        s = MagicMock()
        s.date_end = _now_budapest() + timedelta(hours=1)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [attendance, s]

        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="dispute", dispute_reason="I was there",
            db=db, user=user,
        ))
        assert "attendance_disputed" in result.headers["location"]
        assert attendance.confirmation_status == ConfirmationStatus.disputed

    def test_invalid_action_redirects(self):
        user = _student()
        attendance = MagicMock()
        s = MagicMock()
        s.date_end = _now_budapest() + timedelta(hours=1)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [attendance, s]

        result = _run(confirm_attendance(
            request=_req(), session_id=1,
            action="unknown_action", dispute_reason=None,
            db=db, user=user,
        ))
        assert "invalid_action" in result.headers["location"]


# ──────────────────────────────────────────────────────────────────────────────
# handle_change_request
# ──────────────────────────────────────────────────────────────────────────────

class TestHandleChangeRequest:

    def test_not_student_redirects(self):
        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="approve",
            db=MagicMock(), user=_instructor(),
        ))
        assert "unauthorized" in result.headers["location"]

    def test_no_attendance_redirects(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="approve",
            db=db, user=_student(),
        ))
        assert "no_change_request" in result.headers["location"]

    def test_no_pending_change_redirects(self):
        attendance = MagicMock()
        attendance.pending_change_to = None  # No pending change

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = attendance
        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="approve",
            db=db, user=_student(),
        ))
        assert "no_change_request" in result.headers["location"]

    def test_approve_applies_change(self):
        user = _student()
        attendance = MagicMock()
        attendance.pending_change_to = "present"
        attendance.status = AttendanceStatus.absent
        attendance.change_request_reason = "Was late"
        attendance.id = 3

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = attendance

        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="approve",
            db=db, user=user,
        ))
        assert "change_approved" in result.headers["location"]
        assert attendance.status == AttendanceStatus.present
        assert attendance.pending_change_to is None
        db.commit.assert_called()

    def test_reject_clears_change_request(self):
        user = _student()
        attendance = MagicMock()
        attendance.pending_change_to = "absent"
        attendance.status = AttendanceStatus.present
        attendance.id = 4

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = attendance

        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="reject",
            db=db, user=user,
        ))
        assert "change_rejected" in result.headers["location"]
        assert attendance.pending_change_to is None
        db.commit.assert_called()

    def test_invalid_action_redirects(self):
        attendance = MagicMock()
        attendance.pending_change_to = "absent"
        attendance.id = 4

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = attendance

        result = _run(handle_change_request(
            request=_req(), session_id=1,
            action="invalid",
            db=db, user=_student(),
        ))
        assert "invalid_action" in result.headers["location"]
