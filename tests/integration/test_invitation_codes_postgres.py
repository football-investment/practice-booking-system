"""
PostgreSQL-based Integration Tests for Invitation Code System

CRITICAL DIFFERENCE from tests/api/test_invitation_codes.py:
- This test suite writes to REAL PostgreSQL database
- Data PERSISTS after tests complete
- Users visible in Admin Dashboard frontend
- Purpose: Controlled test data seeding + UI validation

Email prefix: "api." (e.g., api.k1sqx1@f1stteam.hu)
This distinguishes API-created users from Playwright E2E users (pwt. prefix)

⚠️ WARNING: Requires manual cleanup between test runs

USAGE:
    # Run these tests to seed test data for UI validation
    pytest tests/integration/test_invitation_codes_postgres.py -v

    # Then check Admin Dashboard to see api.* users
    # Navigate to: http://localhost:8501/Admin_Dashboard

Part of Phase B: Invitation Code Testing (PostgreSQL Variant)
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.invitation_code import InvitationCode


# =============================================================================
# TEST GROUP 1: Create 3 Invitation Codes (Persist to PostgreSQL)
# =============================================================================

@pytest.mark.integration
@pytest.mark.postgres
def test_pg1_create_first_team_invitation_codes(
    postgres_client: TestClient,
    postgres_admin_token: str,
    postgres_db: Session
):
    """
    Integration Test PG1: Create 3 invitation codes in PostgreSQL

    CRITICAL REQUIREMENTS:
    - Writes to REAL PostgreSQL database
    - Codes PERSIST after test completes
    - Visible in Admin Dashboard UI
    - Email prefix: "api." (api.k1sqx1@f1stteam.hu, etc.)
    - Bonus credits: 50 ONLY

    Expected Result:
    - 3 invitation codes created in PostgreSQL
    - Admin can see them at http://localhost:8501/Admin_Dashboard
    - Each code has 50 bonus credits
    """
    print("\n" + "="*80)
    print("🔥 INTEGRATION TEST: Creating invitation codes in PostgreSQL")
    print("="*80)

    invitation_codes = []
    categories = [
        ("Pre Category", "api.k1sqx1@f1stteam.hu", "Pre (age 6-11)"),
        ("Youth Category", "api.p3t1k3@f1stteam.hu", "Youth (age 12-17)"),
        ("Amateur Category", "api.V4lv3rd3jr@f1stteam.hu", "Amateur (age 18+)")
    ]

    for i, (category, email, description) in enumerate(categories, 1):
        print(f"\n📝 Creating invitation code {i}/3: {category}")

        response = postgres_client.post(
            "/api/v1/admin/invitation-codes",
            headers={"Authorization": f"Bearer {postgres_admin_token}"},
            json={
                "invited_name": f"API Test - First Team Player {i} - {category}",
                "invited_email": email,
                "bonus_credits": 50,  # CRITICAL: 50 credits only
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "notes": f"Integration Test - First Team - {description}"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["invited_name"] == f"API Test - First Team Player {i} - {category}"
        assert data["bonus_credits"] == 50
        assert data["invited_email"] == email
        assert data["is_used"] is False
        assert data["is_valid"] is True

        code = data["code"]
        invitation_codes.append(code)

        print(f"✅ Code created: {code}")
        print(f"   Email: {email}")
        print(f"   Credits: 50")
        print(f"   Category: {category}")

    # Verify all codes are unique
    assert len(invitation_codes) == 3
    assert len(set(invitation_codes)) == 3

    # Verify codes exist in PostgreSQL database
    db_codes = postgres_db.query(InvitationCode).filter(
        InvitationCode.invited_name.like("API Test - First Team Player%")
    ).all()

    assert len(db_codes) >= 3  # At least our 3 codes (might be more from previous runs)

    print("\n" + "="*80)
    print("✅ SUCCESS: 3 invitation codes created in PostgreSQL")
    print("="*80)
    print("\n📊 VERIFICATION:")
    print("   1. Open Admin Dashboard: http://localhost:8501/Admin_Dashboard")
    print("   2. Check 'Invitation Codes' section")
    print("   3. You should see 3 codes with emails:")
    print(f"      - {categories[0][1]}")
    print(f"      - {categories[1][1]}")
    print(f"      - {categories[2][1]}")
    print("\n💾 Data persists in PostgreSQL database 'lfa_intern_system'")
    print("="*80 + "\n")


# =============================================================================
# TEST GROUP 2: Verify Codes in PostgreSQL Database
# =============================================================================

@pytest.mark.integration
@pytest.mark.postgres
def test_pg2_verify_codes_in_database(postgres_db: Session):
    """
    Integration Test PG2: Verify invitation codes exist in PostgreSQL

    Expected:
    - At least 3 codes exist with "api." email prefix
    - Codes are NOT marked as used
    - Each has 50 bonus credits
    """
    print("\n" + "="*80)
    print("🔍 VERIFICATION: Checking PostgreSQL database")
    print("="*80)

    # Query PostgreSQL for api. prefix codes
    api_codes = postgres_db.query(InvitationCode).filter(
        InvitationCode.invited_email.like("api.%")
    ).all()

    print(f"\n📊 Found {len(api_codes)} invitation codes with 'api.' prefix")

    # We expect at least 3 codes (from previous test)
    assert len(api_codes) >= 3, f"Expected at least 3 codes, found {len(api_codes)}"

    # Verify each code
    for code in api_codes:
        print(f"\n   Code: {code.code}")
        print(f"   Email: {code.invited_email}")
        print(f"   Credits: {code.bonus_credits}")
        print(f"   Used: {code.is_used}")
        print(f"   Valid: {code.is_valid()}")

        # Assertions
        assert code.bonus_credits == 50, f"Expected 50 credits, got {code.bonus_credits}"
        assert code.invited_email.startswith("api."), f"Email should start with 'api.', got {code.invited_email}"

    print("\n✅ All codes verified successfully")
    print("="*80 + "\n")


# =============================================================================
# TEST GROUP 3: Cleanup Utilities (Manual - not auto-run)
# =============================================================================

@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.skip(reason="Manual cleanup only - run explicitly when needed")
def test_pg_cleanup_api_test_data(postgres_db: Session):
    """
    Manual Cleanup: Remove all api.* test data from PostgreSQL

    ⚠️ WARNING: This deletes data! Only run when you want to clean up.

    Usage:
        pytest tests/integration/test_invitation_codes_postgres.py::test_pg_cleanup_api_test_data -v
    """
    print("\n" + "="*80)
    print("🗑️  CLEANUP: Removing api.* test data from PostgreSQL")
    print("="*80)

    # Delete invitation codes with api.* emails
    codes = postgres_db.query(InvitationCode).filter(
        InvitationCode.invited_email.like("api.%")
    ).all()

    code_count = len(codes)
    for code in codes:
        print(f"   Deleting code: {code.code} ({code.invited_email})")
        postgres_db.delete(code)

    # Delete users with api.* emails
    users = postgres_db.query(User).filter(
        User.email.like("api.%")
    ).all()

    user_count = len(users)
    for user in users:
        print(f"   Deleting user: {user.email}")
        postgres_db.delete(user)

    postgres_db.commit()

    print(f"\n✅ Cleanup complete:")
    print(f"   - Deleted {code_count} invitation codes")
    print(f"   - Deleted {user_count} users")
    print("="*80 + "\n")


# =============================================================================
# DOCUMENTATION
# =============================================================================

"""
USAGE GUIDE
===========

