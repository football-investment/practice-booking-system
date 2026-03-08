"""
Unit tests for app/models/semester_enrollment.py

Branch coverage targets:
  to_dict():
    - payment_verified_at / enrolled_at / deactivated_at / created_at / updated_at
      each: datetime present → isoformat() vs None → None
  specialization_type property:
    - user_license present vs None
  payment_status_display:
    - payment_verified True vs False
  status_display:
    - PENDING / REJECTED / WITHDRAWN
    - APPROVED + is_active=False
    - APPROVED + is_active=True + payment_verified=True
    - APPROVED + is_active=True + payment_verified=False
    - unknown status (unreachable in prod, tests defensive branch)
  generate_payment_code():
    - known spec_type (LFA_FOOTBALL_PLAYER → LFP)
    - unknown spec_type (→ UNK)
    - no semester (→ fallback "S{semester_id}")
    - semester with Spring name → {year}S1
    - semester with Fall name  → {year}S2
    - semester with year but no Spring/Fall → {year}S{semester_id}
    - semester with no year match → fallback code
  set_payment_code():
    - code not yet set → generates and stores
    - code already set → returns existing
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrollment(**overrides):
    """Build a transient SemesterEnrollment with safe defaults."""
    e = SemesterEnrollment()
    e.id = 1
    e.user_id = 42
    e.semester_id = 5
    e.user_license_id = 10
    e.payment_verified = False
    e.payment_verified_at = None
    e.payment_verified_by = None
    e.is_active = False
    e.enrolled_at = None
    e.deactivated_at = None
    e.created_at = None
    e.updated_at = None
    e.request_status = EnrollmentStatus.PENDING
    e.user_license = None
    e.semester = None
    e.payment_reference_code = None
    for k, v in overrides.items():
        setattr(e, k, v)
    return e


_DT = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# to_dict()
# ============================================================================

class TestToDict:

    def test_all_datetime_fields_none(self):
        e = _enrollment()
        d = e.to_dict()
        assert d["payment_verified_at"] is None
        assert d["enrolled_at"] is None
        assert d["deactivated_at"] is None
        assert d["created_at"] is None
        assert d["updated_at"] is None

    def test_all_datetime_fields_set(self):
        e = _enrollment(
            payment_verified_at=_DT,
            enrolled_at=_DT,
            deactivated_at=_DT,
            created_at=_DT,
            updated_at=_DT,
        )
        d = e.to_dict()
        assert d["payment_verified_at"] == _DT.isoformat()
        assert d["enrolled_at"] == _DT.isoformat()
        assert d["deactivated_at"] == _DT.isoformat()
        assert d["created_at"] == _DT.isoformat()
        assert d["updated_at"] == _DT.isoformat()

    def test_mixed_datetimes(self):
        e = _enrollment(payment_verified_at=_DT, enrolled_at=None)
        d = e.to_dict()
        assert d["payment_verified_at"] == _DT.isoformat()
        assert d["enrolled_at"] is None

    def test_core_fields_present(self):
        e = _enrollment()
        d = e.to_dict()
        assert d["id"] == 1
        assert d["user_id"] == 42
        assert d["semester_id"] == 5


# ============================================================================
# specialization_type property
# ============================================================================

class TestSpecializationType:

    def test_no_license_returns_none(self):
        e = _enrollment(user_license=None)
        assert e.specialization_type is None

    def test_with_license_returns_spec_type(self):
        lic = MagicMock()
        lic.specialization_type = "LFA_FOOTBALL_PLAYER"
        e = _enrollment(user_license=lic)
        assert e.specialization_type == "LFA_FOOTBALL_PLAYER"


# ============================================================================
# payment_status_display property
# ============================================================================

class TestPaymentStatusDisplay:

    def test_not_paid(self):
        e = _enrollment(payment_verified=False)
        display = e.payment_status_display
        assert "Not Paid" in display or "❌" in display

    def test_paid(self):
        e = _enrollment(payment_verified=True)
        display = e.payment_status_display
        assert "Paid" in display


# ============================================================================
# status_display property
# ============================================================================

class TestStatusDisplay:

    def test_pending(self):
        e = _enrollment(request_status=EnrollmentStatus.PENDING)
        assert "Pending" in e.status_display

    def test_rejected(self):
        e = _enrollment(request_status=EnrollmentStatus.REJECTED)
        assert "Rejected" in e.status_display or "❌" in e.status_display

    def test_withdrawn(self):
        e = _enrollment(request_status=EnrollmentStatus.WITHDRAWN)
        assert "Withdrawn" in e.status_display or "🚫" in e.status_display

    def test_approved_inactive(self):
        e = _enrollment(request_status=EnrollmentStatus.APPROVED, is_active=False)
        assert "Inactive" in e.status_display or "🔒" in e.status_display

    def test_approved_active_paid(self):
        e = _enrollment(
            request_status=EnrollmentStatus.APPROVED,
            is_active=True,
            payment_verified=True,
        )
        assert "Paid" in e.status_display

    def test_approved_active_unpaid(self):
        e = _enrollment(
            request_status=EnrollmentStatus.APPROVED,
            is_active=True,
            payment_verified=False,
        )
        assert "Unpaid" in e.status_display or "⚠️" in e.status_display

    def test_unknown_status_returns_unknown(self):
        e = _enrollment()
        e.request_status = "NOT_AN_ENUM"  # falls through all elif branches
        assert "Unknown" in e.status_display or "❓" in e.status_display


# ============================================================================
# generate_payment_code()
# ============================================================================

class TestGeneratePaymentCode:

    def _make(self, spec_type=None, semester=None):
        """Build enrollment with optional spec type and semester."""
        lic = None
        if spec_type is not None:
            lic = MagicMock()
            lic.specialization_type = spec_type
        return _enrollment(user_license=lic, semester=semester)

    def test_known_spec_lfa_football_player(self):
        e = self._make(spec_type="LFA_FOOTBALL_PLAYER")
        code = e.generate_payment_code()
        assert "LFP" in code
        assert code.startswith("LFA-")

    def test_known_spec_internship(self):
        e = self._make(spec_type="INTERNSHIP")
        code = e.generate_payment_code()
        assert "INT" in code

    def test_known_spec_lfa_coach(self):
        e = self._make(spec_type="LFA_COACH")
        assert "LFC" in e.generate_payment_code()

    def test_unknown_spec_uses_unk(self):
        e = self._make(spec_type="SOMETHING_ELSE")
        assert "UNK" in e.generate_payment_code()

    def test_no_license_gives_unk(self):
        e = _enrollment(user_license=None, semester=None)
        assert "UNK" in e.generate_payment_code()

    def test_no_semester_uses_fallback_code(self):
        e = self._make(spec_type=None, semester=None)
        code = e.generate_payment_code()
        assert f"S{e.semester_id}" in code

    def test_spring_semester_gives_s1(self):
        sem = MagicMock()
        sem.name = "Spring 2024"
        e = self._make(spec_type=None, semester=sem)
        assert "2024S1" in e.generate_payment_code()

    def test_fall_semester_gives_s2(self):
        sem = MagicMock()
        sem.name = "Fall 2024"
        e = self._make(spec_type=None, semester=sem)
        assert "2024S2" in e.generate_payment_code()

    def test_other_named_semester_with_year(self):
        sem = MagicMock()
        sem.name = "Summer 2025"
        e = self._make(spec_type=None, semester=sem)
        code = e.generate_payment_code()
        assert "2025" in code

    def test_semester_name_no_year_uses_fallback(self):
        sem = MagicMock()
        sem.name = "Current Term"  # no 4-digit year
        e = self._make(spec_type=None, semester=sem)
        code = e.generate_payment_code()
        assert code.startswith("LFA-")

    def test_semester_none_name(self):
        sem = MagicMock()
        sem.name = None
        e = self._make(spec_type=None, semester=sem)
        code = e.generate_payment_code()
        assert code.startswith("LFA-")


# ============================================================================
# set_payment_code()
# ============================================================================

class TestSetPaymentCode:

    def test_generates_and_stores_when_unset(self):
        e = _enrollment(payment_reference_code=None, user_license=None, semester=None)
        result = e.set_payment_code()
        assert result is not None
        assert result.startswith("LFA-")
        assert e.payment_reference_code == result

    def test_returns_existing_without_regenerating(self):
        e = _enrollment(payment_reference_code="LFA-EXISTING-S5-042-ABCD")
        result = e.set_payment_code()
        assert result == "LFA-EXISTING-S5-042-ABCD"
        assert e.payment_reference_code == "LFA-EXISTING-S5-042-ABCD"
