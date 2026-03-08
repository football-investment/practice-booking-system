"""
Sprint 30 — app/api/api_v1/endpoints/projects/quizzes.py
=========================================================
Target: ≥80% statement, ≥70% branch

Covers add_quiz_to_project:
  * project not found → 404
  * instructor (non-admin) not owner → 403
  * admin skips ownership check
  * quiz not found → 404
  * success → project_quiz created

Covers get_project_quizzes:
  * project not found → 404
  * empty list → []
  * 1 pq, no milestone_id → milestone=None in result
  * 1 pq with milestone_id → milestone fetched
  * quiz found/not found → quiz dict or None
  * quiz.category/difficulty None → None in result
  * milestone.deadline None/set → serialized correctly

Covers remove_quiz_from_project:
  * not found → 404
  * non-admin, not owner → 403
  * admin bypass → success
  * instructor owner → success

Covers get_enrollment_quiz_info:
  * project not found → 404
  * no enrollment_quiz → has_enrollment_quiz=False
  * enrollment_quiz + no user_enrollment_quiz → user_completed=False
  * user_completed + score >= min + eligible
  * user_completed + score >= min + waiting
  * user_completed + score >= min + confirmed
  * user_completed + score < min → not_eligible
  * user_completed + attempt is None → not_eligible

Covers get_project_waitlist:
  * project not found → 404
  * empty waitlist → empty result
  * entry.user is None → skipped
  * entry.quiz_attempt is None → skipped
  * enrollment_confirmed → confirmed
  * priority <= max → eligible
  * priority > max → waiting
  * nickname → display_name
  * no nickname → "Diák #N"
  * user.id == current_user.id → user_position set
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.projects.quizzes import (
    add_quiz_to_project,
    get_project_quizzes,
    remove_quiz_from_project,
    get_enrollment_quiz_info,
    get_project_waitlist,
)

_BASE = "app.api.api_v1.endpoints.projects.quizzes"


# ── helpers ──────────────────────────────────────────────────────────────────

def _user(role="instructor", uid=99):
    u = MagicMock()
    u.id = uid
    u.role.value = role
    return u


def _admin():
    return _user(role="admin", uid=1)


def _instructor(uid=99):
    return _user(role="instructor", uid=uid)


def _student():
    return _user(role="student", uid=42)


def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.first.return_value = None
    q.all.return_value = []
    q.count.return_value = 0
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
            else:
                q.first.return_value = v
        return q

    db = MagicMock()
    db.query.side_effect = qside
    return db


def _project(instructor_id=99):
    p = MagicMock()
    p.id = 10
    p.instructor_id = instructor_id
    p.title = "Test Project"
    p.max_participants = 10
    return p


def _pq(has_milestone_id=False):
    pq = MagicMock()
    pq.id = 50
    pq.project_id = 10
    pq.quiz_id = 77
    pq.milestone_id = 200 if has_milestone_id else None
    pq.quiz_type = "enrollment"
    pq.is_required = True
    pq.minimum_score = 60
    pq.order_index = 1
    pq.is_active = True
    pq.created_at = MagicMock()
    pq.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    return pq


def _quiz():
    q = MagicMock()
    q.id = 77
    q.title = "Quiz A"
    q.description = "Desc"
    q.category = MagicMock()
    q.category.value = "GENERAL"
    q.difficulty = MagicMock()
    q.difficulty.value = "EASY"
    q.time_limit_minutes = 30
    q.passing_score = 60
    q.xp_reward = 100
    return q


def _milestone_mock():
    m = MagicMock()
    m.id = 200
    m.title = "M1"
    m.description = "D1"
    m.order_index = 1
    m.required_sessions = 3
    m.xp_reward = 50
    m.deadline = None
    m.is_required = True
    m.project_id = 10
    m.created_at = MagicMock()
    m.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    return m


# ============================================================================
# add_quiz_to_project
# ============================================================================

class TestAddQuizToProject:

    def _call(self, project_id=10, quiz_data=None, user=None, db=None):
        if quiz_data is None:
            quiz_data = MagicMock()
            quiz_data.quiz_id = 77
            quiz_data.model_dump.return_value = {"project_id": 10, "quiz_id": 77, "quiz_type": "enrollment"}
        return add_quiz_to_project(
            project_id=project_id,
            quiz_data=quiz_data,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_project_not_found_404(self):
        """AQP-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_instructor_not_owner_403(self):
        """AQP-02: instructor doesn't own project → 403."""
        project = _project(instructor_id=55)  # different instructor
        db = _seq_db(project)
        with pytest.raises(HTTPException) as exc:
            self._call(user=_instructor(uid=99), db=db)
        assert exc.value.status_code == 403

    def test_admin_bypasses_ownership_check(self):
        """AQP-03: admin can add quiz even if not owner."""
        project = _project(instructor_id=55)
        quiz = _quiz()
        db = _seq_db(project, quiz)
        result = self._call(user=_admin(), db=db)
        db.add.assert_called_once()
        db.commit.assert_called()

    def test_quiz_not_found_404(self):
        """AQP-04: project ok, quiz not found → 404."""
        project = _project(instructor_id=99)
        db = _seq_db(project, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_success_instructor_owner(self):
        """AQP-05: instructor owns project, quiz found → created."""
        project = _project(instructor_id=99)
        quiz = _quiz()
        db = _seq_db(project, quiz)
        self._call(user=_instructor(uid=99), db=db)
        db.add.assert_called_once()
        db.commit.assert_called()
        db.refresh.assert_called_once()


# ============================================================================
# get_project_quizzes
# ============================================================================

class TestGetProjectQuizzes:

    def _call(self, project_id=10, db=None):
        return get_project_quizzes(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=_student(),
        )

    def test_project_not_found_404(self):
        """GPQ-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_empty_list(self):
        """GPQ-02: project found, no project_quizzes → []."""
        project = _project()
        db = _seq_db(project, [])
        result = self._call(db=db)
        assert result == []

    def test_pq_no_milestone(self):
        """GPQ-03: pq without milestone_id → milestone=None."""
        project = _project()
        pq = _pq(has_milestone_id=False)
        quiz = _quiz()
        # n=0: project, n=1: [pq], n=2: quiz
        db = _seq_db(project, [pq], quiz)
        result = self._call(db=db)
        assert len(result) == 1
        assert result[0]["milestone"] is None
        assert result[0]["quiz"]["id"] == 77

    def test_pq_with_milestone(self):
        """GPQ-04: pq with milestone_id → milestone fetched."""
        project = _project()
        pq = _pq(has_milestone_id=True)
        quiz = _quiz()
        m = _milestone_mock()
        # n=0: project, n=1: [pq], n=2: quiz, n=3: milestone
        db = _seq_db(project, [pq], quiz, m)
        result = self._call(db=db)
        assert result[0]["milestone"]["id"] == 200

    def test_quiz_not_found_returns_none(self):
        """GPQ-05: quiz not found → quiz=None in result."""
        project = _project()
        pq = _pq(has_milestone_id=False)
        db = _seq_db(project, [pq], None)  # quiz returns None
        result = self._call(db=db)
        assert result[0]["quiz"] is None

    def test_quiz_category_none(self):
        """GPQ-06: quiz.category is None → category=None in result."""
        project = _project()
        pq = _pq()
        quiz = _quiz()
        quiz.category = None
        quiz.difficulty = None
        db = _seq_db(project, [pq], quiz)
        result = self._call(db=db)
        assert result[0]["quiz"]["category"] is None
        assert result[0]["quiz"]["difficulty"] is None

    def test_milestone_with_deadline(self):
        """GPQ-07: milestone.deadline set → isoformat called."""
        project = _project()
        pq = _pq(has_milestone_id=True)
        quiz = _quiz()
        m = _milestone_mock()
        m.deadline = MagicMock()
        m.deadline.isoformat.return_value = "2026-06-01"
        db = _seq_db(project, [pq], quiz, m)
        result = self._call(db=db)
        assert result[0]["milestone"]["deadline"] == "2026-06-01"


# ============================================================================
# remove_quiz_from_project
# ============================================================================

class TestRemoveQuizFromProject:

    def _call(self, project_id=10, quiz_connection_id=50, user=None, db=None):
        return remove_quiz_from_project(
            project_id=project_id,
            quiz_connection_id=quiz_connection_id,
            db=db or _seq_db(),
            current_user=user or _instructor(),
        )

    def test_not_found_404(self):
        """RQP-01: quiz connection not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_instructor_not_owner_403(self):
        """RQP-02: instructor not owner → 403."""
        pq = MagicMock()
        project = _project(instructor_id=55)
        db = _seq_db(pq, project)
        with pytest.raises(HTTPException) as exc:
            self._call(user=_instructor(uid=99), db=db)
        assert exc.value.status_code == 403

    def test_admin_success(self):
        """RQP-03: admin can remove quiz from any project."""
        pq = MagicMock()
        project = _project(instructor_id=55)
        db = _seq_db(pq, project)
        result = self._call(user=_admin(), db=db)
        db.delete.assert_called_once_with(pq)
        assert "removed" in result["message"].lower()

    def test_instructor_owner_success(self):
        """RQP-04: instructor owns project → success."""
        pq = MagicMock()
        project = _project(instructor_id=99)
        db = _seq_db(pq, project)
        result = self._call(user=_instructor(uid=99), db=db)
        db.delete.assert_called_once_with(pq)
        assert "removed" in result["message"].lower()


# ============================================================================
# get_enrollment_quiz_info
# ============================================================================

class TestGetEnrollmentQuizInfo:

    def _call(self, project_id=10, user=None, db=None):
        return get_enrollment_quiz_info(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=user or _student(),
        )

    def test_project_not_found_404(self):
        """EQI-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_no_enrollment_quiz(self):
        """EQI-02: no active enrollment quiz → has_enrollment_quiz=False."""
        project = _project()
        db = _seq_db(project, None)
        result = self._call(db=db)
        assert result["has_enrollment_quiz"] is False
        assert result["user_completed"] is False

    def test_enrollment_quiz_no_user_record(self):
        """EQI-03: enrollment_quiz found, no user_enrollment_quiz → not completed."""
        project = _project()
        eq = _pq()
        quiz = _quiz()
        # n=0: project, n=1: enrollment_quiz, n=2: quiz, n=3: user_enrollment_quiz=None
        db = _seq_db(project, eq, quiz, None)
        result = self._call(db=db)
        assert result["has_enrollment_quiz"] is True
        assert result["user_completed"] is False
        assert result["user_status"] is None

    def test_user_completed_eligible(self):
        """EQI-04: score >= min, priority <= max → eligible."""
        project = _project()
        project.max_participants = 10
        eq = _pq()
        eq.minimum_score = 60
        quiz = _quiz()
        ueq = MagicMock()
        ueq.quiz_attempt_id = 5
        ueq.enrollment_priority = 3
        ueq.enrollment_confirmed = False
        attempt = MagicMock()
        attempt.score = 80
        # n=0: project, n=1: eq, n=2: quiz, n=3: ueq, n=4: attempt
        db = _seq_db(project, eq, quiz, ueq, attempt)
        result = self._call(db=db)
        assert result["user_completed"] is True
        assert result["user_status"] == "eligible"

    def test_user_completed_waiting(self):
        """EQI-05: score >= min, priority > max → waiting."""
        project = _project()
        project.max_participants = 5
        eq = _pq()
        eq.minimum_score = 60
        quiz = _quiz()
        ueq = MagicMock()
        ueq.quiz_attempt_id = 5
        ueq.enrollment_priority = 8
        ueq.enrollment_confirmed = False
        attempt = MagicMock()
        attempt.score = 75
        db = _seq_db(project, eq, quiz, ueq, attempt)
        result = self._call(db=db)
        assert result["user_status"] == "waiting"

    def test_user_completed_confirmed(self):
        """EQI-06: score >= min + enrollment_confirmed → confirmed."""
        project = _project()
        project.max_participants = 10
        eq = _pq()
        eq.minimum_score = 60
        quiz = _quiz()
        ueq = MagicMock()
        ueq.quiz_attempt_id = 5
        ueq.enrollment_priority = 2
        ueq.enrollment_confirmed = True
        attempt = MagicMock()
        attempt.score = 90
        db = _seq_db(project, eq, quiz, ueq, attempt)
        result = self._call(db=db)
        assert result["user_status"] == "confirmed"

    def test_user_completed_not_eligible(self):
        """EQI-07: score < minimum_score → not_eligible."""
        project = _project()
        project.max_participants = 10
        eq = _pq()
        eq.minimum_score = 60
        quiz = _quiz()
        ueq = MagicMock()
        ueq.quiz_attempt_id = 5
        ueq.enrollment_priority = 1
        attempt = MagicMock()
        attempt.score = 40  # below minimum
        db = _seq_db(project, eq, quiz, ueq, attempt)
        result = self._call(db=db)
        assert result["user_status"] == "not_eligible"

    def test_user_completed_attempt_none(self):
        """EQI-08: user_enrollment_quiz exists but attempt is None → not_eligible."""
        project = _project()
        project.max_participants = 10
        eq = _pq()
        eq.minimum_score = 60
        quiz = _quiz()
        ueq = MagicMock()
        ueq.quiz_attempt_id = 5
        ueq.enrollment_priority = 1
        db = _seq_db(project, eq, quiz, ueq, None)  # attempt=None
        result = self._call(db=db)
        assert result["user_status"] == "not_eligible"


# ============================================================================
# get_project_waitlist
# ============================================================================

class TestGetProjectWaitlist:

    def _call(self, project_id=10, user=None, db=None):
        return get_project_waitlist(
            project_id=project_id,
            db=db or _seq_db(),
            current_user=user or _student(),
        )

    def test_project_not_found_404(self):
        """GPW-01: project not found → 404."""
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_empty_waitlist(self):
        """GPW-02: empty waitlist → empty result."""
        project = _project()
        db = _seq_db(project, [])
        result = self._call(db=db)
        assert result["waitlist"] == []
        assert result["total_applicants"] == 0
        assert result["user_position"] is None

    def _entry(self, user_id=42, priority=1, confirmed=False, score=80.0, nickname="PlayerX"):
        entry = MagicMock()
        entry.enrollment_priority = priority
        entry.enrollment_confirmed = confirmed
        entry.user = MagicMock()
        entry.user.id = user_id
        entry.user.nickname = nickname
        entry.quiz_attempt = MagicMock()
        entry.quiz_attempt.score = score
        return entry

    def test_entry_user_none_skipped(self):
        """GPW-03: entry.user is None → skipped."""
        project = _project()
        entry = MagicMock()
        entry.user = None
        entry.quiz_attempt = MagicMock()
        db = _seq_db(project, [entry])
        result = self._call(db=db)
        assert result["total_applicants"] == 0

    def test_entry_attempt_none_skipped(self):
        """GPW-04: entry.quiz_attempt is None → skipped."""
        project = _project()
        entry = MagicMock()
        entry.user = MagicMock()
        entry.user.id = 99
        entry.quiz_attempt = None
        db = _seq_db(project, [entry])
        result = self._call(db=db)
        assert result["total_applicants"] == 0

    def test_entry_confirmed_status(self):
        """GPW-05: enrollment_confirmed → status=confirmed."""
        project = _project()
        e = self._entry(confirmed=True)
        db = _seq_db(project, [e])
        result = self._call(db=db)
        assert result["waitlist"][0]["status"] == "confirmed"

    def test_entry_eligible_status(self):
        """GPW-06: priority <= max_participants, not confirmed → eligible."""
        project = _project()
        project.max_participants = 10
        e = self._entry(priority=3, confirmed=False)
        db = _seq_db(project, [e])
        result = self._call(db=db)
        assert result["waitlist"][0]["status"] == "eligible"

    def test_entry_waiting_status(self):
        """GPW-07: priority > max_participants → waiting."""
        project = _project()
        project.max_participants = 5
        e = self._entry(priority=8, confirmed=False)
        db = _seq_db(project, [e])
        result = self._call(db=db)
        assert result["waitlist"][0]["status"] == "waiting"

    def test_nickname_used_as_display_name(self):
        """GPW-08: user.nickname set → display_name = nickname."""
        project = _project()
        e = self._entry(nickname="StarPlayer")
        db = _seq_db(project, [e])
        result = self._call(db=db)
        assert result["waitlist"][0]["display_name"] == "StarPlayer"

    def test_no_nickname_fallback(self):
        """GPW-09: user.nickname is None → display_name = 'Diák #N'."""
        project = _project()
        e = self._entry(priority=3, nickname=None)
        db = _seq_db(project, [e])
        result = self._call(db=db)
        assert result["waitlist"][0]["display_name"] == "Diák #3"

    def test_current_user_position_tracked(self):
        """GPW-10: current_user.id matches entry.user.id → user_position set."""
        project = _project()
        user = _student()
        user.id = 42
        e = self._entry(user_id=42, priority=2)
        db = _seq_db(project, [e])
        result = self._call(user=user, db=db)
        assert result["user_position"] == 2

    def test_other_user_position_not_tracked(self):
        """GPW-11: different user → user_position=None."""
        project = _project()
        user = _student()
        user.id = 42
        e = self._entry(user_id=99, priority=1)
        db = _seq_db(project, [e])
        result = self._call(user=user, db=db)
        assert result["user_position"] is None
