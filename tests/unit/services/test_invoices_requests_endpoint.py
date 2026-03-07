"""
Unit tests for app/api/api_v1/endpoints/invoices/requests.py
Covers: create_invoice_request, list_invoices, get_invoice_count,
        get_financial_summary, get_my_invoices
Note: all endpoints are async → use asyncio.run()
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.invoices.requests import (
    create_invoice_request, list_invoices, get_invoice_count,
    get_financial_summary, get_my_invoices, InvoiceRequestCreate,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.invoices.requests"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None, all_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.group_by.return_value = q
    q.all.return_value = all_val if all_val is not None else []
    q.first.return_value = first_val
    q.one.return_value = MagicMock(total_balance=1000, total_purchased=900, users_with_balance=5)
    return q


def _user(uid=42, role=UserRole.STUDENT):
    u = MagicMock()
    u.id = uid
    u.name = "Student"
    u.email = "student@example.com"
    u.role = role
    return u


def _admin():
    return _user(uid=42, role=UserRole.ADMIN)


def _invoice_data(credit=100, eur=10.0, coupon=None):
    return InvoiceRequestCreate(credit_amount=credit, amount_eur=eur, coupon_code=coupon)


def _invoice_mock(iid=1, uid=42):
    inv = MagicMock()
    inv.id = iid
    inv.user_id = uid
    inv.credit_amount = 100
    inv.amount_eur = 10.0
    inv.coupon_code = None
    inv.payment_reference = "123456"
    inv.status = "pending"
    inv.created_at = MagicMock()
    inv.verified_at = None
    return inv


def _request():
    return MagicMock()


# ---------------------------------------------------------------------------
# create_invoice_request
# ---------------------------------------------------------------------------

class TestCreateInvoiceRequest:
    def _call(self, data=None, db=None, current_user=None):
        return asyncio.run(create_invoice_request(
            invoice_data=data or _invoice_data(),
            db=db or MagicMock(),
            current_user=current_user or _user(),
        ))

    def test_negative_credit_400(self):
        """CIR-01: credit_amount <= 0 → 400."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            self._call(data=_invoice_data(credit=0))
        assert exc.value.status_code == 400

    def test_negative_eur_400(self):
        """CIR-02: amount_eur <= 0 → 400."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            self._call(data=_invoice_data(eur=0.0))
        assert exc.value.status_code == 400

    def test_invalid_coupon_400(self):
        """CIR-03: coupon found but not valid → 400."""
        from fastapi import HTTPException
        coupon = MagicMock()
        coupon.is_valid.return_value = False
        q = _q(first_val=None)  # For the payment_reference check
        db = MagicMock()
        db.query.return_value = _q(first_val=coupon)
        with pytest.raises(HTTPException) as exc:
            self._call(data=_invoice_data(coupon="BADCODE"), db=db)
        assert exc.value.status_code == 400

    def test_success_no_coupon(self):
        """CIR-04: valid request, no coupon → invoice created."""
        inv = _invoice_mock()
        db = MagicMock()
        db.query.return_value = _q(first_val=None)  # no duplicate reference
        with patch(f"{_BASE}.InvoiceRequest", return_value=inv):
            result = self._call(db=db)
        assert result["success"] is True
        db.add.assert_called()
        db.commit.assert_called_once()

    def test_success_with_valid_coupon(self):
        """CIR-05: valid coupon → usage incremented."""
        coupon = MagicMock()
        coupon.is_valid.return_value = True
        inv = _invoice_mock()
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = coupon  # coupon found
            else:
                q.first.return_value = None  # no duplicate ref
            return q
        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}.InvoiceRequest", return_value=inv):
            result = self._call(data=_invoice_data(coupon="VALID10"), db=db)
        coupon.increment_usage.assert_called_once()
        assert result["success"] is True

    def test_coupon_not_found_proceeds(self):
        """CIR-06: coupon code given but not found → no error, proceeds."""
        inv = _invoice_mock()
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = None  # coupon not found
            else:
                q.first.return_value = None  # no duplicate ref
            return q
        db = MagicMock()
        db.query.side_effect = qside
        with patch(f"{_BASE}.InvoiceRequest", return_value=inv):
            result = self._call(data=_invoice_data(coupon="MISSING"), db=db)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# list_invoices
# ---------------------------------------------------------------------------

class TestListInvoices:
    def _call(self, status_filter=None, limit=50, db=None, current_user=None):
        return asyncio.run(list_invoices(
            request=_request(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
            status=status_filter,
            limit=limit,
        ))

    def test_no_filter_returns_all(self):
        """LI-01: no status filter → all invoices."""
        invoices = [_invoice_mock(iid=1), _invoice_mock(iid=2)]
        student = _user()
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q(all_val=invoices if n == 0 else [])
            q.first.return_value = student
            return q
        db = MagicMock()
        db.query.side_effect = qside
        result = self._call(db=db)
        assert len(result) == 2

    def test_with_status_filter(self):
        """LI-02: status filter → filter applied."""
        invoices = [_invoice_mock()]
        student = _user()
        q = _q(all_val=invoices)
        q.first.return_value = student
        db = MagicMock()
        db.query.return_value = q
        result = self._call(status_filter="pending", db=db)
        assert len(result) == 1

    def test_student_not_found_shows_unknown(self):
        """LI-03: student not found → 'Unknown' in response."""
        invoices = [_invoice_mock()]
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.all.return_value = invoices
            else:
                q.first.return_value = None
            return q
        db = MagicMock()
        db.query.side_effect = qside
        result = self._call(db=db)
        assert result[0]["student_name"] == "Unknown"


# ---------------------------------------------------------------------------
# get_invoice_count
# ---------------------------------------------------------------------------

class TestGetInvoiceCount:
    def _call(self, db=None, current_user=None):
        return asyncio.run(get_invoice_count(
            request=_request(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        ))

    def test_empty_returns_zeros(self):
        """GIC-01: no invoices → all zeros."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result["total"] == 0

    def test_counts_by_status(self):
        """GIC-02: counts aggregated by status."""
        row1 = MagicMock()
        row1.status = "pending"
        row1.count = 3
        row2 = MagicMock()
        row2.status = "verified"
        row2.count = 1
        # Unpack as tuple for `for status, count in counts`
        rows = [("pending", 3), ("verified", 1)]
        q = _q(all_val=rows)
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result["pending"] == 3
        assert result["verified"] == 1
        assert result["total"] == 4


