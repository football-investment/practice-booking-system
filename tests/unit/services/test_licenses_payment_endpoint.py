"""
Unit tests for app/api/api_v1/endpoints/licenses/payment.py
Covers: verify_license_payment, unverify_license_payment
Note: success paths reference undeclared names (AuditService, datetime) in source —
      only the 404 and pre-condition 400 branches are tested here.
All endpoints are async → asyncio.run()
"""
import asyncio
import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.api_v1.endpoints.licenses.payment import (
    verify_license_payment,
    unverify_license_payment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _q(first_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first_val
    return q


def _license(payment_verified=False):
    lic = MagicMock()
    lic.payment_verified = payment_verified
    lic.payment_reference_code = "LFA-LICENSE-0001"
    lic.user_id = 99
    lic.specialization_type = "LFA_FOOTBALL_PLAYER"
    return lic


# ---------------------------------------------------------------------------
# verify_license_payment
# ---------------------------------------------------------------------------

class TestVerifyLicensePayment:

    def _call(self, license_id=1, db=None, admin_user=None):
        return asyncio.run(verify_license_payment(
            license_id=license_id,
            request=MagicMock(),
            db=db or MagicMock(),
            admin_user=admin_user or _admin(),
        ))

    def test_vlp01_not_found_404(self):
        """VLP-01: license not found → 404."""
        db = MagicMock()
        db.query.return_value = _q(first_val=None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404
        assert "License" in exc.value.detail

    def test_vlp02_already_verified_400(self):
        """VLP-02: payment already verified → 400 before any mutation."""
        lic = _license(payment_verified=True)
        db = MagicMock()
        db.query.return_value = _q(first_val=lic)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert "already" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# unverify_license_payment
# ---------------------------------------------------------------------------

class TestUnverifyLicensePayment:

    def _call(self, license_id=1, db=None, admin_user=None):
        return asyncio.run(unverify_license_payment(
            license_id=license_id,
            request=MagicMock(),
            db=db or MagicMock(),
            admin_user=admin_user or _admin(),
        ))

    def test_uvlp01_not_found_404(self):
        """UVLP-01: license not found → 404."""
        db = MagicMock()
        db.query.return_value = _q(first_val=None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_uvlp02_not_verified_400(self):
        """UVLP-02: payment_verified=False → 400 (nothing to unverify)."""
        lic = _license(payment_verified=False)
        db = MagicMock()
        db.query.return_value = _q(first_val=lic)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400
        assert "not verified" in exc.value.detail.lower()
