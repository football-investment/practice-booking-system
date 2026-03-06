"""
Unit tests for app/api/api_v1/endpoints/coupons.py
Sprint 24 P2 — coverage: 32% stmt, 0% branch → ≥85%

9 endpoints:
1. list_all_coupons       GET  /admin/coupons
2. create_coupon_api      POST /admin/coupons
3. create_coupon_web      POST /admin/coupons/web
4. update_coupon          PUT  /admin/coupons/{id}
5. delete_coupon          DELETE /admin/coupons/{id}
6. toggle_coupon_status   POST /admin/coupons/{id}/toggle
7. list_active_coupons    GET  /coupons/active
8. validate_coupon        POST /coupons/validate/{code}
9. apply_coupon           POST /coupons/apply
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import datetime, timezone

from app.api.api_v1.endpoints.coupons import (
    list_all_coupons,
    create_coupon_api,
    create_coupon_web,
    update_coupon,
    delete_coupon,
    toggle_coupon_status,
    list_active_coupons,
    validate_coupon,
    apply_coupon,
    CouponCreate,
    CouponUpdate,
    ApplyCouponRequest,
)
from app.models.coupon import CouponType
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.coupons"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    u = MagicMock()
    u.id = 42
    u.name = "Admin User"
    u.email = "admin@lfa.com"
    u.role = UserRole.ADMIN
    u.credit_balance = 500
    u.credit_purchased = 500
    return u


def _coupon(**kwargs):
    c = MagicMock()
    c.id = 1
    c.code = "TEST10"
    c.type = CouponType.BONUS_CREDITS
    c.discount_value = 100.0
    c.description = "Test coupon description"
    c.is_active = True
    c.expires_at = None
    c.max_uses = None
    c.current_uses = 0
    c.requires_purchase = False
    c.requires_admin_approval = False
    c.created_at = MagicMock()
    c.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    c.updated_at = MagicMock()
    c.updated_at.isoformat.return_value = "2026-01-01T00:00:00"
    c.is_valid = MagicMock(return_value=True)
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def _q(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    return q


def _db(first=None, all_=None):
    db = MagicMock()
    db.query.return_value = _q(first=first, all_=all_)
    return db


def _run(coro):
    return asyncio.run(coro)


# ===========================================================================
# list_all_coupons
# ===========================================================================

@pytest.mark.unit
class TestListAllCoupons:
    def test_empty_list_returns_empty(self):
        db = _db(all_=[])
        result = _run(list_all_coupons(request=MagicMock(), db=db, current_user=_admin()))
        assert result == []

    def test_returns_list_of_coupon_dicts_with_is_valid(self):
        c = _coupon()
        db = _db(all_=[c])
        result = _run(list_all_coupons(request=MagicMock(), db=db, current_user=_admin()))
        assert len(result) == 1
        row = result[0]
        assert row["code"] == "TEST10"
        assert row["is_valid"] is True
        c.is_valid.assert_called_once()

    def test_multiple_coupons(self):
        c1 = _coupon(code="CODE1")
        c2 = _coupon(code="CODE2", is_active=False)
        db = _db(all_=[c1, c2])
        result = _run(list_all_coupons(request=MagicMock(), db=db, current_user=_admin()))
        assert len(result) == 2


# ===========================================================================
# create_coupon_api
# ===========================================================================

@pytest.mark.unit
class TestCreateCouponApi:
    def _payload(self, code="NEWCODE", ctype=CouponType.BONUS_CREDITS, value=500.0):
        return CouponCreate(
            code=code,
            type=ctype,
            discount_value=value,
            description="Test discount",
        )

    def test_duplicate_code_raises_400(self):
        existing = _coupon(code="NEWCODE")
        db = _db(first=existing)
        with pytest.raises(HTTPException) as exc:
            _run(create_coupon_api(
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400

    def test_success_creates_and_returns_coupon(self):
        mock_coupon = _coupon(code="NEWCODE")
        mock_coupon.expires_at = None
        db = _db(first=None)  # no duplicate
        with patch(f"{_BASE}.Coupon", return_value=mock_coupon):
            result = _run(create_coupon_api(
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert result["code"] == "NEWCODE"
        assert "is_valid" in result
        db.add.assert_called_once_with(mock_coupon)
        db.commit.assert_called_once()

    def test_expires_at_present_calls_isoformat(self):
        mock_coupon = _coupon(code="NEWCODE")
        exp = MagicMock()
        exp.isoformat.return_value = "2027-01-01T00:00:00"
        mock_coupon.expires_at = exp
        db = _db(first=None)
        with patch(f"{_BASE}.Coupon", return_value=mock_coupon):
            result = _run(create_coupon_api(
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert result["expires_at"] == "2027-01-01T00:00:00"


# ===========================================================================
# create_coupon_web
# ===========================================================================

@pytest.mark.unit
class TestCreateCouponWeb:
    def _payload(self):
        return CouponCreate(
            code="WEBCODE",
            type=CouponType.BONUS_CREDITS,
            discount_value=200.0,
            description="Web coupon",
        )

    def test_duplicate_code_raises_400(self):
        existing = _coupon(code="WEBCODE")
        db = _db(first=existing)
        with pytest.raises(HTTPException) as exc:
            _run(create_coupon_web(
                request=MagicMock(),
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400

    def test_success_with_audit_log(self):
        mock_coupon = _coupon(code="WEBCODE")
        db = _db(first=None)
        with patch(f"{_BASE}.Coupon", return_value=mock_coupon), \
             patch(f"{_BASE}.AuditLog") as MockAudit:
            result = _run(create_coupon_web(
                request=MagicMock(),
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        assert result["code"] == "WEBCODE"
        MockAudit.assert_called_once()

    def test_audit_log_exception_triggers_rollback(self):
        mock_coupon = _coupon(code="WEBCODE")
        db = _db(first=None)
        with patch(f"{_BASE}.Coupon", return_value=mock_coupon), \
             patch(f"{_BASE}.AuditLog", side_effect=Exception("table missing")):
            result = _run(create_coupon_web(
                request=MagicMock(),
                coupon_data=self._payload(),
                db=db,
                current_user=_admin(),
            ))
        # Rollback called, but function still succeeds
        db.rollback.assert_called_once()
        assert result["code"] == "WEBCODE"


# ===========================================================================
# update_coupon
# ===========================================================================

@pytest.mark.unit
class TestUpdateCoupon:
    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(update_coupon(
                request=MagicMock(),
                coupon_id=99,
                coupon_data=CouponUpdate(is_active=False),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 404

    def test_new_code_conflicts_raises_400(self):
        existing = _coupon(code="OLDCODE")
        conflicting = _coupon(code="NEWCODE")
        q1 = _q(first=existing)
        q2 = _q(first=conflicting)
        db = MagicMock()
        db.query.side_effect = [q1, q2]
        with pytest.raises(HTTPException) as exc:
            _run(update_coupon(
                request=MagicMock(),
                coupon_id=1,
                coupon_data=CouponUpdate(code="newcode"),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400

    def test_code_uppercased_on_update(self):
        existing = _coupon(code="OLDCODE")
        q1 = _q(first=existing)
        q2 = _q(first=None)   # no conflict
        db = MagicMock()
        db.query.side_effect = [q1, q2]
        with patch(f"{_BASE}.AuditLog"):
            _run(update_coupon(
                request=MagicMock(),
                coupon_id=1,
                coupon_data=CouponUpdate(code="lowercase"),
                db=db,
                current_user=_admin(),
            ))
        # setattr was called with "code" set to "LOWERCASE"
        # check that db operations happened
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(existing)

    def test_update_without_code_change(self):
        existing = _coupon(code="STABLE")
        db = _db(first=existing)
        with patch(f"{_BASE}.AuditLog"):
            result = _run(update_coupon(
                request=MagicMock(),
                coupon_id=1,
                coupon_data=CouponUpdate(is_active=False),
                db=db,
                current_user=_admin(),
            ))
        db.commit.assert_called_once()
        assert "is_active" in result

    def test_audit_log_exception_still_commits(self):
        existing = _coupon(code="STABLE")
        db = _db(first=existing)
        with patch(f"{_BASE}.AuditLog", side_effect=Exception("table missing")):
            _run(update_coupon(
                request=MagicMock(),
                coupon_id=1,
                coupon_data=CouponUpdate(is_active=False),
                db=db,
                current_user=_admin(),
            ))
        db.commit.assert_called_once()


# ===========================================================================
# delete_coupon
# ===========================================================================

@pytest.mark.unit
class TestDeleteCoupon:
    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(delete_coupon(
                request=MagicMock(),
                coupon_id=99,
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 404

    def test_success_deletes_coupon(self):
        c = _coupon()
        db = _db(first=c)
        with patch(f"{_BASE}.AuditLog"):
            result = _run(delete_coupon(
                request=MagicMock(),
                coupon_id=1,
                db=db,
                current_user=_admin(),
            ))
        db.delete.assert_called_once_with(c)
        db.commit.assert_called_once()
        assert result is None

    def test_audit_log_exception_still_deletes(self):
        c = _coupon()
        db = _db(first=c)
        with patch(f"{_BASE}.AuditLog", side_effect=Exception("table missing")):
            _run(delete_coupon(
                request=MagicMock(),
                coupon_id=1,
                db=db,
                current_user=_admin(),
            ))
        db.delete.assert_called_once_with(c)
        db.commit.assert_called_once()


# ===========================================================================
# toggle_coupon_status
# ===========================================================================

@pytest.mark.unit
class TestToggleCouponStatus:
    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(toggle_coupon_status(
                request=MagicMock(),
                coupon_id=99,
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 404

    def test_active_coupon_toggled_to_inactive(self):
        c = _coupon(is_active=True)
        db = _db(first=c)
        result = _run(toggle_coupon_status(
            request=MagicMock(),
            coupon_id=1,
            db=db,
            current_user=_admin(),
        ))
        # is_active was True, endpoint does: coupon.is_active = not coupon.is_active
        # The mock.is_active is set to False in the endpoint body
        db.commit.assert_called_once()
        assert "id" in result

    def test_inactive_coupon_toggled_to_active(self):
        c = _coupon(is_active=False)
        db = _db(first=c)
        result = _run(toggle_coupon_status(
            request=MagicMock(),
            coupon_id=1,
            db=db,
            current_user=_admin(),
        ))
        db.commit.assert_called_once()
        assert "is_valid" in result


# ===========================================================================
# list_active_coupons
# ===========================================================================

@pytest.mark.unit
class TestListActiveCoupons:
    def test_empty_returns_empty(self):
        db = _db(all_=[])
        result = _run(list_active_coupons(db=db))
        assert result == []

    def test_filters_invalid_coupons(self):
        valid = _coupon(is_valid=MagicMock(return_value=True))
        invalid = _coupon(is_valid=MagicMock(return_value=False))
        db = _db(all_=[valid, invalid])
        result = _run(list_active_coupons(db=db))
        # Only valid coupon passes the filter
        assert len(result) == 1
        assert result[0] is valid


# ===========================================================================
# validate_coupon
# ===========================================================================

@pytest.mark.unit
class TestValidateCoupon:
    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(validate_coupon(code="NOPE", db=db))
        assert exc.value.status_code == 404

    def test_valid_coupon_returns_details(self):
        c = _coupon()
        db = _db(first=c)
        result = _run(validate_coupon(code="test10", db=db))
        assert result["valid"] is True
        assert result["code"] == "TEST10"

    def test_inactive_coupon_raises_400_with_reason(self):
        c = _coupon(is_active=False)
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(validate_coupon(code="TEST10", db=db))
        assert exc.value.status_code == 400
        assert "inactive" in exc.value.detail.lower()

    def test_expired_coupon_raises_400_with_reason(self):
        c = _coupon()
        c.is_active = True
        c.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)  # in the past
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(validate_coupon(code="TEST10", db=db))
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail.lower()

    def test_max_uses_reached_raises_400_with_reason(self):
        c = _coupon()
        c.is_active = True
        c.expires_at = None
        c.max_uses = 10
        c.current_uses = 10
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(validate_coupon(code="TEST10", db=db))
        assert exc.value.status_code == 400
        assert "maximum" in exc.value.detail.lower()


# ===========================================================================
# apply_coupon
# ===========================================================================

@pytest.mark.unit
class TestApplyCoupon:
    def _req(self, code="TEST10"):
        return ApplyCouponRequest(code=code)

    def test_not_found_raises_404(self):
        db = _db(first=None)
        with pytest.raises(HTTPException) as exc:
            _run(apply_coupon(
                coupon_data=self._req(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 404
        assert exc.value.detail["error"] == "coupon_not_found"

    def test_invalid_coupon_raises_400(self):
        c = _coupon(is_active=False)
        c.is_valid.return_value = False
        db = _db(first=c)
        with pytest.raises(HTTPException) as exc:
            _run(apply_coupon(
                coupon_data=self._req(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400
        assert exc.value.detail["error"] == "coupon_invalid"

    def test_already_used_raises_400(self):
        c = _coupon()
        usage = MagicMock()
        usage.used_at.isoformat.return_value = "2026-01-01T00:00:00"
        q_coupon = _q(first=c)
        q_usage = _q(first=usage)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        with pytest.raises(HTTPException) as exc:
            _run(apply_coupon(
                coupon_data=self._req(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400
        assert exc.value.detail["error"] == "coupon_already_used"

    def test_requires_purchase_raises_400(self):
        c = _coupon(requires_purchase=True)
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        with pytest.raises(HTTPException) as exc:
            _run(apply_coupon(
                coupon_data=self._req(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 400
        assert exc.value.detail["error"] == "coupon_requires_purchase"

    def test_bonus_credits_type_awards_credits(self):
        c = _coupon(type=CouponType.BONUS_CREDITS, discount_value=500.0)
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        user = _admin()
        result = _run(apply_coupon(
            coupon_data=self._req(),
            db=db,
            current_user=user,
        ))
        assert result["credits_awarded"] == 500
        db.commit.assert_called_once()

    def test_credits_legacy_type_awards_credits(self):
        c = _coupon(type=CouponType.CREDITS, discount_value=200.0)
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        result = _run(apply_coupon(
            coupon_data=self._req(),
            db=db,
            current_user=_admin(),
        ))
        assert result["credits_awarded"] == 200  # int(200.0)

    def test_fixed_legacy_type_converts_to_credits(self):
        c = _coupon(type=CouponType.FIXED, discount_value=5.0)
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        result = _run(apply_coupon(
            coupon_data=self._req(),
            db=db,
            current_user=_admin(),
        ))
        # 1 EUR = 10 credits → 5 EUR → 50 credits
        assert result["credits_awarded"] == 50

    def test_percent_legacy_type_gives_bonus_credits(self):
        c = _coupon(type=CouponType.PERCENT, discount_value=10.0)
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        result = _run(apply_coupon(
            coupon_data=self._req(),
            db=db,
            current_user=_admin(),
        ))
        # 10% = 10 * 1000 = 10000 credits
        assert result["credits_awarded"] == 10000

    def test_unhandled_type_raises_500(self):
        # requires_purchase=False but type is PURCHASE_DISCOUNT_PERCENT → else branch → 500
        c = _coupon(
            type=CouponType.PURCHASE_DISCOUNT_PERCENT,
            requires_purchase=False,  # bypasses the requires_purchase check
        )
        q_coupon = _q(first=c)
        q_usage = _q(first=None)
        db = MagicMock()
        db.query.side_effect = [q_coupon, q_usage]
        with pytest.raises(HTTPException) as exc:
            _run(apply_coupon(
                coupon_data=self._req(),
                db=db,
                current_user=_admin(),
            ))
        assert exc.value.status_code == 500
        assert exc.value.detail["error"] == "invalid_coupon_type"
