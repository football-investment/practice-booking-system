"""
API Tests for Invitation Code System

Tests the complete invitation code workflow:
1. Admin creates invitation codes (50 credits each)
2. Validates invitation codes
3. User redeems invitation code during registration

CRITICAL REQUIREMENTS:
- Email addresses (FIXED with api. prefix): api.k1sqx1@f1stteam.hu, api.p3t1k3@f1stteam.hu, api.V4lv3rd3jr@f1stteam.hu
- Bonus credits: 50 credits ONLY (no other amount allowed)
- Age groups: Pre (6-11), Youth (12-17), Amateur (18+)
- Clean database: users created ONLY via invitation code redemption
- PREFIX: "api." to distinguish from E2E tests (which use "pwt.")

Part of Phase B: Invitation Code Testing
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.invitation_code import InvitationCode


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def admin_token(client: TestClient, admin_user) -> str:
    """Get admin authentication token"""
    # Admin user created by admin_user fixture
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@lfa.com",
            "password": "admin123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# =============================================================================
# TEST GROUP 1: Admin Creates Invitation Codes
# =============================================================================

def test_c1_admin_creates_first_team_invitation_code(client: TestClient, admin_token: str, test_db: Session):
    """
    Test C1.1: Admin creates invitation code for First Team player (Pre category)

    Expected:
    - Code created successfully with 50 bonus credits (CRITICAL: ONLY 50 credits allowed)
    - Code format: INV-YYYYMMDD-XXXXXX
    - Email restriction: api.k1sqx1@f1stteam.hu
    - Valid for 7 days
    """
    response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 1 - Pre Category",
            "invited_email": "api.k1sqx1@f1stteam.hu",  # Email restricted with api. prefix
            "bonus_credits": 50,  # CRITICAL: 50 credits only
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Pre category (age 6-11)"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "code" in data
    assert "invited_name" in data
    assert data["invited_name"] == "API Test - First Team Player 1 - Pre Category"
    assert data["bonus_credits"] == 50  # CRITICAL: Must be 50
    assert data["invited_email"] == "api.k1sqx1@f1stteam.hu"
    assert data["is_used"] is False
    assert data["is_valid"] is True

    # Verify code format: INV-YYYYMMDD-XXXXXX
    code = data["code"]
    assert code.startswith("INV-")
    parts = code.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 6  # Random string

    # Verify in database
    db_code = test_db.query(InvitationCode).filter(InvitationCode.code == code).first()
    assert db_code is not None
    assert db_code.invited_name == "API Test - First Team Player 1 - Pre Category"
    assert db_code.bonus_credits == 50  # CRITICAL: Verify 50 credits
    assert db_code.invited_email == "api.k1sqx1@f1stteam.hu"

    print(f"\n✅ API Test - First Team invitation code created: {code} (50 credits, Pre category)")


def test_c2_admin_creates_second_first_team_invitation_code(client: TestClient, admin_token: str, test_db: Session):
    """
    Test C1.2: Admin creates second invitation code for First Team player (Youth category)

    Expected:
    - Code created successfully with 50 bonus credits (CRITICAL: ONLY 50 credits allowed)
    - Different code from first test
    - Email restriction: api.p3t1k3@f1stteam.hu
    """
    # Create first code to ensure we have at least one
    client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 1 - Pre Category",
            "invited_email": "api.k1sqx1@f1stteam.hu",
            "bonus_credits": 50,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Pre category (age 6-11)"
        }
    )

    # Now create second code
    response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 2 - Youth Category",
            "invited_email": "api.p3t1k3@f1stteam.hu",  # Email restricted with api. prefix
            "bonus_credits": 50,  # CRITICAL: 50 credits only
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Youth category (age 12-17)"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["invited_name"] == "API Test - First Team Player 2 - Youth Category"
    assert data["bonus_credits"] == 50  # CRITICAL: Must be 50
    assert data["invited_email"] == "api.p3t1k3@f1stteam.hu"
    assert data["is_used"] is False
    assert data["is_valid"] is True

    # Verify code uniqueness
    all_codes = test_db.query(InvitationCode).filter(
        InvitationCode.invited_name.like("API Test - First Team Player%")
    ).all()

    # Should have exactly 2 codes now
    assert len(all_codes) == 2

    # All codes should be unique
    code_values = [c.code for c in all_codes]
    assert len(code_values) == len(set(code_values))

    print(f"\n✅ API Test - Second First Team invitation code created: {data['code']} (50 credits, Youth category)")


def test_c3_admin_creates_third_first_team_invitation_code(client: TestClient, admin_token: str, test_db: Session):
    """
    Test C1.3: Admin creates third invitation code for First Team player (Amateur category)

    Expected:
    - Code created successfully with 50 bonus credits (CRITICAL: ONLY 50 credits allowed)
    - Different code from previous tests
    - Email restriction: api.V4lv3rd3jr@f1stteam.hu
    """
    # Create first two codes
    client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 1 - Pre Category",
            "invited_email": "api.k1sqx1@f1stteam.hu",
            "bonus_credits": 50,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Pre category (age 6-11)"
        }
    )

    client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 2 - Youth Category",
            "invited_email": "api.p3t1k3@f1stteam.hu",
            "bonus_credits": 50,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Youth category (age 12-17)"
        }
    )

    # Now create third code
    response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 3 - Amateur Category",
            "invited_email": "api.V4lv3rd3jr@f1stteam.hu",  # Email restricted with api. prefix
            "bonus_credits": 50,  # CRITICAL: 50 credits only
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Amateur category (age 18+)"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["invited_name"] == "API Test - First Team Player 3 - Amateur Category"
    assert data["bonus_credits"] == 50  # CRITICAL: Must be 50
    assert data["invited_email"] == "api.V4lv3rd3jr@f1stteam.hu"
    assert data["is_used"] is False
    assert data["is_valid"] is True

    # Verify we now have exactly 3 First Team codes
    all_codes = test_db.query(InvitationCode).filter(
        InvitationCode.invited_name.like("API Test - First Team Player%")
    ).all()

    assert len(all_codes) == 3

    # All codes should be unique
    code_values = [c.code for c in all_codes]
    assert len(code_values) == len(set(code_values))

    print(f"\n✅ API Test - Third First Team invitation code created: {data['code']} (50 credits, Amateur category)")
    print(f"✅ Total API Test First Team codes: {len(all_codes)}")


# =============================================================================
# TEST GROUP 2: Admin Retrieves Invitation Codes
# =============================================================================

def test_c4_admin_gets_all_invitation_codes(client: TestClient, admin_token: str, test_db: Session):
    """
    Test C2.1: Admin retrieves all invitation codes

    Expected:
    - Returns list of all codes including the 3 First Team codes
    - Each code has full details (created_by, is_valid, etc.)
    """
    # Create 3 invitation codes first
    for i, (name, email, category) in enumerate([
        ("API Test - First Team Player 1 - Pre Category", "api.k1sqx1@f1stteam.hu", "Pre"),
        ("API Test - First Team Player 2 - Youth Category", "api.p3t1k3@f1stteam.hu", "Youth"),
        ("API Test - First Team Player 3 - Amateur Category", "api.V4lv3rd3jr@f1stteam.hu", "Amateur")
    ], 1):
        client.post(
            "/api/v1/admin/invitation-codes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "invited_name": name,
                "invited_email": email,
                "bonus_credits": 50,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "notes": f"API Test - First Team - {category} category"
            }
        )

    response = client.get(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 3  # At least the 3 First Team codes

    # Find our API Test First Team codes
    first_team_codes = [c for c in data if "API Test - First Team Player" in c.get("invited_name", "")]

    assert len(first_team_codes) == 3

    # Verify each code has required fields
    for code in first_team_codes:
        assert "code" in code
        assert "invited_name" in code
        assert "bonus_credits" in code
        assert code["bonus_credits"] == 50  # CRITICAL: Must be 50
        assert "is_used" in code
        assert code["is_used"] is False  # Not used yet
        assert "is_valid" in code
        assert code["is_valid"] is True
        assert "created_by_name" in code
        assert code["created_by_name"] == "Admin User"  # Created by admin

    print(f"\n✅ Admin retrieved {len(data)} invitation codes")
    print(f"✅ API Test First Team codes: {len(first_team_codes)}")


# =============================================================================
# TEST GROUP 3: Invitation Code Validation
# =============================================================================

def test_c5_validate_invitation_code_success(client: TestClient, test_db: Session, admin_token: str):
    """
    Test C3.1: Validate a valid invitation code (no auth required)

    Expected:
    - Returns code details and bonus credits
    - Confirms code is valid
    """
    # Create an invitation code first
    create_response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "API Test - First Team Player 1 - Pre Category",
            "invited_email": "api.k1sqx1@f1stteam.hu",
            "bonus_credits": 50,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "notes": "API Test - First Team - Pre category (age 6-11)"
        }
    )

    assert create_response.status_code == 200
    created_code = create_response.json()["code"]

    # Now validate it
    response = client.post(
        "/api/v1/invitation-codes/validate",
        json={
            "code": created_code
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["valid"] is True
    assert data["bonus_credits"] == 50  # CRITICAL: Must be 50
    assert data["invited_name"] == "API Test - First Team Player 1 - Pre Category"

    print(f"\n✅ Validated invitation code: {created_code}")


def test_c6_validate_nonexistent_invitation_code(client: TestClient):
    """
    Test C3.2: Validate a non-existent invitation code

    Expected:
    - Returns 404 error
    """
    response = client.post(
        "/api/v1/invitation-codes/validate",
        json={
            "code": "INV-99999999-XXXXXX"
        }
    )

    assert response.status_code == 404
    data = response.json()
    # Check if response uses 'detail' or 'error' format
    if "detail" in data:
        assert "not found" in data["detail"].lower()
    elif "error" in data:
        assert "not found" in data["error"]["message"].lower()
    else:
        raise AssertionError(f"Unexpected response format: {data}")


# =============================================================================
# TEST GROUP 4: Error Cases
# =============================================================================

def test_c7_admin_creates_code_with_invalid_credits(client: TestClient, admin_token: str):
    """
    Test C4.1: Admin tries to create code with 0 or negative credits

    Expected:
    - Returns 400 error
    """
    response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "invited_name": "Invalid Credits Test",
            "bonus_credits": 0,  # Invalid
            "expires_at": None,
            "notes": None
        }
    )

    assert response.status_code == 400
    data = response.json()
    # Check if response uses 'detail' or 'error' format
    if "detail" in data:
        assert "positive" in data["detail"].lower()
    elif "error" in data:
        assert "positive" in data["error"]["message"].lower()
    else:
        raise AssertionError(f"Unexpected response format: {data}")


def test_c8_non_admin_cannot_create_invitation_code(client: TestClient, test_db: Session):
    """
    Test C4.2: Non-admin user cannot create invitation codes

    Expected:
    - Returns 401 or 403 error
    """
    # Create a regular student user
    from app.core.security import get_password_hash

    student = User(
        email="student_test@lfa.com",
        password_hash=get_password_hash("password123"),
        name="Test Student",
        first_name="Test",
        last_name="Student",
        nickname="Testy",
        phone="+36201234567",
        role="STUDENT",
        is_active=True,
        credit_balance=0
    )
    test_db.add(student)
    test_db.commit()

    # Login as student
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "student_test@lfa.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    student_token = response.json()["access_token"]

    # Try to create invitation code
    response = client.post(
        "/api/v1/admin/invitation-codes",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "invited_name": "Should Fail",
            "bonus_credits": 100,
            "expires_at": None,
            "notes": None
        }
    )

    # Should fail with 401 or 403
    assert response.status_code in [401, 403]

    # Cleanup
    test_db.delete(student)
    test_db.commit()
