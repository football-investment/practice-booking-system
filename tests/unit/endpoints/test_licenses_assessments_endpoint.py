"""
Unit tests for app/api/api_v1/endpoints/licenses/assessments.py.

Branch coverage targets (33.3% → ~90%):
  create_skill_assessment:
    - student role → 403
    - license not found → 404
    - non-LFA specialization → 400
    - skill_name empty or >50 chars → 400
    - created=True + requires_validation → message with note
    - created=True, no validation needed → message without note
    - created=False → idempotent message
    - ValueError → 400
    - Exception → 500 + rollback
  get_skill_assessment_history:
    - license not found → 404
    - student (not owner, not instructor) → 403
    - include_archived=False → filter by status
    - include_archived=True → no additional filter
  get_assessment:
    - assessment not found → 404
    - license not found → 404
    - permission check (student not owner) → 403
    - success (instructor bypasses ownership)
  validate_assessment:
    - student role → 403
    - ValueError → 400
    - Exception → 500 + rollback
    - success
  archive_assessment:
    - student role → 403
    - reason=None → default reason applied
    - ValueError → 400
    - Exception → 500 + rollback
    - success
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.licenses.assessments import (
    create_skill_assessment,
    get_skill_assessment_history,
    get_assessment,
    validate_assessment,
    archive_assessment,
    CreateAssessmentRequest,
)
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.football_skill_assessment import FootballSkillAssessment

_BASE = "app.api.api_v1.endpoints.licenses.assessments"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(role=UserRole.INSTRUCTOR, id_=10):
    u = MagicMock(spec=User)
    u.role = role
    u.id = id_
    return u


def _license(id_=1, specialization="LFA_PLAYER_BRONZE", user_id=42):
    lic = MagicMock(spec=UserLicense)
    lic.id = id_
    lic.specialization_type = specialization
    lic.user_id = user_id
    return lic


def _assessment(id_=1, user_license_id=42):
    a = MagicMock(spec=FootballSkillAssessment)
    a.id = id_
    a.user_license_id = user_license_id
    a.status = "ASSESSED"
    a.requires_validation = False
    return a


def _db_license_assessment(license=None, assessment=None):
    """Routes UserLicense → license query, FootballSkillAssessment → assessment query."""
    lic_q = MagicMock()
    lic_q.filter.return_value = lic_q
    lic_q.first.return_value = license

    ass_q = MagicMock()
    ass_q.filter.return_value = ass_q
    ass_q.order_by.return_value = ass_q
    ass_q.all.return_value = []
    ass_q.first.return_value = assessment

    db = MagicMock()
    db.query.side_effect = lambda model: lic_q if model is UserLicense else ass_q
    return db


def _mock_assessment_response():
    """Minimal mock for AssessmentResponse.from_orm."""
    return MagicMock()


# ---------------------------------------------------------------------------
# create_skill_assessment
# ---------------------------------------------------------------------------

class TestCreateSkillAssessment:

    def test_student_role_raises_403(self):
        db = _db_license_assessment()
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_skill_assessment(1, "ball_control", req,
                current_user=_user(role=UserRole.STUDENT), db=db))
        assert exc.value.status_code == 403

    def test_license_not_found_raises_404(self):
        db = _db_license_assessment(license=None)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_skill_assessment(1, "ball_control", req,
                current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_non_lfa_specialization_raises_400(self):
        lic = _license(specialization="COACH_LEVEL_1")  # not LFA_PLAYER_
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_skill_assessment(1, "ball_control", req,
                current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_empty_skill_name_raises_400(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_skill_assessment(1, "", req,
                current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_skill_name_too_long_raises_400(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_skill_assessment(1, "x" * 51, req,
                current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_created_true_requires_validation_message_has_note(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        mock_ass = _assessment()
        mock_ass.requires_validation = True
        # Patch CreateAssessmentResponse to bypass Pydantic v2 nested validation
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.CreateAssessmentResponse") as MockCreate:
            MockSvc.return_value.create_assessment.return_value = (mock_ass, True)
            MockAss.from_orm.return_value = MagicMock()
            MockCreate.return_value = MagicMock()
            asyncio.run(create_skill_assessment(1, "passing", req,
                current_user=_user(), db=db))
        # Verify message passed to response includes validation note
        call_kwargs = MockCreate.call_args.kwargs
        assert "requires admin validation" in call_kwargs["message"]
        assert call_kwargs["created"] is True

    def test_created_true_no_validation_message_no_note(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        mock_ass = _assessment()
        mock_ass.requires_validation = False
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.CreateAssessmentResponse") as MockCreate:
            MockSvc.return_value.create_assessment.return_value = (mock_ass, True)
            MockAss.from_orm.return_value = MagicMock()
            MockCreate.return_value = MagicMock()
            asyncio.run(create_skill_assessment(1, "passing", req,
                current_user=_user(), db=db))
        call_kwargs = MockCreate.call_args.kwargs
        assert "requires admin validation" not in call_kwargs["message"]
        assert call_kwargs["created"] is True

    def test_created_false_idempotent_message(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        mock_ass = _assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.CreateAssessmentResponse") as MockCreate:
            MockSvc.return_value.create_assessment.return_value = (mock_ass, False)
            MockAss.from_orm.return_value = MagicMock()
            MockCreate.return_value = MagicMock()
            asyncio.run(create_skill_assessment(1, "passing", req,
                current_user=_user(), db=db))
        call_kwargs = MockCreate.call_args.kwargs
        assert "idempotent" in call_kwargs["message"]
        assert call_kwargs["created"] is False

    def test_value_error_raises_400(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.create_assessment.side_effect = ValueError("bad state")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(create_skill_assessment(1, "passing", req,
                    current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_generic_exception_raises_500_and_rollback(self):
        lic = _license()
        db = _db_license_assessment(license=lic)
        req = CreateAssessmentRequest(points_earned=5, points_total=10)
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.create_assessment.side_effect = RuntimeError("db error")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(create_skill_assessment(1, "passing", req,
                    current_user=_user(), db=db))
        assert exc.value.status_code == 500
        db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# get_skill_assessment_history
# ---------------------------------------------------------------------------

class TestGetSkillAssessmentHistory:

    def test_license_not_found_raises_404(self):
        db = _db_license_assessment(license=None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_skill_assessment_history(1, "passing",
                include_archived=False, current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_student_not_owner_raises_403(self):
        lic = _license(user_id=99)  # owner is 99
        db = _db_license_assessment(license=lic)
        caller = _user(role=UserRole.STUDENT, id_=10)  # caller is 10 (not owner)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_skill_assessment_history(1, "passing",
                include_archived=False, current_user=caller, db=db))
        assert exc.value.status_code == 403

    def test_instructor_sees_any_license(self):
        lic = _license(user_id=99)  # different owner
        db = _db_license_assessment(license=lic)
        caller = _user(role=UserRole.INSTRUCTOR, id_=10)
        with patch(f"{_BASE}.AssessmentResponse"):
            result = asyncio.run(get_skill_assessment_history(1, "passing",
                include_archived=False, current_user=caller, db=db))
        assert result == []

    def test_include_archived_false_filters(self):
        lic = _license(user_id=10)
        ass_q = MagicMock()
        ass_q.filter.return_value = ass_q
        ass_q.order_by.return_value = ass_q
        ass_q.all.return_value = []
        lic_q = MagicMock()
        lic_q.filter.return_value = lic_q
        lic_q.first.return_value = lic
        db = MagicMock()
        db.query.side_effect = lambda model: lic_q if model is UserLicense else ass_q

        caller = _user(role=UserRole.INSTRUCTOR, id_=10)
        asyncio.run(get_skill_assessment_history(1, "passing",
            include_archived=False, current_user=caller, db=db))
        # filter() should be called at least twice (base filter + status filter)
        assert ass_q.filter.call_count >= 2

    def test_include_archived_true_no_status_filter(self):
        lic = _license(user_id=10)
        ass_q = MagicMock()
        ass_q.filter.return_value = ass_q
        ass_q.order_by.return_value = ass_q
        ass_q.all.return_value = []
        lic_q = MagicMock()
        lic_q.filter.return_value = lic_q
        lic_q.first.return_value = lic
        db = MagicMock()
        db.query.side_effect = lambda model: lic_q if model is UserLicense else ass_q

        caller = _user(role=UserRole.INSTRUCTOR, id_=10)
        asyncio.run(get_skill_assessment_history(1, "passing",
            include_archived=True, current_user=caller, db=db))
        # Only base filter called (not the status filter)
        assert ass_q.filter.call_count == 1


# ---------------------------------------------------------------------------
# get_assessment
# ---------------------------------------------------------------------------

class TestGetAssessment:

    def test_assessment_not_found_raises_404(self):
        db = _db_license_assessment(license=None, assessment=None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_assessment(1, current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_license_not_found_raises_404(self):
        ass = _assessment()
        # assessment found, license not found
        ass_q = MagicMock()
        ass_q.filter.return_value = ass_q
        ass_q.first.return_value = ass
        lic_q = MagicMock()
        lic_q.filter.return_value = lic_q
        lic_q.first.return_value = None
        db = MagicMock()
        db.query.side_effect = lambda model: ass_q if model is FootballSkillAssessment else lic_q
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_assessment(1, current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_student_not_owner_raises_403(self):
        ass = _assessment(user_license_id=42)
        lic = _license(user_id=99)  # owner is 99
        ass_q = MagicMock()
        ass_q.filter.return_value = ass_q
        ass_q.first.return_value = ass
        lic_q = MagicMock()
        lic_q.filter.return_value = lic_q
        lic_q.first.return_value = lic
        db = MagicMock()
        db.query.side_effect = lambda model: ass_q if model is FootballSkillAssessment else lic_q
        caller = _user(role=UserRole.STUDENT, id_=10)  # not owner (99)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_assessment(1, current_user=caller, db=db))
        assert exc.value.status_code == 403

    def test_instructor_success(self):
        ass = _assessment(user_license_id=42)
        lic = _license(user_id=99)
        ass_q = MagicMock()
        ass_q.filter.return_value = ass_q
        ass_q.first.return_value = ass
        lic_q = MagicMock()
        lic_q.filter.return_value = lic_q
        lic_q.first.return_value = lic
        db = MagicMock()
        db.query.side_effect = lambda model: ass_q if model is FootballSkillAssessment else lic_q
        with patch(f"{_BASE}.AssessmentResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            result = asyncio.run(get_assessment(1, current_user=_user(role=UserRole.INSTRUCTOR), db=db))
        assert result is not None


# ---------------------------------------------------------------------------
# validate_assessment
# ---------------------------------------------------------------------------

class TestValidateAssessment:

    def test_student_raises_403(self):
        db = _db_license_assessment()
        with pytest.raises(HTTPException) as exc:
            asyncio.run(validate_assessment(1, current_user=_user(role=UserRole.STUDENT), db=db))
        assert exc.value.status_code == 403

    def test_value_error_raises_400(self):
        db = _db_license_assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.validate_assessment.side_effect = ValueError("invalid transition")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(validate_assessment(1, current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_exception_raises_500_and_rollback(self):
        db = _db_license_assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.validate_assessment.side_effect = RuntimeError("db crash")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(validate_assessment(1, current_user=_user(), db=db))
        assert exc.value.status_code == 500
        db.rollback.assert_called_once()

    def test_success(self):
        db = _db_license_assessment()
        mock_ass = _assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.ValidateArchiveResponse") as MockValidate:
            MockSvc.return_value.validate_assessment.return_value = mock_ass
            MockAss.from_orm.return_value = MagicMock()
            MockValidate.return_value = MagicMock()
            asyncio.run(validate_assessment(1, current_user=_user(), db=db))
        call_kwargs = MockValidate.call_args.kwargs
        assert call_kwargs["success"] is True


# ---------------------------------------------------------------------------
# archive_assessment
# ---------------------------------------------------------------------------

class TestArchiveAssessment:

    def test_student_raises_403(self):
        db = _db_license_assessment()
        with pytest.raises(HTTPException) as exc:
            asyncio.run(archive_assessment(1, reason=None,
                current_user=_user(role=UserRole.STUDENT), db=db))
        assert exc.value.status_code == 403

    def test_none_reason_gets_default(self):
        db = _db_license_assessment()
        mock_ass = _assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.ValidateArchiveResponse") as MockValidate:
            MockSvc.return_value.archive_assessment.return_value = mock_ass
            MockAss.from_orm.return_value = MagicMock()
            MockValidate.return_value = MagicMock()
            asyncio.run(archive_assessment(1, reason=None, current_user=_user(), db=db))
        # default reason is used — verify via service call args
        svc_call = MockSvc.return_value.archive_assessment.call_args
        assert svc_call.kwargs["reason"] == "Manually archived by instructor"

    def test_value_error_raises_400(self):
        db = _db_license_assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.archive_assessment.side_effect = ValueError("not found")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(archive_assessment(1, reason="test",
                    current_user=_user(), db=db))
        assert exc.value.status_code == 400

    def test_exception_raises_500_and_rollback(self):
        db = _db_license_assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc:
            MockSvc.return_value.archive_assessment.side_effect = RuntimeError("crash")
            with pytest.raises(HTTPException) as exc:
                asyncio.run(archive_assessment(1, reason="test",
                    current_user=_user(), db=db))
        assert exc.value.status_code == 500
        db.rollback.assert_called_once()

    def test_success_with_reason(self):
        db = _db_license_assessment()
        mock_ass = _assessment()
        with patch(f"{_BASE}.FootballSkillService") as MockSvc, \
             patch(f"{_BASE}.AssessmentResponse") as MockAss, \
             patch(f"{_BASE}.ValidateArchiveResponse") as MockValidate:
            MockSvc.return_value.archive_assessment.return_value = mock_ass
            MockAss.from_orm.return_value = MagicMock()
            MockValidate.return_value = MagicMock()
            asyncio.run(archive_assessment(1, reason="Superseded", current_user=_user(), db=db))
        call_kwargs = MockValidate.call_args.kwargs
        assert call_kwargs["success"] is True
