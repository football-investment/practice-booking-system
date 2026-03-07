"""
Sprint 30 — app/api/api_v1/endpoints/projects/enrollment/enroll.py
==================================================================
Target: ≥80% statement, ≥70% branch

Covers enroll_in_project:
  * non-student → 403
  * all 3 validators called with correct args
  * validator raises → propagates
  * project not found → 404
  * already enrolled ACTIVE → 409
  * existing WITHDRAWN → re-enroll, return existing enrollment
  * project full → 409
  * success, no milestones → enrollment created
  * success, 2 milestones → enrollment + 2 milestone progress records

Covers withdraw_from_project:
  * no enrollment → 404
  * already WITHDRAWN → message, no commit
  * non-ACTIVE non-WITHDRAWN status → 400
  * ACTIVE enrollment → WITHDRAWN, commit, message

Covers get_my_current_project:
  * no active enrollment → None
  * enrollment with project → dict with project_title
  * enrollment.project is None → project_title = "Unknown"
  * enrolled_at is None → enrolled_at field is None
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.enrollment.enroll import (
    enroll_in_project,
    withdraw_from_project,
    get_my_current_project,
)
from app.models.project import (
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
)

_BASE = "app.api.api_v1.endpoints.projects.enrollment.enroll"


# ── helpers ──────────────────────────────────────────────────────────────────

def _student():
    u = MagicMock()
    u.id = 42
    u.role.value = "student"
    return u


def _admin():
    u = MagicMock()
    u.id = 1
    u.role.value = "admin"
    return u


def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
    return q


def _seq_db(*first_vals):
    """n-th db.query() call returns first_vals[n] as first() or all()."""
    call_n = [0]

    def qside(*args):
        q = _q()
        n = call_n[0]
        call_n[0] += 1
        if n < len(first_vals):
            val = first_vals[n]
            if isinstance(val, list):
                q.all.return_value = val
            else:
                q.first.return_value = val
        return q

    db = MagicMock()
    db.query.side_effect = qside
    return db


def _project(full=False):
    p = MagicMock()
    p.id = 10
    p.enrolled_count = 5
    p.max_participants = 5 if full else 10
    return p


def _enrollment(status=None):
    e = MagicMock()
    e.id = 100
    e.project_id = 10
    e.user_id = 42
    e.status = status if status is not None else ProjectEnrollmentStatus.ACTIVE.value
    e.progress_status = ProjectProgressStatus.PLANNING.value
    return e


def _milestone(mid=200):
    m = MagicMock()
    m.id = mid
    return m


def _patch_validators():
    return [
        patch(f"{_BASE}.validate_semester_enrollment"),
        patch(f"{_BASE}.validate_specialization_enrollment"),
        patch(f"{_BASE}.validate_payment_enrollment"),
    ]


def _enroll(project_id=10, user=None, db=None):
    return enroll_in_project(
        project_id=project_id,
        db=db if db is not None else _seq_db(),
        current_user=user if user is not None else _student(),
    )


# ============================================================================
# enroll_in_project
# ============================================================================

class TestEnrollInProject:

    def test_non_student_403(self):
        """ENR-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            _enroll(user=_admin(), db=MagicMock())
        assert exc.value.status_code == 403

    def test_all_validators_called(self):
        """ENR-02: all 3 validators called with (project_id, user, db) or (user, db)."""
        project = _project()
        db = _seq_db(project, None)   # project found, no existing enrollment
        user = _student()
        patches = _patch_validators()
        with patches[0] as mv_sem, patches[1] as mv_spec, patches[2] as mv_pay:
            _enroll(user=user, db=db)
        mv_sem.assert_called_once_with(10, user, db)
        mv_spec.assert_called_once_with(10, user, db)
        mv_pay.assert_called_once_with(user, db)

    def test_validator_raises_propagates(self):
        """ENR-03: validator HTTPException propagates without calling subsequent validators."""
        with patch(f"{_BASE}.validate_semester_enrollment",
                   side_effect=HTTPException(status_code=403, detail="not enrolled")):
            with patch(f"{_BASE}.validate_specialization_enrollment") as mv_spec:
                with patch(f"{_BASE}.validate_payment_enrollment") as mv_pay:
                    with pytest.raises(HTTPException) as exc:
                        _enroll()
        assert exc.value.status_code == 403
        mv_spec.assert_not_called()
        mv_pay.assert_not_called()

    def test_project_not_found_404(self):
        """ENR-04: project not found → 404."""
        db = _seq_db(None)
        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            with pytest.raises(HTTPException) as exc:
                _enroll(db=db)
        assert exc.value.status_code == 404
        assert "not found" in exc.value.detail.lower()

    def test_already_enrolled_active_409(self):
        """ENR-05: existing ACTIVE enrollment → 409."""
        project = _project()
        enrollment = _enrollment(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = _seq_db(project, enrollment)
        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            with pytest.raises(HTTPException) as exc:
                _enroll(db=db)
        assert exc.value.status_code == 409
        assert "already enrolled" in exc.value.detail.lower()

    def test_reenroll_after_withdrawn(self):
        """ENR-06: existing WITHDRAWN enrollment → re-enroll, return same object."""
        project = _project()
        enrollment = _enrollment(status=ProjectEnrollmentStatus.WITHDRAWN.value)
        db = _seq_db(project, enrollment)
        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            result = _enroll(db=db)
        assert enrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        assert enrollment.progress_status == ProjectProgressStatus.PLANNING.value
        assert result is enrollment
        db.commit.assert_called()
        db.refresh.assert_called_with(enrollment)

    def test_project_full_409(self):
        """ENR-07: enrolled_count >= max_participants → 409."""
        project = _project(full=True)
        db = _seq_db(project, None)
        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            with pytest.raises(HTTPException) as exc:
                _enroll(db=db)
        assert exc.value.status_code == 409
        assert "full" in exc.value.detail.lower()

    def test_success_no_milestones(self):
        """ENR-08: success path, no milestones → only enrollment added."""
        project = _project()
        # query 0: project, query 1: no existing enrollment, query 2: milestones → []
        db = _seq_db(project, None, [])
        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            _enroll(db=db)
        # enrollment added once; no milestone progress added
        assert db.add.call_count == 1
        assert db.commit.call_count >= 1

    def test_success_with_milestones(self):
        """ENR-09: success path, 2 milestones → 3 db.add() calls."""
        project = _project()
        m1 = _milestone(201)
        m2 = _milestone(202)

        call_n = [0]

        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.first.return_value = None
            elif n == 2:
                q.all.return_value = [m1, m2]
            return q

        db = MagicMock()
        db.query.side_effect = qside

        patches = _patch_validators()
        with patches[0], patches[1], patches[2]:
            _enroll(db=db)

        # 1 enrollment + 2 milestone progress records
        assert db.add.call_count == 3


# ============================================================================
# withdraw_from_project
# ============================================================================

class TestWithdrawFromProject:

    def _call(self, project_id=10, user=None, db=None):
        return withdraw_from_project(
            project_id=project_id,
            db=db if db is not None else _seq_db(),
            current_user=user if user is not None else _student(),
        )

    def test_no_enrollment_404(self):
        """WIT-01: no enrollment → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "no enrollment" in exc.value.detail.lower()

    def test_already_withdrawn_returns_message(self):
        """WIT-02: status == WITHDRAWN → message, no commit."""
        enrollment = _enrollment(status=ProjectEnrollmentStatus.WITHDRAWN.value)
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert "already withdrawn" in result["message"].lower()
        db.commit.assert_not_called()

    def test_non_active_non_withdrawn_status_400(self):
        """WIT-03: status not ACTIVE and not WITHDRAWN → 400."""
        enrollment = _enrollment(status="completed")
        db = _seq_db(enrollment)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert "cannot withdraw" in exc.value.detail.lower()

    def test_active_enrollment_withdrawn_successfully(self):
        """WIT-04: ACTIVE enrollment → status set to WITHDRAWN, commit, message."""
        enrollment = _enrollment(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value
        db.commit.assert_called_once()
        assert "withdrawn" in result["message"].lower()


# ============================================================================
# get_my_current_project
# ============================================================================

class TestGetMyCurrentProject:

    def _call(self, user=None, db=None):
        return get_my_current_project(
            db=db if db is not None else _seq_db(),
            current_user=user if user is not None else _student(),
        )

    def test_no_enrollment_returns_none(self):
        """CUR-01: no active enrollment → None."""
        db = _seq_db(None)
        assert self._call(db=db) is None

    def test_enrollment_with_project_title(self):
        """CUR-02: enrollment with project → full dict."""
        enrollment = MagicMock()
        enrollment.id = 100
        enrollment.project_id = 10
        enrollment.project = MagicMock()
        enrollment.project.title = "AI Research"
        enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        enrollment.progress_status = "planning"
        enrollment.enrolled_at = MagicMock()
        enrollment.enrolled_at.isoformat.return_value = "2026-03-01T00:00:00"
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["id"] == 100
        assert result["project_id"] == 10
        assert result["project_title"] == "AI Research"
        assert result["status"] == ProjectEnrollmentStatus.ACTIVE.value
        assert result["progress_status"] == "planning"
        assert result["enrolled_at"] == "2026-03-01T00:00:00"

    def test_enrollment_without_project_uses_unknown(self):
        """CUR-03: enrollment.project is None → project_title = 'Unknown'."""
        enrollment = MagicMock()
        enrollment.id = 101
        enrollment.project_id = 11
        enrollment.project = None
        enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        enrollment.progress_status = "in_progress"
        enrollment.enrolled_at = MagicMock()
        enrollment.enrolled_at.isoformat.return_value = "2026-02-01T00:00:00"
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["project_title"] == "Unknown"

    def test_enrollment_without_enrolled_at(self):
        """CUR-04: enrolled_at is None → enrolled_at field is None."""
        enrollment = MagicMock()
        enrollment.id = 102
        enrollment.project_id = 12
        enrollment.project = MagicMock()
        enrollment.project.title = "Data Science"
        enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        enrollment.progress_status = "planning"
        enrollment.enrolled_at = None
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["enrolled_at"] is None
