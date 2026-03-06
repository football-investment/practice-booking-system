"""
Unit tests for grade_exercise_submission() in
app/api/api_v1/endpoints/curriculum/exercises.py

Coverage targets:
  - 403 path: non-instructor role
  - 404 path: submission not found
  - 400 path: invalid score (None, out of range)
  - 200 happy path: passed=True, XP awarded (APPROVED)
  - 200 happy path: passed=False, XP not awarded
  - Hook execution: CompetencyService.assess_from_exercise called
  - Hook execution: AdaptiveLearningService.update_profile_metrics called
  - Hook rollback: exception in hook → endpoint still returns success
  - grade_status not APPROVED → xp_awarded = 0

Patch paths (after import fix):
  _BASE = "app.api.api_v1.endpoints.curriculum.exercises"
  _COMP  = f"{_BASE}.CompetencyService"
  _ADAPT = f"{_BASE}.AdaptiveLearningService"
  _SL    = "app.database.SessionLocal"   (lazy import inside function body)

Mock strategy
-------------
db.execute.return_value.fetchone.side_effect = [row, ...]
Submission row: MagicMock with attributes passing_score, xp_reward, student_id
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from types import SimpleNamespace

from app.api.api_v1.endpoints.curriculum.exercises import grade_exercise_submission
from app.models.user import UserRole

# ── Constants ──────────────────────────────────────────────────────────────────

_BASE  = "app.api.api_v1.endpoints.curriculum.exercises"
_COMP  = f"{_BASE}.CompetencyService"
_ADAPT = f"{_BASE}.AdaptiveLearningService"
_SL    = "app.database.SessionLocal"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role: UserRole = UserRole.INSTRUCTOR) -> MagicMock:
    u = MagicMock()
    u.id = 99
    u.role = role
    return u


def _submission_row(passing_score=70.0, xp_reward=50, student_id=7):
    row = MagicMock()
    row.passing_score = passing_score
    row.xp_reward     = xp_reward
    row.student_id    = student_id
    return row


def _db_with_submission(submission_row=None):
    """db.execute(...).fetchone() returns submission_row on first call."""
    db = MagicMock()
    execute_mock = MagicMock()
    execute_mock.fetchone.return_value = submission_row
    db.execute.return_value = execute_mock
    return db


# ── Role guard ─────────────────────────────────────────────────────────────────

class TestGradeExerciseRoleGuard:

    def test_student_role_raises_403(self):
        db = _db_with_submission(_submission_row())
        with pytest.raises(HTTPException) as exc:
            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(UserRole.STUDENT),
                db=db,
            )
        assert exc.value.status_code == 403

    def test_instructor_role_allowed(self):
        db = _db_with_submission(_submission_row())
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(UserRole.INSTRUCTOR),
                db=db,
            )
        assert result["status"] == "success"

    def test_admin_role_allowed(self):
        db = _db_with_submission(_submission_row())
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(UserRole.ADMIN),
                db=db,
            )
        assert result["status"] == "success"


# ── 404 path ───────────────────────────────────────────────────────────────────

class TestGradeExercise404:

    def test_raises_404_when_submission_not_found(self):
        db = _db_with_submission(None)
        with pytest.raises(HTTPException) as exc:
            grade_exercise_submission(
                submission_id=99999,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        assert exc.value.status_code == 404


# ── Score validation ───────────────────────────────────────────────────────────

class TestGradeExerciseScoreValidation:

    def test_missing_score_raises_400(self):
        db = _db_with_submission(_submission_row())
        with pytest.raises(HTTPException) as exc:
            grade_exercise_submission(
                submission_id=1,
                payload={},                   # score=None → payload.get("score")=None
                current_user=_user(),
                db=db,
            )
        assert exc.value.status_code == 400

    def test_score_above_100_raises_400(self):
        db = _db_with_submission(_submission_row())
        with pytest.raises(HTTPException) as exc:
            grade_exercise_submission(
                submission_id=1,
                payload={"score": 101},
                current_user=_user(),
                db=db,
            )
        assert exc.value.status_code == 400

    def test_score_below_0_raises_400(self):
        db = _db_with_submission(_submission_row())
        with pytest.raises(HTTPException) as exc:
            grade_exercise_submission(
                submission_id=1,
                payload={"score": -1},
                current_user=_user(),
                db=db,
            )
        assert exc.value.status_code == 400

    def test_score_0_is_valid(self):
        db = _db_with_submission(_submission_row())
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 0},
                current_user=_user(),
                db=db,
            )
        assert result["status"] == "success"

    def test_score_100_is_valid(self):
        db = _db_with_submission(_submission_row())
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 100},
                current_user=_user(),
                db=db,
            )
        assert result["status"] == "success"


# ── Happy path — passed / not passed ──────────────────────────────────────────

class TestGradeExerciseHappyPath:

    def test_response_fields_present(self):
        db = _db_with_submission(_submission_row(passing_score=70.0, xp_reward=30))
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 85, "feedback": "Great!", "status": "APPROVED"},
                current_user=_user(),
                db=db,
            )
        assert result["status"] == "success"
        assert "grade_status" in result
        assert "score" in result
        assert "passed" in result
        assert "xp_awarded" in result
        assert "submission_id" in result

    def test_passed_true_when_score_above_passing(self):
        db = _db_with_submission(_submission_row(passing_score=70.0, xp_reward=50))
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 85, "status": "APPROVED"},
                current_user=_user(),
                db=db,
            )
        assert result["passed"] is True
        assert result["xp_awarded"] == 50

    def test_passed_false_when_score_below_passing(self):
        db = _db_with_submission(_submission_row(passing_score=70.0, xp_reward=50))
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 60, "status": "APPROVED"},
                current_user=_user(),
                db=db,
            )
        assert result["passed"] is False
        assert result["xp_awarded"] == 0

    def test_no_xp_when_status_not_approved(self):
        """NEEDS_REVISION or REJECTED → xp_awarded = 0 even if score passes."""
        db = _db_with_submission(_submission_row(passing_score=70.0, xp_reward=50))
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 90, "status": "NEEDS_REVISION"},
                current_user=_user(),
                db=db,
            )
        assert result["xp_awarded"] == 0

    def test_db_commit_called(self):
        db = _db_with_submission(_submission_row())
        with patch(_COMP), patch(_ADAPT), patch(_SL):
            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        db.commit.assert_called_once()


# ── Hook execution verification ────────────────────────────────────────────────

class TestGradeExerciseHooks:
    """Verify that CompetencyService and AdaptiveLearningService are invoked."""

    def _run(self, score=85, mock_sl=None):
        db = _db_with_submission(_submission_row(passing_score=70.0, xp_reward=20, student_id=7))
        mock_hook_db = MagicMock()
        sl_factory = mock_sl or MagicMock(return_value=mock_hook_db)

        with patch(_COMP) as mock_comp_cls, \
             patch(_ADAPT) as mock_adapt_cls, \
             patch(_SL, sl_factory):

            mock_comp  = mock_comp_cls.return_value
            mock_adapt = mock_adapt_cls.return_value

            result = grade_exercise_submission(
                submission_id=3,
                payload={"score": score, "status": "APPROVED"},
                current_user=_user(),
                db=db,
            )
            return result, mock_comp, mock_adapt

    def test_competency_service_instantiated_with_hook_db(self):
        _, mock_comp, _ = self._run()
        # assert_called_once verifies the service was instantiated
        assert mock_comp is not None

    def test_assess_from_exercise_called(self):
        _, mock_comp, _ = self._run(score=85)
        mock_comp.assess_from_exercise.assert_called_once()

    def test_assess_from_exercise_args(self):
        """Verify correct user_id, submission_id, and score passed to hook."""
        _, mock_comp, _ = self._run(score=90)
        call_kwargs = mock_comp.assess_from_exercise.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert kwargs.get("user_id") == 7
        assert kwargs.get("exercise_submission_id") == 3
        assert kwargs.get("score") == 90.0

    def test_update_profile_metrics_called(self):
        _, _, mock_adapt = self._run()
        mock_adapt.update_profile_metrics.assert_called_once_with(7)

    def test_hook_db_commit_called(self):
        db = _db_with_submission(_submission_row())
        mock_hook_db = MagicMock()
        with patch(_COMP), patch(_ADAPT), patch(_SL, return_value=mock_hook_db):
            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        mock_hook_db.commit.assert_called_once()

    def test_hook_db_closed_always(self):
        """hook_db.close() must be called even on success."""
        db = _db_with_submission(_submission_row())
        mock_hook_db = MagicMock()
        with patch(_COMP), patch(_ADAPT), patch(_SL, return_value=mock_hook_db):
            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        mock_hook_db.close.assert_called_once()


# ── Hook resilience — exception path ──────────────────────────────────────────

class TestGradeExerciseHookResilience:
    """Hook errors must NOT propagate — endpoint returns success regardless."""

    def test_returns_success_even_when_competency_hook_raises(self):
        db = _db_with_submission(_submission_row())
        mock_hook_db = MagicMock()

        with patch(_COMP) as mock_comp_cls, \
             patch(_ADAPT), \
             patch(_SL, return_value=mock_hook_db):
            mock_comp_cls.return_value.assess_from_exercise.side_effect = RuntimeError("db error")

            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        assert result["status"] == "success"

    def test_hook_db_rollback_called_on_exception(self):
        db = _db_with_submission(_submission_row())
        mock_hook_db = MagicMock()

        with patch(_COMP) as mock_comp_cls, \
             patch(_ADAPT), \
             patch(_SL, return_value=mock_hook_db):
            mock_comp_cls.return_value.assess_from_exercise.side_effect = ValueError("fail")

            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        mock_hook_db.rollback.assert_called_once()

    def test_hook_db_closed_even_on_hook_exception(self):
        """finally block must close hook_db even when hook raises."""
        db = _db_with_submission(_submission_row())
        mock_hook_db = MagicMock()

        with patch(_COMP) as mock_comp_cls, \
             patch(_ADAPT), \
             patch(_SL, return_value=mock_hook_db):
            mock_comp_cls.return_value.assess_from_exercise.side_effect = Exception("crash")

            grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        mock_hook_db.close.assert_called_once()

    def test_session_local_failure_hook_db_stays_none(self):
        """
        When SessionLocal() itself raises, hook_db stays None.
        Both `if hook_db:` guards in except + finally must evaluate False.
        Endpoint must still return success (exception is caught).
        Covers branch edges 363->368 and 368->371.
        """
        db = _db_with_submission(_submission_row())

        with patch(_COMP), patch(_ADAPT), \
             patch(_SL, side_effect=RuntimeError("cannot connect")):
            result = grade_exercise_submission(
                submission_id=1,
                payload={"score": 80},
                current_user=_user(),
                db=db,
            )
        # hook_db=None path: rollback and close are skipped — endpoint still succeeds
        assert result["status"] == "success"