1. SEED TEST DATA (Create invitation codes in PostgreSQL):

   pytest tests/integration/test_invitation_codes_postgres.py::test_pg1_create_first_team_invitation_codes -v

   Result: 3 invitation codes with "api." prefix created in PostgreSQL


2. VERIFY IN ADMIN DASHBOARD:

   a) Open browser: http://localhost:8501/Admin_Dashboard
   b) Login as admin (admin@lfa.com / admin123)
   c) Navigate to "Invitation Codes" section
   d) You should see codes with emails:
      - api.k1sqx1@f1stteam.hu
      - api.p3t1k3@f1stteam.hu
      - api.V4lv3rd3jr@f1stteam.hu


3. VERIFY IN DATABASE:

   pytest tests/integration/test_invitation_codes_postgres.py::test_pg2_verify_codes_in_database -v

   Or via psql:

   psql -U postgres -d lfa_intern_system -c "SELECT code, invited_email, bonus_credits FROM invitation_codes WHERE invited_email LIKE 'api.%';"


4. CLEANUP (Manual - only when needed):

   pytest tests/integration/test_invitation_codes_postgres.py::test_pg_cleanup_api_test_data -v

   This removes ALL api.* test data from PostgreSQL.


COMPARISON WITH tests/api/test_invitation_codes.py
===================================================

┌────────────────────────────────────────────────────────────────────┐
│  tests/api/test_invitation_codes.py (Unit Tests)                  │
├────────────────────────────────────────────────────────────────────┤
│  Database:     SQLite in-memory                                    │
│  Persistence:  ❌ NO (destroyed after each test)                   │
│  UI Visible:   ❌ NO (data never reaches PostgreSQL)               │
│  Purpose:      Fast unit testing, business logic validation        │
│  Prefix:       "api." (but irrelevant since not visible)           │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  tests/integration/test_invitation_codes_postgres.py (This File)  │
├────────────────────────────────────────────────────────────────────┤
│  Database:     PostgreSQL (lfa_intern_system)                      │
│  Persistence:  ✅ YES (data persists after tests)                  │
│  UI Visible:   ✅ YES (visible in Admin Dashboard)                 │
│  Purpose:      UI validation, controlled test data seeding         │
│  Prefix:       "api." (distinguishes from pwt. E2E test users)     │
└────────────────────────────────────────────────────────────────────┘

PREFIX STRATEGY
===============

api.* = API/Integration tests (PostgreSQL) - Visible in UI
pwt.* = Playwright E2E tests (PostgreSQL) - Visible in UI

Both persist to PostgreSQL, both visible in Admin Dashboard.
The prefix allows you to identify the source of test data in the UI.
"""
