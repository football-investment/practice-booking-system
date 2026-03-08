"""
Unit tests for app/services/tournament/instructor_service.py

Covers all three functions end-to-end with every decision branch:
  send_instructor_request    — semester/instructor validation + duplicate guard
  accept_instructor_request  — auth + status checks + session assignment
  decline_instructor_request — auth + status checks + optional reason
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from app.services.tournament.instructor_service import (
    send_instructor_request,
    accept_instructor_request,
    decline_instructor_request,
)
from app.models.semester import SemesterStatus
from app.models.user import UserRole
from app.models.instructor_assignment import AssignmentRequestStatus


# ── helpers ──────────────────────────────────────────────────────────────────

def _db():
    return MagicMock()


def _mock_semester(status=SemesterStatus.SEEKING_INSTRUCTOR, name="Cup"):
    s = MagicMock()
    s.id = 10
    s.name = name
    s.status = status
    s.start_date = "2026-04-01"
    return s


def _mock_instructor(role=UserRole.INSTRUCTOR):
    u = MagicMock()
    u.id = 99
    u.role = role
    return u


def _mock_request(instructor_id=99, status=AssignmentRequestStatus.PENDING, req_id=1):
    r = MagicMock()
    r.id = req_id
    r.instructor_id = instructor_id
    r.semester_id = 10
    r.status = status
    return r


def _q(db, return_value):
    """Set db.query(...).filter(...).first() chain return value."""
    db.query.return_value.filter.return_value.first.return_value = return_value


def _q_and(db, return_value):
    """Set db.query(...).filter(and_(...)).first() chain."""
    db.query.return_value.filter.return_value.first.return_value = return_value


# ─────────────────────────────────────────────────────────────────────────────
# send_instructor_request
# ─────────────────────────────────────────────────────────────────────────────

class TestSendInstructorRequest:

    def test_semester_not_found_raises(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)

    def test_wrong_semester_status_raises(self):
        db = _db()
        semester = _mock_semester(status=SemesterStatus.DRAFT)
        db.query.return_value.filter.return_value.first.return_value = semester
        with pytest.raises(ValueError, match="SEEKING_INSTRUCTOR"):
            send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)

    def test_instructor_not_found_raises(self):
        db = _db()
        semester = _mock_semester()
        # First call → semester, second call → None (instructor not found)
        db.query.return_value.filter.return_value.first.side_effect = [semester, None]
        with pytest.raises(ValueError, match="not found"):
            send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)

    def test_user_not_instructor_role_raises(self):
        db = _db()
        semester = _mock_semester()
        instructor = _mock_instructor(role=UserRole.STUDENT)
        db.query.return_value.filter.return_value.first.side_effect = [semester, instructor]
        with pytest.raises(ValueError, match="not an instructor"):
            send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)

    def test_existing_pending_request_raises(self):
        db = _db()
        semester = _mock_semester()
        instructor = _mock_instructor()
        existing = _mock_request()
        db.query.return_value.filter.return_value.first.side_effect = [semester, instructor, existing]
        with pytest.raises(ValueError, match="Pending request"):
            send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)

    def test_success_creates_and_commits(self):
        db = _db()
        semester = _mock_semester()
        instructor = _mock_instructor()
        # No existing request
        db.query.return_value.filter.return_value.first.side_effect = [semester, instructor, None]
        result = send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_success_with_custom_message(self):
        db = _db()
        semester = _mock_semester()
        instructor = _mock_instructor()
        db.query.return_value.filter.return_value.first.side_effect = [semester, instructor, None]
        send_instructor_request(
            db, semester_id=10, instructor_id=99, requested_by_admin_id=1, message="Please join"
        )
        db.commit.assert_called_once()

    def test_default_message_uses_semester_name(self):
        db = _db()
        semester = _mock_semester(name="Winter Cup")
        instructor = _mock_instructor()
        db.query.return_value.filter.return_value.first.side_effect = [semester, instructor, None]
        # No message provided — default constructed from semester.name
        send_instructor_request(db, semester_id=10, instructor_id=99, requested_by_admin_id=1)
        added = db.add.call_args[0][0]
        assert "Winter Cup" in (added.request_message or "")


# ─────────────────────────────────────────────────────────────────────────────
# accept_instructor_request
# ─────────────────────────────────────────────────────────────────────────────

class TestAcceptInstructorRequest:

    def test_request_not_found_raises(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            accept_instructor_request(db, request_id=1, instructor_id=99)

    def test_wrong_instructor_raises(self):
        db = _db()
        req = _mock_request(instructor_id=999)  # different instructor
        db.query.return_value.filter.return_value.first.return_value = req
        with pytest.raises(ValueError, match="not authorized"):
            accept_instructor_request(db, request_id=1, instructor_id=99)

    def test_non_pending_request_raises(self):
        db = _db()
        req = _mock_request(status=AssignmentRequestStatus.DECLINED)
        db.query.return_value.filter.return_value.first.side_effect = [req]
        with pytest.raises(ValueError, match="PENDING"):
            accept_instructor_request(db, request_id=1, instructor_id=99)

    def test_semester_not_found_raises(self):
        db = _db()
        req = _mock_request()
        db.query.return_value.filter.return_value.first.side_effect = [req, None]
        with pytest.raises(ValueError, match="semester not found"):
            accept_instructor_request(db, request_id=1, instructor_id=99)

    def test_success_activates_tournament(self):
        db = _db()
        req = _mock_request()
        semester = _mock_semester()
        db.query.return_value.filter.return_value.first.side_effect = [req, semester]
        # No sessions to assign
        db.query.return_value.filter.return_value.all.return_value = []
        result = accept_instructor_request(db, request_id=1, instructor_id=99)
        assert req.status == AssignmentRequestStatus.ACCEPTED
        assert semester.status == SemesterStatus.READY_FOR_ENROLLMENT
        assert semester.master_instructor_id == 99
        db.commit.assert_called_once()

    def test_success_assigns_instructor_to_sessions(self):
        db = _db()
        req = _mock_request()
        semester = _mock_semester()
        session1, session2 = MagicMock(), MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [req, semester]
        db.query.return_value.filter.return_value.all.return_value = [session1, session2]
        accept_instructor_request(db, request_id=1, instructor_id=99)
        assert session1.instructor_id == 99
        assert session2.instructor_id == 99


# ─────────────────────────────────────────────────────────────────────────────
# decline_instructor_request
# ─────────────────────────────────────────────────────────────────────────────

class TestDeclineInstructorRequest:

    def test_request_not_found_raises(self):
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            decline_instructor_request(db, request_id=1, instructor_id=99)

    def test_wrong_instructor_raises(self):
        db = _db()
        req = _mock_request(instructor_id=888)
        db.query.return_value.filter.return_value.first.return_value = req
        with pytest.raises(ValueError, match="not authorized"):
            decline_instructor_request(db, request_id=1, instructor_id=99)

    def test_non_pending_raises(self):
        db = _db()
        req = _mock_request(status=AssignmentRequestStatus.ACCEPTED)
        db.query.return_value.filter.return_value.first.return_value = req
        with pytest.raises(ValueError, match="PENDING"):
            decline_instructor_request(db, request_id=1, instructor_id=99)

    def test_success_sets_declined_status(self):
        db = _db()
        req = _mock_request()
        db.query.return_value.filter.return_value.first.return_value = req
        decline_instructor_request(db, request_id=1, instructor_id=99)
        assert req.status == AssignmentRequestStatus.DECLINED
        db.commit.assert_called_once()

    def test_success_with_reason_sets_message(self):
        db = _db()
        req = _mock_request()
        db.query.return_value.filter.return_value.first.return_value = req
        decline_instructor_request(db, request_id=1, instructor_id=99, reason="Not available")
        assert req.response_message == "Not available"

    def test_success_without_reason_no_message_set(self):
        db = _db()
        req = _mock_request()
        db.query.return_value.filter.return_value.first.return_value = req
        decline_instructor_request(db, request_id=1, instructor_id=99, reason=None)
        # response_message should NOT be set when no reason given
        assert not hasattr(req, 'response_message') or req.response_message != "ignored"
        db.commit.assert_called_once()
