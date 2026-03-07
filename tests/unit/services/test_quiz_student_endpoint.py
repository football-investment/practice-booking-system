"""
Sprint 30 — app/api/api_v1/endpoints/quiz/student.py
=====================================================
Target: ≥80% statement, ≥70% branch

Covers:
  get_available_quizzes:
    * non-student → 403
    * student → returns list (empty for simplicity)

  get_quizzes_by_category:
    * non-student → 403
    * student → returns list (empty)

  get_quiz_for_taking (no session_id — session_id path has NameError bug line 107):
    * non-student → 403
    * quiz already completed → 400
    * quiz not found → 404
    * quiz found but inactive → 404
    * quiz active + no session_quiz → returns quiz
    * quiz active + session_quiz + session not found → 404
    * quiz active + session_quiz + session found + no booking → 403
    * quiz active + session_quiz + booking + HYBRID + not unlocked → 403
    * quiz active + session_quiz + booking + HYBRID + unlocked + no attendance → 403
    * quiz active + session_quiz + booking + HYBRID + unlocked + present → returns quiz
    * quiz active + session_quiz + booking + VIRTUAL + before start → 400
    * quiz active + session_quiz + booking + VIRTUAL + after end → 400
    * quiz active + session_quiz + booking + VIRTUAL + within time → returns quiz

  get_my_quiz_attempts:
    * success path → list (empty)

  get_my_quiz_statistics:
    * success path → statistics object

  get_quiz_dashboard_overview:
    * non-student → 403
    * student → QuizDashboardOverview returned

Note: session_id path (lines 106-143) skipped — NameError bug: `SessionTypel`
on line 107 (should be `SessionModel`) prevents testing without mocking internals.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta

from app.api.api_v1.endpoints.quiz.student import (
    get_available_quizzes,
    get_quizzes_by_category,
    get_quiz_for_taking,
    get_my_quiz_attempts,
    get_my_quiz_statistics,
    get_quiz_dashboard_overview,
)
from app.models.user import UserRole
from app.models.quiz import QuizCategory
from app.models.session import SessionType

_BASE = "app.api.api_v1.endpoints.quiz.student"


# ── helpers ──────────────────────────────────────────────────────────────────

def _student():
    u = MagicMock()
    u.id = 42
    u.role = UserRole.STUDENT
    return u


def _admin():
    u = MagicMock()
    u.id = 1
    u.role = UserRole.ADMIN
    return u


def _quiz_svc():
    svc = MagicMock()
    svc.get_available_quizzes.return_value = []
    svc.get_quizzes_by_category.return_value = []
    svc.is_quiz_completed_by_user.return_value = False
    svc.get_quiz_by_id.return_value = None
    svc.get_user_quiz_attempts.return_value = []
    svc.get_user_quiz_statistics.return_value = MagicMock(favorite_category=None)
    return svc


def _active_quiz():
    q = MagicMock()
    q.id = 5
    q.is_active = True
    return q


def _seq_db(*first_vals):
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        q = MagicMock()
        q.filter.return_value = q
        val = first_vals[idx] if idx < len(first_vals) else None
        q.first.return_value = val
        q.all.return_value = val if isinstance(val, list) else []
        q.count.return_value = 0
        return q

    db = MagicMock()
    db.query.side_effect = _side
    return db


# ============================================================================
# get_available_quizzes
# ============================================================================

class TestGetAvailableQuizzes:

    def test_non_student_403(self):
        """GAQ-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            get_available_quizzes(current_user=_admin(), quiz_service=_quiz_svc())
        assert exc.value.status_code == 403

    def test_student_returns_list(self):
        """GAQ-02: student + empty list → returns []."""
        result = get_available_quizzes(current_user=_student(), quiz_service=_quiz_svc())
        assert result == []


# ============================================================================
# get_quizzes_by_category
# ============================================================================

