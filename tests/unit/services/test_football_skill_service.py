"""
Unit tests for app/services/football_skill_service.py (FootballSkillService)

Covers:
  create_assessment (validation-only, before DB/lock):
    invalid skill name → ValueError
    negative points_earned → ValueError
    zero points_total → ValueError
    points_earned > points_total → ValueError

  validate_assessment:
    assessment not found → ValueError
    already VALIDATED → idempotent return
    invalid state transition (ARCHIVED → VALIDATED) → ValueError
    happy path ASSESSED → VALIDATED

  archive_assessment:
    assessment not found → ValueError
    already ARCHIVED → idempotent return
    invalid state transition (NOT_ASSESSED → ARCHIVED) → ValueError
    happy path ASSESSED → ARCHIVED
    happy path VALIDATED → ARCHIVED

  recalculate_skill_average:
    no assessments → returns 0.0 (early return before lock_timer)

  get_current_averages:
    no license → all zeros dict
    license with no football_skills → all zeros
    license with scalar skills → returns values
    missing skill defaults to 0.0

  get_assessment_counts:
    counts per skill, None scalar defaults to 0
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.football_skill_service import FootballSkillService
from app.services.skill_state_machine import SkillAssessmentState
from app.skills_config import get_all_skill_keys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SKILL = "ball_control"
ANOTHER_VALID_SKILL = "dribbling"


def _svc():
    """Return (service, mock_db)."""
    db = MagicMock()
    return FootballSkillService(db), db


def _wfu_q(db, result):
    """Wire db.query().filter().with_for_update().first() → result."""
    q = MagicMock()
    q.filter.return_value = q
    q.with_for_update.return_value = q
    q.first.return_value = result
    db.query.return_value = q
    return q


def _filter_first_q(db, result):
    """Wire db.query().filter().first() → result."""
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = result
    db.query.return_value = q
    return q


def _mock_assessment(status=SkillAssessmentState.ASSESSED, points_earned=7, points_total=10):
    a = MagicMock()
    a.status = status
    a.points_earned = points_earned
    a.points_total = points_total
    a.id = 1
    return a


# ===========================================================================
# create_assessment — validation-only paths (before DB/lock)
# ===========================================================================

@pytest.mark.unit
class TestCreateAssessmentValidation:
    def test_invalid_skill_name_raises_value_error(self):
        svc, db = _svc()
        with pytest.raises(ValueError, match="Invalid skill name"):
            svc.create_assessment(
                user_license_id=1,
                skill_name="not_a_real_skill",
                points_earned=5,
                points_total=10,
                assessed_by=99
            )
        db.query.assert_not_called()

    def test_negative_points_earned_raises_value_error(self):
        svc, db = _svc()
        with pytest.raises(ValueError, match="cannot be negative"):
            svc.create_assessment(
                user_license_id=1,
                skill_name=VALID_SKILL,
                points_earned=-1,
                points_total=10,
                assessed_by=99
            )
        db.query.assert_not_called()

    def test_zero_points_total_raises_value_error(self):
        svc, db = _svc()
        with pytest.raises(ValueError, match="must be greater than 0"):
            svc.create_assessment(
                user_license_id=1,
                skill_name=VALID_SKILL,
                points_earned=0,
                points_total=0,
                assessed_by=99
            )
        db.query.assert_not_called()

    def test_points_earned_exceeds_total_raises_value_error(self):
        svc, db = _svc()
        with pytest.raises(ValueError, match="cannot exceed total points"):
            svc.create_assessment(
                user_license_id=1,
                skill_name=VALID_SKILL,
                points_earned=11,
                points_total=10,
                assessed_by=99
            )
        db.query.assert_not_called()


# ===========================================================================
# validate_assessment
# ===========================================================================

@pytest.mark.unit
class TestValidateAssessment:
    def test_assessment_not_found_raises_value_error(self):
        svc, db = _svc()
        _wfu_q(db, None)
        with pytest.raises(ValueError, match="not found"):
            svc.validate_assessment(assessment_id=99, validated_by=1)

    def test_already_validated_returns_idempotent(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.VALIDATED)
        _wfu_q(db, assessment)
        result = svc.validate_assessment(assessment_id=1, validated_by=1)
        assert result is assessment
        # Status should remain VALIDATED (idempotent)
        assert assessment.status == SkillAssessmentState.VALIDATED

    def test_invalid_transition_archived_to_validated_raises(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.ARCHIVED)
        _wfu_q(db, assessment)
        with pytest.raises(ValueError, match="Invalid state transition"):
            svc.validate_assessment(assessment_id=1, validated_by=1)

    def test_happy_path_assessed_to_validated(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.ASSESSED)
        assessment.previous_status = None
        _wfu_q(db, assessment)
        result = svc.validate_assessment(assessment_id=1, validated_by=42)
        assert result is assessment
        assert assessment.status == SkillAssessmentState.VALIDATED
        assert assessment.validated_by == 42
        db.flush.assert_called_once()


# ===========================================================================
# archive_assessment
# ===========================================================================

@pytest.mark.unit
class TestArchiveAssessment:
    def test_assessment_not_found_raises_value_error(self):
        svc, db = _svc()
        _wfu_q(db, None)
        with pytest.raises(ValueError, match="not found"):
            svc.archive_assessment(assessment_id=99, archived_by=1, reason="test")

    def test_already_archived_returns_idempotent(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.ARCHIVED)
        _wfu_q(db, assessment)
        result = svc.archive_assessment(assessment_id=1, archived_by=1, reason="no-op")
        assert result is assessment
        assert assessment.status == SkillAssessmentState.ARCHIVED

    def test_invalid_transition_not_assessed_to_archived_raises(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.NOT_ASSESSED)
        _wfu_q(db, assessment)
        with pytest.raises(ValueError, match="Invalid state transition"):
            svc.archive_assessment(assessment_id=1, archived_by=1, reason="test")

    def test_happy_path_assessed_to_archived(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.ASSESSED)
        assessment.previous_status = None
        _wfu_q(db, assessment)
        result = svc.archive_assessment(assessment_id=1, archived_by=7, reason="Replaced")
        assert result is assessment
        assert assessment.status == SkillAssessmentState.ARCHIVED
        assert assessment.archived_by == 7
        assert assessment.archived_reason == "Replaced"
        db.flush.assert_called_once()

    def test_happy_path_validated_to_archived(self):
        svc, db = _svc()
        assessment = _mock_assessment(status=SkillAssessmentState.VALIDATED)
        assessment.previous_status = None
        _wfu_q(db, assessment)
        result = svc.archive_assessment(assessment_id=2, archived_by=3, reason="Superseded")
        assert result is assessment
        assert assessment.status == SkillAssessmentState.ARCHIVED


# ===========================================================================
# recalculate_skill_average — early return path (no lock needed)
# ===========================================================================

@pytest.mark.unit
class TestRecalculateSkillAverage:
    def test_no_assessments_returns_zero(self):
        svc, db = _svc()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = []  # no assessments
        db.query.return_value = q
        result = svc.recalculate_skill_average(user_license_id=1, skill_name=VALID_SKILL)
        assert result == 0.0


# ===========================================================================
# get_current_averages
# ===========================================================================

@pytest.mark.unit
class TestGetCurrentAverages:
    def test_no_license_returns_all_zeros(self):
        svc, db = _svc()
        _filter_first_q(db, None)
        result = svc.get_current_averages(user_license_id=1)
        assert isinstance(result, dict)
        assert all(v == 0.0 for v in result.values())
        assert len(result) > 0

    def test_license_no_football_skills_returns_all_zeros(self):
        svc, db = _svc()
        license = MagicMock()
        license.football_skills = None
        _filter_first_q(db, license)
        result = svc.get_current_averages(user_license_id=1)
        assert all(v == 0.0 for v in result.values())

    def test_license_with_scalar_skills_returns_values(self):
        svc, db = _svc()
        license = MagicMock()
        license.football_skills = {VALID_SKILL: 75.0, ANOTHER_VALID_SKILL: 80.0}
        _filter_first_q(db, license)
        result = svc.get_current_averages(user_license_id=1)
        assert result[VALID_SKILL] == 75.0
        assert result[ANOTHER_VALID_SKILL] == 80.0

    def test_missing_skill_defaults_to_zero(self):
        svc, db = _svc()
        license = MagicMock()
        license.football_skills = {VALID_SKILL: 60.0}  # only one skill set
        _filter_first_q(db, license)
        result = svc.get_current_averages(user_license_id=1)
        assert result[VALID_SKILL] == 60.0
        missing = [v for k, v in result.items() if k != VALID_SKILL]
        assert all(v == 0.0 for v in missing)


# ===========================================================================
# get_assessment_counts
# ===========================================================================

@pytest.mark.unit
class TestGetAssessmentCounts:
    def test_counts_per_skill(self):
        svc, db = _svc()
        q = MagicMock()
        q.filter.return_value = q
        q.scalar.return_value = 3
        db.query.return_value = q
        result = svc.get_assessment_counts(user_license_id=1)
        assert isinstance(result, dict)
        assert all(v == 3 for v in result.values())
        assert len(result) == len(get_all_skill_keys())

    def test_none_scalar_defaults_to_zero(self):
        svc, db = _svc()
        q = MagicMock()
        q.filter.return_value = q
        q.scalar.return_value = None
        db.query.return_value = q
        result = svc.get_assessment_counts(user_license_id=1)
        assert all(v == 0 for v in result.values())
