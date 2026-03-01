"""
Integration tests for Specialization Selection API (TICKET-SMOKE-003)

Tests for 5 Acceptance Criteria:
- AC1: Valid specialization selection succeeds
- AC2: Insufficient credits rejected with 400
- AC3: Invalid specialization rejected with 422
- AC4: Duplicate selection allowed (no cost if license exists)
- AC5: Credit transaction logged correctly
"""
import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import User, UserRole, SpecializationType
from app.models.license import UserLicense
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.core.security import get_password_hash


@pytest.fixture(scope="function")
def test_user(postgres_db: Session):
    """Create test user with credits"""
    user = User(
        name="Test User",
        email=f"test.spec.select.{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT,
        credit_balance=500,
        is_active=True
    )
    postgres_db.add(user)
    postgres_db.commit()
    postgres_db.refresh(user)

    user_id = user.id  # Store ID before yielding to avoid session expiration issues

    yield user

    # Cleanup - use stored user_id to avoid session expiration
    postgres_db.query(CreditTransaction).filter(
        CreditTransaction.user_license_id.in_(
            postgres_db.query(UserLicense.id).filter(UserLicense.user_id == user_id)
        )
    ).delete(synchronize_session=False)
    postgres_db.query(UserLicense).filter(UserLicense.user_id == user_id).delete()
    postgres_db.query(User).filter(User.id == user_id).delete()
    postgres_db.commit()


@pytest.fixture(scope="function")
def auth_token(test_user: User):
    """Generate auth token for test user"""
    from app.core.auth import create_access_token
    from datetime import timedelta
    return create_access_token(data={"sub": test_user.email}, expires_delta=timedelta(hours=1))


@pytest.fixture(scope="function")
def api_client():
    """FastAPI test client"""
    return TestClient(app)


# ============================================================================
# AC1: Valid specialization selection succeeds
# ============================================================================

def test_ac1_valid_specialization_selection_succeeds(
    api_client: TestClient,
    auth_token: str,
    test_user: User,
    postgres_db: Session
):
    """
    AC1: Valid specialization selection succeeds

    Given: User with 500 credits
    When: POST /api/v1/specialization/select with valid specialization
    Then:
      - 200 OK
      - UserLicense created
      - 100 credits deducted
      - next_step_url returned
    """
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"specialization": "LFA_FOOTBALL_PLAYER"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload,
        headers=headers
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Verify response structure
    assert data["success"] is True
    assert data["specialization"] == "LFA_FOOTBALL_PLAYER"
    assert data["license_created"] is True
    assert data["credits_deducted"] == 100
    assert data["credit_balance_after"] == 400  # 500 - 100
    assert "/lfa-player/onboarding" in data["next_step_url"]

    # Verify UserLicense created in DB
    postgres_db.refresh(test_user)
    license = postgres_db.query(UserLicense).filter(
        UserLicense.user_id == test_user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
    ).first()

    assert license is not None, "UserLicense should be created"
    assert license.current_level == 1
    assert license.payment_verified is True
    assert license.onboarding_completed is False

    # Verify credit balance updated
    assert test_user.credit_balance == 400
    assert test_user.specialization == SpecializationType.LFA_FOOTBALL_PLAYER


# ============================================================================
# AC2: Insufficient credits rejected with 400
# ============================================================================

def test_ac2_insufficient_credits_rejected(
    api_client: TestClient,
    postgres_db: Session
):
    """
    AC2: Insufficient credits rejected with 400

    Given: User with 50 credits (< 100 required)
    When: POST /api/v1/specialization/select
    Then:
      - 400 Bad Request
      - Error message indicates insufficient credits
      - No license created
      - No credits deducted
    """
    # Create user with insufficient credits
    user = User(
        name="Poor User",
        email=f"poor.user.{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT,
        credit_balance=50,  # Insufficient
        is_active=True
    )
    postgres_db.add(user)
    postgres_db.commit()
    postgres_db.refresh(user)

    from app.core.auth import create_access_token
    from datetime import timedelta
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"specialization": "LFA_COACH"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload,
        headers=headers
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    error_data = response.json()
    # Error middleware wraps in {"error": {"message": "..."}} format
    error_message = error_data.get("detail") or error_data.get("error", {}).get("message", "")
    assert "Insufficient credits" in error_message, f"Expected 'Insufficient credits' in {error_message}"
    assert "100 credits" in error_message, f"Expected '100 credits' in {error_message}"

    # Verify no license created
    license = postgres_db.query(UserLicense).filter(
        UserLicense.user_id == user.id
    ).first()
    assert license is None, "No license should be created"

    # Verify credits unchanged
    postgres_db.refresh(user)
    assert user.credit_balance == 50, "Credits should not be deducted"

    # Cleanup
    postgres_db.query(User).filter(User.id == user.id).delete()
    postgres_db.commit()


# ============================================================================
# AC3: Invalid specialization rejected with 422
# ============================================================================

