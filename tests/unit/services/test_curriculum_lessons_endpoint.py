"""
Unit tests for app/api/api_v1/endpoints/curriculum/lessons.py
Covers: get_lesson_details, get_lesson_modules, get_lesson_quizzes,
        get_lesson_exercises, get_lesson_progress
Note: all endpoints are sync (no asyncio.run needed)
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.api.api_v1.endpoints.curriculum.lessons import (
    get_lesson_details,
    get_lesson_modules,
    get_lesson_quizzes,
    get_lesson_exercises,
    get_lesson_progress,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(uid=42):
    u = MagicMock(); u.id = uid; return u


def _exec(fetchone=None, fetchall=None):
    """Mock for a single db.execute() return value."""
    m = MagicMock()
    m.fetchone.return_value = fetchone
    m.fetchall.return_value = fetchall if fetchall is not None else []
    return m


# ---------------------------------------------------------------------------
# get_lesson_details
# ---------------------------------------------------------------------------

class TestGetLessonDetails:
    def _call(self, lesson_id=1, db=None):
        return get_lesson_details(
            lesson_id=lesson_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_gld01_not_found_404(self):
        """GLD-01: lesson not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_gld02_found_with_estimated_hours(self):
        """GLD-02: found, estimated_hours present → float returned."""
        row = (1, "Lesson 1", "Desc", 1, 1.5, 100, 2, True, "spec_1")
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["estimated_hours"] == 1.5
        assert result["id"] == 1
        assert result["title"] == "Lesson 1"

    def test_gld03_estimated_hours_none_returns_zero(self):
        """GLD-03: estimated_hours None → 0."""
        row = (1, "Lesson 1", "Desc", 1, None, 100, 2, True, "spec_1")
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["estimated_hours"] == 0


# ---------------------------------------------------------------------------
# get_lesson_modules
# ---------------------------------------------------------------------------

