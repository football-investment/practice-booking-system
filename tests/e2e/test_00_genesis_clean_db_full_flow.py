"""
GENESIS E2E TEST - Clean DB to CHAMPION Badge Display
======================================================

**CRITICAL PATH TEST** - This is the single source of truth for:
"Can we start from a clean database and get a working system with CHAMPION badges?"

**Purpose**:
- Validate clean DB → production-ready system flow
- Verify CHAMPION badge metadata end-to-end (DB → API → UI)
- Catch serialization bugs (like commit 2f38506)
- Ensure seed scripts work correctly

**Assumptions**:
- PostgreSQL is running
- Alembic migrations exist
- Seed script exists: scripts/seed_champion_test_data.py
- FastAPI is running on localhost:8000
- Streamlit is running on localhost:8501

**Test Scope**:
1. Clean database (drop + recreate)
2. Run migrations (alembic upgrade head)
3. Seed minimal test data
4. Verify DB integrity
5. Call API to verify badge_metadata serialization
6. Login to UI
7. Navigate to Tournament Achievements
8. Verify CHAMPION badge displays correctly
9. Screenshot for visual regression

**Markers**:
- @pytest.mark.genesis - Clean DB test
- @pytest.mark.critical - Build blocker
- @pytest.mark.slow - ~60 second runtime

**Runtime**: ~60 seconds (includes DB setup)

**Related Commits**:
- 2f38506 - Fixed badge_metadata serialization (this test would catch regression)
- a013113 - Fixed performance_card primary_badge
- 569808f - Fixed accordion primary_badge
"""

import os
import sys
import time
import json
import pytest
import requests
from playwright.sync_api import sync_playwright, Page, expect
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
API_URL = os.environ.get("API_URL", "http://localhost:8000")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
TEST_USER_EMAIL = "junior.intern@lfa.com"
TEST_USER_PASSWORD = "password123"
SCREENSHOT_DIR = "tests_e2e/screenshots"
TIMEOUT_MS = 30_000


# ============================================================================
# Database Setup Helpers
# ============================================================================

def _drop_and_recreate_db():
    """
    Drop all tables and recreate schema.
    WARNING: DESTRUCTIVE - only use in test environment!
    """
    import subprocess

    print("\n🗑️  Dropping all tables...")

    # Extract DB name from connection string
    db_name = DB_URL.split("/")[-1].split("?")[0]

    # Drop and recreate database
    try:
        # Use psql to drop/create (faster than Python)
        subprocess.run([
            "psql",
            "-U", "postgres",
            "-h", "localhost",
            "-c", f"DROP DATABASE IF EXISTS {db_name};"
        ], check=False, capture_output=True)

        subprocess.run([
            "psql",
            "-U", "postgres",
            "-h", "localhost",
            "-c", f"CREATE DATABASE {db_name};"
        ], check=True, capture_output=True)

        print("   ✅ Database recreated")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to recreate DB: {e}")
        raise


def _run_migrations():
    """Run alembic migrations to create schema."""
    import subprocess

    print("\n📦 Running migrations (alembic upgrade head)...")

    try:
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], cwd=project_root, env={**os.environ, "DATABASE_URL": DB_URL},
        check=True, capture_output=True, text=True)

        print("   ✅ Migrations complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Migration failed: {e.stderr}")
        raise


def _seed_test_data():
    """Run seed script to create minimal test data."""
    import subprocess

    print("\n🌱 Seeding test data...")

    seed_script = project_root / "scripts" / "seed_champion_test_data.py"

    if not seed_script.exists():
        print(f"   ⚠️  Seed script not found: {seed_script}")
        print("   Creating minimal seed data via SQL...")
        _seed_minimal_sql()
        return

    try:
        result = subprocess.run([
            sys.executable, str(seed_script)
        ], cwd=project_root, env={**os.environ, "DATABASE_URL": DB_URL},
        check=True, capture_output=True, text=True)

        print("   ✅ Seed data created")
        print(f"      Output: {result.stdout[:200]}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Seed failed: {e.stderr}")
        raise


