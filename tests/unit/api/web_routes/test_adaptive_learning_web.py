"""
Unit tests for al_session_start UX fix (v3).

Decision matrix under test:
  T-1: No active session         → resumed=false, new session created
  T-2: Same category active      → resumed=true  (frontend must show prompt)
  T-3: Same category + force_new → resumed=false, previous_session_retired=true
  T-4: Different category active → resumed=false, previous_session_retired=true (auto-retire)
  T-5: pool_exhausted from svc   → route returns session_complete + reason (not silent complete)
"""
import asyncio
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.api.web_routes.adaptive_learning import al_session_start, al_session_next_question
from app.models.quiz import QuizCategory


_BASE = "app.api.web_routes.adaptive_learning"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _existing_session(category=QuizCategory.LESSON, elapsed_s=60, time_limit=180,
                      questions=3, correct=2):
    s = MagicMock()
    s.id = 77
    s.category = category
    s.session_start_time = datetime.now(timezone.utc) - timedelta(seconds=elapsed_s)
    s.session_time_limit_seconds = time_limit
    s.questions_presented = questions
    s.questions_correct = correct
    s.ended_at = None
    return s


def _new_session_obj(sid=100):
    s = MagicMock()
    s.id = sid
    s.session_start_time = datetime.now(timezone.utc)
    return s


def _db(question_count=15, existing=None):
    """Two-query mock: (1) question count → scalar(), (2) existing session → first()."""
    db = MagicMock()

    count_q = MagicMock()
    count_q.join.return_value = count_q
    count_q.filter.return_value = count_q
    count_q.scalar.return_value = question_count

    exist_q = MagicMock()
    exist_q.filter.return_value = exist_q
    exist_q.order_by.return_value = exist_q
    exist_q.first.return_value = existing

    db.query.side_effect = [count_q, exist_q]
    return db


def _run_start(category="LESSON", time_limit=180, language="en", force_new=False,
               db_obj=None, user_obj=None, new_sid=100):
    """Call al_session_start synchronously and return parsed JSON body."""
    new_sess = _new_session_obj(new_sid)
    with patch(f"{_BASE}.require_student_onboarding", return_value=None), \
         patch(f"{_BASE}.AdaptiveLearningService") as MockSvc:
        MockSvc.return_value.start_adaptive_session.return_value = new_sess
        resp = asyncio.run(al_session_start(
            request=MagicMock(),
            category=category,
            time_limit=time_limit,
            language=language,
            force_new=force_new,
            db=db_obj or _db(),
            user=user_obj or _user(),
        ))
    return json.loads(resp.body)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAlSessionStartUXFix:
    """v3 UX fix: force_new, category mismatch, resume prompt contract."""

    def test_fresh_user_returns_new_session_not_resumed(self):
        """T-1: no active session → resumed=false, new session created."""
        data = _run_start(db_obj=_db(existing=None))

        assert data["resumed"] is False
        assert data["session_id"] == 100
        assert data["previous_session_retired"] is False
        assert data["force_new"] is False

    def test_same_category_active_returns_resumed_true(self):
        """T-2: same category active → resumed=true, frontend shows prompt (not auto-flow)."""
        existing = _existing_session(category=QuizCategory.LESSON)
        data = _run_start(category="LESSON", db_obj=_db(existing=existing))

        assert data["resumed"] is True
        assert data["session_id"] == 77
        assert data["category"] == "LESSON"
        assert "questions_presented" in data
        assert "current_score" in data
        # No auto-flow fields expected: timer/flow is purely frontend responsibility

    def test_same_category_force_new_retires_and_creates(self):
        """T-3: same category + force_new=true → new session, previous_session_retired=true."""
        existing = _existing_session(category=QuizCategory.LESSON)
        data = _run_start(category="LESSON", force_new=True,
                          db_obj=_db(existing=existing), new_sid=200)

        assert data["resumed"] is False
        assert data["force_new"] is True
        assert data["previous_session_retired"] is True
        assert data["session_id"] == 200

    def test_different_category_auto_retires_and_creates_new(self):
        """T-4: active session in different category → auto-retire, new session, no prompt."""
        existing = _existing_session(category=QuizCategory.LESSON)
        data = _run_start(category="NUTRITION", db_obj=_db(existing=existing), new_sid=300)

        assert data["resumed"] is False
        assert data["previous_session_retired"] is True
        assert data["session_id"] == 300
        assert data["category"] == "NUTRITION"

    def test_pool_exhausted_passes_through_to_frontend(self):
        """T-5: service returns pool_exhausted → route returns it as-is (not silent complete)."""
        mock_session = MagicMock()
        mock_session.ended_at = None

        with patch(f"{_BASE}.require_student_onboarding", return_value=None), \
             patch(f"{_BASE}._session_guard", return_value=(mock_session, None)), \
             patch(f"{_BASE}.AdaptiveLearningService") as MockSvc:
            MockSvc.return_value.get_next_question.return_value = {
                "session_complete": True,
                "reason": "pool_exhausted",
            }
            resp = asyncio.run(al_session_next_question(
                session_id=77,
                request=MagicMock(),
                db=MagicMock(),
                user=_user(),
                exclude_ids="",
            ))
        data = json.loads(resp.body)

        assert data["session_complete"] is True
        assert data["reason"] == "pool_exhausted"
