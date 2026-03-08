"""
Unit tests for app/api/api_v1/endpoints/session_groups.py.

Branch coverage targets (8.3% → ~90%):
  auto_assign_groups: session not found, auth (admin bypass, instructor match, instructor mismatch),
                      ValueError on service, success
  get_session_groups: session not found, success
  move_student: group not found, session None, auth (admin bypass, instructor mismatch), failure, success
  delete_session_groups: session not found, auth (admin bypass, instructor mismatch), success
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.session_groups import (
    auto_assign_groups, get_session_groups, move_student, delete_session_groups,
    AutoAssignRequest, MoveStudentRequest,
)
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel

_BASE = "app.api.api_v1.endpoints.session_groups"

_SUMMARY = {"session_id": 1, "total_students": 0, "total_instructors": 0, "groups": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock(spec=User)
    u.role = UserRole.ADMIN
    u.id = 99
    return u


def _instructor(id_=10):
    u = MagicMock(spec=User)
    u.role = UserRole.INSTRUCTOR
    u.id = id_
    return u


def _session(id_=1, instructor_id=10):
    s = MagicMock(spec=SessionModel)
    s.id = id_
    s.instructor_id = instructor_id
    return s


def _db_session(session_val=None):
    """DB that returns session_val for any .first() call."""
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = session_val
    db = MagicMock()
    db.query.return_value = q
    return db


# ---------------------------------------------------------------------------
# auto_assign_groups
# ---------------------------------------------------------------------------

class TestAutoAssignGroups:

    def test_session_not_found_raises_404(self):
        db = _db_session(session_val=None)
        req = AutoAssignRequest(session_id=1)
        with pytest.raises(HTTPException) as exc:
            auto_assign_groups(req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_instructor_mismatch_raises_403(self):
        sess = _session(instructor_id=99)  # not the caller's id
        db = _db_session(session_val=sess)
        req = AutoAssignRequest(session_id=1)
        with pytest.raises(HTTPException) as exc:
            auto_assign_groups(req, db=db, current_user=_instructor(id_=10))
        assert exc.value.status_code == 403

    def test_admin_bypasses_auth_success(self):
        sess = _session(instructor_id=99)
        db = _db_session(session_val=sess)
        req = AutoAssignRequest(session_id=1)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.auto_assign_groups.return_value = []
            MockSGS.get_group_summary.return_value = _SUMMARY
            result = auto_assign_groups(req, db=db, current_user=_admin())
        assert result.session_id == 1

    def test_instructor_matching_session_success(self):
        sess = _session(instructor_id=10)
        db = _db_session(session_val=sess)
        req = AutoAssignRequest(session_id=1)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.auto_assign_groups.return_value = []
            MockSGS.get_group_summary.return_value = _SUMMARY
            result = auto_assign_groups(req, db=db, current_user=_instructor(id_=10))
        assert result.session_id == 1

    def test_value_error_raises_400(self):
        sess = _session(instructor_id=10)
        db = _db_session(session_val=sess)
        req = AutoAssignRequest(session_id=1)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.auto_assign_groups.side_effect = ValueError("not enough students")
            with pytest.raises(HTTPException) as exc:
                auto_assign_groups(req, db=db, current_user=_instructor(id_=10))
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_session_groups
# ---------------------------------------------------------------------------

class TestGetSessionGroups:

    def test_session_not_found_raises_404(self):
        db = _db_session(session_val=None)
        with pytest.raises(HTTPException) as exc:
            get_session_groups(session_id=1, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_session_found_returns_summary(self):
        sess = _session()
        db = _db_session(session_val=sess)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.get_group_summary.return_value = _SUMMARY
            result = get_session_groups(session_id=1, db=db, current_user=_admin())
        assert result.session_id == 1


# ---------------------------------------------------------------------------
# move_student
# ---------------------------------------------------------------------------

class TestMoveStudent:

    def test_group_not_found_raises_404(self):
        # DB returns None for SessionGroupAssignment query
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db = MagicMock()
        db.query.return_value = q
        req = MoveStudentRequest(student_id=1, from_group_id=1, to_group_id=2)
        with pytest.raises(HTTPException) as exc:
            move_student(req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_session_none_raises_404(self):
        from_group = MagicMock()
        from_group.session = None  # no session relationship
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = from_group
        db = MagicMock()
        db.query.return_value = q
        req = MoveStudentRequest(student_id=1, from_group_id=1, to_group_id=2)
        with pytest.raises(HTTPException) as exc:
            move_student(req, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_instructor_mismatch_raises_403(self):
        from_group = MagicMock()
        from_group.session = MagicMock()
        from_group.session.instructor_id = 99  # not caller's id
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = from_group
        db = MagicMock()
        db.query.return_value = q
        req = MoveStudentRequest(student_id=1, from_group_id=1, to_group_id=2)
        with pytest.raises(HTTPException) as exc:
            move_student(req, db=db, current_user=_instructor(id_=10))
        assert exc.value.status_code == 403

    def test_admin_bypasses_auth_failure_raises_400(self):
        from_group = MagicMock()
        from_group.session = MagicMock()
        from_group.session.instructor_id = 99
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = from_group
        db = MagicMock()
        db.query.return_value = q
        req = MoveStudentRequest(student_id=1, from_group_id=1, to_group_id=2)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.move_student_to_group.return_value = False
            with pytest.raises(HTTPException) as exc:
                move_student(req, db=db, current_user=_admin())
        assert exc.value.status_code == 400

    def test_success_returns_message(self):
        from_group = MagicMock()
        from_group.session = MagicMock()
        from_group.session.instructor_id = 99
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = from_group
        db = MagicMock()
        db.query.return_value = q
        req = MoveStudentRequest(student_id=1, from_group_id=1, to_group_id=2)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.move_student_to_group.return_value = True
            result = move_student(req, db=db, current_user=_admin())
        assert "moved" in result["message"]


# ---------------------------------------------------------------------------
# delete_session_groups
# ---------------------------------------------------------------------------

class TestDeleteSessionGroups:

    def test_session_not_found_raises_404(self):
        db = _db_session(session_val=None)
        with pytest.raises(HTTPException) as exc:
            delete_session_groups(session_id=1, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_instructor_mismatch_raises_403(self):
        sess = _session(instructor_id=99)
        db = _db_session(session_val=sess)
        with pytest.raises(HTTPException) as exc:
            delete_session_groups(session_id=1, db=db, current_user=_instructor(id_=10))
        assert exc.value.status_code == 403

    def test_admin_bypasses_auth_success(self):
        sess = _session(instructor_id=99)
        db = _db_session(session_val=sess)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.delete_all_groups.return_value = None
            result = delete_session_groups(session_id=1, db=db, current_user=_admin())
        assert result is None

    def test_instructor_matching_success(self):
        sess = _session(instructor_id=10)
        db = _db_session(session_val=sess)
        with patch(f"{_BASE}.SessionGroupService") as MockSGS:
            MockSGS.delete_all_groups.return_value = None
            result = delete_session_groups(session_id=1, db=db, current_user=_instructor(id_=10))
        assert result is None