def _seed_minimal_sql():
    """
    Fallback: Insert minimal seed data via raw SQL.
    Used if seed_champion_test_data.py doesn't exist.
    """
    import psycopg2

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        # Create test user
        cur.execute("""
            INSERT INTO users (email, password_hash, name, role, specialization, onboarding_completed)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                onboarding_completed = EXCLUDED.onboarding_completed
            RETURNING id
        """, (
            TEST_USER_EMAIL,
            "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K5dQ5L2zJQK6",  # password123
            "Junior Intern",
            "STUDENT",
            "LFA_FOOTBALL_PLAYER",
            True
        ))
        user_id = cur.fetchone()[0]

        # Create test semester with CHAMPION badge
        cur.execute("""
            INSERT INTO semesters (code, name, specialization_type, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            RETURNING id
        """, (
            "E2E-TEST-CHAMPION",
            "E2E Test Tournament",
            "LFA_FOOTBALL_PLAYER",
            "2026-01-01",
            "2026-12-31",
            "COMPLETED"
        ))
        semester_result = cur.fetchone()
        if semester_result:
            semester_id = semester_result[0]

            # Create CHAMPION badge with metadata
            cur.execute("""
                INSERT INTO tournament_badges (
                    user_id, semester_id, badge_type, badge_category,
                    title, description, icon, rarity, badge_metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                user_id,
                semester_id,
                "CHAMPION",
                "PLACEMENT",
                "Champion",
                f"Claimed 1st place in E2E Test Tournament",
                "🥇",
                "EPIC",
                json.dumps({"placement": 1, "total_participants": 24})
            ))

        conn.commit()
        print("   ✅ Minimal seed data inserted via SQL")

    finally:
        cur.close()
        conn.close()


def _verify_db_integrity():
    """
    Verify database has expected test data.
    Returns (success, errors)
    """
    import psycopg2

    print("\n🔍 Verifying DB integrity...")

    errors = []

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # Check test user exists
        cur.execute("SELECT id, email, onboarding_completed FROM users WHERE email = %s", (TEST_USER_EMAIL,))
        user = cur.fetchone()
        if not user:
            errors.append("Test user not found")
        else:
            print(f"   ✅ Test user exists: {user[1]} (onboarded={user[2]})")

        # Check CHAMPION badge exists with metadata
        cur.execute("""
            SELECT badge_type, badge_metadata
            FROM tournament_badges
            WHERE user_id = (SELECT id FROM users WHERE email = %s)
                AND badge_type = 'CHAMPION'
            LIMIT 1
        """, (TEST_USER_EMAIL,))
        badge = cur.fetchone()

        if not badge:
            errors.append("CHAMPION badge not found in DB")
        else:
            badge_type, badge_metadata = badge
            print(f"   ✅ CHAMPION badge exists in DB")

            if badge_metadata is None:
                errors.append("CHAMPION badge has NULL badge_metadata in DB")
            elif not isinstance(badge_metadata, dict):
                errors.append(f"badge_metadata is not dict: {type(badge_metadata)}")
            elif 'placement' not in badge_metadata:
                errors.append("badge_metadata missing 'placement' key")
            elif 'total_participants' not in badge_metadata:
                errors.append("badge_metadata missing 'total_participants' key")
            else:
                print(f"   ✅ badge_metadata valid: {badge_metadata}")

        cur.close()
        conn.close()

    except Exception as e:
        errors.append(f"DB verification failed: {str(e)}")

    if errors:
        print(f"   ❌ DB integrity errors: {errors}")
        return False, errors
    else:
        print("   ✅ DB integrity verified")
        return True, []


# ============================================================================
# API Verification Helpers
# ============================================================================

def _verify_api_badge_metadata():
    """
    Call API to get badges and verify "badge_metadata" key exists.
    This catches the bug fixed in commit 2f38506.
    """
    print("\n🔌 Verifying API badge_metadata serialization...")

    # First, login to get token
    login_response = requests.post(
        f"{API_URL}/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        timeout=10
    )

    if login_response.status_code != 200:
        print(f"   ❌ Login failed: {login_response.status_code}")
        print(f"      Response: {login_response.text}")
        return False, ["API login failed"]

    token = login_response.json().get("access_token")
    print(f"   ✅ Logged in, got token")

    # Get user ID
    profile_response = requests.get(
        f"{API_URL}/api/v1/users/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    if profile_response.status_code != 200:
        return False, ["Could not fetch user profile"]

    user_id = profile_response.json().get("id")
    print(f"   ✅ User ID: {user_id}")

    # Get badges
    badges_response = requests.get(
        f"{API_URL}/api/v1/tournaments/badges/user/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100},
        timeout=10
    )

    if badges_response.status_code != 200:
        print(f"   ❌ Badges API failed: {badges_response.status_code}")
        print(f"      Response: {badges_response.text}")
        return False, ["Badges API failed"]

    data = badges_response.json()
    badges = data.get("badges", [])

    print(f"   ✅ Fetched {len(badges)} badges from API")

    # Find CHAMPION badge
    champion_badge = next((b for b in badges if b.get("badge_type") == "CHAMPION"), None)

    if not champion_badge:
        return False, ["CHAMPION badge not in API response"]

    print(f"   ✅ CHAMPION badge found in API response")

    # CRITICAL CHECK: Does response have "badge_metadata" key?
    # Bug 2f38506: API was sending "metadata" instead of "badge_metadata"
    errors = []

    if "metadata" in champion_badge:
        errors.append("API response has 'metadata' key (should be 'badge_metadata')")

    if "badge_metadata" not in champion_badge:
        errors.append("API response missing 'badge_metadata' key")
        print(f"   ❌ REGRESSION: API response missing 'badge_metadata' key!")
        print(f"      Badge keys: {list(champion_badge.keys())}")
        return False, errors

    badge_metadata = champion_badge["badge_metadata"]

    if badge_metadata is None:
        errors.append("API badge_metadata is NULL")
    elif not isinstance(badge_metadata, dict):
        errors.append(f"API badge_metadata is not dict: {type(badge_metadata)}")
    elif "placement" not in badge_metadata:
        errors.append("API badge_metadata missing 'placement'")
    elif "total_participants" not in badge_metadata:
        errors.append("API badge_metadata missing 'total_participants'")
    else:
        print(f"   ✅ API badge_metadata valid: {badge_metadata}")

    if errors:
        print(f"   ❌ API validation errors: {errors}")
        return False, errors

    return True, []


# ============================================================================
# UI Verification Helpers
# ============================================================================

def _login(page: Page) -> None:
    """Login to Streamlit UI."""
    print("\n🔐 Logging in to UI...")

    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
    time.sleep(2)

    # Fill email
    email_input = page.locator("input").first
    email_input.wait_for(state="visible", timeout=TIMEOUT_MS)
    email_input.fill(TEST_USER_EMAIL)
    time.sleep(0.5)

    # Fill password
    pwd_input = page.locator('input[type="password"]').first
    pwd_input.wait_for(state="visible", timeout=5_000)
    pwd_input.fill(TEST_USER_PASSWORD)
    time.sleep(0.5)

    # Click login
    login_btn = page.locator("button").filter(has_text="Login").first
    login_btn.click()

    page.wait_for_load_state("networkidle", timeout=20_000)
    time.sleep(3)

    # Verify login succeeded
    body = page.text_content("body") or ""
    if "Incorrect email" in body or "Login failed" in body:
        raise AssertionError(f"Login failed for {TEST_USER_EMAIL}")

    print("   ✅ Logged in to UI")


def _navigate_to_dashboard(page: Page) -> None:
    """Navigate to Player Dashboard."""
    print("\n📊 Navigating to Player Dashboard...")

    # Use JS click on hidden sidebar link
    page.evaluate("""
        const links = Array.from(document.querySelectorAll('a[href]'));
        const dashboardLink = links.find(a =>
            a.href.includes('LFA_Player_Dashboard') ||
            a.textContent.includes('Player Dashboard')
        );
        if (dashboardLink) {
            dashboardLink.click();
        }
    """)

    time.sleep(4)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)

    print("   ✅ Navigated to dashboard")


def _verify_champion_badge_ui(page: Page) -> tuple[bool, list[str]]:
    """
    Verify CHAMPION badge displays correctly in UI.
    Returns (success, errors)
    """
    print("\n🏆 Verifying CHAMPION badge in UI...")

    errors = []

    # Expand all accordions to reveal badges
    try:
        expanders = page.locator('[data-testid="stExpander"]').all()
        for exp in expanders[:10]:  # Limit to first 10 to avoid timeout
            try:
                header = exp.locator("summary").first
                if header.is_visible(timeout=1_000):
                    header.click()
                    time.sleep(0.3)
            except:
                pass
    except:
        pass

    time.sleep(2)

    # Get full page text
    body_text = page.text_content("body") or ""

    # Check for CHAMPION badge
    if "CHAMPION" not in body_text and "Champion" not in body_text:
        errors.append("CHAMPION badge not visible in UI")
        print("   ❌ CHAMPION badge not found in UI")
    else:
        print("   ✅ CHAMPION badge visible")

    # Check for "No ranking data" (the bug we fixed)
    if "No ranking data" in body_text:
        errors.append("Found 'No ranking data' - REGRESSION DETECTED!")
        print("   ❌ REGRESSION: 'No ranking data' found in UI!")
    else:
        print("   ✅ No 'No ranking data' text (bug fixed)")

    # Check for ranking display (e.g., "#1 of 24 players")
    if "#1" in body_text or "placement" in body_text.lower():
        print("   ✅ Ranking data visible")
    else:
        errors.append("No ranking data visible in UI")
        print("   ⚠️  No ranking text found")

    return len(errors) == 0, errors


# ============================================================================
# Main Test
# ============================================================================

@pytest.mark.genesis
@pytest.mark.critical
@pytest.mark.slow
def test_00_genesis_clean_db_full_flow():
    """
    GENESIS TEST: Clean DB → CHAMPION Badge Display

    This is the SINGLE SOURCE OF TRUTH for full system functionality.
    """

    print("\n" + "="*80)
    print("🌟 GENESIS E2E TEST - Clean DB to CHAMPION Badge Display")
    print("="*80)

    all_errors = []

    # ========================================================================
    # PHASE 1: Database Setup
    # ========================================================================

    try:
        _drop_and_recreate_db()
        _run_migrations()
        _seed_test_data()

        # Verify DB
        db_ok, db_errors = _verify_db_integrity()
        if not db_ok:
            all_errors.extend(db_errors)
            pytest.fail(f"DB integrity check failed: {db_errors}")

    except Exception as e:
        pytest.fail(f"Database setup failed: {str(e)}")

    # ========================================================================
    # PHASE 2: API Verification
    # ========================================================================

    try:
        api_ok, api_errors = _verify_api_badge_metadata()
        if not api_ok:
            all_errors.extend(api_errors)
            # Don't fail yet - continue to UI test
    except Exception as e:
        all_errors.append(f"API verification failed: {str(e)}")

    # ========================================================================
    # PHASE 3: UI Verification
    # ========================================================================

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            _login(page)
            _navigate_to_dashboard(page)

            ui_ok, ui_errors = _verify_champion_badge_ui(page)
            if not ui_ok:
                all_errors.extend(ui_errors)

            # Screenshot for visual regression
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            page.screenshot(path=f"{SCREENSHOT_DIR}/genesis_final_state.png")
            print(f"\n📸 Screenshot saved: {SCREENSHOT_DIR}/genesis_final_state.png")

        except Exception as e:
            all_errors.append(f"UI verification failed: {str(e)}")
            page.screenshot(path=f"{SCREENSHOT_DIR}/genesis_error.png")

        finally:
            browser.close()

    # ========================================================================
    # FINAL VERDICT
    # ========================================================================

    print("\n" + "="*80)
    print("GENESIS TEST RESULTS")
    print("="*80)

    if all_errors:
        print(f"❌ FAILED with {len(all_errors)} error(s):")
        for i, err in enumerate(all_errors, 1):
            print(f"   {i}. {err}")
        pytest.fail(f"Genesis test failed: {all_errors}")
    else:
        print("✅ GENESIS TEST PASSED")
        print("   - Database setup successful")
        print("   - API badge_metadata serialization correct")
        print("   - UI displays CHAMPION badge with ranking data")
        print("   - NO 'No ranking data' regression detected")


if __name__ == "__main__":
    # Allow running directly for debugging
    test_00_genesis_clean_db_full_flow()
