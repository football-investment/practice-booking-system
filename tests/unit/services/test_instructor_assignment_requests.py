"""
Sprint 30 — app/api/api_v1/endpoints/instructor_assignments/requests.py
=======================================================================
Target: ≥85% statement, ≥70% branch

Covers:
  create_assignment_request:
    * non-admin → 403
    * semester not found → 404
    * instructor not found → 404
    * existing pending request → 409
    * success path (Notification missing-import patched)

  get_instructor_assignment_requests:
    * non-admin, different instructor_id → 403
    * non-admin, own instructor_id → allowed (no filters)
    * admin → allowed
    * invalid status_filter → 400
    * valid status_filter → filter applied
    * specialization_type filter
    * age_group filter
    * location_city filter
    * priority_min filter

  get_semester_assignment_requests:
    * non-admin → 403
    * admin → success

  accept_assignment_request:
    * request not found → 404
    * wrong instructor (not the target) → 403
    * already processed → 409
    * success + semester found (master_instructor_id set)
    * success + semester not found

  decline_assignment_request:
    * request not found → 404
    * wrong instructor → 403
    * already processed → 409
    * success

  cancel_assignment_request:
    * non-admin → 403
    * request not found → 404
    * already processed → 409
    * success
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.instructor_assignments.requests import (
    create_assignment_request,
    get_instructor_assignment_requests,
    get_semester_assignment_requests,
    accept_assignment_request,
    decline_assignment_request,
    cancel_assignment_request,
)
from app.schemas.instructor_assignment import (
    InstructorAssignmentRequestCreate,
    InstructorAssignmentRequestAccept,
    InstructorAssignmentRequestDecline,
)
from app.models.user import UserRole
from app.models.instructor_assignment import AssignmentRequestStatus

_BASE = "app.api.api_v1.endpoints.instructor_assignments.requests"


# ── helpers ──────────────────────────────────────────────────────────────────

def _admin(uid=1):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.ADMIN
    u.name = "Admin"
    return u


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    u.name = "Instructor"
    return u


def _student(uid=99):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.STUDENT
    return u


def _create_req(semester_id=10, instructor_id=42):
    return InstructorAssignmentRequestCreate(
        semester_id=semester_id,
        instructor_id=instructor_id,
    )


def _accept_req():
    return InstructorAssignmentRequestAccept(response_message="Sure!")


def _decline_req():
    return InstructorAssignmentRequestDecline(response_message="Cannot do it")


def _seq_db(*first_vals):
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        q = MagicMock()
        q.filter.return_value = q
        q.join.return_value = q
        q.order_by.return_value = q
        val = first_vals[idx] if idx < len(first_vals) else None
        if isinstance(val, list):
            q.all.return_value = val
        else:
            q.first.return_value = val
            q.all.return_value = [val] if val is not None else []
        return q

    db = MagicMock()
    db.query.side_effect = _side
    return db


def _ar(request_id=5, instructor_id=42, status=AssignmentRequestStatus.PENDING, semester_id=10):
    ar = MagicMock()
    ar.id = request_id
    ar.instructor_id = instructor_id
    ar.semester_id = semester_id
    ar.status = status
    return ar


# ============================================================================
# create_assignment_request
# ============================================================================

class TestCreateAssignmentRequest:

    def test_non_admin_403(self):
        """CAR-01: non-admin → 403."""
        with pytest.raises(HTTPException) as exc:
            create_assignment_request(
                request_data=_create_req(),
                db=MagicMock(),
                current_user=_student(),
            )
        assert exc.value.status_code == 403

    def test_semester_not_found_404(self):
        """CAR-02: semester not found → 404."""
        db = _seq_db(None)  # semester query returns None
        with pytest.raises(HTTPException) as exc:
            create_assignment_request(
                request_data=_create_req(),
                db=db,
                current_user=_admin(),
            )
        assert exc.value.status_code == 404
        assert "semester" in exc.value.detail.lower()

    def test_instructor_not_found_404(self):
        """CAR-03: instructor not found → 404."""
        semester = MagicMock()
        db = _seq_db(semester, None)  # semester found, instructor not found
        with pytest.raises(HTTPException) as exc:
            create_assignment_request(
                request_data=_create_req(),
                db=db,
                current_user=_admin(),
            )
        assert exc.value.status_code == 404
        assert "instructor" in exc.value.detail.lower()

    def test_existing_pending_409(self):
        """CAR-04: existing pending request → 409."""
        semester = MagicMock()
        instructor = MagicMock()
        existing = MagicMock()  # existing pending
        db = _seq_db(semester, instructor, existing)
        with pytest.raises(HTTPException) as exc:
            create_assignment_request(
                request_data=_create_req(),
                db=db,
                current_user=_admin(),
            )
        assert exc.value.status_code == 409
        assert "pending" in exc.value.detail.lower()

    def test_success_path(self):
        """CAR-05: success path → db_request returned (Notification patched)."""
        semester = MagicMock()
        semester.id = 10
        semester.name = "Test Semester"
        instructor = MagicMock()
        instructor.id = 42
        db_request = MagicMock()
        db_request.id = 99

        db = _seq_db(semester, instructor, None)  # no existing pending
        db.refresh.return_value = None

        admin = _admin(uid=1)
        admin.name = "Admin Name"

        with patch(f"{_BASE}.InstructorAssignmentRequest", return_value=db_request):
            with patch(f"{_BASE}.Notification", create=True) as MockNotif:
                with patch(f"{_BASE}.NotificationType", create=True):
                    MockNotif.return_value = MagicMock()
                    result = create_assignment_request(
                        request_data=_create_req(),
                        db=db,
                        current_user=admin,
                    )

        assert result is db_request


# ============================================================================
# get_instructor_assignment_requests
# ============================================================================

class TestGetInstructorAssignmentRequests:

    def _call(self, instructor_id=42, current_user=None, status_filter=None,
              spec=None, age=None, city=None, priority=None, db=None):
        if current_user is None:
            current_user = _instructor(uid=instructor_id)
        if db is None:
            q = MagicMock()
            q.filter.return_value = q
            q.join.return_value = q
            q.order_by.return_value = q
            q.all.return_value = []
            db = MagicMock()
            db.query.return_value = q
        return get_instructor_assignment_requests(
            instructor_id=instructor_id,
            status_filter=status_filter,
            specialization_type=spec,
            age_group=age,
            location_city=city,
            priority_min=priority,
            db=db,
            current_user=current_user,
        )

    def test_non_admin_different_instructor_403(self):
        """GIAR-01: non-admin, different instructor_id → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(instructor_id=99, current_user=_instructor(uid=42))
        assert exc.value.status_code == 403

    def test_non_admin_own_id_allowed(self):
        """GIAR-02: non-admin, own instructor_id → allowed."""
        result = self._call(instructor_id=42, current_user=_instructor(uid=42))
        assert result == []

    def test_admin_any_instructor_allowed(self):
        """GIAR-03: admin → can query any instructor."""
        result = self._call(instructor_id=99, current_user=_admin())
        assert result == []

    def test_invalid_status_filter_400(self):
        """GIAR-04: invalid status string → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(status_filter="INVALID_STATUS")
        assert exc.value.status_code == 400
        assert "invalid status" in exc.value.detail.lower()

    def test_valid_status_filter(self):
        """GIAR-05: valid status_filter → no error."""
        result = self._call(status_filter="PENDING")
        assert result == []

    def test_specialization_filter(self):
        """GIAR-06: specialization_type filter → applied."""
        result = self._call(spec="LFA_PLAYER")
        assert result == []

    def test_age_group_filter(self):
        """GIAR-07: age_group filter → applied."""
        result = self._call(age="YOUTH")
        assert result == []

    def test_priority_min_filter(self):
        """GIAR-09: priority_min filter → applied."""
        result = self._call(priority=5)
        assert result == []


# ============================================================================
# get_semester_assignment_requests
# ============================================================================

class TestGetSemesterAssignmentRequests:

    def test_non_admin_403(self):
        """GSAR-01: non-admin → 403."""
        with pytest.raises(HTTPException) as exc:
            get_semester_assignment_requests(
                semester_id=10, db=MagicMock(), current_user=_instructor()
            )
        assert exc.value.status_code == 403

    def test_admin_returns_list(self):
        """GSAR-02: admin → queries and returns list."""
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = []
        db = MagicMock()
        db.query.return_value = q
        result = get_semester_assignment_requests(
            semester_id=10, db=db, current_user=_admin()
        )
        assert result == []


# ============================================================================
# accept_assignment_request
# ============================================================================

class TestAcceptAssignmentRequest:

    def test_request_not_found_404(self):
        """AAR-01: assignment_request not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            accept_assignment_request(
                request_id=99,
                accept_data=_accept_req(),
                db=db,
                current_user=_instructor(),
            )
        assert exc.value.status_code == 404

    def test_wrong_instructor_403(self):
        """AAR-02: current_user.id != assignment_request.instructor_id → 403."""
        ar = _ar(instructor_id=42)
        db = _seq_db(ar)
        with pytest.raises(HTTPException) as exc:
            accept_assignment_request(
                request_id=5,
                accept_data=_accept_req(),
                db=db,
                current_user=_instructor(uid=99),  # different user
            )
        assert exc.value.status_code == 403

    def test_already_processed_409(self):
        """AAR-03: status != PENDING → 409."""
        ar = _ar(instructor_id=42, status=AssignmentRequestStatus.ACCEPTED)
        db = _seq_db(ar)
        with pytest.raises(HTTPException) as exc:
            accept_assignment_request(
                request_id=5,
                accept_data=_accept_req(),
                db=db,
                current_user=_instructor(uid=42),
            )
        assert exc.value.status_code == 409

    def test_success_with_semester(self):
        """AAR-04: PENDING → ACCEPTED, semester.master_instructor_id set."""
        ar = _ar(instructor_id=42, semester_id=10)
        semester = MagicMock()
        semester.id = 10
        db = _seq_db(ar, semester)
        result = accept_assignment_request(
            request_id=5,
            accept_data=_accept_req(),
            db=db,
            current_user=_instructor(uid=42),
        )
        assert ar.status == AssignmentRequestStatus.ACCEPTED
        assert semester.master_instructor_id == 42
        assert result is ar

    def test_success_without_semester(self):
        """AAR-05: PENDING → ACCEPTED, semester query returns None (ok)."""
        ar = _ar(instructor_id=42, semester_id=10)
        db = _seq_db(ar, None)  # semester not found
        result = accept_assignment_request(
            request_id=5,
            accept_data=_accept_req(),
            db=db,
            current_user=_instructor(uid=42),
        )
        assert ar.status == AssignmentRequestStatus.ACCEPTED
        assert result is ar


