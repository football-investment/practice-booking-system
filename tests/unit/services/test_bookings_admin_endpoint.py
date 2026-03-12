"""
Unit tests for app/api/api_v1/endpoints/bookings/admin.py

Covers:
  get_all_bookings — no filters, semester_id filter (join), status filter, pagination
  confirm_booking — not found → 404, at capacity → 409, success → CONFIRMED
  admin_cancel_booking — not found → 404 (with_for_update), confirmed booking triggers
                         auto_promote, non-confirmed booking no auto_promote
  update_booking_attendance — not found → 404, invalid status → 400, existing attendance
                               → update, no attendance → create new,
                               IntegrityError uq_booking_attendance → 409

Uses with_for_update() loop pattern: fm.with_for_update.return_value = fm
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException

from app.api.api_v1.endpoints.bookings.admin import (
    admin_cancel_booking,
    confirm_booking,
    get_all_bookings,
    update_booking_attendance,
)
from app.models.booking import BookingStatus
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.bookings.admin"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _admin_user(uid=1):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.ADMIN
    return u


def _instructor_user(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    return u


def _booking_mock(bid=1, status=BookingStatus.CONFIRMED, session_id=10, user_id=99):
    b = MagicMock()
    b.id = bid
    b.status = status
    b.session_id = session_id
    b.user_id = user_id
    b.attendance = None
    b.user = MagicMock()
    b.session = MagicMock()
    return b


def _mock_q():
    q = MagicMock()
    for m in ("filter", "join", "options", "order_by", "offset", "limit",
              "filter_by", "distinct"):
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


def _wfu_mock_db(booking=None):
    """DB mock with with_for_update().first() chain for admin_cancel_booking/update_booking_attendance."""
    db = MagicMock()
    q = _mock_q()
    fm = MagicMock()
    fm.with_for_update.return_value = fm
    fm.first.return_value = booking
    q.filter.return_value = fm
    db.query.return_value = q
    return db


# ──────────────────────────────────────────────────────────────────────────────
# get_all_bookings
# ──────────────────────────────────────────────────────────────────────────────

class TestGetAllBookings:

    def test_no_filters_returns_empty_list(self):
        user = _admin_user()
        db, q = _mock_db()
        q.count.return_value = 0
        q.all.return_value = []
        result = get_all_bookings(db=db, current_user=user, page=1, size=50)
        assert result.total == 0
        assert result.bookings == []

    def test_semester_id_filter_applies_join(self):
        user = _admin_user()
        db, q = _mock_db()
        q.count.return_value = 0
        q.all.return_value = []
        get_all_bookings(db=db, current_user=user, semester_id=5, page=1, size=50)
        q.join.assert_called()

    def test_status_filter_applied(self):
        user = _admin_user()
        db, q = _mock_db()
        q.count.return_value = 0
        q.all.return_value = []
        get_all_bookings(db=db, current_user=user, status=BookingStatus.CONFIRMED, page=1, size=50)
        q.filter.assert_called()

    def test_pagination_page_2(self):
        user = _admin_user()
        db, q = _mock_db()
        q.count.return_value = 10
        q.all.return_value = []
        result = get_all_bookings(db=db, current_user=user, page=2, size=5)
        assert result.page == 2
        assert result.size == 5
        assert result.total == 10


# ──────────────────────────────────────────────────────────────────────────────
# confirm_booking
# ──────────────────────────────────────────────────────────────────────────────

class TestConfirmBooking:

    def test_booking_not_found_raises_404(self):
        user = _admin_user()
        db, q = _mock_db()
        q.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            confirm_booking(booking_id=999, db=db, current_user=user)
        assert exc_info.value.status_code == 404

    def test_session_at_capacity_raises_409(self):
        user = _admin_user()
        booking = _booking_mock(bid=1, session_id=10)
        session_mock = MagicMock()
        session_mock.capacity = 2
        session_mock.id = 10

        q = _mock_q()
        # Sequential .first() calls: booking, booking (2nd redundant query), session_obj
        q.first.side_effect = [booking, booking, session_mock]
        q.scalar.return_value = 2  # confirmed_count == capacity → 409

        db = MagicMock()
        db.query.return_value = q

        with pytest.raises(HTTPException) as exc_info:
            confirm_booking(booking_id=1, db=db, current_user=user)
        assert exc_info.value.status_code == 409

    def test_success_sets_confirmed_and_commits(self):
        user = _admin_user()
        booking = _booking_mock(bid=1, session_id=10)
        db, q = _mock_db()
        # first call: booking found, second: booking found again, third: session_obj (None → skip capacity check)
        q.first.side_effect = [booking, booking, None]
        q.scalar.return_value = 0  # no confirmed bookings

        result = confirm_booking(booking_id=1, db=db, current_user=user)
        assert booking.status == BookingStatus.CONFIRMED
        db.commit.assert_called_once()
        assert result["message"] == "Booking confirmed successfully"


# ──────────────────────────────────────────────────────────────────────────────
# admin_cancel_booking
# ──────────────────────────────────────────────────────────────────────────────

class TestAdminCancelBooking:

    def _cancel_data(self, reason="Admin override"):
        d = MagicMock()
        d.reason = reason
        return d

    def test_booking_not_found_raises_404(self):
        user = _admin_user()
        db = _wfu_mock_db(booking=None)
        with pytest.raises(HTTPException) as exc_info:
            admin_cancel_booking(booking_id=999, cancel_data=self._cancel_data(), db=db, current_user=user)
        assert exc_info.value.status_code == 404

    def test_confirmed_booking_triggers_auto_promote(self):
        user = _admin_user()
        booking = _booking_mock(bid=1, status=BookingStatus.CONFIRMED)
        db = _wfu_mock_db(booking=booking)
        promoted_user = MagicMock()
        promoted_user.name = "Alice"
        promoted_user.email = "alice@test.com"
        with patch(f"{_BASE}.auto_promote_from_waitlist", return_value=(promoted_user, 5)):
            result = admin_cancel_booking(
                booking_id=1, cancel_data=self._cancel_data(), db=db, current_user=user
            )
        assert booking.status == BookingStatus.CANCELLED
        assert "promotion" in result
        assert result["promotion"]["promoted_user_name"] == "Alice"

    def test_non_confirmed_booking_no_auto_promote(self):
        user = _admin_user()
        booking = _booking_mock(bid=1, status=BookingStatus.PENDING)
        db = _wfu_mock_db(booking=booking)
        with patch(f"{_BASE}.auto_promote_from_waitlist") as mock_promote:
            result = admin_cancel_booking(
                booking_id=1, cancel_data=self._cancel_data(), db=db, current_user=user
            )
        mock_promote.assert_not_called()
        assert booking.status == BookingStatus.CANCELLED
        assert "promotion" not in result

    def test_cancel_sets_cancelled_at_and_notes(self):
        user = _admin_user()
        booking = _booking_mock(bid=1, status=BookingStatus.CONFIRMED)
        db = _wfu_mock_db(booking=booking)
        with patch(f"{_BASE}.auto_promote_from_waitlist", return_value=None):
            admin_cancel_booking(
                booking_id=1, cancel_data=self._cancel_data("Test reason"), db=db, current_user=user
            )
        assert booking.cancelled_at is not None
        assert booking.notes == "Test reason"


# ──────────────────────────────────────────────────────────────────────────────
# update_booking_attendance
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateBookingAttendance:

    def test_booking_not_found_raises_404(self):
        user = _admin_user()
        db = _wfu_mock_db(booking=None)
        with pytest.raises(HTTPException) as exc_info:
            update_booking_attendance(
                booking_id=999, attendance_data={"status": "present"}, db=db, current_user=user
            )
        assert exc_info.value.status_code == 404

    def test_invalid_attendance_status_raises_400(self):
        user = _admin_user()
        booking = _booking_mock()
        db = _wfu_mock_db(booking=booking)
        with pytest.raises(HTTPException) as exc_info:
            update_booking_attendance(
                booking_id=1, attendance_data={"status": "flying"}, db=db, current_user=user
            )
        assert exc_info.value.status_code == 400

    def test_existing_attendance_updates_status(self):
        user = _admin_user()
        booking = _booking_mock()
        booking.attendance = MagicMock()  # Has existing attendance
        db = _wfu_mock_db(booking=booking)
        update_booking_attendance(
            booking_id=1, attendance_data={"status": "present"}, db=db, current_user=user
        )
        # Existing attendance.status should be updated
        assert booking.attendance.status is not None
        db.commit.assert_called_once()

    def test_no_attendance_creates_new_record(self):
        user = _admin_user()
        booking = _booking_mock()
        booking.attendance = None
        db = _wfu_mock_db(booking=booking)
        with patch(f"{_BASE}.Attendance") as mock_att_cls:
            mock_att = MagicMock()
            mock_att_cls.return_value = mock_att
            with patch(f"{_BASE}.AttendanceStatus"):
                update_booking_attendance(
                    booking_id=1, attendance_data={"status": "absent"}, db=db, current_user=user
                )
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_integrity_error_uq_booking_raises_409(self):
        user = _admin_user()
        booking = _booking_mock()
        booking.attendance = None
        db = _wfu_mock_db(booking=booking)
        orig = Exception("uq_booking_attendance constraint")
        err = IntegrityError(None, None, orig)
        err.orig = orig
        db.commit.side_effect = err
        with patch(f"{_BASE}.Attendance"), \
             patch(f"{_BASE}.AttendanceStatus"):
            with pytest.raises(HTTPException) as exc_info:
                update_booking_attendance(
                    booking_id=1, attendance_data={"status": "present"}, db=db, current_user=user
                )
        assert exc_info.value.status_code == 409

    def test_integrity_error_other_raises_409(self):
        user = _admin_user()
        booking = _booking_mock()
        booking.attendance = None
        db = _wfu_mock_db(booking=booking)
        orig = Exception("some other constraint violation")
        err = IntegrityError(None, None, orig)
        err.orig = orig
        db.commit.side_effect = err
        with patch(f"{_BASE}.Attendance"), \
             patch(f"{_BASE}.AttendanceStatus"):
            with pytest.raises(HTTPException) as exc_info:
                update_booking_attendance(
                    booking_id=1, attendance_data={"status": "late"}, db=db, current_user=user
                )
        assert exc_info.value.status_code == 409
