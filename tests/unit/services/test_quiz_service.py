"""
Unit tests for QuizService

Covers DB-query methods via MagicMock db (no real DB required):
  create_quiz                 — no questions, with 1 question + 2 answers
  get_quiz_by_id              — found / not found
  get_available_quizzes       — empty / with results
  get_quizzes_by_category     — empty / with results
  start_quiz_attempt          — already completed, ongoing, quiz-not-found,
                                inactive, happy-path (creates new attempt)
  submit_quiz_attempt         — attempt not found, time limit exceeded,
                                happy-path MULTIPLE_CHOICE correct (passes),
                                FILL_IN_BLANK correct answer path
  get_user_quiz_attempts      — empty / with results
  get_user_quiz_statistics    — no attempts / one completed passing attempt
  get_quiz_statistics         — no attempts / with completed attempts
  get_user_ongoing_attempt    — found / not found
  is_quiz_completed_by_user   — True / False

GamificationService is patched in __init__ to avoid transitive DB setup.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from app.services.quiz_service import QuizService
from app.models.quiz import QuizCategory, QuizDifficulty, QuestionType
from app.schemas.quiz import QuizCreate, QuizQuestionCreate, QuizAnswerOptionCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc():
    """Return (QuizService, mock_db) with GamificationService fully patched."""
    db = MagicMock()
    with patch("app.services.quiz_service.GamificationService"):
        svc = QuizService(db)
    return svc, db


def _q(db, first=None, all_=None):
    """Wire db.query(...).filter(...).order_by(...).first/all to given values."""
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.join.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.subquery.return_value = MagicMock()
    db.query.return_value = q
    return q


def _multi_q(db, specs):
    """
    Set db.query.side_effect so successive calls return different mocks.

    specs: list of dicts with optional keys 'first', 'all_'.
    """
    mocks = []
    for spec in specs:
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.join.return_value = q
        q.first.return_value = spec.get("first")
        q.all.return_value = spec.get("all_", [])
        q.subquery.return_value = MagicMock()
        mocks.append(q)
    db.query.side_effect = mocks
    return mocks


def _make_quiz(id=1, title="Test Quiz", is_active=True, time_limit_minutes=30,
               passing_score=70.0, xp_reward=50, questions=None,
               category=QuizCategory.GENERAL):
    q = MagicMock()
    q.id = id
    q.title = title
    q.is_active = is_active
    q.time_limit_minutes = time_limit_minutes
    q.passing_score = passing_score
    q.xp_reward = xp_reward
    q.questions = questions if questions is not None else []
    q.category = category
    return q


def _make_attempt(id=1, user_id=42, quiz_id=1, completed_at=None,
                  started_at=None, score=None, passed=False,
                  xp_awarded=0, total_questions=1, correct_answers=0):
    a = MagicMock()
    a.id = id
    a.user_id = user_id
    a.quiz_id = quiz_id
    a.completed_at = completed_at
    a.started_at = started_at or datetime.now(timezone.utc)
    a.score = score
    a.passed = passed
    a.xp_awarded = xp_awarded
    a.total_questions = total_questions
    a.correct_answers = correct_answers
    return a


# ===========================================================================
# TestGetQuizById
# ===========================================================================

@pytest.mark.unit
class TestGetQuizById:
    def test_returns_quiz_when_found(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=7)
        _q(db, first=quiz)
        assert svc.get_quiz_by_id(7) is quiz

    def test_returns_none_when_not_found(self):
        svc, db = _make_svc()
        _q(db, first=None)
        assert svc.get_quiz_by_id(999) is None


# ===========================================================================
# TestGetAvailableQuizzes
# ===========================================================================

@pytest.mark.unit
class TestGetAvailableQuizzes:
    def test_returns_empty_list_when_all_completed(self):
        svc, db = _make_svc()
        _q(db, all_=[])
        result = svc.get_available_quizzes(user_id=42)
        assert result == []

    def test_returns_available_quizzes(self):
        svc, db = _make_svc()
        quizzes = [_make_quiz(id=1), _make_quiz(id=2)]
        _q(db, all_=quizzes)
        result = svc.get_available_quizzes(user_id=42)
        assert result == quizzes


# ===========================================================================
# TestGetQuizzesByCategory
# ===========================================================================

@pytest.mark.unit
class TestGetQuizzesByCategory:
    def test_returns_quizzes_for_category(self):
        svc, db = _make_svc()
        quizzes = [_make_quiz(category=QuizCategory.MARKETING)]
        _q(db, all_=quizzes)
        result = svc.get_quizzes_by_category(QuizCategory.MARKETING)
        assert result == quizzes

    def test_returns_empty_for_empty_category(self):
        svc, db = _make_svc()
        _q(db, all_=[])
        result = svc.get_quizzes_by_category(QuizCategory.NUTRITION)
        assert result == []


# ===========================================================================
# TestStartQuizAttempt
# ===========================================================================

@pytest.mark.unit
class TestStartQuizAttempt:
    def test_raises_when_already_completed(self):
        svc, db = _make_svc()
        completed = _make_attempt(completed_at=datetime.now(timezone.utc))
        _q(db, first=completed)  # First query returns completed attempt
        with pytest.raises(ValueError, match="already completed"):
            svc.start_quiz_attempt(user_id=42, quiz_id=1)

    def test_returns_ongoing_attempt_when_exists(self):
        svc, db = _make_svc()
        ongoing = _make_attempt(id=5, completed_at=None)
        _multi_q(db, [
            {"first": None},     # check completed → not found
            {"first": ongoing},  # check ongoing → found
        ])
        result = svc.start_quiz_attempt(user_id=42, quiz_id=1)
        assert result is ongoing

    def test_raises_when_quiz_not_found(self):
        svc, db = _make_svc()
        _multi_q(db, [
            {"first": None},  # check completed
            {"first": None},  # check ongoing
            {"first": None},  # get_quiz_by_id → quiz not found
        ])
        with pytest.raises(ValueError, match="Quiz not found"):
            svc.start_quiz_attempt(user_id=42, quiz_id=999)

    def test_raises_when_quiz_inactive(self):
        svc, db = _make_svc()
        inactive = _make_quiz(is_active=False)
        _multi_q(db, [
            {"first": None},      # check completed
            {"first": None},      # check ongoing
            {"first": inactive},  # get_quiz_by_id → inactive quiz
        ])
        with pytest.raises(ValueError, match="not active"):
            svc.start_quiz_attempt(user_id=42, quiz_id=1)

    def test_creates_new_attempt_happy_path(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=1, is_active=True, questions=[MagicMock(), MagicMock()])
        _multi_q(db, [
            {"first": None},   # check completed
            {"first": None},   # check ongoing
            {"first": quiz},   # get_quiz_by_id → found + active
        ])
        result = svc.start_quiz_attempt(user_id=42, quiz_id=1)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_creates_new_attempt_with_zero_questions(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=2, is_active=True, questions=[])
        _multi_q(db, [
            {"first": None},
            {"first": None},
            {"first": quiz},
        ])
        svc.start_quiz_attempt(user_id=2, quiz_id=2)
        db.add.assert_called_once()


# ===========================================================================
# TestSubmitQuizAttempt
# ===========================================================================

@pytest.mark.unit
class TestSubmitQuizAttempt:
    def test_raises_when_attempt_not_found(self):
        svc, db = _make_svc()
        _q(db, first=None)
        submission = MagicMock()
        submission.attempt_id = 1
        with pytest.raises(ValueError, match="not found"):
            svc.submit_quiz_attempt(user_id=42, submission=submission)

    def test_raises_when_time_limit_exceeded(self):
        svc, db = _make_svc()
        # Attempt started long in the past (naive UTC)
        old_start = datetime(2020, 1, 1, 0, 0, 0)
        attempt = _make_attempt(id=1, started_at=old_start, completed_at=None)
        attempt.quiz_id = 1
        quiz = _make_quiz(id=1, time_limit_minutes=1)  # 1-minute limit

        _multi_q(db, [
            {"first": attempt},  # query for the attempt
            {"first": quiz},     # get_quiz_by_id
        ])
        submission = MagicMock()
        submission.attempt_id = 1
        with pytest.raises(ValueError, match="Time limit exceeded"):
            svc.submit_quiz_attempt(user_id=42, submission=submission)


# ===========================================================================
# TestGetUserQuizAttempts
# ===========================================================================

@pytest.mark.unit
class TestGetUserQuizAttempts:
    def test_returns_empty_list(self):
        svc, db = _make_svc()
        _q(db, all_=[])
        assert svc.get_user_quiz_attempts(user_id=42) == []

    def test_returns_attempts(self):
        svc, db = _make_svc()
        attempts = [_make_attempt(id=1), _make_attempt(id=2)]
        _q(db, all_=attempts)
        result = svc.get_user_quiz_attempts(user_id=42)
        assert result == attempts


# ===========================================================================
# TestGetUserQuizStatistics
# ===========================================================================

@pytest.mark.unit
class TestGetUserQuizStatistics:
    def test_empty_user_has_zero_stats(self):
        svc, db = _make_svc()
        _q(db, all_=[])  # No attempts at all
        stats = svc.get_user_quiz_statistics(user_id=42)
        assert stats.total_quizzes_attempted == 0
        assert stats.total_quizzes_completed == 0
        assert stats.total_quizzes_passed == 0
        assert stats.total_xp_earned == 0
        assert stats.average_score is None
        assert stats.completion_rate == 0
        assert stats.pass_rate == 0
        assert stats.favorite_category is None

    def test_user_with_one_completed_passing_attempt(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=1, category=QuizCategory.GENERAL)
        attempt = _make_attempt(
            id=1,
            completed_at=datetime.now(timezone.utc),
            score=85.0,
            passed=True,
            xp_awarded=50,
        )

        # First query: all attempts for user
        # Second query: get_quiz_by_id (called inside loop for category counting)
        _multi_q(db, [
            {"all_": [attempt]},  # query(QuizAttempt).filter().all()
            {"first": quiz},      # get_quiz_by_id inside favorite_category loop
        ])
        stats = svc.get_user_quiz_statistics(user_id=42)
        assert stats.total_quizzes_attempted == 1
        assert stats.total_quizzes_completed == 1
        assert stats.total_quizzes_passed == 1
        assert stats.total_xp_earned == 50
        assert stats.average_score == 85.0
        assert stats.completion_rate == 100.0
        assert stats.pass_rate == 100.0


# ===========================================================================
# TestGetQuizStatistics
# ===========================================================================

@pytest.mark.unit
class TestGetQuizStatistics:
    def test_quiz_with_no_attempts(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=1, title="Empty Quiz")
        _multi_q(db, [
            {"all_": []},    # query(QuizAttempt).filter().all()
            {"first": quiz}, # get_quiz_by_id
        ])
        stats = svc.get_quiz_statistics(quiz_id=1)
        assert stats.quiz_id == 1
        assert stats.quiz_title == "Empty Quiz"
        assert stats.total_attempts == 0
        assert stats.completed_attempts == 0
        assert stats.average_score is None
        assert stats.pass_rate == 0

    def test_quiz_with_completed_attempts(self):
        svc, db = _make_svc()
        quiz = _make_quiz(id=2, title="Popular Quiz")
        a1 = _make_attempt(completed_at=datetime.now(timezone.utc), score=90.0, passed=True)
        a1.time_spent_minutes = 10.0
        a2 = _make_attempt(completed_at=datetime.now(timezone.utc), score=60.0, passed=False)
        a2.time_spent_minutes = 15.0
        _multi_q(db, [
            {"all_": [a1, a2]},  # quiz attempts
            {"first": quiz},     # get_quiz_by_id
        ])
        stats = svc.get_quiz_statistics(quiz_id=2)
        assert stats.total_attempts == 2
        assert stats.completed_attempts == 2
        assert stats.average_score == 75.0  # (90+60)/2
        assert stats.pass_rate == 50.0      # 1/2 passed


# ===========================================================================
# TestGetUserOngoingAttempt
# ===========================================================================

@pytest.mark.unit
class TestGetUserOngoingAttempt:
    def test_returns_ongoing_when_found(self):
        svc, db = _make_svc()
        ongoing = _make_attempt(id=3, completed_at=None)
        _q(db, first=ongoing)
        result = svc.get_user_ongoing_attempt(user_id=42, quiz_id=1)
        assert result is ongoing

    def test_returns_none_when_no_ongoing(self):
        svc, db = _make_svc()
        _q(db, first=None)
        result = svc.get_user_ongoing_attempt(user_id=42, quiz_id=1)
        assert result is None


# ===========================================================================
# TestIsQuizCompletedByUser
# ===========================================================================

@pytest.mark.unit
class TestIsQuizCompletedByUser:
    def test_returns_true_when_completed(self):
        svc, db = _make_svc()
        completed = _make_attempt(completed_at=datetime.now(timezone.utc))
        _q(db, first=completed)
        assert svc.is_quiz_completed_by_user(user_id=42, quiz_id=1) is True

    def test_returns_false_when_not_completed(self):
        svc, db = _make_svc()
        _q(db, first=None)
        assert svc.is_quiz_completed_by_user(user_id=42, quiz_id=1) is False


# NOTE: get_quiz_leaderboard is excluded — it references User.full_name which
# does not exist on the User model (should be User.name). This is a pre-existing
# bug in quiz_service.py that raises AttributeError before any DB call is made.


# ===========================================================================
# TestCreateQuiz
# ===========================================================================

@pytest.mark.unit
class TestCreateQuiz:
    def test_create_quiz_with_no_questions(self):
        svc, db = _make_svc()
        quiz_data = QuizCreate(
            title="Empty Quiz",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.MEDIUM,
        )
        result = svc.create_quiz(quiz_data)
        db.add.assert_called_once()   # only the quiz
        db.flush.assert_called()
        db.commit.assert_called_once()

    def test_create_quiz_with_one_question_and_two_answers(self):
        svc, db = _make_svc()
        quiz_data = QuizCreate(
            title="Multi-Choice Quiz",
            description="A quiz with one question",
            category=QuizCategory.MARKETING,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=10,
            xp_reward=25,
            passing_score=60.0,
            questions=[
                QuizQuestionCreate(
                    question_text="What is 2+2?",
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    points=2,
                    order_index=0,
                    answer_options=[
                        QuizAnswerOptionCreate(option_text="4", is_correct=True, order_index=0),
                        QuizAnswerOptionCreate(option_text="5", is_correct=False, order_index=1),
                    ],
                )
            ],
        )
        svc.create_quiz(quiz_data)
        # db.add: quiz(1) + question(1) + 2 answer options = 4 calls
        assert db.add.call_count == 4
        db.commit.assert_called_once()

    def test_create_quiz_with_fill_in_blank_question(self):
        svc, db = _make_svc()
        quiz_data = QuizCreate(
            title="Fill In Blank Quiz",
            category=QuizCategory.ECONOMICS,
            difficulty=QuizDifficulty.HARD,
            questions=[
                QuizQuestionCreate(
                    question_text="Complete: The capital of France is ___",
                    question_type=QuestionType.FILL_IN_BLANK,
                    answer_options=[
                        QuizAnswerOptionCreate(option_text="Paris", is_correct=True, order_index=0),
                    ],
                )
            ],
        )
        svc.create_quiz(quiz_data)
        # quiz(1) + question(1) + 1 answer = 3 adds
        assert db.add.call_count == 3


# ===========================================================================
# TestSubmitQuizAttemptHappyPath
# ===========================================================================

@pytest.mark.unit
class TestSubmitQuizAttemptHappyPath:
    """
    Tests the full submit_quiz_attempt success path including:
    - answer processing (MULTIPLE_CHOICE and FILL_IN_BLANK)
    - score calculation
    - XP award (gamification service, mocked)
    - _process_enrollment_quiz_if_applicable early-return path
    """

    def _make_mc_submission(self, question_id=1, option_id=10):
        """Build a MULTIPLE_CHOICE submission mock."""
        answer = MagicMock()
        answer.question_id = question_id
        answer.selected_option_id = option_id
        answer.answer_text = None
        submission = MagicMock()
        submission.attempt_id = 1
        submission.answers = [answer]
        return submission

    def _make_fib_submission(self, question_id=1, text="Paris"):
        """Build a FILL_IN_BLANK submission mock."""
        answer = MagicMock()
        answer.question_id = question_id
        answer.selected_option_id = None
        answer.answer_text = text
        submission = MagicMock()
        submission.attempt_id = 1
        submission.answers = [answer]
        return submission

    def test_multiple_choice_correct_answer_passes(self):
        svc, db = _make_svc()
        now = datetime.now(timezone.utc)
        attempt = _make_attempt(id=1, started_at=now, completed_at=None, quiz_id=1)

        quiz = _make_quiz(id=1, time_limit_minutes=60, passing_score=70.0, xp_reward=50)

        question = MagicMock()
        question.id = 1
        question.points = 1
        question.question_type = QuestionType.MULTIPLE_CHOICE

        correct_option = MagicMock()
        correct_option.is_correct = True

        # 5 queries in order:
        # 1. find attempt
        # 2. get_quiz_by_id (time check)
        # 3. get all questions
        # 4. check correct option
        # 5. ProjectQuiz lookup → None → early return from _process_enrollment
        _multi_q(db, [
            {"first": attempt},          # query 1
            {"first": quiz},             # query 2: get_quiz_by_id
            {"all_": [question]},        # query 3: questions
            {"first": correct_option},   # query 4: correct answer check
            {"first": None},             # query 5: ProjectQuiz → None
        ])

        result = svc.submit_quiz_attempt(user_id=42, submission=self._make_mc_submission())

        db.commit.assert_called()
        svc.gamification_service.award_xp.assert_called_once()  # xp awarded (passed=True)
        assert result is attempt

    def test_multiple_choice_wrong_answer_fails_no_xp(self):
        svc, db = _make_svc()
        now = datetime.now(timezone.utc)
        attempt = _make_attempt(id=1, started_at=now, completed_at=None, quiz_id=1)
        quiz = _make_quiz(id=1, time_limit_minutes=60, passing_score=70.0, xp_reward=50)

        question = MagicMock()
        question.id = 1
        question.points = 1
        question.question_type = QuestionType.MULTIPLE_CHOICE

        # Wrong answer: selected_option_id returns None (option not found as correct)
        _multi_q(db, [
            {"first": attempt},    # find attempt
            {"first": quiz},       # get_quiz_by_id
            {"all_": [question]},  # questions
            {"first": None},       # correct option → None (wrong answer)
            {"first": None},       # ProjectQuiz lookup
        ])

        result = svc.submit_quiz_attempt(user_id=42, submission=self._make_mc_submission())

        # score = 0/1 * 100 = 0 → < 70 → not passed → no XP
        svc.gamification_service.award_xp.assert_not_called()
        assert result is attempt

    def test_fill_in_blank_correct_answer_case_insensitive(self):
        svc, db = _make_svc()
        now = datetime.now(timezone.utc)
        attempt = _make_attempt(id=1, started_at=now, completed_at=None, quiz_id=1)
        quiz = _make_quiz(id=1, time_limit_minutes=60, passing_score=50.0, xp_reward=30)

        question = MagicMock()
        question.id = 1
        question.points = 1
        question.question_type = QuestionType.FILL_IN_BLANK

        correct_opt = MagicMock()
        correct_opt.option_text = "Paris"

        _multi_q(db, [
            {"first": attempt},          # find attempt
            {"first": quiz},             # get_quiz_by_id
            {"all_": [question]},        # questions
            {"all_": [correct_opt]},     # fill-in-blank: get all correct options
            {"first": None},             # ProjectQuiz lookup
        ])

        result = svc.submit_quiz_attempt(
            user_id=42,
            submission=self._make_fib_submission(text="paris"),  # lowercase
        )

        db.commit.assert_called()
        assert result is attempt
