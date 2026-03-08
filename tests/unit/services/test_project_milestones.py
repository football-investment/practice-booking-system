"""
Sprint 30 — app/api/api_v1/endpoints/projects/milestones.py
=============================================================
Target: ≥80% statement, ≥70% branch

Covers submit_milestone:
  * non-student → 403
  * no active enrollment → 404
  * milestone progress not found → 404
  * milestone not IN_PROGRESS → 400
  * insufficient sessions completed → 400
  * success → status SUBMITTED, committed

Covers approve_milestone:
  * non-instructor → 403
  * project not found → 404
  * no submitted milestones → 404
  * milestone found → awards XP via GamificationService
  * milestone not found → skips XP award
  * multiple milestone_progresses approved → count returned
  * _activate_next_milestone called

Covers reject_milestone:
  * non-instructor → 403
  * project not found → 404
  * no submitted milestones → 404
  * success → status IN_PROGRESS, feedback set

Covers _activate_next_milestone:
  * current_milestone not found → early return
  * next_milestone found + PENDING → activated
  * next_milestone found + not PENDING → not changed
  * no next_milestone → _check_project_completion called

Covers _check_project_completion:
  * enrollment not found → early return
  * total_milestones != approved → no completion
  * total_milestones == approved → enrollment COMPLETED, XP awarded
"""

import pytest
from unittest.mock import MagicMock, patch, call

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.milestones import (
    submit_milestone,
    approve_milestone,
    reject_milestone,
    _activate_next_milestone,
    _check_project_completion,
)
from app.models.project import (
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus,
)

_BASE = "app.api.api_v1.endpoints.projects.milestones"


# ── helpers ──────────────────────────────────────────────────────────────────

def _student():
    u = MagicMock()
    u.id = 42
    u.role.value = "student"
    return u


def _instructor():
    u = MagicMock()
    u.id = 99
    u.role.value = "instructor"
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
    q.join.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
    return q


def _seq_db(*vals):
    """n-th db.query() returns vals[n] as first() or all()."""
    call_n = [0]

    def qside(*args):
        q = _q()
        n = call_n[0]
        call_n[0] += 1
        if n < len(vals):
            v = vals[n]
            if isinstance(v, list):
                q.all.return_value = v
            else:
                q.first.return_value = v
        return q

    db = MagicMock()
    db.query.side_effect = qside
    return db


def _enrollment(eid=100, status=None):
    e = MagicMock()
    e.id = eid
    e.project_id = 10
    e.user_id = 42
    e.status = status or ProjectEnrollmentStatus.ACTIVE.value
    return e


def _mp(status=None, sessions_completed=5, enrollment_id=100):
    mp = MagicMock()
    mp.enrollment_id = enrollment_id
    mp.status = status or MilestoneStatus.IN_PROGRESS.value
    mp.sessions_completed = sessions_completed
    mp.enrollment = MagicMock()
    mp.enrollment.user_id = 42
    return mp


def _milestone(required_sessions=3, xp_reward=100, order_index=1, project_id=10):
    m = MagicMock()
    m.id = 200
    m.project_id = project_id
    m.required_sessions = required_sessions
    m.xp_reward = xp_reward
    m.order_index = order_index
    return m


# ============================================================================
# submit_milestone
# ============================================================================

class TestSubmitMilestone:

    def _call(self, project_id=10, milestone_id=200, user=None, db=None):
        return submit_milestone(
            project_id=project_id,
            milestone_id=milestone_id,
            db=db or _seq_db(),
            current_user=user or _student(),
        )

    def test_non_student_403(self):
        """SUB-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(user=_admin(), db=MagicMock())
        assert exc.value.status_code == 403

    def test_no_active_enrollment_404(self):
        """SUB-02: no active enrollment → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "active enrollment" in exc.value.detail.lower()

    def test_milestone_progress_not_found_404(self):
        """SUB-03: enrollment found but no milestone progress → 404."""
        enrollment = _enrollment()
        db = _seq_db(enrollment, None)  # enrollment ok, progress missing
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "milestone progress" in exc.value.detail.lower()

    def test_milestone_not_in_progress_400(self):
        """SUB-04: milestone status != IN_PROGRESS → 400."""
        enrollment = _enrollment()
        mp = _mp(status=MilestoneStatus.PENDING.value)
        db = _seq_db(enrollment, mp)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert "in progress" in exc.value.detail.lower()

    def test_insufficient_sessions_400(self):
        """SUB-05: sessions_completed < required_sessions → 400."""
        enrollment = _enrollment()
        mp = _mp(status=MilestoneStatus.IN_PROGRESS.value, sessions_completed=1)
        m = _milestone(required_sessions=5)
        db = _seq_db(enrollment, mp, m)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert "sessions" in exc.value.detail.lower()

    def test_success_submits_milestone(self):
        """SUB-06: all checks pass → status=SUBMITTED, commit, refresh."""
        enrollment = _enrollment()
        mp = _mp(status=MilestoneStatus.IN_PROGRESS.value, sessions_completed=5)
        m = _milestone(required_sessions=3)
        db = _seq_db(enrollment, mp, m)
        result = self._call(db=db)
        assert mp.status == MilestoneStatus.SUBMITTED.value
        assert mp.submitted_at is not None
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mp)
        assert result["milestone_id"] == 200


