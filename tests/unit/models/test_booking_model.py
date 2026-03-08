"""
Unit tests for app/models/booking.py hybrid properties.

No DB required — plain Booking() instantiation with MagicMock attributes.
Targets the 69% branch coverage gap on the model's hybrid properties.
"""

import pytest
from unittest.mock import MagicMock

from app.models.booking import Booking, BookingStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _booking_with_attendance(status_value: str) -> Booking:
    """Return a Booking with a mock attendance record."""
    booking = Booking()
    booking.attendance = MagicMock()
    booking.attendance.status.value = status_value
    return booking


def _booking_no_attendance() -> Booking:
    """Return a Booking with no attendance record (None)."""
    booking = Booking()
    booking.attendance = None
    return booking


# ---------------------------------------------------------------------------
# hybrid_property: attended
# ---------------------------------------------------------------------------

class TestAttendedProperty:

    def test_attended_true_when_present(self):
        booking = _booking_with_attendance("present")
        assert booking.attended is True

    def test_attended_true_when_late(self):
        booking = _booking_with_attendance("late")
        assert booking.attended is True

    def test_attended_false_when_absent(self):
        booking = _booking_with_attendance("absent")
        assert booking.attended is False

    def test_attended_false_when_excused(self):
        booking = _booking_with_attendance("excused")
        assert booking.attended is False

    def test_attended_false_no_attendance_record(self):
        booking = _booking_no_attendance()
        assert booking.attended is False


# ---------------------------------------------------------------------------
# hybrid_property: can_give_feedback
# ---------------------------------------------------------------------------

class TestCanGiveFeedback:

    def _confirmed_attended(self, *, has_feedback: bool, same_session: bool = True) -> Booking:
        """Helper: CONFIRMED + attended + optional existing feedback."""
        booking = Booking()
        booking.status = BookingStatus.CONFIRMED
        booking.session_id = 10

        # attendance → attended = True
        booking.attendance = MagicMock()
        booking.attendance.status.value = "present"

        # user feedbacks
        if has_feedback:
            fb = MagicMock()
            fb.session_id = 10 if same_session else 99
            booking.user = MagicMock()
            booking.user.feedbacks = [fb]
        else:
            booking.user = MagicMock()
            booking.user.feedbacks = []

        return booking

    def test_not_confirmed_returns_false(self):
        booking = _booking_with_attendance("present")
        booking.status = BookingStatus.WAITLISTED
        booking.session_id = 10
        booking.user = MagicMock()
        booking.user.feedbacks = []
        assert booking.can_give_feedback is False

    def test_not_attended_returns_false(self):
        booking = _booking_no_attendance()
        booking.status = BookingStatus.CONFIRMED
        booking.session_id = 10
        booking.user = MagicMock()
        booking.user.feedbacks = []
        assert booking.can_give_feedback is False

    def test_already_has_feedback_same_session_returns_false(self):
        booking = self._confirmed_attended(has_feedback=True, same_session=True)
        assert booking.can_give_feedback is False

    def test_feedback_for_different_session_does_not_block(self):
        booking = self._confirmed_attended(has_feedback=True, same_session=False)
        assert booking.can_give_feedback is True

    def test_all_conditions_met_returns_true(self):
        booking = self._confirmed_attended(has_feedback=False)
        assert booking.can_give_feedback is True


# ---------------------------------------------------------------------------
# hybrid_property: feedback_submitted
# ---------------------------------------------------------------------------

class TestFeedbackSubmitted:

    def test_feedback_submitted_true_matching_session(self):
        booking = Booking()
        booking.session_id = 5
        fb = MagicMock()
        fb.session_id = 5
        booking.user = MagicMock()
        booking.user.feedbacks = [fb]
        assert booking.feedback_submitted is True

    def test_feedback_submitted_false_no_feedbacks(self):
        booking = Booking()
        booking.session_id = 5
        booking.user = MagicMock()
        booking.user.feedbacks = []
        assert booking.feedback_submitted is False

    def test_feedback_submitted_false_different_session(self):
        booking = Booking()
        booking.session_id = 5
        fb = MagicMock()
        fb.session_id = 99
        booking.user = MagicMock()
        booking.user.feedbacks = [fb]
        assert booking.feedback_submitted is False


# ---------------------------------------------------------------------------
# update_attendance_status()
# ---------------------------------------------------------------------------

class TestUpdateAttendanceStatus:

    def test_with_attendance_syncs_value(self):
        booking = _booking_with_attendance("present")
        booking.update_attendance_status()
        assert booking.attended_status == "present"

    def test_no_attendance_sets_none(self):
        booking = _booking_no_attendance()
        booking.update_attendance_status()
        assert booking.attended_status is None
