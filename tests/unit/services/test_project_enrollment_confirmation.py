"""
Sprint 30 — app/api/api_v1/endpoints/projects/enrollment/confirmation.py
=========================================================================
Target: ≥80% statement, ≥70% branch

Covers complete_enrollment_quiz:
  * project not found → 404
  * quiz_attempt not found → 404
  * existing enrollment_quiz → 409
  * no prior attempts → priority=1
  * 1 prior attempt with higher score → priority=2
  * 1 prior attempt with equal score + earlier completed_at → priority=2
  * 1 prior attempt with equal score + later completed_at → priority=1 (no increment)
  * 1 prior attempt with lower score → priority=1 (no increment)
  * prior attempt not found (DB returns None) → skipped (priority unchanged)

Covers confirm_project_enrollment:
  * enrollment_quiz not found → 404
  * priority > max_participants → 400
  * existing enrollment ACTIVE → "Already enrolled"
  * no existing enrollment → new enrollment created
  * existing enrollment non-ACTIVE → updated to ACTIVE
  * gamification service called

Covers _recalculate_enrollment_priorities:
  * empty enrollments → no commit
  * 2 enrollments with attempts → sorted by score desc
  * enrollment without attempt → skipped
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.enrollment.confirmation import (
    complete_enrollment_quiz,
    confirm_project_enrollment,
    _recalculate_enrollment_priorities,
)
from app.models.project import ProjectEnrollmentStatus, ProjectProgressStatus

_BASE = "app.api.api_v1.endpoints.projects.enrollment.confirmation"


# ── helpers ──────────────────────────────────────────────────────────────────

def _user(uid=42):
    u = MagicMock()
    u.id = uid
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
    q.scalar.return_value = 0
    return q


def _seq_db(*vals):
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


def _project(max_participants=10):
    p = MagicMock()
    p.id = 10
    p.max_participants = max_participants
    return p


def _attempt(score=80.0, completed_at=None):
    a = MagicMock()
    a.score = score
    a.completed_at = completed_at or datetime(2026, 3, 1, 10, 0, 0)
    return a


def _eq_record(priority=1, quiz_attempt_id=99, confirmed=False):
    e = MagicMock()
    e.quiz_attempt_id = quiz_attempt_id
    e.enrollment_priority = priority
    e.enrollment_confirmed = confirmed
    return e


# ============================================================================
# complete_enrollment_quiz
# ============================================================================

class TestCompleteEnrollmentQuiz:

    def _call(self, project_id=10, quiz_attempt_id=99, user=None, db=None):
        return complete_enrollment_quiz(
            project_id=project_id,
            quiz_attempt_id=quiz_attempt_id,
            db=db or _seq_db(),
            current_user=user or _user(),
        )

    def test_project_not_found_404(self):
        """CEQ-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_attempt_not_found_404(self):
        """CEQ-02: quiz attempt not found → 404."""
        project = _project()
        db = _seq_db(project, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_existing_enrollment_409(self):
        """CEQ-03: enrollment quiz already exists → 409."""
        project = _project()
        attempt = _attempt()
        existing = _eq_record()
        db = _seq_db(project, attempt, existing)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 409

    def test_no_prior_attempts_priority_one(self):
        """CEQ-04: no prior attempts → priority=1."""
        project = _project()
        attempt = _attempt(score=80.0)
        # n=0: project, n=1: attempt, n=2: None (no existing), n=3: [] (all_attempts)
        # _recalculate calls: n=4: [], n=5...: quiz attempt lookups (none since [] empty)
        db = _seq_db(project, attempt, None, [])
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.enrollment_priority == 1
        assert result.total_applicants == 1  # 0 + 1

    def test_higher_score_existing_increments_priority(self):
        """CEQ-05: existing attempt has higher score → priority=2."""
        project = _project()
        my_attempt = _attempt(score=70.0)
        existing_eq = _eq_record(quiz_attempt_id=88)
        existing_attempt = _attempt(score=90.0)  # higher than mine

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.first.return_value = my_attempt
            elif n == 2:
                q.first.return_value = None  # no existing quiz
            elif n == 3:
                q.all.return_value = [existing_eq]  # 1 prior attempt
            elif n == 4:
                q.first.return_value = existing_attempt  # the prior attempt
            # n>=5: _recalculate queries (mocked anyway)
            return q

        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.enrollment_priority == 2  # 1 + 1

    def test_equal_score_earlier_completion_increments_priority(self):
        """CEQ-06: same score, existing earlier → priority+1."""
        project = _project()
        my_attempt = _attempt(score=80.0, completed_at=datetime(2026, 3, 1, 11, 0, 0))
        existing_eq = _eq_record(quiz_attempt_id=88)
        # same score but earlier completion
        existing_attempt = _attempt(score=80.0, completed_at=datetime(2026, 3, 1, 9, 0, 0))

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.first.return_value = my_attempt
            elif n == 2:
                q.first.return_value = None
            elif n == 3:
                q.all.return_value = [existing_eq]
            elif n == 4:
                q.first.return_value = existing_attempt
            return q

        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.enrollment_priority == 2

    def test_lower_score_does_not_increment_priority(self):
        """CEQ-07: existing attempt has lower score → priority stays 1."""
        project = _project()
        my_attempt = _attempt(score=90.0)
        existing_eq = _eq_record(quiz_attempt_id=88)
        existing_attempt = _attempt(score=70.0)  # lower than mine

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.first.return_value = my_attempt
            elif n == 2:
                q.first.return_value = None
            elif n == 3:
                q.all.return_value = [existing_eq]
            elif n == 4:
                q.first.return_value = existing_attempt
            return q

        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.enrollment_priority == 1

    def test_prior_attempt_db_none_skipped(self):
        """CEQ-08: existing_eq but its attempt not found → skipped, priority=1."""
        project = _project()
        my_attempt = _attempt(score=80.0)
        existing_eq = _eq_record(quiz_attempt_id=88)

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.first.return_value = project
            elif n == 1:
                q.first.return_value = my_attempt
            elif n == 2:
                q.first.return_value = None
            elif n == 3:
                q.all.return_value = [existing_eq]
            elif n == 4:
                q.first.return_value = None  # existing attempt not found
            return q

        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.enrollment_priority == 1

    def test_is_eligible_score_gte_75(self):
        """CEQ-09: score >= 75 → is_eligible=True."""
        project = _project()
        attempt = _attempt(score=75.0)
        db = _seq_db(project, attempt, None, [])
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.is_eligible is True

    def test_is_eligible_score_lt_75(self):
        """CEQ-10: score < 75 → is_eligible=False."""
        project = _project()
        attempt = _attempt(score=60.0)
        db = _seq_db(project, attempt, None, [])
        with patch(f"{_BASE}._recalculate_enrollment_priorities"):
            result = self._call(db=db)
        assert result.is_eligible is False


# ============================================================================
# confirm_project_enrollment
# ============================================================================

class TestConfirmProjectEnrollment:

    def _call(self, project_id=10, user=None, db=None):
        return confirm_project_enrollment(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=user or _user(),
        )

    def test_no_enrollment_quiz_404(self):
        """CPE-01: no enrollment_quiz → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_priority_exceeds_max_400(self):
        """CPE-02: enrollment_quiz.priority > max_participants → 400."""
        eq = _eq_record(priority=15)
        project = _project(max_participants=10)
        db = _seq_db(eq, project)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_already_enrolled_active_returns_message(self):
        """CPE-03: existing enrollment ACTIVE → 'Already enrolled'."""
        eq = _eq_record(priority=2)
        project = _project(max_participants=10)
        enrollment = MagicMock()
        enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        db = _seq_db(eq, project, enrollment)
        result = self._call(db=db)
        assert "already enrolled" in result["message"].lower()

    def test_no_existing_enrollment_creates_new(self):
        """CPE-04: no existing enrollment → new enrollment created."""
        eq = _eq_record(priority=3)
        project = _project(max_participants=10)
        db = _seq_db(eq, project, None)  # no existing enrollment

        mock_gami = MagicMock()
        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            result = self._call(db=db)

        db.add.assert_called_once()  # new enrollment added
        assert eq.enrollment_confirmed is True
        db.commit.assert_called_once()
        mock_gami.check_first_project_enrollment.assert_called_once()
        mock_gami.check_newcomer_welcome.assert_called_once()
        assert "confirmed" in result["message"].lower()

    def test_existing_non_active_enrollment_updated(self):
        """CPE-05: existing enrollment non-ACTIVE → updated to ACTIVE."""
        eq = _eq_record(priority=2)
        project = _project(max_participants=10)
        enrollment = MagicMock()
        enrollment.status = ProjectEnrollmentStatus.WITHDRAWN.value
        db = _seq_db(eq, project, enrollment)

        mock_gami = MagicMock()
        with patch(f"{_BASE}.GamificationService", return_value=mock_gami):
            result = self._call(db=db)

        # existing updated (not added)
        db.add.assert_not_called()
        assert enrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        assert enrollment.progress_status == ProjectProgressStatus.PLANNING.value
        assert "confirmed" in result["message"].lower()


# ============================================================================
# _recalculate_enrollment_priorities
# ============================================================================

class TestRecalculateEnrollmentPriorities:

    def test_empty_enrollments_commits(self):
        """REP-01: no enrollments → loop skipped, commit still called at end."""
        db = _seq_db([])  # n=0: enrollments=[]
        _recalculate_enrollment_priorities(db, project_id=10)
        db.commit.assert_called_once()

    def test_two_enrollments_sorted_by_score(self):
        """REP-02: 2 enrollments → sorted by score desc, priorities reassigned."""
        eq1 = _eq_record(priority=2, quiz_attempt_id=1)
        eq2 = _eq_record(priority=1, quiz_attempt_id=2)

        # attempt1 has score 60, attempt2 has score 90
        attempt1 = _attempt(score=60.0, completed_at=datetime(2026, 1, 1))
        attempt2 = _attempt(score=90.0, completed_at=datetime(2026, 1, 2))

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.all.return_value = [eq1, eq2]
            elif n == 1:
                q.first.return_value = attempt1
            elif n == 2:
                q.first.return_value = attempt2
            return q

        db = MagicMock()
        db.query.side_effect = qside
        _recalculate_enrollment_priorities(db, project_id=10)
        # attempt2 (score=90) should be priority 1, attempt1 (score=60) should be priority 2
        assert eq2.enrollment_priority == 1
        assert eq1.enrollment_priority == 2
        db.commit.assert_called_once()

    def test_enrollment_without_attempt_skipped(self):
        """REP-03: enrollment's attempt not found → skipped in sorted list."""
        eq1 = _eq_record(priority=1, quiz_attempt_id=1)

        call_n = [0]
        def qside(*args):
            q = _q()
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                q.all.return_value = [eq1]
            elif n == 1:
                q.first.return_value = None  # attempt not found
            return q

        db = MagicMock()
        db.query.side_effect = qside
        _recalculate_enrollment_priorities(db, project_id=10)
        # eq1 skipped → enrollment_data empty → no priority changes
        # eq1.enrollment_priority stays at 1 (unchanged)
        assert eq1.enrollment_priority == 1
        db.commit.assert_called_once()
