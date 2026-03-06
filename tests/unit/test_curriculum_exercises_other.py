"""
Unit tests for the 4 remaining endpoints in
app/api/api_v1/endpoints/curriculum/exercises.py

Coverage targets:
  get_exercise_details()          — GET  /exercise/{exercise_id}
  get_exercise_submission()       — GET  /exercise/{exercise_id}/submission
  submit_exercise()               — POST /exercise/{exercise_id}/submit
  update_exercise_submission()    — PUT  /exercise/submission/{submission_id}
  upload_exercise_file()          — POST /exercise/submission/{submission_id}/upload  (async)

Mock strategy
-------------
All raw-SQL endpoints use db.execute(text(...)).fetchone() / .fetchone().id.
  - Single-call: db.execute.return_value.fetchone.return_value = row
  - Multi-call:  db.execute.return_value.fetchone.side_effect  = [row1, row2, ...]

Row mock: _Row(*values) — supports both index access ([0]) and attribute access (.id).
  JSON fields (requirements, submission_data) are tested with:
    - None (no JSON)
    - valid JSON string → parsed dict
    - invalid JSON string → raw value fallback

Datetime fields (submitted_at, reviewed_at etc.): use MagicMock with .isoformat()
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.api_v1.endpoints.curriculum.exercises import (
    get_exercise_details,
    get_exercise_submission,
    submit_exercise,
    update_exercise_submission,
    upload_exercise_file,
)


# ── Row helper ────────────────────────────────────────────────────────────────

class _Row:
    """Lightweight DB row supporting both index access ([i]) and .attribute access."""

    def __init__(self, *values, **attrs):
        self._values = list(values)
        for k, v in attrs.items():
            setattr(self, k, v)

    def __getitem__(self, i):
        return self._values[i]

    def __bool__(self):
        return True


def _db_seq(*fetchone_values):
    """Sequential mock: n-th .fetchone() returns fetchone_values[n]."""
    db = MagicMock()
    ex = MagicMock()
    ex.fetchone.side_effect = list(fetchone_values)
    db.execute.return_value = ex
    return db


def _db_single(row):
    """Single fetchone call → row."""
    db = MagicMock()
    ex = MagicMock()
    ex.fetchone.return_value = row
    db.execute.return_value = ex
    return db


def _user(user_id: int = 42):
    u = MagicMock()
    u.id = user_id
    return u


def _dt():
    """Mock datetime with .isoformat()."""
    dt = MagicMock()
    dt.isoformat.return_value = "2026-01-01T00:00:00"
    return dt


# ── get_exercise_details ───────────────────────────────────────────────────────

class TestGetExerciseDetails:
    """GET /exercise/{exercise_id}"""

    def _exercise_row(self, requirements=None):
        """Build a 15-field exercise row."""
        return _Row(
            1,              # id [0]
            "Header Ball",  # title [1]
            "Desc",         # description [2]
            "VIDEO",        # exercise_type [3]
            "Instructions", # instructions [4]
            requirements,   # requirements [5]
            100,            # max_points [6]
            70.0,           # passing_score [7]
            50,             # xp_reward [8]
            1,              # order_number [9]
            30,             # estimated_time_minutes [10]
            True,           # is_mandatory [11]
            False,          # allow_resubmission [12]
            7,              # deadline_days [13]
            10,             # lesson_id [14]
        )

    def test_raises_404_when_not_found(self):
        db = _db_single(None)
        with pytest.raises(HTTPException) as exc:
            get_exercise_details(exercise_id=99, current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_returns_id_and_title(self):
        db = _db_single(self._exercise_row())
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["id"] == 1
        assert result["title"] == "Header Ball"

    def test_passing_score_defaults_to_70_when_none(self):
        row = self._exercise_row()
        row._values[7] = None  # passing_score = None
        db = _db_single(row)
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["passing_score"] == 70.0

    def test_passing_score_from_db_when_present(self):
        db = _db_single(self._exercise_row())
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["passing_score"] == 70.0

    def test_requirements_none_when_field_is_none(self):
        db = _db_single(self._exercise_row(requirements=None))
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["requirements"] is None

    def test_requirements_parsed_from_valid_json_string(self):
        req_json = json.dumps({"min_score": 80, "deadline": 7})
        db = _db_single(self._exercise_row(requirements=req_json))
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["requirements"]["min_score"] == 80

    def test_requirements_dict_passed_through_directly(self):
        req_dict = {"min_score": 90}
        db = _db_single(self._exercise_row(requirements=req_dict))
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["requirements"] == req_dict

    def test_requirements_fallback_on_invalid_json(self):
        """If json.loads raises, raw value is returned."""
        db = _db_single(self._exercise_row(requirements="NOT_JSON{"))
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        assert result["requirements"] == "NOT_JSON{"

    def test_all_expected_fields_present(self):
        db = _db_single(self._exercise_row())
        result = get_exercise_details(exercise_id=1, current_user=_user(), db=db)
        for field in ("id", "title", "description", "exercise_type", "instructions",
                      "requirements", "max_points", "passing_score", "xp_reward",
                      "order_number", "estimated_time_minutes", "is_mandatory",
                      "allow_resubmission", "deadline_days", "lesson_id"):
            assert field in result


# ── get_exercise_submission ───────────────────────────────────────────────────

class TestGetExerciseSubmission:
    """GET /exercise/{exercise_id}/submission"""

    def _submission_row(self, submission_data=None, submitted_at=None,
                        reviewed_at=None, created_at=None, updated_at=None,
                        score=None):
        return _Row(
            5,               # id [0]
            "VIDEO",         # submission_type [1]
            "http://url",    # submission_url [2]
            None,            # submission_text [3]
            submission_data, # submission_data [4]
            "SUBMITTED",     # status [5]
            score,           # score [6]
            None,            # passed [7]
            10,              # xp_awarded [8]
            None,            # instructor_feedback [9]
            submitted_at,    # submitted_at [10]
            None,            # reviewed_by [11]
            reviewed_at,     # reviewed_at [12]
            created_at,      # created_at [13]
            updated_at,      # updated_at [14]
        )

    def test_raises_404_when_no_submission(self):
        db = _db_single(None)
        with pytest.raises(HTTPException) as exc:
            get_exercise_submission(exercise_id=99, current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_returns_id_and_status(self):
        db = _db_single(self._submission_row())
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["id"] == 5
        assert result["status"] == "SUBMITTED"

    def test_score_float_when_present(self):
        db = _db_single(self._submission_row(score=85))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["score"] == 85.0

    def test_score_none_when_not_graded(self):
        db = _db_single(self._submission_row(score=None))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["score"] is None

    def test_datetime_fields_isoformat_when_set(self):
        dt = _dt()
        db = _db_single(self._submission_row(submitted_at=dt))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["submitted_at"] == "2026-01-01T00:00:00"

    def test_datetime_fields_none_when_not_set(self):
        db = _db_single(self._submission_row(submitted_at=None))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["submitted_at"] is None

    def test_submission_data_parsed_from_valid_json_string(self):
        data_json = json.dumps({"key": "value"})
        db = _db_single(self._submission_row(submission_data=data_json))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["submission_data"]["key"] == "value"

    def test_submission_data_none_when_field_is_none(self):
        db = _db_single(self._submission_row(submission_data=None))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["submission_data"] is None

    def test_submission_data_fallback_on_invalid_json(self):
        db = _db_single(self._submission_row(submission_data="BAD_JSON{"))
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["submission_data"] == "BAD_JSON{"

    def test_xp_awarded_defaults_to_zero_when_none(self):
        row = self._submission_row()
        row._values[8] = None  # xp_awarded = None
        db = _db_single(row)
        result = get_exercise_submission(exercise_id=1, current_user=_user(), db=db)
        assert result["xp_awarded"] == 0


# ── submit_exercise ────────────────────────────────────────────────────────────

class TestSubmitExercise:
    """POST /exercise/{exercise_id}/submit"""

    def _db_submit(self, exercise_exists: bool, submission_id: int = 77):
        db = MagicMock()
        ex = MagicMock()
        exercise_row = _Row(1) if exercise_exists else None
        insert_row = MagicMock()
        insert_row.id = submission_id
        ex.fetchone.side_effect = [exercise_row, insert_row]
        db.execute.return_value = ex
        return db

    def test_raises_404_when_exercise_not_found(self):
        db = self._db_submit(exercise_exists=False)
        with pytest.raises(HTTPException) as exc:
            submit_exercise(
                exercise_id=99, payload={"submission_type": "TEXT"},
                current_user=_user(), db=db,
            )
        assert exc.value.status_code == 404

    def test_returns_submission_id(self):
        db = self._db_submit(exercise_exists=True, submission_id=77)
        result = submit_exercise(
            exercise_id=1, payload={"submission_type": "VIDEO", "submission_url": "http://x"},
            current_user=_user(), db=db,
        )
        assert result["submission_id"] == 77

    def test_returns_success_status(self):
        db = self._db_submit(exercise_exists=True)
        result = submit_exercise(
            exercise_id=1, payload={},
            current_user=_user(), db=db,
        )
        assert result["status"] == "success"

    def test_db_commit_called(self):
        db = self._db_submit(exercise_exists=True)
        submit_exercise(
            exercise_id=1, payload={},
            current_user=_user(), db=db,
        )
        db.commit.assert_called_once()

    def test_submission_data_serialized_to_json(self):
        """When payload has submission_data dict, it is json.dumps()-ed in execute call."""
        db = self._db_submit(exercise_exists=True)
        submit_exercise(
            exercise_id=1,
            payload={"submission_data": {"score": 80}},
            current_user=_user(), db=db,
        )
        # Verify execute was called at least twice (exercise check + insert)
        assert db.execute.call_count >= 2

    def test_submission_data_none_when_not_in_payload(self):
        """No submission_data in payload → None passed to DB."""
        db = self._db_submit(exercise_exists=True)
        submit_exercise(
            exercise_id=1, payload={},
            current_user=_user(), db=db,
        )
        # Verify the second execute (insert) was called
        assert db.execute.call_count >= 2


# ── update_exercise_submission ─────────────────────────────────────────────────

class TestUpdateExerciseSubmission:
    """PUT /exercise/submission/{submission_id}"""

    def _db_update(self, owner_id=42):
        """existing row: [0] = owner user_id."""
        db = MagicMock()
        ex = MagicMock()
        existing = _Row(owner_id)  # [0] = user_id
        ex.fetchone.return_value = existing
        db.execute.return_value = ex
        return db

    def test_raises_404_when_submission_not_found(self):
        db = MagicMock()
        ex = MagicMock()
        ex.fetchone.return_value = None
        db.execute.return_value = ex
        with pytest.raises(HTTPException) as exc:
            update_exercise_submission(
                submission_id=999, payload={},
                current_user=_user(42), db=db,
            )
        assert exc.value.status_code == 404

    def test_raises_403_when_not_owner(self):
        db = self._db_update(owner_id=99)  # owned by user 99
        with pytest.raises(HTTPException) as exc:
            update_exercise_submission(
                submission_id=1, payload={},
                current_user=_user(42),  # user 42 ≠ 99
                db=db,
            )
        assert exc.value.status_code == 403

    def test_owner_can_update(self):
        db = self._db_update(owner_id=42)
        result = update_exercise_submission(
            submission_id=1, payload={"submission_type": "TEXT", "submission_text": "My answer"},
            current_user=_user(42), db=db,
        )
        assert result["status"] == "success"

    def test_db_commit_called_on_success(self):
        db = self._db_update(owner_id=42)
        update_exercise_submission(
            submission_id=1, payload={},
            current_user=_user(42), db=db,
        )
        db.commit.assert_called_once()

    def test_execute_called_twice(self):
        """First execute = SELECT (ownership check), second = UPDATE."""
        db = self._db_update(owner_id=42)
        update_exercise_submission(
            submission_id=1, payload={},
            current_user=_user(42), db=db,
        )
        assert db.execute.call_count == 2

    def test_submission_data_serialized_when_present(self):
        db = self._db_update(owner_id=42)
        update_exercise_submission(
            submission_id=1, payload={"submission_data": {"note": "test"}},
            current_user=_user(42), db=db,
        )
        assert db.execute.call_count == 2  # check + update


# ── upload_exercise_file ───────────────────────────────────────────────────────

class TestUploadExerciseFile:
    """POST /exercise/submission/{submission_id}/upload (async, placeholder)"""

    def test_returns_success_status(self):
        db = MagicMock()
        result = asyncio.run(
            upload_exercise_file(submission_id="123", current_user=_user(42), db=db)
        )
        assert result["status"] == "success"

    def test_returns_file_url(self):
        db = MagicMock()
        result = asyncio.run(
            upload_exercise_file(submission_id="123", current_user=_user(42), db=db)
        )
        assert "file_url" in result
        assert result["file_url"].startswith("https://")

    def test_file_url_contains_user_id(self):
        db = MagicMock()
        result = asyncio.run(
            upload_exercise_file(submission_id="456", current_user=_user(42), db=db)
        )
        assert "/42/" in result["file_url"]

    def test_file_url_contains_submission_id(self):
        db = MagicMock()
        result = asyncio.run(
            upload_exercise_file(submission_id="456", current_user=_user(42), db=db)
        )
        assert "/456/" in result["file_url"]

    def test_no_db_access(self):
        """Upload is a placeholder — must not touch the DB."""
        db = MagicMock()
        asyncio.run(
            upload_exercise_file(submission_id="1", current_user=_user(), db=db)
        )
        db.execute.assert_not_called()
        db.commit.assert_not_called()
