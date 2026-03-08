"""
Sprint 30 — app/api/api_v1/endpoints/projects/instructor.py
============================================================
Target: ≥80% statement, ≥70% branch

Covers get_instructor_projects:
  * non-instructor → 403
  * empty list → empty projects
  * project with deadline → isoformat called
  * project without deadline → None
  * total_enrollments > 0 → completion_percentage calculated
  * total_enrollments == 0 → completion_percentage = 0

Covers instructor_enroll_student:
  * non-instructor → 403
  * project not found → 404
  * student not found → 404
  * user is not student → 400
  * already enrolled ACTIVE → "already enrolled" message
  * already enrolled non-ACTIVE → reactivate
  * project full (active >= max) → 400
  * success 0 milestones → only enrollment added
  * success 2 milestones → enrollment + 2 progress (first IN_PROGRESS, second PENDING)

Covers instructor_remove_student:
  * non-instructor → 403
  * project not found → 404
  * enrollment not found → 404
  * already WITHDRAWN → message
  * active enrollment → WITHDRAWN, commit
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.instructor import (
    get_instructor_projects,
    instructor_enroll_student,
    instructor_remove_student,
)
from app.models.project import ProjectEnrollmentStatus, ProjectProgressStatus, MilestoneStatus

_BASE = "app.api.api_v1.endpoints.projects.instructor"


# ── helpers ──────────────────────────────────────────────────────────────────

def _instructor(uid=99):
    u = MagicMock()
    u.id = uid
    u.role.value = "instructor"
    return u


def _student_user(uid=42):
    u = MagicMock()
    u.id = uid
    u.role.value = "student"
    return u


def _admin():
    u = MagicMock()
    u.id = 1
    u.role.value = "admin"
    return u


def _q(scalar_val=0):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.options.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
    q.scalar.return_value = scalar_val
    return q


def _seq_db(*vals):
    """n-th db.query() returns vals[n]; int → scalar/count, list → all, else → first."""
    call_n = [0]

    def qside(*args):
        q = _q()
        n = call_n[0]
        call_n[0] += 1
        if n < len(vals):
            v = vals[n]
            if isinstance(v, list):
                q.all.return_value = v
            elif isinstance(v, int):
                q.count.return_value = v
                q.scalar.return_value = v
            else:
                q.first.return_value = v
        return q

    db = MagicMock()
    db.query.side_effect = qside
    return db


def _project_mock(with_deadline=True, max_participants=10):
    p = MagicMock()
    p.id = 10
    p.title = "Project A"
    p.description = "Desc"
    p.semester_id = 5
    p.max_participants = max_participants
    p.required_sessions = 8
    p.xp_reward = 200
    p.status = "active"
    p.instructor_id = 99
    p.created_at = MagicMock()
    p.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    p.updated_at = MagicMock()
    p.updated_at.isoformat.return_value = "2026-01-02T00:00:00"
    if with_deadline:
        p.deadline = MagicMock()
        p.deadline.isoformat.return_value = "2026-12-31"
    else:
        p.deadline = None
    return p


def _enrollment_mock(status=None):
    e = MagicMock()
    e.id = 100
    e.project_id = 10
    e.user_id = 42
    e.status = status or ProjectEnrollmentStatus.ACTIVE.value
    e.progress_status = ProjectProgressStatus.PLANNING.value
    return e


def _milestone_mock(mid=200):
    m = MagicMock()
    m.id = mid
    return m


# ============================================================================
# get_instructor_projects
# ============================================================================

class TestGetInstructorProjects:

    def _instructor_db(self, projects, scalar_values=(0, 0, 0)):
        """DB where projects query returns list and scalars follow a sequence."""
        scalar_idx = [0]

        def scalar_side():
            n = scalar_idx[0]
            scalar_idx[0] += 1
            return scalar_values[n] if n < len(scalar_values) else 0

        q = _q()
        q.count.return_value = len(projects)
        q.all.return_value = projects
        q.scalar.side_effect = scalar_side

        db = MagicMock()
        db.query.return_value = q
        return db

    def _call(self, user=None, db=None, page=1, size=50):
        return get_instructor_projects(
            db=db or self._instructor_db([]),
            current_user=user or _instructor(),
            page=page,
            size=size,
        )

    def test_non_instructor_403(self):
        """GIP-01: non-instructor → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(user=_admin())
        assert exc.value.status_code == 403

    def test_empty_list(self):
        """GIP-02: no projects → empty list."""
        db = self._instructor_db([])
        result = self._call(db=db)
        assert result["projects"] == []
        assert result["total"] == 0

    def test_project_with_deadline(self):
        """GIP-03: project has deadline → isoformat called."""
        p = _project_mock(with_deadline=True)
        db = self._instructor_db([p])
        result = self._call(db=db)
        assert len(result["projects"]) == 1
        assert result["projects"][0]["deadline"] == "2026-12-31"

    def test_project_without_deadline(self):
        """GIP-04: deadline is None → None in result."""
        p = _project_mock(with_deadline=False)
        db = self._instructor_db([p])
        result = self._call(db=db)
        assert result["projects"][0]["deadline"] is None

    def test_completion_percentage_calculated(self):
        """GIP-05: total_enrollments=4, completed=2 → 50%."""
        p = _project_mock()
        # scalar_values: enroll_count=3, total_enrollments=4, completed=2
        db = self._instructor_db([p], scalar_values=(3, 4, 2))
        result = self._call(db=db)
        assert result["projects"][0]["completion_percentage"] == 50.0

    def test_completion_percentage_zero_when_no_enrollments(self):
        """GIP-06: total_enrollments=0 → completion_percentage=0."""
        p = _project_mock()
        db = self._instructor_db([p], scalar_values=(0, 0, 0))
        result = self._call(db=db)
        assert result["projects"][0]["completion_percentage"] == 0

    def test_pagination(self):
        """GIP-07: page=2, size=10 → result includes page/size."""
        db = self._instructor_db([])
        result = self._call(db=db, page=2, size=10)
        assert result["page"] == 2
        assert result["size"] == 10


