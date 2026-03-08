"""
Sprint 30 — app/api/api_v1/endpoints/projects/enrollment/status.py
===================================================================
Target: ≥80% statement, ≥70% branch

Covers get_project_enrollment_status:
  Enrollment found:
    * status ACTIVE → confirmed
    * status NOT_ELIGIBLE → not_eligible
    * status COMPLETED → completed
    * status WITHDRAWN → withdrawn
  No enrollment:
    * no project_quiz → no_quiz_required
    * project_quiz + no quiz_attempt → quiz_required
    * project_quiz + quiz_attempt + no user_enrollment_quiz + passed → eligible
    * project_quiz + quiz_attempt + no user_enrollment_quiz + not passed → not_eligible
    * project_quiz + quiz_attempt + enrollment_quiz + passed + confirmed → confirmed
    * project_quiz + quiz_attempt + enrollment_quiz + passed + can_confirm → eligible
    * project_quiz + quiz_attempt + enrollment_quiz + passed + waiting → waiting

Covers get_project_progress:
  * no active enrollment → 404
  * enrollment + 0 milestones + no next_milestone → progress=0, sessions_remaining
  * enrollment + milestones + one APPROVED → overall_progress calculated
  * next_milestone found with deadline
  * next_milestone found without deadline → deadline=None

Covers get_my_project_summary:
  * no active enrollments → current_project=None
  * active enrollment → current_project populated
  * available projects with deadline/without deadline
  * completed enrollments with instructor_approved → XP counted
  * completed enrollments without instructor_approved → XP excluded
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.enrollment.status import (
    get_project_enrollment_status,
    get_project_progress,
    get_my_project_summary,
)
from app.models.project import (
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus,
)

_BASE = "app.api.api_v1.endpoints.projects.enrollment.status"


# ── helpers ──────────────────────────────────────────────────────────────────

def _student():
    u = MagicMock()
    u.id = 42
    return u


def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.join.return_value = q
    q.subquery.return_value = MagicMock()
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
    return q


def _seq_db(*vals):
    """n-th db.query() returns vals[n] as first/all/count."""
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
            else:
                q.first.return_value = v
        return q

    db = MagicMock()
    db.query.side_effect = qside
    return db


def _enrollment(status=None, eid=100):
    e = MagicMock()
    e.id = eid
    e.project_id = 10
    e.user_id = 42
    e.status = status or ProjectEnrollmentStatus.ACTIVE.value
    e.progress_status = ProjectProgressStatus.PLANNING.value
    e.completion_percentage = 0.0
    e.instructor_approved = True
    e.enrolled_at = MagicMock()
    e.enrolled_at.isoformat.return_value = "2026-03-01T00:00:00"
    e.project = MagicMock()
    e.project.title = "Test Project"
    e.project.xp_reward = 300
    e.project.required_sessions = 10
    e.project.milestones = []
    e.milestone_progress = []
    return e


# ============================================================================
# get_project_enrollment_status — enrollment found
# ============================================================================

class TestEnrollmentStatusFound:

    def _call(self, project_id=10, user=None, db=None):
        return get_project_enrollment_status(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=user or _student(),
        )

    def test_active_returns_confirmed(self):
        """GES-01: enrollment.status == ACTIVE → user_status=confirmed."""
        e = _enrollment(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = _seq_db(e)
        result = self._call(db=db)
        assert result["user_status"] == "confirmed"
        assert result["enrollment_id"] == 100

    def test_not_eligible_returns_not_eligible(self):
        """GES-02: enrollment.status == NOT_ELIGIBLE → user_status=not_eligible."""
        e = _enrollment(status=ProjectEnrollmentStatus.NOT_ELIGIBLE.value)
        db = _seq_db(e)
        result = self._call(db=db)
        assert result["user_status"] == "not_eligible"

    def test_completed_returns_completed(self):
        """GES-03: enrollment.status == COMPLETED → user_status=completed."""
        e = _enrollment(status=ProjectEnrollmentStatus.COMPLETED.value)
        db = _seq_db(e)
        result = self._call(db=db)
        assert result["user_status"] == "completed"

    def test_withdrawn_returns_withdrawn(self):
        """GES-04: enrollment.status == WITHDRAWN → user_status=withdrawn."""
        e = _enrollment(status=ProjectEnrollmentStatus.WITHDRAWN.value)
        db = _seq_db(e)
        result = self._call(db=db)
        assert result["user_status"] == "withdrawn"


# ============================================================================
# get_project_enrollment_status — no enrollment
# ============================================================================

class TestEnrollmentStatusNoEnrollment:

    def _call(self, project_id=10, db=None):
        return get_project_enrollment_status(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=_student(),
        )

    def test_no_quiz_required(self):
        """GES-05: no enrollment, no project_quiz → no_quiz_required."""
        db = _seq_db(None, None)  # no enrollment, no quiz
        result = self._call(db=db)
        assert result["user_status"] == "no_quiz_required"

    def test_quiz_required_no_attempt(self):
        """GES-06: no enrollment, quiz found, no attempt → quiz_required."""
        pq = MagicMock()
        pq.quiz_id = 77
        db = _seq_db(None, pq, None)  # no enrollment, quiz, no attempt
        result = self._call(db=db)
        assert result["user_status"] == "quiz_required"
        assert result["quiz_id"] == 77

    def test_no_enrollment_quiz_passed(self):
        """GES-07: attempt passed, no enrollment_quiz → eligible."""
        pq = MagicMock()
        pq.quiz_id = 77
        attempt = MagicMock()
        attempt.passed = True
        attempt.score = 85
        db = _seq_db(None, pq, attempt, None)  # no user_enrollment_quiz
        result = self._call(db=db)
        assert result["user_status"] == "eligible"
        assert result["quiz_score"] == 85

    def test_no_enrollment_quiz_not_passed(self):
        """GES-08: attempt not passed, no enrollment_quiz → not_eligible."""
        pq = MagicMock()
        pq.quiz_id = 77
        attempt = MagicMock()
        attempt.passed = False
        attempt.score = 40
        db = _seq_db(None, pq, attempt, None)
        result = self._call(db=db)
        assert result["user_status"] == "not_eligible"
        assert result["quiz_score"] == 40

    def test_enrollment_quiz_passed_confirmed(self):
        """GES-09: enrollment_quiz + passed + confirmed → confirmed."""
        pq = MagicMock()
        pq.quiz_id = 77
        attempt = MagicMock()
        attempt.passed = True
        attempt.score = 90
        ueq = MagicMock()
        ueq.enrollment_priority = 1
        ueq.enrollment_confirmed = True
        project = MagicMock()
        project.max_participants = 10
        # n=0:no enrollment, n=1:pq, n=2:attempt, n=3:ueq, n=4:count(10), n=5:project
        db = _seq_db(None, pq, attempt, ueq, 10, project)
        result = self._call(db=db)
        assert result["user_status"] == "confirmed"
        assert result["enrollment_confirmed"] is True

    def test_enrollment_quiz_passed_eligible(self):
        """GES-10: priority <= max_participants, not confirmed → eligible."""
        pq = MagicMock()
        pq.quiz_id = 77
        attempt = MagicMock()
        attempt.passed = True
        attempt.score = 88
        ueq = MagicMock()
        ueq.enrollment_priority = 3
        ueq.enrollment_confirmed = False
        project = MagicMock()
        project.max_participants = 10
        db = _seq_db(None, pq, attempt, ueq, 15, project)
        result = self._call(db=db)
        assert result["user_status"] == "eligible"
        assert result["can_confirm"] is True

    def test_enrollment_quiz_passed_waiting(self):
        """GES-11: priority > max_participants → waiting."""
        pq = MagicMock()
        pq.quiz_id = 77
        attempt = MagicMock()
        attempt.passed = True
        attempt.score = 70
        ueq = MagicMock()
        ueq.enrollment_priority = 15
        ueq.enrollment_confirmed = False
        project = MagicMock()
        project.max_participants = 10
        db = _seq_db(None, pq, attempt, ueq, 20, project)
        result = self._call(db=db)
        assert result["user_status"] == "waiting"
        assert result["can_confirm"] is False


# ============================================================================
# get_project_progress
# ============================================================================

class TestGetProjectProgress:

    def _call(self, project_id=10, db=None):
        return get_project_progress(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=_student(),
        )

    def test_no_active_enrollment_404(self):
        """GPP-01: no active enrollment → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_no_milestones_progress_zero(self):
        """GPP-02: 0 milestones → overall_progress=0."""
        enrollment = _enrollment()
        enrollment.project.milestones = []
        enrollment.milestone_progress = []
        enrollment.project.required_sessions = 5
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["overall_progress"] == 0
        assert result["sessions_remaining"] == 5
        assert result["next_milestone"] is None

    def test_with_approved_milestone(self):
        """GPP-03: 2 milestones, 1 APPROVED → overall_progress=50."""
        enrollment = _enrollment()

        m1 = MagicMock()
        m1.id = 201
        m1.title = "Milestone 1"
        m1.description = "Desc 1"
        m1.required_sessions = 3
        m1.xp_reward = 50
        m1.deadline = None

        m2 = MagicMock()
        m2.id = 202
        m2.title = "Milestone 2"
        m2.description = "Desc 2"
        m2.required_sessions = 3
        m2.xp_reward = 50
        m2.deadline = None

        mp1 = MagicMock()
        mp1.id = 301
        mp1.milestone_id = 201
        mp1.status = MilestoneStatus.APPROVED.value
        mp1.sessions_completed = 3
        mp1.milestone = m1
        mp1.submitted_at = None
        mp1.instructor_feedback = None

        mp2 = MagicMock()
        mp2.id = 302
        mp2.milestone_id = 202
        mp2.status = MilestoneStatus.PENDING.value
        mp2.sessions_completed = 0
        mp2.milestone = m2
        mp2.submitted_at = None
        mp2.instructor_feedback = None

        enrollment.project.milestones = [m1, m2]
        enrollment.milestone_progress = [mp1, mp2]
        enrollment.project.required_sessions = 6
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["overall_progress"] == 50.0  # 1/2 * 100
        assert result["sessions_completed"] == 3
        assert result["sessions_remaining"] == 3

    def test_next_milestone_with_deadline(self):
        """GPP-04: PENDING milestone → becomes next_milestone, deadline serialized."""
        enrollment = _enrollment()
        m = MagicMock()
        m.id = 201
        m.title = "M1"
        m.description = "D1"
        m.required_sessions = 3
        m.xp_reward = 100
        m.deadline = MagicMock()
        m.deadline.isoformat.return_value = "2026-06-01"

        mp = MagicMock()
        mp.id = 301
        mp.milestone_id = 201
        mp.status = MilestoneStatus.PENDING.value
        mp.sessions_completed = 0
        mp.milestone = m
        mp.submitted_at = None
        mp.instructor_feedback = None

        enrollment.project.milestones = [m]
        enrollment.milestone_progress = [mp]
        enrollment.project.required_sessions = 3
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["next_milestone"]["deadline"] == "2026-06-01"
        assert result["next_milestone"]["title"] == "M1"

    def test_next_milestone_submitted_at_serialized(self):
        """GPP-05: mp.submitted_at set → isoformat called."""
        enrollment = _enrollment()
        m = MagicMock()
        m.id = 201
        m.title = "M1"
        m.description = "D1"
        m.required_sessions = 3
        m.xp_reward = 100
        m.deadline = None

        mp = MagicMock()
        mp.id = 301
        mp.milestone_id = 201
        mp.status = MilestoneStatus.IN_PROGRESS.value
        mp.sessions_completed = 1
        mp.milestone = m
        mp.submitted_at = MagicMock()
        mp.submitted_at.isoformat.return_value = "2026-05-01T00:00:00"
        mp.instructor_feedback = "Keep going"

        enrollment.project.milestones = [m]
        enrollment.milestone_progress = [mp]
        enrollment.project.required_sessions = 3
        db = _seq_db(enrollment)
        result = self._call(db=db)
        assert result["milestone_progress"][0]["submitted_at"] == "2026-05-01T00:00:00"