class TestGetLessonModules:
    def _call(self, lesson_id=1, db=None):
        return get_lesson_modules(
            lesson_id=lesson_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_glm01_no_modules_empty(self):
        """GLM-01: no modules → []."""
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = self._call(db=db)
        assert result == []

    def test_glm02_content_data_string_parsed(self):
        """GLM-02: content_data JSON string → parsed dict."""
        row = (1, "Module", "video", "content", '{"key": "val"}', 30, 50, 1, True)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["content_data"] == {"key": "val"}

    def test_glm03_content_data_dict_passes_through(self):
        """GLM-03: content_data already dict → returned as-is."""
        row = (1, "Module", "video", "content", {"key": "val"}, 30, 50, 1, True)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["content_data"] == {"key": "val"}

    def test_glm04_content_data_none(self):
        """GLM-04: content_data None → None."""
        row = (1, "Module", "video", "content", None, 30, 50, 1, True)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["content_data"] is None

    def test_glm05_invalid_json_returns_raw(self):
        """GLM-05: invalid JSON content_data → raw value returned."""
        row = (1, "Module", "video", "content", "INVALID_JSON{{{", 30, 50, 1, True)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["content_data"] == "INVALID_JSON{{{"

    def test_glm06_multiple_modules_ordered(self):
        """GLM-06: multiple modules → all returned."""
        rows = [
            (1, "Mod A", "video", None, None, 20, 30, 1, True),
            (2, "Mod B", "quiz", None, None, 15, 20, 2, False),
        ]
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = rows
        result = self._call(db=db)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2


# ---------------------------------------------------------------------------
# get_lesson_quizzes
# ---------------------------------------------------------------------------

class TestGetLessonQuizzes:
    def _call(self, lesson_id=1, db=None):
        return get_lesson_quizzes(
            lesson_id=lesson_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_glq01_no_quizzes_empty(self):
        """GLQ-01: no quizzes → []."""
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = self._call(db=db)
        assert result == []

    def test_glq02_passing_score_present(self):
        """GLQ-02: passing_score present → float."""
        row = (1, "Quiz", "Desc", "cat", "easy", 30, 100, "75.5", True, False, 1)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["passing_score"] == 75.5

    def test_glq03_passing_score_none_defaults(self):
        """GLQ-03: passing_score None → 70.0."""
        row = (1, "Quiz", "Desc", "cat", "easy", 30, 100, None, True, False, 1)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["passing_score"] == 70.0


# ---------------------------------------------------------------------------
# get_lesson_exercises
# ---------------------------------------------------------------------------

class TestGetLessonExercises:
    def _call(self, lesson_id=1, db=None):
        return get_lesson_exercises(
            lesson_id=lesson_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_gle01_no_exercises(self):
        """GLE-01: no exercises → []."""
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = self._call(db=db)
        assert result == []

    def test_gle02_requirements_string_parsed(self):
        """GLE-02: requirements as JSON string → parsed list."""
        row = (1, "Ex", "Desc", "VIDEO", "Instructions", '["req1"]', 100, 70, 50, 1, 60, True, False, 7)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["requirements"] == ["req1"]

    def test_gle03_requirements_none(self):
        """GLE-03: requirements None → None."""
        row = (1, "Ex", "Desc", "VIDEO", "Instructions", None, 100, 70, 50, 1, 60, True, False, 7)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["requirements"] is None

    def test_gle04_passing_score_none_defaults(self):
        """GLE-04: passing_score None → 70.0."""
        row = (1, "Ex", "Desc", "VIDEO", "Instructions", None, 100, None, 50, 1, 60, True, False, 7)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["passing_score"] == 70.0

    def test_gle05_invalid_requirements_json_raw(self):
        """GLE-05: invalid requirements JSON → raw string."""
        row = (1, "Ex", "Desc", "VIDEO", "Instructions", "INVALID{", 100, 70, 50, 1, 60, True, False, 7)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["requirements"] == "INVALID{"

    def test_gle06_requirements_dict_passes_through(self):
        """GLE-06: requirements already dict → returned as-is."""
        row = (1, "Ex", "Desc", "VIDEO", "Instructions", {"min": 1}, 100, 70, 50, 1, 60, True, False, 7)
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [row]
        result = self._call(db=db)
        assert result[0]["requirements"] == {"min": 1}


# ---------------------------------------------------------------------------
# get_lesson_progress
# ---------------------------------------------------------------------------

class TestGetLessonProgress:
    def _call(self, lesson_id=1, db=None):
        return get_lesson_progress(
            lesson_id=lesson_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_glp01_no_progress_defaults(self):
        """GLP-01: no lesson_progress row → defaults (LOCKED, 0%)."""
        exec_lesson = _exec(fetchone=None)
        exec_modules = _exec(fetchall=[])
        exec_exercises = _exec(fetchall=[])
        db = MagicMock()
        db.execute.side_effect = [exec_lesson, exec_modules, exec_exercises]
        result = self._call(db=db)
        assert result["status"] == "LOCKED"
        assert result["completion_percentage"] == 0
        assert result["xp_earned"] == 0
        assert result["modules"] == {}
        assert result["exercises"] == {}

    def test_glp02_with_progress_and_data(self):
        """GLP-02: full progress with modules and exercises."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        lesson_row = ("COMPLETED", 100, ts, ts, 200)
        module_row = (5, "COMPLETED", 45, ts)
        exercise_row = (10, "APPROVED", 85, True, 50, ts, "Good job")
        exec_lesson = _exec(fetchone=lesson_row)
        exec_modules = _exec(fetchall=[module_row])
        exec_exercises = _exec(fetchall=[exercise_row])
        db = MagicMock()
        db.execute.side_effect = [exec_lesson, exec_modules, exec_exercises]
        result = self._call(db=db)
        assert result["status"] == "COMPLETED"
        assert result["completion_percentage"] == 100
        assert result["xp_earned"] == 200
        assert 5 in result["modules"]
        assert result["modules"][5]["status"] == "COMPLETED"
        assert 10 in result["exercises"]
        assert result["exercises"][10]["score"] == 85.0

    def test_glp03_module_time_spent_none_defaults_zero(self):
        """GLP-03: module time_spent_minutes None → 0."""
        lesson_row = ("IN_PROGRESS", 50, None, None, 0)
        module_row = (5, "IN_PROGRESS", None, None)
        exec_lesson = _exec(fetchone=lesson_row)
        exec_modules = _exec(fetchall=[module_row])
        exec_exercises = _exec(fetchall=[])
        db = MagicMock()
        db.execute.side_effect = [exec_lesson, exec_modules, exec_exercises]
        result = self._call(db=db)
        assert result["modules"][5]["time_spent_minutes"] == 0

    def test_glp04_exercise_score_none(self):
        """GLP-04: exercise score None → score=None."""
        lesson_row = ("IN_PROGRESS", 50, None, None, 0)
        exercise_row = (10, "PENDING", None, False, 0, None, None)
        exec_lesson = _exec(fetchone=lesson_row)
        exec_modules = _exec(fetchall=[])
        exec_exercises = _exec(fetchall=[exercise_row])
        db = MagicMock()
        db.execute.side_effect = [exec_lesson, exec_modules, exec_exercises]
        result = self._call(db=db)
        assert result["exercises"][10]["score"] is None
        assert result["exercises"][10]["xp_awarded"] == 0

    def test_glp05_started_completed_isoformat(self):
        """GLP-05: timestamps present → isoformat strings."""
        ts = datetime(2025, 6, 1, 9, 0, 0)
        lesson_row = ("COMPLETED", 100, ts, ts, 50)
        exec_lesson = _exec(fetchone=lesson_row)
        exec_modules = _exec(fetchall=[])
        exec_exercises = _exec(fetchall=[])
        db = MagicMock()
        db.execute.side_effect = [exec_lesson, exec_modules, exec_exercises]
        result = self._call(db=db)
        assert result["started_at"] == ts.isoformat()
        assert result["completed_at"] == ts.isoformat()
