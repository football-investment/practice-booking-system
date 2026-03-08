"""
Unit tests for app/api/api_v1/endpoints/tournaments/lifecycle_instructor.py.

Branch coverage targets (31.8% → ~90%):
  assign_instructor_to_tournament:
    - role != ADMIN → 403
    - tournament not found → 404
    - status != SEEKING_INSTRUCTOR → 400
    - instructor not found → 404
    - instructor.role != GRANDMASTER → 400  (NOTE: UserRole.GRANDMASTER missing — patch required)
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

NOTE: Production code uses `UserRole.GRANDMASTER` which does NOT exist in the current
UserRole enum (ADMIN/INSTRUCTOR/STUDENT only). Tests that reach this check must patch
the module-level UserRole to inject a GRANDMASTER sentinel value.
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

# Sentinel for the missing GRANDMASTER role — used in patched UserRole
_GRANDMASTER_SENTINEL = "grandmaster_sentinel"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_user_role():
    """Return a mock UserRole with all required attributes including GRANDMASTER."""
    mr = MagicMock()
    mr.ADMIN = UserRole.ADMIN
    mr.INSTRUCTOR = UserRole.INSTRUCTOR
    mr.STUDENT = UserRole.STUDENT
    mr.GRANDMASTER = _GRANDMASTER_SENTINEL
    return mr


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


def _gm_user(id_=42):
    """User with sentinel GRANDMASTER role."""
    u = MagicMock(spec=User)
    u.role = _GRANDMASTER_SENTINEL
    u.id = id_
    u.name = "Grand Master"
    u.email = "gm@example.com"
    return u


def _student():
    u = MagicMock(spec=User)
    u.role = UserRole.STUDENT
    u.id = 99
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
        with patch(f"{_BASE}.UserRole", _mock_user_role()):
            with pytest.raises(HTTPException) as exc:
                assign_instructor_to_tournament(1, req, db=db, current_user=_student())
        assert exc.value.status_code == 403

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.UserRole", _mock_user_role()):
            with pytest.raises(HTTPException) as exc:
                assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="IN_PROGRESS")
        db = _db(tournament=t)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.UserRole", _mock_user_role()):
            with pytest.raises(HTTPException) as exc:
                assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 400

    def test_instructor_not_found_raises_404(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        db = _db(tournament=t, user=None)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.UserRole", _mock_user_role()):
            with pytest.raises(HTTPException) as exc:
                assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_instructor_wrong_role_raises_400(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        inst = _instructor_user(id_=42)  # role=INSTRUCTOR != GRANDMASTER_SENTINEL
        db = _db(tournament=t, user=inst)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.UserRole", _mock_user_role()), \
             patch(f"{_BASE}.record_status_change"):
            with pytest.raises(HTTPException) as exc:
                assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert exc.value.status_code == 400

    def test_success_path(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        gm = _gm_user(id_=42)  # role=GRANDMASTER_SENTINEL == MockRole.GRANDMASTER
        db = _db(tournament=t, user=gm)
        req = AssignInstructorRequest(instructor_id=42)
        with patch(f"{_BASE}.UserRole", _mock_user_role()), \
             patch(f"{_BASE}.record_status_change"):
            result = assign_instructor_to_tournament(1, req, db=db, current_user=_admin())
        assert result.action == "assigned"
        assert result.instructor_id == 42


# ---------------------------------------------------------------------------
# instructor_accept_assignment
# (no GRANDMASTER check — only checks master_instructor_id == current_user.id)
# ---------------------------------------------------------------------------

class TestInstructorAcceptAssignment:

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=_gm_user())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="SEEKING_INSTRUCTOR")
        db = _db(tournament=t)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=_gm_user())
        assert exc.value.status_code == 400

    def test_not_assigned_instructor_raises_403(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=99)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _gm_user(id_=42)  # id=42 != master_instructor_id=99
        with pytest.raises(HTTPException) as exc:
            instructor_accept_assignment(1, req, db=db, current_user=caller)
        assert exc.value.status_code == 403

    def test_success_path(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _gm_user(id_=42)
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
            instructor_decline_assignment(1, req, db=db, current_user=_gm_user())
        assert exc.value.status_code == 404

    def test_wrong_status_raises_400(self):
        t = _tournament(status="INSTRUCTOR_CONFIRMED")
        db = _db(tournament=t)
        req = InstructorActionRequest()
        with pytest.raises(HTTPException) as exc:
            instructor_decline_assignment(1, req, db=db, current_user=_gm_user())
        assert exc.value.status_code == 400

    def test_not_assigned_instructor_raises_403(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=99)
        db = _db(tournament=t)
        req = InstructorActionRequest()
        caller = _gm_user(id_=42)
        with pytest.raises(HTTPException) as exc:
            instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert exc.value.status_code == 403

    def test_success_with_message(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest(message="too busy")
        caller = _gm_user(id_=42)
        with patch(f"{_BASE}.record_status_change"):
            result = instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert result.action == "declined"

    def test_success_no_message(self):
        t = _tournament(status="PENDING_INSTRUCTOR_ACCEPTANCE", master_instructor_id=42)
        db = _db(tournament=t)
        req = InstructorActionRequest()  # message=None → "No reason provided"
        caller = _gm_user(id_=42)
        with patch(f"{_BASE}.record_status_change"):
            result = instructor_decline_assignment(1, req, db=db, current_user=caller)
        assert result.action == "declined"