class TestGetQuizzesByCategory:

    def test_non_student_403(self):
        """GQC-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            get_quizzes_by_category(
                category=QuizCategory.GENERAL,
                current_user=_admin(),
                quiz_service=_quiz_svc(),
            )
        assert exc.value.status_code == 403

    def test_student_returns_list(self):
        """GQC-02: student → returns list."""
        result = get_quizzes_by_category(
            category=QuizCategory.GENERAL,
            current_user=_student(),
            quiz_service=_quiz_svc(),
        )
        assert result == []


# ============================================================================
# get_quiz_for_taking
# ============================================================================

class TestGetQuizForTaking:

    def _call(self, svc, db, quiz_id=5, session_id=None):
        return get_quiz_for_taking(
            quiz_id=quiz_id,
            session_id=session_id,
            current_user=_student(),
            quiz_service=svc,
            db=db,
        )

    def test_non_student_403(self):
        """GQT-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            get_quiz_for_taking(
                quiz_id=1, session_id=None,
                current_user=_admin(),
                quiz_service=_quiz_svc(),
                db=MagicMock(),
            )
        assert exc.value.status_code == 403

    def test_quiz_already_completed_400(self):
        """GQT-02: is_quiz_completed_by_user=True → 400."""
        svc = _quiz_svc()
        svc.is_quiz_completed_by_user.return_value = True
        db = _seq_db(None)  # SessionQuiz query returns None
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 400
        assert "completed" in exc.value.detail.lower()

    def test_quiz_not_found_404(self):
        """GQT-03: get_quiz_by_id returns None → 404."""
        svc = _quiz_svc()
        svc.is_quiz_completed_by_user.return_value = False
        svc.get_quiz_by_id.return_value = None
        db = _seq_db(None)  # no session_quiz
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 404

    def test_quiz_inactive_404(self):
        """GQT-04: quiz.is_active=False → 404."""
        svc = _quiz_svc()
        inactive_quiz = MagicMock()
        inactive_quiz.is_active = False
        svc.get_quiz_by_id.return_value = inactive_quiz
        db = _seq_db(None)  # no session_quiz
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 404

    def test_no_session_quiz_returns_quiz(self):
        """GQT-05: active quiz + no session_quiz → returns quiz directly."""
        svc = _quiz_svc()
        quiz = _active_quiz()
        svc.get_quiz_by_id.return_value = quiz
        db = _seq_db(None)  # session_quiz query returns None
        result = self._call(svc, db)
        assert result is quiz

    def test_session_quiz_found_but_session_missing_404(self):
        """GQT-06: session_quiz found + session not found → 404."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        db = _seq_db(session_quiz, None)  # session_quiz found, session not found
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 404
        assert "session" in exc.value.detail.lower()

    def test_session_found_no_booking_403(self):
        """GQT-07: session found + no booking for user → 403."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.on_site  # non-HYBRID/VIRTUAL → skip type checks
        db = _seq_db(session_quiz, session, None)  # no booking
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 403
        assert "booking" in exc.value.detail.lower()

    def test_hybrid_quiz_not_unlocked_403(self):
        """GQT-08: HYBRID session + quiz not unlocked → 403."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.hybrid
        session.quiz_unlocked = False
        booking = MagicMock()
        db = _seq_db(session_quiz, session, booking)
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 403
        assert "unlocked" in exc.value.detail.lower()

    def test_hybrid_unlocked_no_attendance_403(self):
        """GQT-09: HYBRID + unlocked + no attendance → 403."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.hybrid
        session.quiz_unlocked = True
        booking = MagicMock()
        db = _seq_db(session_quiz, session, booking, None)  # no attendance
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 403
        assert "present" in exc.value.detail.lower()

    def test_hybrid_unlocked_present_returns_quiz(self):
        """GQT-10: HYBRID + unlocked + attendance present → returns quiz."""
        svc = _quiz_svc()
        quiz = _active_quiz()
        svc.get_quiz_by_id.return_value = quiz
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.hybrid
        session.quiz_unlocked = True
        booking = MagicMock()
        attendance = MagicMock()
        db = _seq_db(session_quiz, session, booking, attendance)
        result = self._call(svc, db)
        assert result is quiz

    def test_virtual_before_start_400(self):
        """GQT-11: VIRTUAL session + current_time < date_start → 400."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        future = datetime.now() + timedelta(hours=2)
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.virtual
        session.date_start = future
        session.date_end = future + timedelta(hours=1)
        booking = MagicMock()
        db = _seq_db(session_quiz, session, booking)
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 400
        assert "not yet available" in exc.value.detail.lower()

    def test_virtual_after_end_400(self):
        """GQT-12: VIRTUAL session + current_time > date_end → 400."""
        svc = _quiz_svc()
        svc.get_quiz_by_id.return_value = _active_quiz()
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        past = datetime.now() - timedelta(hours=2)
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.virtual
        session.date_start = past - timedelta(hours=1)
        session.date_end = past
        booking = MagicMock()
        db = _seq_db(session_quiz, session, booking)
        with pytest.raises(HTTPException) as exc:
            self._call(svc, db)
        assert exc.value.status_code == 400
        assert "ended" in exc.value.detail.lower()

    def test_virtual_within_time_returns_quiz(self):
        """GQT-13: VIRTUAL session + within time window → returns quiz."""
        svc = _quiz_svc()
        quiz = _active_quiz()
        svc.get_quiz_by_id.return_value = quiz
        session_quiz = MagicMock()
        session_quiz.session_id = 99
        now = datetime.now()
        session = MagicMock()
        session.id = 99
        session.session_type = SessionType.virtual
        session.date_start = now - timedelta(hours=1)
        session.date_end = now + timedelta(hours=1)
        booking = MagicMock()
        db = _seq_db(session_quiz, session, booking)
        result = self._call(svc, db)
        assert result is quiz


# ============================================================================
# get_my_quiz_attempts
# ============================================================================

class TestGetMyQuizAttempts:

    def test_returns_empty_list(self):
        """MQA-01: no attempts → returns []."""
        svc = _quiz_svc()
        svc.get_user_quiz_attempts.return_value = []
        result = get_my_quiz_attempts(current_user=_student(), quiz_service=svc)
        assert result == []


# ============================================================================
# get_my_quiz_statistics
# ============================================================================

class TestGetMyQuizStatistics:

    def test_returns_statistics(self):
        """MQS-01: quiz_service returns stats → passed through."""
        svc = _quiz_svc()
        stats = MagicMock()
        svc.get_user_quiz_statistics.return_value = stats
        result = get_my_quiz_statistics(current_user=_student(), quiz_service=svc)
        assert result is stats
        svc.get_user_quiz_statistics.assert_called_once_with(42)


# ============================================================================
# get_quiz_dashboard_overview
# ============================================================================

class TestGetQuizDashboardOverview:

    def test_non_student_403(self):
        """QDO-01: non-student → 403."""
        with pytest.raises(HTTPException) as exc:
            get_quiz_dashboard_overview(current_user=_admin(), quiz_service=_quiz_svc())
        assert exc.value.status_code == 403

    def test_student_builds_dashboard(self):
        """QDO-02: student + empty data → QuizDashboardOverview returned."""
        svc = _quiz_svc()
        svc.get_available_quizzes.return_value = []
        svc.get_user_quiz_attempts.return_value = []
        svc.get_user_quiz_statistics.return_value = MagicMock(favorite_category=None)

        result = get_quiz_dashboard_overview(current_user=_student(), quiz_service=svc)

        assert result.available_quizzes == 0
        assert result.completed_quizzes == 0
        assert result.total_xp_from_quizzes == 0
        assert result.recent_attempts == []
