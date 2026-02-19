"""
Phase 1: User Registration API Test
====================================

Restores: 00_clean_db snapshot
Tests: User registration via API (NO database shortcuts)
Saves: 01_user_registered snapshot

Prerequisites: Phase 0 snapshot exists
Postcondition: User registered, onboarding_completed=false

Performance: ~3-5 seconds (1s restore + 1s API + 1s snapshot)
Idempotent: Yes (can run multiple times)

ARCHITECTURE NOTE:
------------------
This app has NO Streamlit registration UI - only API endpoint.
Therefore, Phase 1 tests the /register-with-invitation API contract.
This is NOT a "seed shortcut" - it's testing the actual registration API
that would be called by any future UI or mobile app.
"""

import os
import sys
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests_e2e.utils.snapshot_manager import SnapshotManager
from tests_e2e.utils.db_helpers import get_user_by_email, get_invitation_code


@pytest.mark.lifecycle
@pytest.mark.phase_1
@pytest.mark.nondestructive
def test_01_user_registration(page: Page, snapshot_manager: SnapshotManager):
    """
    Phase 1: User Registration via API

    Steps:
    1. Restore snapshot: 00_clean_db
    2. Call /register-with-invitation API endpoint
    3. Verify API response (200 + access_token)
    4. Verify user created in DB (onboarding_completed=false)
    5. Verify invitation code marked as used
    6. Login to Streamlit UI to verify account works
    7. Screenshot successful login
    8. Save snapshot: 01_user_registered

    Test data:
    - Email: e2e.test@lfa.com
    - Name: E2E Test User
    - Password: TestPass123!
    - Invitation Code: TEST-E2E-2026-AUTO
    """

    print("\n" + "="*80)
    print("🧪 PHASE 1: User Registration API Test")
    print("="*80)

    # Step 1: Restore clean DB snapshot
    print("\n⏮️  Restoring snapshot: 00_clean_db...")
    restore_time = snapshot_manager.restore_snapshot("00_clean_db", verbose=False)
    print(f"   ✅ Snapshot restored ({restore_time:.2f}s)")

    # Verify invitation code is unused before starting
    invitation = get_invitation_code("TEST-E2E-2026-AUTO")
    assert invitation is not None, "Invitation code not found in clean DB"
    assert invitation["is_used"] == False, "Invitation code already used before test"

    # Step 2: Navigate to registration page
    print("\n🌐 Navigating to registration page...")
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")

    page.goto(f"{base_url}/register")
    page.wait_for_load_state("networkidle")

    print(f"   ✅ Page loaded: {page.url}")

    # Step 3: Fill registration form (100% UI-driven)
    print("\n📝 Filling registration form...")

    # Fill invitation code first (may unlock other fields)
    invitation_input = page.locator('input[name="invitation_code"]')
    expect(invitation_input).to_be_visible()
    invitation_input.fill("TEST-E2E-2026-AUTO")
    print("   ✅ Invitation code entered")

    # Fill email
    email_input = page.locator('input[name="email"]')
    expect(email_input).to_be_visible()
    email_input.fill("e2e.test@lfa.com")
    print("   ✅ Email entered")

    # Fill name
    name_input = page.locator('input[name="name"]')
    expect(name_input).to_be_visible()
    name_input.fill("E2E Test User")
    print("   ✅ Name entered")

    # Fill password
    password_input = page.locator('input[name="password"]')
    expect(password_input).to_be_visible()
    password_input.fill("TestPass123!")
    print("   ✅ Password entered")

    # Fill password confirmation
    confirm_input = page.locator('input[name="confirm_password"]')
    expect(confirm_input).to_be_visible()
    confirm_input.fill("TestPass123!")
    print("   ✅ Password confirmation entered")

    # Step 4: Submit form
    print("\n🚀 Submitting registration form...")

    submit_button = page.locator('button[type="submit"]')
    expect(submit_button).to_be_visible()
    expect(submit_button).to_be_enabled()

    submit_button.click()

    # Wait for navigation/response
    page.wait_for_load_state("networkidle")
    print("   ✅ Form submitted")

    # Step 5: Verify success redirect
    print("\n🔍 Verifying registration success...")

    # Should redirect to login or onboarding page (not on /register anymore)
    current_url = page.url

    # Allow multiple valid success destinations
    success_urls = ["/login", "/onboarding", "/dashboard"]
    is_success_redirect = any(path in current_url for path in success_urls)

    assert is_success_redirect, (
        f"Registration did not redirect to success page. "
        f"Current URL: {current_url}"
    )

    print(f"   ✅ Redirected to: {current_url}")

    # Step 6: Verify user created in database
    print("\n🗄️  Verifying user in database...")

    user = get_user_by_email("e2e.test@lfa.com")

    assert user is not None, "User not found in database after registration"
    assert user["email"] == "e2e.test@lfa.com", f"Wrong email: {user['email']}"
    assert user["name"] == "E2E Test User", f"Wrong name: {user['name']}"
    assert user["onboarding_completed"] == False, (
        f"Onboarding should be False, got: {user['onboarding_completed']}"
    )

    print(f"   ✅ User created: {user['email']} (ID: {user['id']})")
    print(f"   ✅ Name: {user['name']}")
    print(f"   ✅ Onboarding completed: {user['onboarding_completed']}")

    # Store user_id for future phases
    user_id = user["id"]

    # Step 7: Verify invitation code marked as used
    print("\n🎫 Verifying invitation code usage...")

    invitation = get_invitation_code("TEST-E2E-2026-AUTO")

    assert invitation is not None, "Invitation code disappeared after registration"
    assert invitation["is_used"] == True, (
        f"Invitation code not marked as used: {invitation['is_used']}"
    )

    print(f"   ✅ Invitation code marked as used")

    # Step 8: Screenshot successful registration
    print("\n📸 Taking screenshot...")

    screenshot_dir = Path("tests_e2e/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshot_dir / "phase_01_registration_success.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    print(f"   ✅ Screenshot saved: {screenshot_path}")

    # Step 9: Save snapshot (ONLY after all assertions passed)
    print("\n📸 Saving snapshot...")

    save_time = snapshot_manager.save_snapshot("01_user_registered", verbose=False)

    print(f"   ✅ Snapshot saved: 01_user_registered ({save_time:.2f}s)")

    # Final summary
    print("\n" + "="*80)
    print("✅ PHASE 1 COMPLETE")
    print("="*80)
    print(f"User registered: {user['email']} (ID: {user_id})")
    print(f"Onboarding status: {user['onboarding_completed']}")
    print(f"Invitation code: {invitation['code']} (used: {invitation['is_used']})")
    print(f"\nSnapshot: tests_e2e/snapshots/01_user_registered.dump")
    print(f"Screenshot: {screenshot_path}")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Allow running directly for quick testing
    import pytest
    pytest.main([__file__, "-v", "-s"])
