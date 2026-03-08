"""
Unit tests for app/api/api_v1/endpoints/invoices/admin.py
Covers: verify_invoice_payment, cancel_invoice, unverify_invoice_payment
Note: endpoints are async → use asyncio.run()
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.invoices.admin import (
    verify_invoice_payment, cancel_invoice, unverify_invoice_payment,
    InvoiceCancellationRequest,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.invoices.admin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first_val
    return q


def _seq_db(*vals):
    call_n = [0]
    db = MagicMock()

    def side(*args):
        n = call_n[0]
        call_n[0] += 1
        v = vals[n] if n < len(vals) else None
        q = _q(first_val=v)
        return q

    db.query.side_effect = side
    return db


def _admin():
    u = MagicMock()
    u.id = 42
    u.name = "Admin User"
    u.role = UserRole.ADMIN
    return u


def _invoice(iid=1, status="pending", user_id=7, credit_amount=100):
    inv = MagicMock()
    inv.id = iid
    inv.status = status
    inv.user_id = user_id
    inv.credit_amount = credit_amount
    inv.payment_reference = "REF-001"
    inv.verified_at = None
    return inv


def _student(uid=7):
    s = MagicMock()
    s.id = uid
    s.name = "Student Name"
    s.email = "student@example.com"
    s.credit_balance = 0
    s.credit_purchased = 0
    return s


def _request():
    return MagicMock()


# ---------------------------------------------------------------------------
# verify_invoice_payment
# ---------------------------------------------------------------------------

class TestVerifyInvoicePayment:
    def _call(self, invoice_id=1, db=None, current_user=None):
        return asyncio.run(verify_invoice_payment(
            request=_request(),
            invoice_id=invoice_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        ))

    def test_invoice_not_found_404(self):
        """VIP-01: invoice not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_already_verified_400(self):
        """VIP-02: already verified → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="verified")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_cancelled_400(self):
        """VIP-03: cancelled invoice → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="cancelled")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_student_not_found_404(self):
        """VIP-04: student not found → 404."""
        from fastapi import HTTPException
        inv = _invoice(status="pending")
        db = _seq_db(inv, None)  # student not found
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_success_adds_credits(self):
        """VIP-05: success → credits added, status set to verified."""
        inv = _invoice(status="pending", credit_amount=100)
        student = _student()
        student.credit_balance = 50
        student.credit_purchased = 50
        db = _seq_db(inv, student)

        result = self._call(db=db)
        assert inv.status == "verified"
        assert student.credit_balance == 150
        assert student.credit_purchased == 150
        assert result["success"] is True
        assert result["credits_added"] == 100
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# cancel_invoice
# ---------------------------------------------------------------------------

class TestCancelInvoice:
    def _call(self, invoice_id=1, db=None, current_user=None, reason="test"):
        return asyncio.run(cancel_invoice(
            request=_request(),
            invoice_id=invoice_id,
            cancellation_request=InvoiceCancellationRequest(reason=reason),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        ))

    def test_invoice_not_found_404(self):
        """CI-01: invoice not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_verified_cannot_cancel_400(self):
        """CI-02: verified invoice → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="verified")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_already_cancelled_400(self):
        """CI-03: already cancelled → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="cancelled")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_student_not_found_404(self):
        """CI-04: student not found → 404."""
        from fastapi import HTTPException
        inv = _invoice(status="pending")
        db = _seq_db(inv, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_success_cancels_invoice(self):
        """CI-05: success → invoice marked cancelled."""
        inv = _invoice(status="pending")
        student = _student()
        db = _seq_db(inv, student)

        result = self._call(db=db, reason="Customer request")
        assert inv.status == "cancelled"
        assert result["success"] is True
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# unverify_invoice_payment
# ---------------------------------------------------------------------------

class TestUnverifyInvoicePayment:
    def _call(self, invoice_id=1, db=None, current_user=None):
        return asyncio.run(unverify_invoice_payment(
            request=_request(),
            invoice_id=invoice_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        ))

    def test_invoice_not_found_404(self):
        """UIV-01: invoice not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_already_pending_400(self):
        """UIV-02: already pending → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="pending")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_cancelled_400(self):
        """UIV-03: cancelled → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="cancelled")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_not_verified_400(self):
        """UIV-04: status not 'verified' (e.g. 'processing') → 400."""
        from fastapi import HTTPException
        inv = _invoice(status="processing")
        db = _seq_db(inv)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_student_not_found_404(self):
        """UIV-05: student not found → 404."""
        from fastapi import HTTPException
        inv = _invoice(status="verified")
        db = _seq_db(inv, None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_success_removes_credits(self):
        """UIV-06: success → credits removed, status back to pending."""
        inv = _invoice(status="verified", credit_amount=100)
        student = _student()
        student.credit_balance = 200
        student.credit_purchased = 200
        db = _seq_db(inv, student)

        result = self._call(db=db)
        assert inv.status == "pending"
        assert inv.verified_at is None
        assert student.credit_balance == 100
        assert student.credit_purchased == 100
        assert result["success"] is True
        assert result["credits_removed"] == 100
        db.commit.assert_called_once()
