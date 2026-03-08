"""
Unit tests for app/api/api_v1/endpoints/spec_info.py
Covers: get_enrollment_requirements_for_user, get_progression_for_license,
        check_can_book_session, check_age_eligibility, list_specialization_types
All 18 branches exercised.
All endpoints are sync — called directly.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from fastapi import HTTPException

from app.api.api_v1.endpoints.spec_info import (
    get_enrollment_requirements_for_user,
    get_progression_for_license,
    check_can_book_session,
    check_age_eligibility,
    list_specialization_types,
)

_BASE = "app.api.api_v1.endpoints.spec_info"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(role="admin", uid=42, dob=None):
    u = MagicMock()
    u.id = uid
    u.role = MagicMock()
    u.role.value = role
    u.date_of_birth = dob
    return u


def _db_license(license=None):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = license
    db.query.return_value = q
    return db


def _license(user_id=42, spec_type="GANCUJU_PLAYER"):
    lic = MagicMock()
    lic.user_id = user_id
    lic.specialization_type = spec_type
    return lic


def _db_session(session=None):
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = session
    db.query.return_value = q
    return db


def _session_mock(session_id=1, spec="GANCUJU_PLAYER"):
    s = MagicMock()
    s.id = session_id
    s.name = "Test Session"
    s.specialization_type = spec
    return s


# ---------------------------------------------------------------------------
# get_enrollment_requirements_for_user
# ---------------------------------------------------------------------------

class TestGetEnrollmentRequirements:

    def test_ger01_invalid_spec_type_400(self):
        """GER-01: unknown specialization_type → 400 (from check_specialization_type)."""
        with patch(f"{_BASE}.check_specialization_type", return_value=(False, "unknown")):
            with pytest.raises(HTTPException) as exc:
                get_enrollment_requirements_for_user(
                    specialization_type="INVALID_TYPE",
                    db=MagicMock(),
                    current_user=_user(),
                )
        assert exc.value.status_code == 400
        assert "unknown specialization type" in exc.value.detail.lower()

    def test_ger02_valid_spec_returns_requirements(self):
        """GER-02: valid spec → requirements dict merged into response."""
        with patch(f"{_BASE}.check_specialization_type", return_value=(True, "semester_based")), \
             patch(f"{_BASE}.get_user_enrollment_requirements",
                   return_value={"can_participate": True, "missing_requirements": []}):
            result = get_enrollment_requirements_for_user(
                specialization_type="GANCUJU_PLAYER",
                db=MagicMock(),
                current_user=_user(),
            )
        assert result["specialization_type"] == "GANCUJU_PLAYER"
        assert result["service_type"] == "semester_based"
        assert result["can_participate"] is True


# ---------------------------------------------------------------------------
# get_progression_for_license
# ---------------------------------------------------------------------------

class TestGetProgressionForLicense:

    def test_gpl01_license_not_found_404(self):
        """GPL-01: license not in DB → 404."""
        db = _db_license(license=None)
        with pytest.raises(HTTPException) as exc:
            get_progression_for_license(
                license_id=999, db=db, current_user=_user()
            )
        assert exc.value.status_code == 404
        assert "999" in exc.value.detail

    def test_gpl02_student_viewing_own_license(self):
        """GPL-02: student views own license → allowed."""
        lic = _license(user_id=42, spec_type="GANCUJU_PLAYER")
        db = _db_license(license=lic)
        u = _user(role="student", uid=42)
        with patch(f"{_BASE}.get_user_progression_status",
                   return_value={"level": 2}), \
             patch(f"{_BASE}.check_specialization_type",
                   return_value=(True, "semester_based")):
            result = get_progression_for_license(
                license_id=5, db=db, current_user=u
            )
        assert result["license_id"] == 5
        assert result["level"] == 2

    def test_gpl03_student_viewing_other_license_403(self):
        """GPL-03: student tries to view another user's license → 403."""
        lic = _license(user_id=99, spec_type="GANCUJU_PLAYER")
        db = _db_license(license=lic)
        u = _user(role="student", uid=42)
        with pytest.raises(HTTPException) as exc:
            get_progression_for_license(
                license_id=5, db=db, current_user=u
            )
        assert exc.value.status_code == 403
        assert "own" in exc.value.detail.lower()

    def test_gpl04_admin_viewing_any_license(self):
        """GPL-04: admin can view any license regardless of user_id."""
        lic = _license(user_id=99, spec_type="GANCUJU_PLAYER")
        db = _db_license(license=lic)
        u = _user(role="admin", uid=1)
        with patch(f"{_BASE}.get_user_progression_status",
                   return_value={"level": 5}), \
             patch(f"{_BASE}.check_specialization_type",
                   return_value=(True, "semester_based")):
            result = get_progression_for_license(
                license_id=5, db=db, current_user=u
            )
        assert result["user_id"] == 99


# ---------------------------------------------------------------------------
# check_can_book_session
# ---------------------------------------------------------------------------

