"""
Unit tests for app/api/helpers/spec_validation.py
Covers: validate_can_book_session, validate_user_age_for_specialization,
        get_user_enrollment_requirements, get_user_progression_status,
        check_specialization_type — all 10 branches.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.helpers.spec_validation import (
    validate_can_book_session,
    validate_user_age_for_specialization,
    get_user_enrollment_requirements,
    get_user_progression_status,
    check_specialization_type,
)

_PATCH = "app.api.helpers.spec_validation.get_spec_service"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user():
    u = MagicMock()
    u.id = 42
    return u


def _session(accessible_to_all=False, target_spec="GANCUJU_PLAYER"):
    s = MagicMock()
    s.is_accessible_to_all = accessible_to_all
    s.target_specialization = MagicMock()
    s.target_specialization.value = target_spec
    return s


def _license(spec_type="GANCUJU_PLAYER"):
    lic = MagicMock()
    lic.specialization_type = spec_type
    return lic


def _spec_service(session_based=True, semester_based=False, can_book=True,
                  book_reason="OK", age_eligible=True, age_reason="OK"):
    svc = MagicMock()
    svc.is_session_based.return_value = session_based
    svc.is_semester_based.return_value = semester_based
    svc.can_book_session.return_value = (can_book, book_reason)
    svc.validate_age_eligibility.return_value = (age_eligible, age_reason)
    svc.get_enrollment_requirements.return_value = {"can_participate": True}
    svc.get_progression_status.return_value = {"level": 3}
    return svc


# ---------------------------------------------------------------------------
# validate_can_book_session
# ---------------------------------------------------------------------------

class TestValidateCanBookSession:

    def test_vcb01_accessible_to_all_returns_true(self):
        """VCB-01: session.is_accessible_to_all=True → (True, ...) immediately."""
        s = _session(accessible_to_all=True)
        result = validate_can_book_session(_user(), s, MagicMock())
        assert result[0] is True

    def test_vcb02_unknown_spec_raises_500(self):
        """VCB-02: get_spec_service raises ValueError → HTTPException 500."""
        s = _session(accessible_to_all=False)
        with patch(_PATCH, side_effect=ValueError("unknown")):
            with pytest.raises(HTTPException) as exc:
                validate_can_book_session(_user(), s, MagicMock())
        assert exc.value.status_code == 500

    def test_vcb03_can_book_true_returns_true(self):
        """VCB-03: spec_service.can_book_session → True → (True, reason)."""
        s = _session(accessible_to_all=False)
        svc = _spec_service(can_book=True, book_reason="All good")
        with patch(_PATCH, return_value=svc):
            ok, reason = validate_can_book_session(_user(), s, MagicMock())
        assert ok is True
        assert reason == "All good"

    def test_vcb04_can_book_false_returns_false(self):
        """VCB-04: can_book=False → (False, reason)."""
        s = _session(accessible_to_all=False)
        svc = _spec_service(can_book=False, book_reason="Payment required")
        with patch(_PATCH, return_value=svc):
            ok, reason = validate_can_book_session(_user(), s, MagicMock())
        assert ok is False
        assert reason == "Payment required"


# ---------------------------------------------------------------------------
# validate_user_age_for_specialization
# ---------------------------------------------------------------------------

class TestValidateUserAgeForSpecialization:

    def test_vuaf01_unknown_spec_raises_400(self):
        """VUAF-01: get_spec_service raises ValueError → HTTPException 400."""
        with patch(_PATCH, side_effect=ValueError("unknown")):
            with pytest.raises(HTTPException) as exc:
                validate_user_age_for_specialization(_user(), "INVALID_SPEC")
        assert exc.value.status_code == 400

    def test_vuaf02_eligible_returns_tuple(self):
        """VUAF-02: age check passes → (True, reason)."""
        svc = _spec_service(age_eligible=True, age_reason="Eligible")
        with patch(_PATCH, return_value=svc):
            ok, reason = validate_user_age_for_specialization(
                _user(), "GANCUJU_PLAYER", target_group="BEGINNER"
            )
        assert ok is True
        assert reason == "Eligible"

    def test_vuaf03_not_eligible_returns_tuple(self):
        """VUAF-03: age check fails → (False, reason)."""
        svc = _spec_service(age_eligible=False, age_reason="Too young")
        with patch(_PATCH, return_value=svc):
            ok, reason = validate_user_age_for_specialization(_user(), "GANCUJU_PLAYER")
        assert ok is False
        assert reason == "Too young"


# ---------------------------------------------------------------------------
# get_user_enrollment_requirements
# ---------------------------------------------------------------------------

class TestGetUserEnrollmentRequirements:

    def test_guer01_unknown_spec_raises_400(self):
        """GUER-01: get_spec_service raises ValueError → HTTPException 400."""
        with patch(_PATCH, side_effect=ValueError("unknown")):
            with pytest.raises(HTTPException) as exc:
                get_user_enrollment_requirements(_user(), "INVALID", MagicMock())
        assert exc.value.status_code == 400

    def test_guer02_returns_requirements_dict(self):
        """GUER-02: spec service found → returns requirements dict."""
        svc = _spec_service()
        svc.get_enrollment_requirements.return_value = {"can_participate": True, "missing": []}
        with patch(_PATCH, return_value=svc):
            result = get_user_enrollment_requirements(_user(), "GANCUJU_PLAYER", MagicMock())
        assert result["can_participate"] is True


# ---------------------------------------------------------------------------
# get_user_progression_status
# ---------------------------------------------------------------------------

class TestGetUserProgressionStatus:

    def test_gups01_no_spec_type_raises_400(self):
        """GUPS-01: license has no spec type → HTTPException 400."""
        lic = _license(spec_type=None)
        with pytest.raises(HTTPException) as exc:
            get_user_progression_status(lic, MagicMock())
        assert exc.value.status_code == 400
        assert "specialization type" in exc.value.detail.lower()

    def test_gups02_unknown_spec_type_raises_500(self):
        """GUPS-02: get_spec_service raises ValueError → HTTPException 500."""
        lic = _license(spec_type="UNKNOWN_SPEC")
        with patch(_PATCH, side_effect=ValueError("unknown")):
            with pytest.raises(HTTPException) as exc:
                get_user_progression_status(lic, MagicMock())
        assert exc.value.status_code == 500

    def test_gups03_valid_spec_returns_progression(self):
        """GUPS-03: valid license → spec service returns progression dict."""
        lic = _license(spec_type="GANCUJU_PLAYER")
        svc = _spec_service()
        svc.get_progression_status.return_value = {"level": 3, "xp": 500}
        with patch(_PATCH, return_value=svc):
            result = get_user_progression_status(lic, MagicMock())
        assert result["level"] == 3


# ---------------------------------------------------------------------------
# check_specialization_type
# ---------------------------------------------------------------------------

class TestCheckSpecializationType:

    def test_cst01_session_based(self):
        """CST-01: spec service is_session_based=True → 'session_based'."""
        svc = _spec_service(session_based=True, semester_based=False)
        with patch(_PATCH, return_value=svc):
            ok, service_type = check_specialization_type("LFA_PLAYER_PRE")
        assert ok is True
        assert service_type == "session_based"

    def test_cst02_semester_based(self):
        """CST-02: is_session_based=False, is_semester_based=True → 'semester_based'."""
        svc = _spec_service(session_based=False, semester_based=True)
        with patch(_PATCH, return_value=svc):
            ok, service_type = check_specialization_type("GANCUJU_PLAYER")
        assert ok is True
        assert service_type == "semester_based"

    def test_cst03_neither_returns_unknown(self):
        """CST-03: is_session_based=False, is_semester_based=False → 'unknown' (valid but unusual)."""
        svc = _spec_service(session_based=False, semester_based=False)
        with patch(_PATCH, return_value=svc):
            ok, service_type = check_specialization_type("WEIRD_TYPE")
        assert ok is True
        assert service_type == "unknown"

    def test_cst04_invalid_type_returns_false(self):
        """CST-04: get_spec_service raises ValueError → (False, 'unknown')."""
        with patch(_PATCH, side_effect=ValueError("unknown")):
            ok, service_type = check_specialization_type("TOTALLY_INVALID")
        assert ok is False
        assert service_type == "unknown"
