"""
Unit tests for app/models/coupon.py

Branch coverage targets:

set_flags_based_on_type():
  - BONUS_CREDITS        → requires_purchase=False, requires_admin_approval=False
  - PURCHASE_DISCOUNT_%  → requires_purchase=True,  requires_admin_approval=True
  - PURCHASE_BONUS_CREDITS→ requires_purchase=True,  requires_admin_approval=True
  - Legacy types (PERCENT, FIXED, CREDITS) → False, False

is_valid():
  - is_active=False                     → False immediately
  - expires_at set and expired          → False
  - expires_at set but not expired      → continues
  - expires_at is None                  → skip expiry check
  - max_uses set and usage exhausted    → False
  - max_uses is None (unlimited)        → skip usage check
  - all checks pass                     → True
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.coupon import Coupon, CouponType


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _coupon(**overrides):
    """Build a transient Coupon with valid defaults."""
    c = Coupon()
    c.code = "TEST10"
    c.type = CouponType.BONUS_CREDITS
    c.discount_value = 100.0
    c.description = "Test coupon"
    c.is_active = True
    c.expires_at = None
    c.max_uses = None
    c.current_uses = 0
    c.requires_purchase = False
    c.requires_admin_approval = False
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


_NOW = datetime.now(timezone.utc)
_PAST = _NOW - timedelta(days=1)
_FUTURE = _NOW + timedelta(days=30)


# ============================================================================
# set_flags_based_on_type()
# ============================================================================

class TestSetFlagsBasedOnType:

    def test_bonus_credits_no_purchase_no_approval(self):
        c = _coupon(type=CouponType.BONUS_CREDITS)
        c.set_flags_based_on_type()
        assert c.requires_purchase is False
        assert c.requires_admin_approval is False

    def test_purchase_discount_percent_requires_both(self):
        c = _coupon(type=CouponType.PURCHASE_DISCOUNT_PERCENT)
        c.set_flags_based_on_type()
        assert c.requires_purchase is True
        assert c.requires_admin_approval is True

    def test_purchase_bonus_credits_requires_both(self):
        c = _coupon(type=CouponType.PURCHASE_BONUS_CREDITS)
        c.set_flags_based_on_type()
        assert c.requires_purchase is True
        assert c.requires_admin_approval is True


# ============================================================================
# is_valid()
# ============================================================================

class TestIsValid:

    def test_inactive_coupon_invalid(self):
        c = _coupon(is_active=False)
        assert c.is_valid() is False

    def test_expired_coupon_invalid(self):
        c = _coupon(expires_at=_PAST)
        assert c.is_valid() is False

    def test_not_yet_expired_coupon_valid(self):
        c = _coupon(expires_at=_FUTURE)
        assert c.is_valid() is True

    def test_no_expiry_skips_expiry_check(self):
        c = _coupon(expires_at=None)
        assert c.is_valid() is True

    def test_max_uses_exhausted_invalid(self):
        c = _coupon(max_uses=5, current_uses=5)
        assert c.is_valid() is False

    def test_max_uses_exceeded_invalid(self):
        c = _coupon(max_uses=5, current_uses=10)
        assert c.is_valid() is False

    def test_max_uses_not_reached_valid(self):
        c = _coupon(max_uses=5, current_uses=4)
        assert c.is_valid() is True

    def test_no_max_uses_skips_usage_check(self):
        c = _coupon(max_uses=None, current_uses=9999)
        assert c.is_valid() is True

    def test_all_conditions_pass_valid(self):
        c = _coupon(is_active=True, expires_at=_FUTURE, max_uses=10, current_uses=3)
        assert c.is_valid() is True


# ============================================================================
# increment_usage()
# ============================================================================

class TestIncrementUsage:

    def test_increments_by_one(self):
        c = _coupon(current_uses=3)
        c.increment_usage()
        assert c.current_uses == 4
