"""
Unit tests for app/api/api_v1/endpoints/tournaments/lifecycle_instructor.py.

Branch coverage targets (~90%):
  assign_instructor_to_tournament:
    - role != ADMIN → 403
    - tournament not found → 404
    - status != SEEKING_INSTRUCTOR → 400
    - instructor not found → 404
    - instructor.role != INSTRUCTOR → 400
    - success path
  instructor_accept_assignment:
    - tournament not found → 404
    - status != PENDING_INSTRUCTOR_ACCEPTANCE → 400
    - instructor not assigned (id mismatch) → 403
    - success path
  instructor_decline_assignment:
    - tournament not found → 404
    - status != PENDING_INSTRUCTOR_ACCEPTANCE → 400
    - instructor not assigned → 403
    - success path
    - success path with no message (default "No reason provided")

Sprint 40 fix: production code now uses UserRole.INSTRUCTOR (was UserRole.GRANDMASTER, a
non-existent enum value that raised AttributeError at runtime). Tests no longer need the
GRANDMASTER sentinel patch.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.lifecycle_instructor import (
    assign_instructor_to_tournament,
    instructor_accept_assignment,
    instructor_decline_assignment,
    AssignInstructorRequest,
    InstructorActionRequest,
)
from app.models.user import User, UserRole
from app.models.semester import Semester

_BASE = "app.api.api_v1.endpoints.tournaments.lifecycle_instructor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock(spec=User)
    u.role = UserRole.ADMIN
    u.id = 1
    u.name = "Admin"
    return u


def _instructor_user(id_=42):
    u = MagicMock(spec=User)
    u.role = UserRole.INSTRUCTOR
    u.id = id_
    u.name = "Instructor"
    u.email = "inst@example.com"
    return u


def _student():
    u = MagicMock(spec=User)
    u.role = UserRole.STUDENT
    u.id = 99
    u.email = "student@example.com"
    return u


def _tournament(id_=1, status="SEEKING_INSTRUCTOR", master_instructor_id=None):
    t = MagicMock(spec=Semester)
    t.id = id_
    t.name = "Test Tournament"
    t.tournament_status = status
    t.master_instructor_id = master_instructor_id
    return t


def _db(tournament=None, user=None):
    """DB that routes Semester → tournament, User → user."""
    t_chain = MagicMock()
    t_chain.filter.return_value = t_chain
    t_chain.first.return_value = tournament

    u_chain = MagicMock()
    u_chain.filter.return_value = u_chain
    u_chain.first.return_value = user

    db = MagicMock()
    db.query.side_effect = lambda model: t_chain if model is Semester else u_chain
    return db


# ---------------------------------------------------------------------------
# assign_instructor_to_tournament
# ---------------------------------------------------------------------------

class TestAssignInstructor:

    def test_non_admin_raises_403(self):
        db = _db()
        req = AssignInstructorRequest(instructor_id=42)
        with pytest.raises(HTTPException) as exc:
            assign_instructor_to_tournament(1, req, db=db, current_user=_student())
        assert exc.value.status_code == 403

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        req = AssignInstructorRequest(instructor_id=42)
        with pytest.raises(HTTPException) as exc:
            assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="IN_PROGRESS")
        db = _db(tournament=t)
        req = AssignInstructorRequest(instructor_id=42)
        with pytest.raises(HTTPException) as exc:
            assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 400

    def test_instructor_not_found_raises_404(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        db = _db(tournament=t, user=None)
        req = AssignInstructorRequest(instructor_id=42)
        with pytest.raises(HTTPException) as exc:
            assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_instructor_wrong_role_raises_400(self):
        """Non-instructor (STUDENT role) cannot be assigned — 400."""
        t = _tournament(status="SEEKING_INSTRUCTOR")
        student = _student()  # role=STUDENT != UserRole.INSTRUCTOR
        db = _db(tournament=t, user=student)
        req = AssignInstructorRequest(instructor_id=99)
        with pytest.raises(HTTPException) as exc:
            assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 400

    def test_success_path(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        inst = _instructor_user(id_=42)  # role=UserRole.INSTRUCTOR ✓
        db = _db(tournament=t, user=inst)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.record_status_change"):
            result = assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert result.action == "assigned"
        assert result.instructor_id == 42


# ---------------------------------------------------------------------------
# instructor_accept_assignment
# (checks master_instructor_id == current_user.id only)
# ---------------------------------------------------------------------------

class TestInstructorAcceptAssignment:

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=_instructor_user())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        db = _db(tournament=t)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=_instructor_user())
        assert exc.value.status_code == 400

    def test_not_assigned_instructor_raises_403(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=99)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _instructor_user(id_=42)  # id=42 != master_instructor_id=99
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=caller)
        assert exc.value.status_code == 403

    def test_success_path(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _instructor_user(id_=42)
        with patch(f"{_BASE}.record_status_change"):
            result = instructor_accept_assignment(1, req, db=db, current_user=caller)
        assert result.action == "accepted"


# ---------------------------------------------------------------------------
# instructor_decline_assignment
# ---------------------------------------------------------------------------

class TestInstructorDeclineAssignment:

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_decline_assignment(1, req, db=db, current_user=_instructor_user())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="INSTRUCTOR_CONFIRMED")
        db = _db(tournament=t)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_decline_assignment(1, req, db=db, current_user=_instructor_user())
        assert exc.value.status_code == 400

    def test_not_assigned_instructor_raises_403(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=99)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _instructor_user(id_=42)
        with pytest.raises(HTTPException) as exc:
            instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert exc.value.status_code == 403

    def test_success_with_message(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest(message="too busy")
        caller = _instructor_user(id_=42)
        with patch(f"{_BASE}.record_status_change"):
            result = instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert result.action == "declined"

    def test_success_no_message(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest()  # message=None → "No reason provided"
        caller = _instructor_user(id_=42)
        with patch(f"{_BASE}.record_status_change"):
            result = instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert result.action == "declined"
