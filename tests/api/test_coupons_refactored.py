"""
API Tests for Refactored Coupon System

Tests all three coupon types:
1. BONUS_CREDITS - Instant free credits (no purchase required)
2. PURCHASE_DISCOUNT_PERCENT - % discount on purchase (requires invoice + admin approval)
3. PURCHASE_BONUS_CREDITS - Bonus credits after purchase (requires invoice + admin approval)

Coverage:
- Coupon creation (admin only)
- Coupon application (user)
- Validation (expired, max uses, invalid codes)
- Double redemption prevention
- Purchase-only coupon rejection
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.main import app
from app.models.coupon import Coupon, CouponUsage, CouponType
from app.models.user import User
from app.core.security import get_password_hash


# Test fixtures
@pytest.fixture
def coupon_test_user(test_db: Session) -> User:
    """Create a test user for coupon redemption"""
    user = User(
        email="coupon.tester@test.com",
        password_hash=get_password_hash("testpass123"),
        name="Coupon Tester",
        is_active=True,
        credit_balance=0,
        credit_purchased=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def coupon_test_user_token(client: TestClient, coupon_test_user: User) -> str:
    """Get test user authentication token"""
    response = client.post(
        "/api/v1/auth/login/form",
        data={"username": coupon_test_user.email, "password": "testpass123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def admin_token_for_coupons(client: TestClient, admin_user: User) -> str:
    """Get admin authentication token"""
    response = client.post(
        "/api/v1/auth/login/form",
        data={"username": admin_user.email, "password": "admin123"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


# =============================================================================
# TEST GROUP 1: BONUS_CREDITS Type (Instant Free Credits)
# =============================================================================

def test_01_create_bonus_credits_coupon(client: TestClient, admin_token_for_coupons: str, test_db: Session):
    """
    Test A2.1: Admin creates BONUS_CREDITS coupon
    Expected: 201 Created, coupon saved in DB with correct flags
    """
    coupon_data = {
        "code": "TEST_BONUS_500",
        "type": "BONUS_CREDITS",
        "discount_value": 500.0,
        "description": "Test bonus credits coupon - 500 credits instant",
        "is_active": True,
        "max_uses": 10,
        "expires_at": None
    }

    response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    assert data["code"] == "TEST_BONUS_500"
    assert data["type"] == "BONUS_CREDITS"
    assert data["discount_value"] == 500.0
    assert data["is_active"] is True
    assert data["max_uses"] == 10

    # Verify in database
    coupon = test_db.query(Coupon).filter(Coupon.code == "TEST_BONUS_500").first()
    assert coupon is not None
    assert coupon.requires_purchase is False
    assert coupon.requires_admin_approval is False


def test_02_apply_bonus_credits_coupon(
    client: TestClient,
    coupon_test_user_token: str,
    coupon_test_user: User,
    admin_token_for_coupons: str,
    test_db: Session
):
    """
    Test A2.2: User applies BONUS_CREDITS coupon
    Expected: 200 OK, credits added immediately, usage record created
    """
    # First create the coupon (database is fresh for each test)
    coupon_data = {
        "code": "BONUS500",
        "type": "BONUS_CREDITS",
        "discount_value": 500.0,
        "description": "Test bonus credits",
        "is_active": True
    }
    client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    # Get user's initial balance
    test_db.refresh(coupon_test_user)
    initial_balance = coupon_test_user.credit_balance or 0

    # Apply coupon
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "BONUS500"}
    )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()

    assert data["coupon_code"] == "BONUS500"
    assert data["coupon_type"] == "BONUS_CREDITS"
    assert data["credits_awarded"] == 500
    assert data["new_balance"] == initial_balance + 500

    # Verify in database
    test_db.refresh(coupon_test_user)
    assert coupon_test_user.credit_balance == initial_balance + 500

    # Verify usage record
    usage = test_db.query(CouponUsage).filter(
        CouponUsage.user_id == coupon_test_user.id
    ).first()
    assert usage is not None
    assert usage.credits_awarded == 500


def test_03_prevent_double_redemption(
    client: TestClient,
    coupon_test_user_token: str,
    admin_token_for_coupons: str
):
    """
    Test A2.3: User tries to use same coupon twice
    Expected: 400 Bad Request with "coupon_already_used" error
    """
    # Create and apply coupon first time
    coupon_data = {
        "code": "NODUP",
        "type": "BONUS_CREDITS",
        "discount_value": 100.0,
        "description": "No duplicate test",
        "is_active": True
    }
    client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "NODUP"}
    )

    # Try again
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "NODUP"}
    )

    assert response.status_code == 400
    data = response.json()
    # Handle both possible error response formats
    if "error" in data and isinstance(data["error"], dict):
        assert "coupon_already_used" in str(data["error"])
    else:
        assert "already used" in str(data).lower()


# =============================================================================
# TEST GROUP 2: PURCHASE_DISCOUNT_PERCENT Type (Purchase Only)
# =============================================================================


def test_04_create_purchase_discount_coupon(
    client: TestClient,
    admin_token_for_coupons: str,
    test_db: Session
):
    """
    Test A3.1: Admin creates PURCHASE_DISCOUNT_PERCENT coupon
    Expected: 201 Created, requires_purchase=True, requires_admin_approval=True
    """
    coupon_data = {
        "code": "DISCOUNT20",
        "type": "PURCHASE_DISCOUNT_PERCENT",
        "discount_value": 0.2,  # 20% discount
        "description": "20% discount on credit package purchase",
        "is_active": True,
        "max_uses": 50
    }

    response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    assert data["type"] == "PURCHASE_DISCOUNT_PERCENT"
    assert data["discount_value"] == 0.2

    # Verify flags in database
    coupon = test_db.query(Coupon).filter(Coupon.code == "DISCOUNT20").first()
    assert coupon.requires_purchase is True
    assert coupon.requires_admin_approval is True


def test_05_reject_purchase_discount_direct_redemption(
    client: TestClient,
    coupon_test_user_token: str,
    admin_token_for_coupons: str
):
    """
    Test A3.2: User tries to apply PURCHASE_DISCOUNT_PERCENT directly (without purchase)
    Expected: 400 Bad Request with "coupon_requires_purchase" error
    """
    # Create coupon
    coupon_data = {
        "code": "DISC10",
        "type": "PURCHASE_DISCOUNT_PERCENT",
        "discount_value": 0.1,
        "description": "10% discount",
        "is_active": True
    }
    client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    # Try to apply directly
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "DISC10"}
    )

    assert response.status_code == 400
    data = response.json()
    # Handle both possible error response formats
    response_str = str(data).lower()
    assert ("purchase" in response_str or "requires_purchase" in response_str)


# =============================================================================
# TEST GROUP 3: PURCHASE_BONUS_CREDITS Type (Purchase Only)
# =============================================================================


def test_06_create_purchase_bonus_coupon(
    client: TestClient,
    admin_token_for_coupons: str,
    test_db: Session
):
    """
    Test A4.1: Admin creates PURCHASE_BONUS_CREDITS coupon
    Expected: 201 Created, requires_purchase=True, requires_admin_approval=True
    """
    coupon_data = {
        "code": "BONUS500",
        "type": "PURCHASE_BONUS_CREDITS",
        "discount_value": 500.0,  # +500 bonus credits
        "description": "Get +500 bonus credits with any purchase",
        "is_active": True
    }

    response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    assert data["type"] == "PURCHASE_BONUS_CREDITS"
    assert data["discount_value"] == 500.0

    # Verify flags
    coupon = test_db.query(Coupon).filter(Coupon.code == "BONUS500").first()
    assert coupon.requires_purchase is True
    assert coupon.requires_admin_approval is True


def test_07_reject_purchase_bonus_direct_redemption(
    client: TestClient,
    coupon_test_user_token: str,
    admin_token_for_coupons: str
):
    """
    Test A4.2: User tries to apply PURCHASE_BONUS_CREDITS directly (without purchase)
    Expected: 400 Bad Request with "coupon_requires_purchase" error
    """
    # Create coupon
    coupon_data = {
        "code": "PBONUS",
        "type": "PURCHASE_BONUS_CREDITS",
        "discount_value": 300.0,
        "description": "+300 bonus",
        "is_active": True
    }
    client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )

    # Try to apply directly
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "PBONUS"}
    )

    assert response.status_code == 400
    data = response.json()
    response_str = str(data).lower()
    assert ("purchase" in response_str or "requires_purchase" in response_str)


# =============================================================================
# TEST GROUP 4: Negative Cases (Validation, Errors)
# =============================================================================


def test_08_apply_invalid_coupon_code(
    client: TestClient,
    coupon_test_user_token: str
):
    """
    Test A5.1: User tries to apply non-existent coupon
    Expected: 404 Not Found with "coupon_not_found" error
    """
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "INVALID_CODE_XYZ"}
    )

    assert response.status_code == 404
    data = response.json()
    response_str = str(data).lower()
    assert "not found" in response_str or "coupon_not_found" in response_str


def test_09_apply_expired_coupon(
    client: TestClient,
    admin_token_for_coupons: str,
    coupon_test_user_token: str,
    test_db: Session
):
    """
    Test A5.2: User tries to apply expired coupon
    Expected: 400 Bad Request with "coupon_invalid" error
    """
    # Create expired coupon
    expired_date = datetime.now(timezone.utc) - timedelta(days=1)
    coupon_data = {
        "code": "EXPIRED_TEST",
        "type": "BONUS_CREDITS",
        "discount_value": 100.0,
        "description": "Expired test coupon",
        "is_active": True,
        "expires_at": expired_date.isoformat()
    }

    create_response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )
    assert create_response.status_code == 201

    # Try to apply
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "EXPIRED_TEST"}
    )

    assert response.status_code == 400
    data = response.json()
    response_str = str(data).lower()
    assert "expired" in response_str or "invalid" in response_str


def test_10_apply_inactive_coupon(
    client: TestClient,
    admin_token_for_coupons: str,
    coupon_test_user_token: str
):
    """
    Test A5.3: User tries to apply inactive coupon
    Expected: 400 Bad Request with "coupon_invalid" error
    """
    # Create inactive coupon
    coupon_data = {
        "code": "INACTIVE_TEST",
        "type": "BONUS_CREDITS",
        "discount_value": 100.0,
        "description": "Inactive test coupon",
        "is_active": False
    }

    create_response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )
    assert create_response.status_code == 201

    # Try to apply
    response = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "INACTIVE_TEST"}
    )

    assert response.status_code == 400
    data = response.json()
    response_str = str(data).lower()
    assert "inactive" in response_str or "invalid" in response_str


def test_11_apply_max_uses_exceeded(
    client: TestClient,
    admin_token_for_coupons: str,
    coupon_test_user: User,
    coupon_test_user_token: str,
    test_db: Session
):
    """
    Test A5.4: Coupon reaches max uses limit
    Expected: 400 Bad Request with "coupon_invalid" error
    """
    # Create coupon with max_uses=1
    coupon_data = {
        "code": "MAXUSE_TEST",
        "type": "BONUS_CREDITS",
        "discount_value": 50.0,
        "description": "Max use test",
        "is_active": True,
        "max_uses": 1
    }

    create_response = client.post(
        "/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token_for_coupons}"},
        json=coupon_data
    )
    assert create_response.status_code == 201

    # User 1 uses the coupon (should succeed)
    apply1 = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {coupon_test_user_token}"},
        json={"code": "MAXUSE_TEST"}
    )
    assert apply1.status_code == 200  # First use succeeds

    # Create a second test user
    user2 = User(
        email="user2@test.com",
        password_hash=get_password_hash("pass123"),
        name="User 2",
        is_active=True,
        credit_balance=0
    )
    test_db.add(user2)
    test_db.commit()

    # User 2 tries to use (should fail - max uses exceeded)
    login2 = client.post(
        "/api/v1/auth/login/form",
        data={"username": "user2@test.com", "password": "pass123"}
    )
    token2 = login2.json()["access_token"]

    apply2 = client.post(
        "/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {token2}"},
        json={"code": "MAXUSE_TEST"}
    )

    assert apply2.status_code == 400
    data = apply2.json()
    response_str = str(data).lower()
    assert "maximum" in response_str or "max" in response_str or "invalid" in response_str
