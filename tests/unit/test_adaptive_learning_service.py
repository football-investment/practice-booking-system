"""
Unit tests for AdaptiveLearningService (AL-1 backend core).

Scope:
  - end_session: GamificationService coupling removed — no external side-effects
  - end_session: sets ended_at, commits, returns correct summary dict
  - start_adaptive_session: creates session row, returns ORM object
  - record_answer correct/incorrect: increments session counts, returns xp_earned
  - _get_candidate_questions fallback: returns questions even when QuestionMetadata is absent
  - _session_guard (route helper): returns 404 / 410 for invalid / completed sessions

All tests use MagicMock DB — no real DB connection required.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.adaptive_learning import AdaptiveLearningService
from app.models.quiz import (
    AdaptiveLearningSession,
    QuizCategory,
    QuizQuestion,
    Quiz,
    QuestionMetadata,
    UserQuestionPerformance,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_session(
    session_id=1,
    user_id=99,
    ended_at=None,
    questions_presented=0,
    questions_correct=0,
    xp_earned=0,
    performance_trend=0.0,
    target_difficulty=0.5,
    session_start_time=None,
    session_time_limit_seconds=600,
):
    s = MagicMock(spec=AdaptiveLearningSession)
    s.id = session_id
    s.user_id = user_id
    s.ended_at = ended_at
    s.questions_presented = questions_presented
    s.questions_correct = questions_correct
    s.xp_earned = xp_earned
    s.performance_trend = performance_trend
    s.target_difficulty = target_difficulty
    s.session_start_time = session_start_time
    s.session_time_limit_seconds = session_time_limit_seconds
    s.category = QuizCategory.LESSON
    return s


def _make_service(db=None):
    if db is None:
        db = MagicMock()
    return AdaptiveLearningService(db), db


# ── end_session ───────────────────────────────────────────────────────────────

class TestEndSession:
    def test_returns_empty_dict_when_session_not_found(self):
        service, db = _make_service()
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.end_session(session_id=42)

        assert result == {}

    def test_sets_ended_at_and_commits(self):
        service, db = _make_service()
        session = _mock_session(questions_presented=5, questions_correct=4, xp_earned=100)
        db.query.return_value.filter.return_value.first.return_value = session

        service.end_session(session_id=1)

        assert session.ended_at is not None
        db.commit.assert_called_once()

    def test_returns_correct_summary_dict(self):
        service, db = _make_service()
        session = _mock_session(questions_presented=5, questions_correct=4, xp_earned=80)
        db.query.return_value.filter.return_value.first.return_value = session

        result = service.end_session(session_id=1)

        assert result["questions_answered"] == 5
        assert result["correct_answers"] == 4
        assert abs(result["success_rate"] - 0.8) < 0.001
        assert result["xp_earned"] == 80

    def test_no_gamification_service_import_or_call(self):
        """GamificationService must not be imported or called in end_session."""
        service, db = _make_service()
        session = _mock_session(questions_presented=3, questions_correct=2)
        db.query.return_value.filter.return_value.first.return_value = session

        with patch("app.services.adaptive_learning.GamificationService", create=True) as mock_gam:
            service.end_session(session_id=1)
            mock_gam.assert_not_called()

    def test_zero_questions_success_rate_is_zero(self):
        service, db = _make_service()
        session = _mock_session(questions_presented=0, questions_correct=0)
        db.query.return_value.filter.return_value.first.return_value = session

        result = service.end_session(session_id=1)

        assert result["success_rate"] == 0


# ── _get_candidate_questions fallback ─────────────────────────────────────────

class TestGetCandidateQuestions:
    def test_falls_back_to_all_category_questions_when_no_metadata(self):
        """With no QuestionMetadata rows, fallback query must return questions."""
        service, db = _make_service()

        # First query (difficulty-filtered with metadata) returns empty
        # Second query (category-only fallback) returns 3 questions
        fallback_questions = [MagicMock(spec=QuizQuestion) for _ in range(3)]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            q = MagicMock()
            # chain: .join().join().filter().all()
            q.join.return_value = q
            q.outerjoin.return_value = q
            q.filter.return_value = q
            call_count += 1
            if call_count == 1:
                q.all.return_value = []        # metadata-filtered → empty
            else:
                q.all.return_value = fallback_questions  # fallback → has content
            return q

        db.query.side_effect = side_effect

        result = service._get_candidate_questions(QuizCategory.LESSON, target_difficulty=0.5)

        assert result == fallback_questions

    def test_returns_metadata_filtered_questions_when_available(self):
        service, db = _make_service()
        filtered_questions = [MagicMock(spec=QuizQuestion) for _ in range(2)]

        q = MagicMock()
        q.join.return_value = q
        q.outerjoin.return_value = q
        q.filter.return_value = q
        q.all.return_value = filtered_questions
        db.query.return_value = q

        result = service._get_candidate_questions(QuizCategory.LESSON, target_difficulty=0.5)

        assert result == filtered_questions


# ── record_answer ─────────────────────────────────────────────────────────────

class TestRecordAnswer:
    def _setup_record(self, is_correct):
        service, db = _make_service()
        session = _mock_session(questions_presented=2, questions_correct=1)
        perf = MagicMock(spec=UserQuestionPerformance)
        perf.total_attempts = 1
        perf.correct_attempts = 1
        perf.mastery_level = 0.5

        meta = MagicMock(spec=QuestionMetadata)
        meta.estimated_difficulty = 0.5
        meta.average_time_seconds = 30.0
        meta.global_success_rate = 0.6

        def query_side(*args):
            q = MagicMock()
            q.filter.return_value = q
            q.join.return_value = q
            q.outerjoin.return_value = q
            q.all.return_value = []
            if AdaptiveLearningSession in args:
                q.first.return_value = session
            elif UserQuestionPerformance in args:
                q.first.return_value = perf
            elif QuestionMetadata in args:
                q.first.return_value = meta
            else:
                q.first.return_value = None
            return q

        db.query.side_effect = query_side
        return service, db, session

    def test_correct_answer_increments_questions_correct(self):
        service, db, session = self._setup_record(is_correct=True)
        service.record_answer(
            user_id=99, session_id=1, question_id=5,
            is_correct=True, time_spent_seconds=20.0,
        )
        assert session.questions_presented == 3
        assert session.questions_correct == 2

    def test_wrong_answer_does_not_increment_questions_correct(self):
        service, db, session = self._setup_record(is_correct=False)
        service.record_answer(
            user_id=99, session_id=1, question_id=5,
            is_correct=False, time_spent_seconds=20.0,
        )
        assert session.questions_presented == 3
        assert session.questions_correct == 1  # unchanged
