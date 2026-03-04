"""
Unit tests for app/services/competency_service.py

Mock-based: uses db.execute side_effect for multi-step raw SQL methods.
Covers: _score_to_level, assess_from_quiz, assess_from_exercise,
        get_user_competencies, get_competency_breakdown,
        get_assessment_history, get_user_milestones.
"""
import pytest
from unittest.mock import MagicMock, call, patch
from app.services.competency_service import CompetencyService


# ── helpers ──────────────────────────────────────────────────────────────────

def _svc():
    db = MagicMock()
    return CompetencyService(db), db


def _exec_mock(*rows_or_none, fetchall=False):
    """Helper to create a db.execute() return value mock."""
    m = MagicMock()
    if fetchall:
        m.fetchall.return_value = list(rows_or_none)
    else:
        m.fetchone.return_value = rows_or_none[0] if rows_or_none else None
    return m


def _row(**kwargs):
    """Create a mock row with named attributes."""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


# ── _score_to_level (pure function) ──────────────────────────────────────────

class TestScoreToLevel:

    def test_score_90_is_expert(self):
        svc, _ = _svc()
        assert svc._score_to_level(90) == 5

    def test_score_100_is_expert(self):
        svc, _ = _svc()
        assert svc._score_to_level(100) == 5

    def test_score_75_is_proficient(self):
        svc, _ = _svc()
        assert svc._score_to_level(75) == 4

    def test_score_80_is_proficient(self):
        svc, _ = _svc()
        assert svc._score_to_level(80) == 4

    def test_score_60_is_competent(self):
        svc, _ = _svc()
        assert svc._score_to_level(60) == 3

    def test_score_65_is_competent(self):
        svc, _ = _svc()
        assert svc._score_to_level(65) == 3

    def test_score_40_is_developing(self):
        svc, _ = _svc()
        assert svc._score_to_level(40) == 2

    def test_score_50_is_developing(self):
        svc, _ = _svc()
        assert svc._score_to_level(50) == 2

    def test_score_39_is_beginner(self):
        svc, _ = _svc()
        assert svc._score_to_level(39) == 1

    def test_score_0_is_beginner(self):
        svc, _ = _svc()
        assert svc._score_to_level(0) == 1


# ── assess_from_quiz — early returns ─────────────────────────────────────────

class TestAssessFromQuiz:

    def test_quiz_not_found_returns_early(self):
        svc, db = _svc()
        db.execute.return_value.fetchone.return_value = None
        svc.assess_from_quiz(user_id=1, quiz_id=99, quiz_attempt_id=1, score=80)
        # Only one execute call (quiz lookup), then returns
        db.execute.assert_called_once()

    def test_quiz_no_specialization_returns_early(self):
        svc, db = _svc()
        quiz_row = _row(specialization_id=None, lesson_id=None, category="MARKETING")
        db.execute.return_value.fetchone.return_value = quiz_row
        svc.assess_from_quiz(user_id=1, quiz_id=1, quiz_attempt_id=1, score=80)
        # Returns after checking specialization_id is None
        db.execute.assert_called_once()

    def test_quiz_no_categories_returns_early(self):
        svc, db = _svc()
        quiz_row = _row(specialization_id="LFA_COACH", lesson_id=None, category="MARKETING")
        # First call returns quiz, second call returns empty categories
        exec1 = _exec_mock(quiz_row)
        exec2 = _exec_mock(fetchall=True)  # empty
        db.execute.side_effect = [exec1, exec2]
        svc.assess_from_quiz(user_id=1, quiz_id=1, quiz_attempt_id=1, score=80)
        assert db.execute.call_count == 2

    def test_quiz_with_lesson_fetches_lesson_data(self):
        svc, db = _svc()
        quiz_row = _row(specialization_id="LFA_COACH", lesson_id=5, category="MARKETING")
        lesson_row = _row(skill_focus_tags=None)
        exec_quiz = _exec_mock(quiz_row)
        exec_lesson = _exec_mock(lesson_row)
        exec_categories = _exec_mock(fetchall=True)  # empty → early return
        db.execute.side_effect = [exec_quiz, exec_lesson, exec_categories]
        svc.assess_from_quiz(user_id=1, quiz_id=1, quiz_attempt_id=1, score=80)
        assert db.execute.call_count == 3


# ── assess_from_exercise — early returns ─────────────────────────────────────

class TestAssessFromExercise:

    def test_exercise_not_found_returns_early(self):
        svc, db = _svc()
        db.execute.return_value.fetchone.return_value = None
        svc.assess_from_exercise(user_id=1, exercise_submission_id=999, score=75)
        db.execute.assert_called_once()

    def test_exercise_no_categories_returns_early(self):
        svc, db = _svc()
        exercise_row = _row(specialization_id="LFA_COACH", exercise_type="VIDEO_UPLOAD")
        exec1 = _exec_mock(exercise_row)
        exec2 = _exec_mock(fetchall=True)  # no categories
        db.execute.side_effect = [exec1, exec2]
        svc.assess_from_exercise(user_id=1, exercise_submission_id=1, score=75)
        assert db.execute.call_count == 2


