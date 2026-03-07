"""
Unit tests for app/api/api_v1/endpoints/curriculum/exercises.py
Covers: get_exercise_details, get_exercise_submission, submit_exercise,
        update_exercise_submission, upload_exercise_file, grade_exercise_submission
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.api.api_v1.endpoints.curriculum.exercises import (
    get_exercise_details,
    get_exercise_submission,
    submit_exercise,
    update_exercise_submission,
    upload_exercise_file,
    grade_exercise_submission,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.curriculum.exercises"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(uid=42, role=UserRole.STUDENT):
    u = MagicMock(); u.id = uid; u.name = "Student"; u.role = role; return u


def _instructor(uid=42):
    return _user(uid=uid, role=UserRole.INSTRUCTOR)


def _exec(fetchone=None, fetchall=None):
    m = MagicMock()
    m.fetchone.return_value = fetchone
    m.fetchall.return_value = fetchall if fetchall is not None else []
    return m


def _sub_mock(passing_score=70, xp_reward=100, student_id=99):
    sub = MagicMock()
    sub.passing_score = passing_score
    sub.xp_reward = xp_reward
    sub.student_id = student_id
    return sub


# ---------------------------------------------------------------------------
# get_exercise_details
# ---------------------------------------------------------------------------

class TestGetExerciseDetails:
    def _call(self, exercise_id=1, db=None):
        return get_exercise_details(
            exercise_id=exercise_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_ged01_not_found_404(self):
        """GED-01: exercise not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_ged02_requirements_string_parsed(self):
        """GED-02: requirements JSON string → parsed dict."""
        row = (1, "Ex", "Desc", "VIDEO", "Instr", '{"min_length": 5}', 100, 70, 50, 1, 60, True, False, 7, 3)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["requirements"] == {"min_length": 5}

    def test_ged03_requirements_none(self):
        """GED-03: requirements None → None."""
        row = (1, "Ex", "Desc", "VIDEO", "Instr", None, 100, 70, 50, 1, 60, True, False, 7, 3)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["requirements"] is None

    def test_ged04_passing_score_none_defaults_70(self):
        """GED-04: passing_score None → 70.0."""
        row = (1, "Ex", "Desc", "VIDEO", "Instr", None, 100, None, 50, 1, 60, True, False, 7, 3)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["passing_score"] == 70.0

    def test_ged05_invalid_requirements_raw_value(self):
        """GED-05: invalid JSON requirements → raw string."""
        row = (1, "Ex", "Desc", "VIDEO", "Instr", "BADJSON{", 100, 70, 50, 1, 60, True, False, 7, 3)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["requirements"] == "BADJSON{"

    def test_ged06_requirements_dict_passes_through(self):
        """GED-06: requirements already dict → returned as-is."""
        row = (1, "Ex", "Desc", "VIDEO", "Instr", {"key": "val"}, 100, 70, 50, 1, 60, True, False, 7, 3)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["requirements"] == {"key": "val"}


# ---------------------------------------------------------------------------
# get_exercise_submission
# ---------------------------------------------------------------------------