def test_ac3_invalid_specialization_rejected(
    api_client: TestClient,
    auth_token: str
):
    """
    AC3: Invalid specialization rejected with 422

    Given: Valid auth token
    When: POST with invalid specialization value
    Then:
      - 422 Unprocessable Entity
      - Pydantic validation error
    """
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Test invalid specialization string
    payload = {"specialization": "INVALID_SPEC"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload,
        headers=headers
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    error_data = response.json()
    # Error middleware may wrap in {"error": {...}} format
    error_str = str(error_data)
    assert "specialization" in error_str.lower(), f"Expected 'specialization' in error response: {error_data}"


# ============================================================================
# AC4: Duplicate selection allowed (no cost if license exists)
# ============================================================================

def test_ac4_duplicate_selection_no_cost(
    api_client: TestClient,
    auth_token: str,
    test_user: User,
    postgres_db: Session
):
    """
    AC4: Duplicate selection allowed (no cost if license exists)

    Given: User already has LFA_COACH license
    When: POST /api/v1/specialization/select with same specialization
    Then:
      - 200 OK
      - license_created = False
      - credits_deducted = 0
      - credit_balance unchanged
    """
    # Pre-create license
    existing_license = UserLicense(
        user_id=test_user.id,
        specialization_type="LFA_COACH",
        current_level=3,
        max_achieved_level=3,
        is_active=True,
        payment_verified=True,
        started_at=datetime.now(timezone.utc),
        payment_verified_at=datetime.now(timezone.utc)
    )
    postgres_db.add(existing_license)
    postgres_db.commit()

    initial_balance = test_user.credit_balance

    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"specialization": "LFA_COACH"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload,
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify no cost for existing license
    assert data["license_created"] is False
    assert data["credits_deducted"] == 0
    assert data["credit_balance_after"] == initial_balance
    assert "already unlocked" in data["message"].lower()

    # Verify credit balance unchanged
    postgres_db.refresh(test_user)
    assert test_user.credit_balance == initial_balance

    # Verify only ONE license exists (no duplicate)
    license_count = postgres_db.query(UserLicense).filter(
        UserLicense.user_id == test_user.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).count()
    assert license_count == 1, "Should not create duplicate license"


# ============================================================================
# AC5: Credit transaction logged correctly
# ============================================================================

def test_ac5_credit_transaction_logged(
    api_client: TestClient,
    auth_token: str,
    test_user: User,
    postgres_db: Session
):
    """
    AC5: Credit transaction logged correctly

    Given: User with 500 credits
    When: POST /api/v1/specialization/select (new unlock)
    Then:
      - CreditTransaction created
      - amount = -100
      - transaction_type = PURCHASE
      - balance_after = 400
      - description mentions specialization
    """
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"specialization": "GANCUJU_PLAYER"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload,
        headers=headers
    )

    assert response.status_code == 200

    # Fetch the created license
    license = postgres_db.query(UserLicense).filter(
        UserLicense.user_id == test_user.id,
        UserLicense.specialization_type == "GANCUJU_PLAYER"
    ).first()

    assert license is not None, "License should be created"

    # Verify credit transaction logged
    transaction = postgres_db.query(CreditTransaction).filter(
        CreditTransaction.user_license_id == license.id
    ).first()

    assert transaction is not None, "CreditTransaction should be created"
    assert transaction.amount == -100
    assert transaction.transaction_type == TransactionType.PURCHASE.value
    assert transaction.balance_after == 400  # 500 - 100
    assert "Unlocked specialization" in transaction.description
    assert "GANCUJU_PLAYER" in transaction.description or "GANCUJU PLAYER" in transaction.description


# ============================================================================
# Additional Edge Cases
# ============================================================================

def test_authentication_required(api_client: TestClient):
    """Verify endpoint requires authentication"""
    payload = {"specialization": "LFA_FOOTBALL_PLAYER"}

    response = api_client.post(
        "/api/v1/specialization/select",
        json=payload
    )

    assert response.status_code == 401, "Should require authentication"


def test_all_specializations_supported(
    api_client: TestClient,
    postgres_db: Session
):
    """Verify all 4 specialization types are supported"""
    specializations = [
        "INTERNSHIP",
        "LFA_FOOTBALL_PLAYER",
        "LFA_COACH",
        "GANCUJU_PLAYER"
    ]

    for spec in specializations:
        # Create fresh user for each specialization
        user = User(
            name=f"User {spec}",
            email=f"user.{spec.lower()}.{uuid.uuid4().hex[:8]}@example.com",
            password_hash=get_password_hash("password123"),
            role=UserRole.STUDENT,
            credit_balance=500,
            is_active=True
        )
        postgres_db.add(user)
        postgres_db.commit()
        postgres_db.refresh(user)

        from app.core.auth import create_access_token
        from datetime import timedelta
        token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"specialization": spec}

        response = api_client.post(
            "/api/v1/specialization/select",
            json=payload,
            headers=headers
        )

        assert response.status_code == 200, f"Specialization {spec} should be supported"

        # Cleanup
        postgres_db.query(CreditTransaction).filter(
            CreditTransaction.user_license_id.in_(
                postgres_db.query(UserLicense.id).filter(UserLicense.user_id == user.id)
            )
        ).delete(synchronize_session=False)
        postgres_db.query(UserLicense).filter(UserLicense.user_id == user.id).delete()
        postgres_db.query(User).filter(User.id == user.id).delete()
        postgres_db.commit()