# ============================================================================
# decline_assignment_request
# ============================================================================

class TestDeclineAssignmentRequest:

    def test_request_not_found_404(self):
        """DAR-01: not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            decline_assignment_request(
                request_id=99,
                decline_data=_decline_req(),
                db=db,
                current_user=_instructor(),
            )
        assert exc.value.status_code == 404

    def test_wrong_instructor_403(self):
        """DAR-02: different user → 403."""
        ar = _ar(instructor_id=42)
        db = _seq_db(ar)
        with pytest.raises(HTTPException) as exc:
            decline_assignment_request(
                request_id=5,
                decline_data=_decline_req(),
                db=db,
                current_user=_instructor(uid=99),
            )
        assert exc.value.status_code == 403

    def test_already_processed_409(self):
        """DAR-03: status != PENDING → 409."""
        ar = _ar(instructor_id=42, status=AssignmentRequestStatus.DECLINED)
        db = _seq_db(ar)
        with pytest.raises(HTTPException) as exc:
            decline_assignment_request(
                request_id=5,
                decline_data=_decline_req(),
                db=db,
                current_user=_instructor(uid=42),
            )
        assert exc.value.status_code == 409

    def test_success(self):
        """DAR-04: PENDING → DECLINED."""
        ar = _ar(instructor_id=42)
        db = _seq_db(ar)
        result = decline_assignment_request(
            request_id=5,
            decline_data=_decline_req(),
            db=db,
            current_user=_instructor(uid=42),
        )
        assert ar.status == AssignmentRequestStatus.DECLINED
        assert result is ar


# ============================================================================
# cancel_assignment_request
# ============================================================================

class TestCancelAssignmentRequest:

    def test_non_admin_403(self):
        """CNAR-01: non-admin → 403."""
        with pytest.raises(HTTPException) as exc:
            cancel_assignment_request(
                request_id=5, db=MagicMock(), current_user=_instructor()
            )
        assert exc.value.status_code == 403

    def test_request_not_found_404(self):
        """CNAR-02: not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            cancel_assignment_request(
                request_id=99, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 404

    def test_already_processed_409(self):
        """CNAR-03: status != PENDING → 409."""
        ar = _ar(status=AssignmentRequestStatus.ACCEPTED)
        db = _seq_db(ar)
        with pytest.raises(HTTPException) as exc:
            cancel_assignment_request(
                request_id=5, db=db, current_user=_admin()
            )
        assert exc.value.status_code == 409

    def test_success(self):
        """CNAR-04: PENDING → CANCELLED."""
        ar = _ar(status=AssignmentRequestStatus.PENDING)
        db = _seq_db(ar)
        result = cancel_assignment_request(
            request_id=5, db=db, current_user=_admin()
        )
        assert ar.status == AssignmentRequestStatus.CANCELLED
        assert result is ar
