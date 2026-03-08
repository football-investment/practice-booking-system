"""
Unit tests for app/api/api_v1/endpoints/quiz/admin.py

Branch coverage targets:
  create_quiz():
    - role not in [INSTRUCTOR, ADMIN] → 403
    - success path
  get_quiz_admin():
    - role check → 403
    - quiz not found → 404
    - success path
  get_all_quizzes_admin():
    - role check → 403
    - success path (returns list of QuizListItem)
  get_quiz_statistics():
    - role check → 403
    - success path
  get_quiz_leaderboard():
    - role check → 403
    - success path

All endpoints are sync — called directly (no asyncio.run).
Role check: `current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]`
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from app.api.api_v1.endpoints.quiz.admin import (
    create_quiz,
    get_quiz_admin,
    get_all_quizzes_admin,
    get_quiz_statistics,
    get_quiz_leaderboard,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.quiz.admin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock()
    u.role = UserRole.ADMIN
    return u


def _instructor():
    u = MagicMock()
    u.role = UserRole.INSTRUCTOR
    return u


def _student():
    u = MagicMock()
    u.role = UserRole.STUDENT
    return u


def _mock_svc():
    return MagicMock()


def _mock_db(quizzes=None):
    """DB mock with configurable quiz query result."""
    db = MagicMock()
    if quizzes is not None:
        db.query.return_value.order_by.return_value.all.return_value = quizzes
    return db


def _quiz_mock():
    """MagicMock quiz with typed attributes to satisfy QuizListItem fields."""
    q = MagicMock()
    q.id = 1
    q.title = "Test Quiz"
    q.description = "A quiz"
    q.category = "football"
    q.difficulty = "medium"
    q.time_limit_minutes = 15
    q.xp_reward = 100
    q.questions = [MagicMock(), MagicMock()]  # len=2
    q.is_active = True
    q.created_at = datetime(2024, 1, 1)
    return q


# ============================================================================
# create_quiz()
# ============================================================================

class TestCreateQuiz:

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            create_quiz(MagicMock(), current_user=_student(), quiz_service=_mock_svc())
        assert exc.value.status_code == 403

    def test_instructor_can_create(self):
        svc = _mock_svc()
        svc.create_quiz.return_value = MagicMock()
        result = create_quiz(MagicMock(), current_user=_instructor(), quiz_service=svc)
        svc.create_quiz.assert_called_once()
        assert result is svc.create_quiz.return_value

    def test_admin_can_create(self):
        svc = _mock_svc()
        svc.create_quiz.return_value = MagicMock()
        result = create_quiz(MagicMock(), current_user=_admin(), quiz_service=svc)
        assert result is svc.create_quiz.return_value


# ============================================================================
# get_quiz_admin()
# ============================================================================

class TestGetQuizAdmin:

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            get_quiz_admin(1, current_user=_student(), quiz_service=_mock_svc())
        assert exc.value.status_code == 403

    def test_quiz_not_found_raises_404(self):
        svc = _mock_svc()
        svc.get_quiz_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            get_quiz_admin(99, current_user=_admin(), quiz_service=svc)
        assert exc.value.status_code == 404

    def test_success_returns_quiz(self):
        svc = _mock_svc()
        quiz = MagicMock()
        svc.get_quiz_by_id.return_value = quiz
        result = get_quiz_admin(1, current_user=_instructor(), quiz_service=svc)
        assert result is quiz


# ============================================================================
# get_all_quizzes_admin()
# ============================================================================

class TestGetAllQuizzesAdmin:

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            get_all_quizzes_admin(
                current_user=_student(),
                quiz_service=_mock_svc(),
                db=_mock_db([]),
            )
        assert exc.value.status_code == 403

    def test_admin_returns_quiz_list(self):
        quiz = _quiz_mock()
        db = _mock_db(quizzes=[quiz])

        # Patch QuizListItem to bypass Pydantic enum validation on category/difficulty
        with patch("app.models.quiz.Quiz"), \
             patch(f"{_BASE}.QuizListItem") as MockItem:
            MockItem.return_value = MagicMock()
            result = get_all_quizzes_admin(
                current_user=_admin(),
                quiz_service=_mock_svc(),
                db=db,
            )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_instructor_returns_empty_list(self):
        db = _mock_db(quizzes=[])

        with patch("app.models.quiz.Quiz"), \
             patch(f"{_BASE}.QuizListItem"):
            result = get_all_quizzes_admin(
                current_user=_instructor(),
                quiz_service=_mock_svc(),
                db=db,
            )

        assert result == []


# ============================================================================
# get_quiz_statistics()
# ============================================================================

class TestGetQuizStatistics:

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            get_quiz_statistics(1, current_user=_student(), quiz_service=_mock_svc())
        assert exc.value.status_code == 403

    def test_instructor_returns_statistics(self):
        svc = _mock_svc()
        stats = MagicMock()
        svc.get_quiz_statistics.return_value = stats
        result = get_quiz_statistics(1, current_user=_instructor(), quiz_service=svc)
        assert result is stats

    def test_admin_returns_statistics(self):
        svc = _mock_svc()
        stats = MagicMock()
        svc.get_quiz_statistics.return_value = stats
        result = get_quiz_statistics(1, current_user=_admin(), quiz_service=svc)
        assert result is stats


# ============================================================================
# get_quiz_leaderboard()
# ============================================================================

class TestGetQuizLeaderboard:

    def test_student_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            get_quiz_leaderboard(1, current_user=_student(), quiz_service=_mock_svc())
        assert exc.value.status_code == 403

    def test_instructor_returns_leaderboard(self):
        svc = _mock_svc()
        board = [MagicMock(), MagicMock()]
        svc.get_quiz_leaderboard.return_value = board
        result = get_quiz_leaderboard(1, current_user=_instructor(), quiz_service=svc)
        assert result is board

    def test_admin_returns_leaderboard(self):
        svc = _mock_svc()
        board = [MagicMock()]
        svc.get_quiz_leaderboard.return_value = board
        result = get_quiz_leaderboard(1, current_user=_admin(), quiz_service=svc)
        assert result is board