# ---------------------------------------------------------------------------
# get_financial_summary
# ---------------------------------------------------------------------------

class TestGetFinancialSummary:
    def _call(self, db=None, current_user=None):
        return asyncio.run(get_financial_summary(
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        ))

    def test_empty_db_returns_zeros(self):
        """GFS-01: no invoices → zeroed summary."""
        balance = MagicMock()
        balance.total_balance = 0
        balance.total_purchased = 0
        balance.users_with_balance = 0
        q = _q(all_val=[])
        q.one.return_value = balance
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result["revenue"]["total_eur"] == 0.0
        assert result["credits"]["active_balance"] == 0

    def test_with_data(self):
        """GFS-02: aggregated data returned correctly."""
        row1 = MagicMock()
        row1.status = "verified"
        row1.cnt = 5
        row1.eur_sum = 100.0
        row1.credit_sum = 500
        balance = MagicMock()
        balance.total_balance = 300
        balance.total_purchased = 500
        balance.users_with_balance = 3
        call_n = [0]
        def qside(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.all.return_value = [row1]
            else:
                q.one.return_value = balance
            return q
        db = MagicMock()
        db.query.side_effect = qside
        result = self._call(db=db)
        assert result["revenue"]["total_eur"] == 100.0
        assert result["invoices"]["total"] == 5


# ---------------------------------------------------------------------------
# get_my_invoices
# ---------------------------------------------------------------------------

class TestGetMyInvoices:
    def _call(self, db=None, current_user=None):
        return asyncio.run(get_my_invoices(
            db=db or MagicMock(),
            current_user=current_user or _user(),
        ))

    def test_empty_returns_empty_list(self):
        """GMI-01: no invoices → []."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result == []

    def test_returns_user_invoices(self):
        """GMI-02: invoices found → list returned."""
        inv = _invoice_mock()
        q = _q(all_val=[inv])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert len(result) == 1
        assert result[0]["credit_amount"] == 100