# ============================================================================
# get_my_project_summary
# ============================================================================

class TestGetMyProjectSummary:

    def _call(self, db=None):
        return get_my_project_summary(
            db=db or _seq_db(),
            current_user=_student(),
        )

    def _summary_db(self, active_enrollments, available_projects, completed_enrollments):
        """Build db mock with the 4-query sequence for get_my_project_summary."""
        call_n = [0]

        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.all.return_value = active_enrollments
            elif n == 1:
                # First available_projects query (discarded)
                q.all.return_value = []
            elif n == 2:
                # subquery
                q.subquery.return_value = MagicMock()
                return q
            elif n == 3:
                # second available_projects query (used)
                q.all.return_value = available_projects
            elif n == 4:
                q.all.return_value = completed_enrollments
            return q

        db = MagicMock()
        db.query.side_effect = qside
        return db

    def test_no_active_enrollments(self):
        """SUM-01: no active enrollments → current_project=None, empty enrolled_projects."""
        db = self._summary_db([], [], [])
        result = self._call(db=db)
        assert result["current_project"] is None
        assert result["enrolled_projects"] == []
        assert result["total_projects_completed"] == 0
        assert result["total_xp_from_projects"] == 0

    def test_active_enrollment_sets_current_project(self):
        """SUM-02: active enrollment → current_project populated."""
        e = _enrollment(status=ProjectEnrollmentStatus.ACTIVE.value)
        db = self._summary_db([e], [], [])
        result = self._call(db=db)
        assert result["current_project"]["project_id"] == 10
        assert result["current_project"]["project_title"] == "Test Project"

    def test_not_eligible_enrollment_no_current_project(self):
        """SUM-03: only NOT_ELIGIBLE enrollment → current_project=None."""
        e = _enrollment(status=ProjectEnrollmentStatus.NOT_ELIGIBLE.value)
        db = self._summary_db([e], [], [])
        result = self._call(db=db)
        assert result["current_project"] is None
        assert len(result["enrolled_projects"]) == 1

    def test_available_projects_serialized(self):
        """SUM-04: available projects → serialized with deadline."""
        project = MagicMock()
        project.id = 20
        project.title = "Open Project"
        project.description = "Desc"
        project.semester_id = 5
        project.instructor_id = 99
        project.max_participants = 10
        project.required_sessions = 8
        project.xp_reward = 200
        project.deadline = MagicMock()
        project.deadline.isoformat.return_value = "2026-12-31"
        project.status = "active"
        project.created_at = MagicMock()
        project.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        project.updated_at = MagicMock()
        project.updated_at.isoformat.return_value = "2026-01-02T00:00:00"
        project.enrolled_count = 3
        project.available_spots = 7
        db = self._summary_db([], [project], [])
        result = self._call(db=db)
        assert len(result["available_projects"]) == 1
        assert result["available_projects"][0]["deadline"] == "2026-12-31"

    def test_available_projects_no_deadline(self):
        """SUM-05: project.deadline is None → deadline=None in result."""
        project = MagicMock()
        project.id = 21
        project.title = "No Deadline"
        project.description = "D"
        project.semester_id = 5
        project.instructor_id = 99
        project.max_participants = 10
        project.required_sessions = 8
        project.xp_reward = 200
        project.deadline = None
        project.status = "active"
        project.created_at = MagicMock()
        project.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        project.updated_at = MagicMock()
        project.updated_at.isoformat.return_value = "2026-01-02T00:00:00"
        project.enrolled_count = 0
        project.available_spots = 10
        db = self._summary_db([], [project], [])
        result = self._call(db=db)
        assert result["available_projects"][0]["deadline"] is None

    def test_completed_enrollments_xp_counted_when_approved(self):
        """SUM-06: instructor_approved=True → XP included in total."""
        e = _enrollment(status=ProjectEnrollmentStatus.ACTIVE.value)
        c1 = MagicMock()
        c1.instructor_approved = True
        c1.project = MagicMock()
        c1.project.xp_reward = 400
        c2 = MagicMock()
        c2.instructor_approved = False
        c2.project = MagicMock()
        c2.project.xp_reward = 300
        db = self._summary_db([e], [], [c1, c2])
        result = self._call(db=db)
        assert result["total_xp_from_projects"] == 400  # only c1 counted
        assert result["total_projects_completed"] == 2