class TestCheckCanBookSession:

    def test_ccbs01_session_not_found_404(self):
        """CCBS-01: session not in DB → 404."""
        db = _db_session(session=None)
        with pytest.raises(HTTPException) as exc:
            check_can_book_session(
                session_id=999, db=db, current_user=_user()
            )
        assert exc.value.status_code == 404
        assert "999" in exc.value.detail

    def test_ccbs02_can_book_true(self):
        """CCBS-02: validate_can_book_session → True."""
        s = _session_mock(session_id=7, spec="GANCUJU_PLAYER")
        db = _db_session(session=s)
        with patch(f"{_BASE}.validate_can_book_session",
                   return_value=(True, "Booking allowed")), \
             patch(f"{_BASE}.check_specialization_type",
                   return_value=(True, "semester_based")):
            result = check_can_book_session(
                session_id=7, db=db, current_user=_user()
            )
        assert result["session_id"] == 7
        assert result["can_book"] is True
        assert result["reason"] == "Booking allowed"

    def test_ccbs03_can_book_false(self):
        """CCBS-03: validate_can_book_session → False."""
        s = _session_mock(session_id=8, spec="GANCUJU_PLAYER")
        db = _db_session(session=s)
        with patch(f"{_BASE}.validate_can_book_session",
                   return_value=(False, "Payment required")), \
             patch(f"{_BASE}.check_specialization_type",
                   return_value=(True, "semester_based")):
            result = check_can_book_session(
                session_id=8, db=db, current_user=_user()
            )
        assert result["can_book"] is False
        assert result["reason"] == "Payment required"


# ---------------------------------------------------------------------------
# check_age_eligibility
# ---------------------------------------------------------------------------

class TestCheckAgeEligibility:

    def test_cae01_invalid_spec_type_400(self):
        """CAE-01: unknown spec → 400."""
        with patch(f"{_BASE}.check_specialization_type", return_value=(False, "unknown")):
            with pytest.raises(HTTPException) as exc:
                check_age_eligibility(
                    specialization_type="INVALID",
                    target_group=None,
                    db=MagicMock(),
                    current_user=_user(),
                )
        assert exc.value.status_code == 400

    def test_cae02_eligible_no_dob(self):
        """CAE-02: user has no date_of_birth → user_age=None."""
        u = _user(dob=None)
        with patch(f"{_BASE}.check_specialization_type", return_value=(True, "session_based")), \
             patch(f"{_BASE}.validate_user_age_for_specialization",
                   return_value=(True, "Eligible")):
            result = check_age_eligibility(
                specialization_type="LFA_PLAYER_PRE",
                target_group=None,
                db=MagicMock(),
                current_user=u,
            )
        assert result["user_age"] is None
        assert result["is_eligible"] is True

    def test_cae03_eligible_with_dob(self):
        """CAE-03: user has date_of_birth → user_age calculated."""
        dob = date(2000, 1, 1)
        u = _user(dob=dob)
        with patch(f"{_BASE}.check_specialization_type", return_value=(True, "session_based")), \
             patch(f"{_BASE}.validate_user_age_for_specialization",
                   return_value=(True, "Eligible")):
            result = check_age_eligibility(
                specialization_type="LFA_PLAYER_PRE",
                target_group=None,
                db=MagicMock(),
                current_user=u,
            )
        assert result["user_age"] is not None
        assert result["user_age"] >= 25  # born 2000, today is 2026

    def test_cae04_with_target_group(self):
        """CAE-04: target_group passed through → reflected in response."""
        u = _user(dob=None)
        with patch(f"{_BASE}.check_specialization_type", return_value=(True, "semester_based")), \
             patch(f"{_BASE}.validate_user_age_for_specialization",
                   return_value=(False, "Too young")):
            result = check_age_eligibility(
                specialization_type="GANCUJU_PLAYER",
                target_group="ADVANCED",
                db=MagicMock(),
                current_user=u,
            )
        assert result["target_group"] == "ADVANCED"
        assert result["is_eligible"] is False


# ---------------------------------------------------------------------------
# list_specialization_types
# ---------------------------------------------------------------------------

class TestListSpecializationTypes:

    def test_lst01_returns_all_known_types(self):
        """LST-01: no args — returns specializations dict with total_count."""
        def _fake_check(spec):
            return (True, "session_based")

        with patch(f"{_BASE}.check_specialization_type", side_effect=_fake_check):
            result = list_specialization_types()

        assert "specializations" in result
        assert "total_count" in result
        assert result["total_count"] == len(result["specializations"])

    def test_lst02_invalid_types_excluded(self):
        """LST-02: if a prefix returns is_valid=False, it's excluded."""
        def _fake_check(spec):
            if spec == "LFA_PLAYER":
                return (False, "unknown")
            return (True, "semester_based")

        with patch(f"{_BASE}.check_specialization_type", side_effect=_fake_check):
            result = list_specialization_types()

        assert "LFA_PLAYER" not in result["specializations"]