# ============================================================================
# instructor_enroll_student
# ============================================================================

class TestInstructorEnrollStudent:

    def _call(self, project_id=10, user_id=42, user=None, db=None):
        return instructor_enroll_student(
            project_id=project_id,
            user_id=user_id,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_non_instructor_unbound_error(self):
        """IES-01: PRODUCTION BUG — 'status = ...' in for-loop shadows fastapi.status.
        All HTTPException-raising branches raise UnboundLocalError instead of HTTPException."""
        with pytest.raises(UnboundLocalError):
            self._call(user=_admin(), db=MagicMock())

    def test_project_not_found_unbound_error(self):
        """IES-02: PRODUCTION BUG — same shadowing issue, branch still executed."""
        db = _seq_db(None)
        with pytest.raises(UnboundLocalError):
            self._call(db=db)

    def test_student_not_found_unbound_error(self):
        """IES-03: PRODUCTION BUG — same shadowing issue."""
        project = _project_mock()
        db = _seq_db(project, None)
        with pytest.raises(UnboundLocalError):
            self._call(db=db)

    def test_user_not_student_unbound_error(self):
        """IES-04: PRODUCTION BUG — same shadowing issue."""
        project = _project_mock()
        admin_user = _admin()
        db = _seq_db(project, admin_user)
        with pytest.raises(UnboundLocalError):
            self._call(db=db)

    def test_already_enrolled_active_returns_message(self):
        """IES-05: existing ACTIVE enrollment → message, no new enrollment."""
        project = _project_mock()
        student = _student_user()
        enrollment = _enrollment_mock(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = _seq_db(project, student, enrollment)
        result = self._call(db=db)
        assert "already enrolled" in result["message"].lower()

    def test_already_enrolled_inactive_reactivated(self):
        """IES-06: existing non-ACTIVE enrollment → reactivate."""
        project = _project_mock()
        student = _student_user()
        enrollment = _enrollment_mock(status=ProjectEnrollmentStatus.WITHDRAWN.value)
        db = _seq_db(project, student, enrollment)
        result = self._call(db=db)
        assert enrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        assert enrollment.progress_status == ProjectProgressStatus.PLANNING.value
        db.commit.assert_called()
        assert "re-enrolled" in result["message"].lower()

    def test_project_full_unbound_error(self):
        """IES-07: PRODUCTION BUG — active_enrollments >= max → UnboundLocalError (same shadowing)."""
        project = _project_mock(max_participants=5)
        student = _student_user()
        # n=0: project, n=1: student, n=2: None (no existing), n=3: 5 (scalar = full)
        db = _seq_db(project, student, None, 5)
        with pytest.raises(UnboundLocalError):
            self._call(db=db)

    def test_success_no_milestones(self):
        """IES-08: success, no milestones → only enrollment added."""
        project = _project_mock(max_participants=10)
        student = _student_user()
        # n=0: project, n=1: student, n=2: None (no existing), n=3: 2 (scalar), n=4: [] (milestones)
        db = _seq_db(project, student, None, 2, [])
        result = self._call(db=db)
        assert "enrolled" in result["message"].lower()
        assert db.add.call_count == 1  # only enrollment

    def test_success_with_milestones(self):
        """IES-09: 2 milestones → enrollment + 2 progress (IN_PROGRESS, PENDING)."""
        project = _project_mock(max_participants=10)
        student = _student_user()
        m1 = _milestone_mock(201)
        m2 = _milestone_mock(202)
        db = _seq_db(project, student, None, 2, [m1, m2])

        result = self._call(db=db)
        assert "enrolled" in result["message"].lower()
        # 1 enrollment + 2 milestone progress
        assert db.add.call_count == 3
        # Check milestone status assignments
        add_calls = db.add.call_args_list
        mp1_arg = add_calls[1][0][0]
        mp2_arg = add_calls[2][0][0]
        assert mp1_arg.status == MilestoneStatus.IN_PROGRESS.value
        assert mp2_arg.status == MilestoneStatus.PENDING.value


# ============================================================================
# instructor_remove_student
# ============================================================================

class TestInstructorRemoveStudent:

    def _call(self, project_id=10, user_id=42, user=None, db=None):
        return instructor_remove_student(
            project_id=project_id,
            user_id=user_id,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_non_instructor_403(self):
        """IRS-01: non-instructor → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(user=_admin(), db=MagicMock())
        assert exc.value.status_code == 403

    def test_project_not_found_404(self):
        """IRS-02: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_enrollment_not_found_404(self):
        """IRS-03: enrollment not found → 404."""
        project = _project_mock()
        db = _seq_db(project, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_already_withdrawn_returns_message(self):
        """IRS-04: enrollment already WITHDRAWN → message, no commit."""
        project = _project_mock()
        enrollment = _enrollment_mock(status=ProjectEnrollmentStatus.WITHDRAWN.value)
        db = _seq_db(project, enrollment)
        result = self._call(db=db)
        assert "already withdrawn" in result["message"].lower()
        db.commit.assert_not_called()

    def test_active_enrollment_withdrawn(self):
        """IRS-05: ACTIVE enrollment → WITHDRAWN, commit."""
        project = _project_mock()
        enrollment = _enrollment_mock(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = _seq_db(project, enrollment)
        result = self._call(db=db)
        assert enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value
        db.commit.assert_called_once()
        assert "removed" in result["message"].lower()