class TestGetExerciseSubmission:
    def _call(self, exercise_id=1, db=None):
        return get_exercise_submission(
            exercise_id=exercise_id,
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_ges01_not_found_404(self):
        """GES-01: no submission → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_ges02_found_with_parsed_data(self):
        """GES-02: submission found, JSON submission_data → parsed."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        row = (1, "FILE", "http://url", "text", '{"a": 1}',
               "SUBMITTED", 85, True, 50, "Good", ts, 99, ts, ts, ts)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["id"] == 1
        assert result["submission_data"] == {"a": 1}
        assert result["score"] == 85.0
        assert result["xp_awarded"] == 50

    def test_ges03_no_timestamps_returns_none(self):
        """GES-03: no timestamps → None."""
        row = (1, "FILE", None, None, None, "DRAFT", None, False, 0, None, None, None, None, None, None)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["submitted_at"] is None
        assert result["score"] is None
        assert result["xp_awarded"] == 0

    def test_ges04_invalid_submission_data_raw(self):
        """GES-04: invalid JSON submission_data → raw string."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        row = (1, "FILE", None, None, "BADJSON{",
               "DRAFT", None, False, 0, None, None, None, None, ts, ts)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["submission_data"] == "BADJSON{"

    def test_ges05_submission_data_dict_passes_through(self):
        """GES-05: submission_data already dict → returned as-is."""
        ts = datetime(2025, 1, 15, 10, 0, 0)
        row = (1, "FILE", None, None, {"key": "val"},
               "SUBMITTED", 80, True, 40, None, ts, None, None, ts, ts)
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = row
        result = self._call(db=db)
        assert result["submission_data"] == {"key": "val"}


# ---------------------------------------------------------------------------
# submit_exercise
# ---------------------------------------------------------------------------

class TestSubmitExercise:
    def _call(self, exercise_id=1, payload=None, db=None):
        return submit_exercise(
            exercise_id=exercise_id,
            payload=payload or {"submission_type": "FILE", "submission_url": "http://url"},
            current_user=_user(),
            db=db or MagicMock(),
        )

    def test_se01_exercise_not_found_404(self):
        """SE-01: exercise not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_se02_success_returns_submission_id(self):
        """SE-02: exercise found → submission created, id returned."""
        sub_row = MagicMock(); sub_row.id = 99
        exec1 = _exec(fetchone=(1,))                       # exercise found
        exec2 = MagicMock(); exec2.fetchone.return_value = sub_row  # INSERT RETURNING
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(db=db)
        assert result["submission_id"] == 99
        db.commit.assert_called_once()

    def test_se03_with_submission_data_json(self):
        """SE-03: submission_data in payload → serialised and inserted."""
        sub_row = MagicMock(); sub_row.id = 77
        exec1 = _exec(fetchone=(1,))
        exec2 = MagicMock(); exec2.fetchone.return_value = sub_row
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(
            payload={"submission_data": {"key": "val"}, "status": "SUBMITTED"},
            db=db,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# update_exercise_submission
# ---------------------------------------------------------------------------

class TestUpdateExerciseSubmission:
    def _call(self, submission_id=1, payload=None, db=None):
        return update_exercise_submission(
            submission_id=submission_id,
            payload=payload or {"submission_type": "FILE"},
            current_user=_user(uid=42),
            db=db or MagicMock(),
        )

    def test_ues01_not_found_404(self):
        """UES-01: submission not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_ues02_not_owner_403(self):
        """UES-02: different user_id → 403."""
        from fastapi import HTTPException
        exec1 = _exec(fetchone=(99,))   # user_id=99, current_user=42
        db = MagicMock(); db.execute.side_effect = [exec1]
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 403

    def test_ues03_success(self):
        """UES-03: own submission → UPDATE called, committed."""
        exec1 = _exec(fetchone=(42,))   # user_id matches
        exec2 = _exec()                 # UPDATE
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(db=db)
        assert result["status"] == "success"
        db.commit.assert_called_once()

    def test_ues04_with_submission_data_serialised(self):
        """UES-04: submission_data in payload → json.dumps applied."""
        exec1 = _exec(fetchone=(42,))
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(
            payload={"submission_data": {"nested": True}, "status": "SUBMITTED"},
            db=db,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# upload_exercise_file (async)
# ---------------------------------------------------------------------------

class TestUploadExerciseFile:
    def test_uef01_returns_mock_url(self):
        """UEF-01: always returns mock URL."""
        result = asyncio.run(upload_exercise_file(
            submission_id="123",
            current_user=_user(),
            db=MagicMock(),
        ))
        assert result["status"] == "success"
        assert "file_url" in result
        assert "123" in result["file_url"]


# ---------------------------------------------------------------------------
# grade_exercise_submission
# ---------------------------------------------------------------------------

class TestGradeExerciseSubmission:
    """grade_exercise_submission uses SessionLocal internally for hooks."""

    def _call(self, submission_id=1, payload=None, db=None, current_user=None):
        payload = payload or {"score": 85, "feedback": "Good", "status": "APPROVED"}
        current_user = current_user or _instructor()
        # SessionLocal is imported lazily inside the function → patch source module
        with patch("app.database.SessionLocal") as MockSL, \
             patch(f"{_BASE}.CompetencyService"), \
             patch(f"{_BASE}.AdaptiveLearningService"):
            MockSL.return_value = MagicMock()
            return grade_exercise_submission(
                submission_id=submission_id,
                payload=payload,
                current_user=current_user,
                db=db or MagicMock(),
            )

    def test_gras01_student_403(self):
        """GRAS-01: student role → 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=_user(uid=42, role=UserRole.STUDENT))
        assert exc.value.status_code == 403

    def test_gras02_submission_not_found_404(self):
        """GRAS-02: submission not found → 404."""
        from fastapi import HTTPException
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_gras03_score_none_400(self):
        """GRAS-03: score absent from payload → 400."""
        from fastapi import HTTPException
        sub = _sub_mock()
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = sub
        with pytest.raises(HTTPException) as exc:
            self._call(payload={"feedback": "OK"}, db=db)
        assert exc.value.status_code == 400

    def test_gras04_score_out_of_range_400(self):
        """GRAS-04: score > 100 → 400."""
        from fastapi import HTTPException
        sub = _sub_mock()
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = sub
        with pytest.raises(HTTPException) as exc:
            self._call(payload={"score": 150}, db=db)
        assert exc.value.status_code == 400

    def test_gras05_negative_score_400(self):
        """GRAS-05: score < 0 → 400."""
        from fastapi import HTTPException
        sub = _sub_mock()
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = sub
        with pytest.raises(HTTPException) as exc:
            self._call(payload={"score": -1}, db=db)
        assert exc.value.status_code == 400

    def test_gras06_passed_approved_xp_awarded(self):
        """GRAS-06: score >= passing_score + APPROVED → xp_awarded."""
        sub = _sub_mock(passing_score=70, xp_reward=100, student_id=99)
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()         # UPDATE submission
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(payload={"score": 85, "status": "APPROVED"}, db=db)
        assert result["passed"] is True
        assert result["xp_awarded"] == 100

    def test_gras07_not_passed_xp_zero(self):
        """GRAS-07: score < passing_score → passed=False, xp=0."""
        sub = _sub_mock(passing_score=70, xp_reward=100, student_id=99)
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(payload={"score": 50, "status": "APPROVED"}, db=db)
        assert result["passed"] is False
        assert result["xp_awarded"] == 0

    def test_gras08_needs_revision_no_xp(self):
        """GRAS-08: passed but status=NEEDS_REVISION → xp=0."""
        sub = _sub_mock(passing_score=70, xp_reward=100, student_id=99)
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(payload={"score": 90, "status": "NEEDS_REVISION"}, db=db)
        assert result["passed"] is True
        assert result["xp_awarded"] == 0

    def test_gras09_passing_score_none_defaults_70(self):
        """GRAS-09: submission.passing_score=None → default 70.0."""
        sub = _sub_mock(passing_score=None, xp_reward=50, student_id=99)
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(payload={"score": 75, "status": "APPROVED"}, db=db)
        assert result["passed"] is True     # 75 >= 70.0

    def test_gras10_hook_error_still_returns_success(self):
        """GRAS-10: hook raises exception → grading committed, success returned."""
        sub = _sub_mock()
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        hook_db = MagicMock()
        with patch("app.database.SessionLocal") as MockSL, \
             patch(f"{_BASE}.CompetencyService") as MockCS, \
             patch(f"{_BASE}.AdaptiveLearningService"):
            MockSL.return_value = hook_db
            MockCS.return_value.assess_from_exercise.side_effect = Exception("hook error")
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 85, "status": "APPROVED"},
                current_user=_instructor(),
                db=db,
            )
        assert result["status"] == "success"
        hook_db.rollback.assert_called_once()
        hook_db.close.assert_called_once()

    def test_gras11_admin_can_grade(self):
        """GRAS-11: admin role → allowed."""
        sub = _sub_mock()
        exec1 = _exec(fetchone=sub)
        exec2 = _exec()
        db = MagicMock(); db.execute.side_effect = [exec1, exec2]
        result = self._call(db=db, current_user=_user(uid=42, role=UserRole.ADMIN))
        assert result["status"] == "success"