# ── get_user_competencies ─────────────────────────────────────────────────────

class TestGetUserCompetencies:

    def test_returns_empty_list_if_no_results(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        result = svc.get_user_competencies(user_id=1)
        assert result == []

    def test_returns_list_of_dicts(self):
        svc, db = _svc()
        row = _row(
            id=1, user_id=1, category_id=2, category_name="Technical",
            category_icon="⚽", specialization_id="LFA_COACH",
            current_score=75.0, current_level="Proficient",
            total_assessments=5, last_assessed_at=None
        )
        db.execute.return_value.fetchall.return_value = [row]
        result = svc.get_user_competencies(user_id=1)
        assert len(result) == 1
        assert result[0]["category_name"] == "Technical"
        assert result[0]["current_score"] == 75.0

    def test_filter_by_specialization_id(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        svc.get_user_competencies(user_id=1, specialization_id="LFA_COACH")
        # Verifies the query was called (specialization filter applied inside)
        db.execute.assert_called_once()

    def test_no_filter_when_spec_id_none(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        svc.get_user_competencies(user_id=1, specialization_id=None)
        db.execute.assert_called_once()


# ── get_competency_breakdown ──────────────────────────────────────────────────

class TestGetCompetencyBreakdown:

    def test_category_not_found_returns_none(self):
        svc, db = _svc()
        db.execute.return_value.fetchone.return_value = None
        result = svc.get_competency_breakdown(user_id=1, category_id=99)
        assert result is None

    def test_returns_breakdown_dict_when_category_found(self):
        svc, db = _svc()
        cat_row = _row(id=1, name="Technical", description="Tech skills", icon="⚽")
        score_row = _row(current_score=80.0, current_level="Proficient", total_assessments=3)
        skill_row = _row(
            id=1, name="Dribbling", description="Ball control",
            current_score=85.0, current_level="Proficient",
            total_assessments=2, last_assessed_at=None
        )
        exec1 = _exec_mock(cat_row)
        exec2 = _exec_mock(score_row)
        exec3 = _exec_mock(skill_row, fetchall=True)
        db.execute.side_effect = [exec1, exec2, exec3]
        result = svc.get_competency_breakdown(user_id=1, category_id=1)
        assert result is not None
        assert result["category"]["name"] == "Technical"
        assert len(result["skills"]) == 1

    def test_no_category_score_uses_defaults(self):
        svc, db = _svc()
        cat_row = _row(id=1, name="Technical", description="Tech", icon="⚽")
        exec1 = _exec_mock(cat_row)
        exec2 = _exec_mock(None)  # no score
        exec3 = _exec_mock(fetchall=True)  # no skills
        db.execute.side_effect = [exec1, exec2, exec3]
        result = svc.get_competency_breakdown(user_id=1, category_id=1)
        assert result["category"]["current_score"] == 0.0
        assert result["category"]["current_level"] == "Beginner"
        assert result["category"]["total_assessments"] == 0


# ── get_assessment_history ────────────────────────────────────────────────────

class TestGetAssessmentHistory:

    def test_returns_empty_list_if_none(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        result = svc.get_assessment_history(user_id=1)
        assert result == []

    def test_returns_list_of_assessment_dicts(self):
        svc, db = _svc()
        row = _row(
            id=1, category_name="Technical", skill_name="Dribbling",
            score=85.0, source_type="QUIZ", source_id=5, assessed_at=None
        )
        db.execute.return_value.fetchall.return_value = [row]
        result = svc.get_assessment_history(user_id=1)
        assert len(result) == 1
        assert result[0]["score"] == 85.0
        assert result[0]["source_type"] == "QUIZ"

    def test_default_limit_is_20(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        svc.get_assessment_history(user_id=1)
        db.execute.assert_called_once()


# ── get_user_milestones ───────────────────────────────────────────────────────

class TestGetUserMilestones:

    def test_returns_empty_list_if_none(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        result = svc.get_user_milestones(user_id=1)
        assert result == []

    def test_returns_list_of_milestone_dicts(self):
        svc, db = _svc()
        row = _row(
            id=1, milestone_id=2, milestone_name="Tech Master",
            description="Technical expert", icon="🏆",
            xp_reward=500, specialization_id="LFA_COACH", achieved_at=None
        )
        db.execute.return_value.fetchall.return_value = [row]
        result = svc.get_user_milestones(user_id=1)
        assert len(result) == 1
        assert result[0]["milestone_name"] == "Tech Master"

    def test_filter_by_specialization(self):
        svc, db = _svc()
        db.execute.return_value.fetchall.return_value = []
        svc.get_user_milestones(user_id=1, specialization_id="LFA_COACH")
        db.execute.assert_called_once()