# ============================================================================
# approve_milestone
# ============================================================================

class TestApproveMilestone:

    def _call(self, project_id=10, milestone_id=200, feedback="Good", user=None, db=None):
        return approve_milestone(
            project_id=project_id,
            milestone_id=milestone_id,
            feedback=feedback,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_non_instructor_403(self):
        """APR-01: non-instructor → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(user=_student(), db=MagicMock())
        assert exc.value.status_code == 403

    def test_project_not_found_404(self):
        """APR-02: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "not found" in exc.value.detail.lower()

    def test_no_submitted_milestones_404(self):
        """APR-03: no submitted milestone progress records → 404."""
        project = MagicMock()
        db = _seq_db(project, [])  # project ok, empty list
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "no submitted" in exc.value.detail.lower()

    def test_success_with_milestone_xp_awarded(self):
        """APR-04: milestone found → XP awarded, _activate_next_milestone called."""
        project = MagicMock()
        mp = _mp(status=MilestoneStatus.SUBMITTED.value)
        m = _milestone(xp_reward=100)

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.all.return_value = [mp]
            elif n == 2:
                q.first.return_value = m
            # _activate_next_milestone queries handled by default (None)
            return q

        db = MagicMock()
        db.query.side_effect = qside

        mock_gami = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_xp = 50
        mock_gami.get_or_create_user_stats.return_value = mock_stats

        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            with patch(f"{_BASE}._activate_next_milestone") as mock_activate:
                result = self._call(db=db)

        assert mp.status == MilestoneStatus.APPROVED.value
        assert mp.instructor_feedback == "Good"
        mock_gami.get_or_create_user_stats.assert_called_once_with(mp.enrollment.user_id)
        assert mock_stats.total_xp == 150  # 50 + 100
        mock_activate.assert_called_once_with(db, mp.enrollment_id, 200)
        assert result["approved_count"] == 1

    def test_success_milestone_not_found_skips_xp(self):
        """APR-05: milestone not found (n=2 returns None) → XP skipped."""
        project = MagicMock()
        mp = _mp(status=MilestoneStatus.SUBMITTED.value)

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.all.return_value = [mp]
            # n==2 returns None (milestone not found)
            return q

        db = MagicMock()
        db.query.side_effect = qside

        with patch(f"{_BASE}.GamificationService") as mock_gami_cls:
            with patch(f"{_BASE}._activate_next_milestone"):
                result = self._call(db=db)

        mock_gami_cls.assert_not_called()
        assert result["approved_count"] == 1

    def test_success_multiple_milestone_progresses(self):
        """APR-06: two submitted milestones → both approved, count=2."""
        project = MagicMock()
        mp1 = _mp(status=MilestoneStatus.SUBMITTED.value, enrollment_id=101)
        mp2 = _mp(status=MilestoneStatus.SUBMITTED.value, enrollment_id=102)
        m = _milestone(xp_reward=50)

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.all.return_value = [mp1, mp2]
            else:
                q.first.return_value = m
            return q

        db = MagicMock()
        db.query.side_effect = qside

        mock_gami = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_xp = 0
        mock_gami.get_or_create_user_stats.return_value = mock_stats

        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            with patch(f"{_BASE}._activate_next_milestone"):
                result = self._call(db=db)

        assert result["approved_count"] == 2
        assert mp1.status == MilestoneStatus.APPROVED.value
        assert mp2.status == MilestoneStatus.APPROVED.value


# ============================================================================
# reject_milestone
# ============================================================================

class TestRejectMilestone:

    def _call(self, project_id=10, milestone_id=200, feedback="Needs work", user=None, db=None):
        return reject_milestone(
            project_id=project_id,
            milestone_id=milestone_id,
            feedback=feedback,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_non_instructor_403(self):
        """REJ-01: non-instructor → 403."""
        with pytest.raises(HTTPException) as exc:
            self._call(user=_student(), db=MagicMock())
        assert exc.value.status_code == 403

    def test_project_not_found_404(self):
        """REJ-02: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_no_submitted_milestones_404(self):
        """REJ-03: empty list → 404."""
        project = MagicMock()
        db = _seq_db(project, [])
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_success_rejects_milestone(self):
        """REJ-04: 2 submitted milestones → both IN_PROGRESS, feedback set."""
        project = MagicMock()
        mp1 = _mp(status=MilestoneStatus.SUBMITTED.value)
        mp2 = _mp(status=MilestoneStatus.SUBMITTED.value)
        db = _seq_db(project, [mp1, mp2])
        result = self._call(db=db, feedback="Needs work")
        assert mp1.status == MilestoneStatus.IN_PROGRESS.value
        assert mp2.status == MilestoneStatus.IN_PROGRESS.value
        assert mp1.instructor_feedback == "Needs work"
        assert mp1.submitted_at is None
        assert mp1.instructor_approved_at is None
        assert result["rejected_count"] == 2
        assert result["feedback"] == "Needs work"
        db.commit.assert_called_once()


# ============================================================================
# _activate_next_milestone
# ============================================================================

class TestActivateNextMilestone:

    def test_current_milestone_not_found_returns(self):
        """ANM-01: current_milestone not found → early return, no further queries."""
        db = _seq_db(None)
        _activate_next_milestone(db, enrollment_id=100, current_milestone_id=999)
        assert db.query.call_count == 1  # only current_milestone query

    def test_no_next_milestone_calls_check_completion(self):
        """ANM-02: no next_milestone → _check_project_completion called."""
        current = _milestone(order_index=5)
        # n=0: current_milestone, n=1: next_milestone (None)
        db = _seq_db(current, None)
        with patch(f"{_BASE}._check_project_completion") as mock_check:
            _activate_next_milestone(db, enrollment_id=100, current_milestone_id=200)
        mock_check.assert_called_once_with(db, 100)

    def test_next_milestone_pending_activated(self):
        """ANM-03: next_milestone found, next_mp status PENDING → IN_PROGRESS."""
        current = _milestone(order_index=1, project_id=10)
        next_m = _milestone(order_index=2, project_id=10)
        next_m.id = 201
        next_mp = MagicMock()
        next_mp.status = MilestoneStatus.PENDING.value
        # n=0: current_milestone, n=1: next_milestone, n=2: next_milestone_progress
        db = _seq_db(current, next_m, next_mp)
        _activate_next_milestone(db, enrollment_id=100, current_milestone_id=200)
        assert next_mp.status == MilestoneStatus.IN_PROGRESS.value
        assert next_mp.updated_at is not None

    def test_next_milestone_not_pending_not_changed(self):
        """ANM-04: next_mp status != PENDING → not changed."""
        current = _milestone(order_index=1)
        next_m = _milestone(order_index=2)
        next_mp = MagicMock()
        next_mp.status = MilestoneStatus.IN_PROGRESS.value
        db = _seq_db(current, next_m, next_mp)
        _activate_next_milestone(db, enrollment_id=100, current_milestone_id=200)
        # status unchanged
        assert next_mp.status == MilestoneStatus.IN_PROGRESS.value

    def test_next_milestone_progress_none_no_error(self):
        """ANM-05: next_milestone found but next_milestone_progress is None → no error."""
        current = _milestone(order_index=1)
        next_m = _milestone(order_index=2)
        db = _seq_db(current, next_m, None)  # next_mp = None
        _activate_next_milestone(db, enrollment_id=100, current_milestone_id=200)
        # No exception raised


# ============================================================================
# _check_project_completion
# ============================================================================

class TestCheckProjectCompletion:

    def test_enrollment_not_found_returns(self):
        """CPC-01: enrollment not found → early return."""
        db = _seq_db(None)
        _check_project_completion(db, enrollment_id=999)
        assert db.query.call_count == 1

    def test_not_all_approved_no_completion(self):
        """CPC-02: total_milestones != approved_milestones → no status change."""
        enrollment = _enrollment()
        enrollment.project_id = 10

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = enrollment
            elif n == 1:
                q.count.return_value = 5  # total_milestones
            elif n == 2:
                q.count.return_value = 3  # approved_milestones
            return q

        db = MagicMock()
        db.query.side_effect = qside
        _check_project_completion(db, enrollment_id=100)
        # No status change
        assert enrollment.status != ProjectEnrollmentStatus.COMPLETED.value

    def test_all_approved_completes_project(self):
        """CPC-03: total == approved → enrollment COMPLETED, XP awarded."""
        enrollment = _enrollment()
        enrollment.project_id = 10
        enrollment.project = MagicMock()
        enrollment.project.xp_reward = 500

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = enrollment
            elif n == 1:
                q.count.return_value = 3  # total_milestones
            elif n == 2:
                q.count.return_value = 3  # approved_milestones (equal)
            return q

        db = MagicMock()
        db.query.side_effect = qside

        mock_gami = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_xp = 100
        mock_gami.get_or_create_user_stats.return_value = mock_stats

        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            _check_project_completion(db, enrollment_id=100)

        assert enrollment.status == ProjectEnrollmentStatus.COMPLETED.value
        assert enrollment.progress_status == ProjectProgressStatus.COMPLETED.value
        assert enrollment.completion_percentage == 100.0
        assert mock_stats.total_xp == 600  # 100 + 500

    def test_zero_milestones_no_completion(self):
        """CPC-04: 0 total milestones, 0 approved → 0 == 0, completes project."""
        enrollment = _enrollment()
        enrollment.project_id = 10
        enrollment.project = MagicMock()
        enrollment.project.xp_reward = 200

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = enrollment
            elif n == 1:
                q.count.return_value = 0  # total_milestones
            elif n == 2:
                q.count.return_value = 0  # approved_milestones
            return q

        db = MagicMock()
        db.query.side_effect = qside

        mock_gami = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_xp = 0
        mock_gami.get_or_create_user_stats.return_value = mock_stats

        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            _check_project_completion(db, enrollment_id=100)

        # 0 == 0 → completed
        assert enrollment.status == ProjectEnrollmentStatus.COMPLETED.value
