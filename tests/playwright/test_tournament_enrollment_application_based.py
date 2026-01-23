"""
Playwright E2E Test: Tournament Enrollment Flow - APPLICATION_BASED

✅ STATUS: ENABLED - Domain gap resolved (2026-01-12)

Tests the complete player enrollment workflow with APPLICATION_BASED tournament type.

WORKFLOW:
1. Admin creates APPLICATION_BASED tournament via UI (SEEKING_INSTRUCTOR)
2. Grandmaster instructor applies to tournament via UI
3. Admin approves instructor application via UI (→ PENDING_INSTRUCTOR_ACCEPTANCE)
4. Instructor accepts assignment via UI (→ READY_FOR_ENROLLMENT)
5. Admin opens enrollment via UI (→ OPEN_FOR_ENROLLMENT)
6. Three players redeem enrollment coupons (500 credits each)
7. Three players enroll in tournament via UI
8. Admin approves enrollments via UI
9. Players verify CONFIRMED enrollment status

PREREQUISITES:
- Database snapshot: after_onboarding.sql
- 3 onboarded players (pwt.k1sqx1, pwt.p3t1k3, pwt.V4lv3rd3jr)
- Grandmaster instructor exists
- Enrollment coupons created (via setup_enrollment_coupons.py)

DOMAIN GAP RESOLUTION:
- ✅ Database migration added assignment_type, max_players columns
- ✅ SQLAlchemy Semester model updated
- ✅ API schemas and validation added
- ✅ Tournament generator endpoint updated
- ✅ UI form fields added (Assignment Type, Max Players, Price, Instructor Selection)
"""

import pytest
import re
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta


# Test configuration
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
GRANDMASTER_EMAIL = "grandmaster@lfa.com"
GRANDMASTER_PASSWORD = "GrandMaster2026!"

TOURNAMENT_NAME = f"E2E Test Tournament - Application Based {datetime.now().strftime('%Y%m%d%H%M%S')}"


def login(page: Page, email: str, password: str):
    """Helper function to log in."""
    page.goto("http://localhost:8501")
    page.wait_for_timeout(2000)

    # Fill login form
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Login").click()
    page.wait_for_timeout(3000)


def logout(page: Page):
    """Helper function to log out."""
    try:
        page.get_by_role("button", name="Logout").click()
        page.wait_for_timeout(2000)
    except:
        page.goto("http://localhost:8501")
        page.wait_for_timeout(2000)


def take_screenshot(page: Page, name: str):
    """Helper to take screenshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    page.screenshot(path=f"tests/e2e/screenshots/{name}_{timestamp}.png")


def test_f1_admin_creates_application_based_tournament(page: Page):
    """Test 1: Admin creates APPLICATION_BASED tournament via Streamlit UI

    ✅ REAL UI AUTOMATION: Creates tournament through actual Streamlit form interaction

    APPROACH:
    1. Admin logs in and navigates to Create Tournament tab
    2. Fills out form using proper Streamlit selector strategies
    3. Submits form with Assignment Type = APPLICATION_BASED
    4. Validates tournament exists in database with SEEKING_INSTRUCTOR status
    """
    import psycopg2

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "admin_logged_in_app_based")

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "tournament_management_page_app")

    # Click Create Tournament TAB
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(3000)
    take_screenshot(page, "create_tournament_tab_open_app")

    # ========================================================================
    # SECTION 1: Location & Campus Selection (OUTSIDE form)
    # ========================================================================
    print("📍 Step 1: Selecting Location...")
    page.wait_for_timeout(2000)

    try:
        location_label = page.locator("label:has-text('Location *')").first
        location_label.wait_for(timeout=10000)

        location_selectbox = page.locator("label:has-text('Location *')").locator("..").locator("[data-baseweb='select']").first
        location_selectbox.click()
        page.wait_for_timeout(1000)

        page.locator("[role='option']").first.click()
        page.wait_for_timeout(1500)
        print("   ✅ Location selected")
    except Exception as e:
        print(f"   ❌ Location selection failed: {e}")
        take_screenshot(page, "location_selection_error_app")
        raise

    print("🏫 Step 2: Selecting Campus...")
    try:
        campus_label = page.locator("label:has-text('Campus *')").first
        campus_label.wait_for(timeout=10000)

        campus_selectbox = page.locator("label:has-text('Campus *')").locator("..").locator("[data-baseweb='select']").first
        campus_selectbox.click()
        page.wait_for_timeout(1000)

        page.locator("[role='option']").first.click()
        page.wait_for_timeout(1500)
        print("   ✅ Campus selected")
    except Exception as e:
        print(f"   ❌ Campus selection failed: {e}")
        take_screenshot(page, "campus_selection_error_app")
        raise

    # ========================================================================
    # SECTION 2: Form Fields (INSIDE form)
    # ========================================================================
    print("📝 Step 3: Filling tournament form...")

    # Tournament Name
    try:
        tournament_name_input = page.get_by_placeholder("e.g., Winter Football Cup")
        tournament_name_input.click()
        tournament_name_input.fill(TOURNAMENT_NAME)
        page.wait_for_timeout(500)
        print(f"   ✅ Tournament name: {TOURNAMENT_NAME}")
    except Exception as e:
        print(f"   ❌ Tournament name input failed: {e}")
        take_screenshot(page, "tournament_name_error_app")
        raise

    # Tournament Date
    try:
        tournament_date = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")
        date_label = page.locator("label:has-text('Tournament Date *')").first
        date_input = date_label.locator("..").locator("input[type='text']").first
        date_input.click()
        date_input.fill(tournament_date)
        page.wait_for_timeout(500)
        print(f"   ✅ Tournament date: {tournament_date}")
    except Exception as e:
        print(f"   ❌ Tournament date input failed: {e}")
        take_screenshot(page, "tournament_date_error_app")
        raise

    # Age Group
    print("👶 Step 4: Selecting Age Group...")
    try:
        age_label = page.locator("label:has-text('Age Group *')").first
        age_label.wait_for(timeout=10000)

        age_selectbox = page.locator("label:has-text('Age Group *')").locator("..").locator("[data-baseweb='select']").first
        age_selectbox.click()
        page.wait_for_timeout(1000)

        page.locator("[role='option']:has-text('YOUTH')").click()
        page.wait_for_timeout(500)
        print("   ✅ Age Group: YOUTH")
    except Exception as e:
        print(f"   ❌ Age Group selection failed: {e}")
        take_screenshot(page, "age_group_error_app")
        raise

    # Assignment Type - APPLICATION_BASED
    print("🎯 Step 5: Selecting Assignment Type...")
    try:
        assignment_label = page.locator("label:has-text('Assignment Type *')").first
        assignment_label.wait_for(timeout=10000)

        assignment_selectbox = page.locator("label:has-text('Assignment Type *')").locator("..").locator("[data-baseweb='select']").first
        assignment_selectbox.click()
        page.wait_for_timeout(1000)

        page.locator("[role='option']:has-text('APPLICATION_BASED')").click()
        page.wait_for_timeout(1500)
        print("   ✅ Assignment Type: APPLICATION_BASED")
    except Exception as e:
        print(f"   ❌ Assignment Type selection failed: {e}")
        take_screenshot(page, "assignment_type_error_app")
        raise

    # Max Players
    try:
        max_players_label = page.locator("label:has-text('Max Players *')").first
        max_players_input = max_players_label.locator("..").locator("input[type='number']").first
        max_players_input.click()
        max_players_input.fill("5")
        page.wait_for_timeout(500)
        print("   ✅ Max Players: 5")
    except Exception as e:
        print(f"   ❌ Max Players input failed: {e}")
        take_screenshot(page, "max_players_error_app")
        raise

    # Price (Credits)
    try:
        price_label = page.locator("label:has-text('Price (Credits) *')").first
        price_input = price_label.locator("..").locator("input[type='number']").first
        price_input.click()
        price_input.fill("500")
        page.wait_for_timeout(500)
        print("   ✅ Price: 500 credits")
    except Exception as e:
        print(f"   ❌ Price input failed: {e}")
        take_screenshot(page, "price_error_app")
        raise

    take_screenshot(page, "tournament_form_filled_app_based")
    print("✅ All form fields filled!")

    # ========================================================================
    # SECTION 3: Submit Form & Verify Creation
    # ========================================================================
    print("🚀 Step 6: Submitting tournament creation form...")

    try:
        submit_button = page.locator("button:has-text('🏆 Create Tournament')").first
        submit_button.click()
        page.wait_for_timeout(5000)
        print("   ✅ Form submitted")
    except Exception as e:
        print(f"   ❌ Form submission failed: {e}")
        take_screenshot(page, "submit_error_app")
        raise

    take_screenshot(page, "after_tournament_creation_app")

    # Verify success message
    print("✅ Step 7: Verifying success message...")
    try:
        success_message = page.locator("text=/Tournament created successfully/i")
        expect(success_message).to_be_visible(timeout=10000)
        print("   ✅ Success message visible")
    except Exception as e:
        print(f"   ❌ Success message not found: {e}")
        take_screenshot(page, "no_success_message_app")
        raise

    # ========================================================================
    # SECTION 4: Backend Database Validation (CRITICAL)
    # ========================================================================
    print("🔍 Step 8: Validating tournament in database...")

    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, status, tournament_status, assignment_type, max_players, enrollment_cost
        FROM semesters
        WHERE name LIKE %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (f"%{TOURNAMENT_NAME}%",))

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        tournament_id, name, status, tournament_status, assignment_type, max_players, enrollment_cost = result
        print("   ✅ TOURNAMENT FOUND IN DATABASE!")
        print(f"      ID: {tournament_id}")
        print(f"      Name: {name}")
        print(f"      Status: {status}")
        print(f"      Tournament Status: {tournament_status}")
        print(f"      Assignment Type: {assignment_type}")
        print(f"      Max Players: {max_players}")
        print(f"      Enrollment Cost: {enrollment_cost} credits")

        # Verify values match what we submitted
        assert assignment_type == "APPLICATION_BASED", f"Expected APPLICATION_BASED, got {assignment_type}"
        assert max_players == 5, f"Expected max_players=5, got {max_players}"
        assert enrollment_cost == 500, f"Expected enrollment_cost=500, got {enrollment_cost}"
        assert status == "SEEKING_INSTRUCTOR", f"Expected SEEKING_INSTRUCTOR status, got {status}"

        print("   ✅ ALL DATABASE VALUES VERIFIED!")
        print("=" * 70)
        print("✅ TEST PASSED: APPLICATION_BASED tournament created successfully via Streamlit UI")
        print("=" * 70)
    else:
        print("   ❌ TOURNAMENT NOT FOUND IN DATABASE!")
        print("   This means the Streamlit form submission did NOT create the tournament")
        take_screenshot(page, "tournament_not_in_database_app")
        raise AssertionError("Tournament not found in database after successful UI creation")


def test_f2_instructor_applies_to_tournament(page: Page):
    """Test 2: Grandmaster instructor applies to the tournament."""

    logout(page)
    login(page, GRANDMASTER_EMAIL, GRANDMASTER_PASSWORD)
    take_screenshot(page, "instructor_logged_in")

    # Navigate to Instructor Dashboard or Available Tournaments
    page.get_by_text("Instructor Dashboard").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "instructor_dashboard")

    # Look for Available Tournaments or Applications tab
    try:
        page.get_by_text("Available Tournaments").click()
    except:
        page.get_by_text("Applications").click()

    page.wait_for_timeout(2000)
    take_screenshot(page, "available_tournaments")

    # Find the SEEKING_INSTRUCTOR tournament
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()

    # Click on tournament to view details
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "tournament_details_instructor")

    # Apply to tournament
    page.get_by_role("button", name="Apply").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "instructor_applied")

    # Verify application success
    expect(page.get_by_text("Application submitted")).to_be_visible()


def test_f3_admin_approves_instructor_application(page: Page):
    """Test 3: Admin approves instructor's application."""

    logout(page)
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Find and click on the tournament
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "admin_views_tournament")

    # Look for Applications or Instructor Applications section
    try:
        page.get_by_text("Applications").click()
        page.wait_for_timeout(2000)
    except:
        pass  # Might already be on the right view

    take_screenshot(page, "admin_views_applications")

    # Find Grandmaster's application
    expect(page.get_by_text("grandmaster@lfa.com")).to_be_visible()

    # Approve the application
    page.get_by_role("button", name="Approve").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "admin_approved_application")

    # Verify tournament status changed to PENDING_INSTRUCTOR_ACCEPTANCE
    expect(page.get_by_text("PENDING_INSTRUCTOR_ACCEPTANCE")).to_be_visible()


def test_f4_instructor_accepts_assignment(page: Page):
    """Test 4: Instructor accepts the assignment."""

    logout(page)
    login(page, GRANDMASTER_EMAIL, GRANDMASTER_PASSWORD)

    # Navigate to Instructor Dashboard
    page.get_by_text("Instructor Dashboard").click()
    page.wait_for_timeout(2000)

    # Look for Pending Assignments or My Applications
    try:
        page.get_by_text("Pending Assignments").click()
    except:
        page.get_by_text("My Applications").click()

    page.wait_for_timeout(2000)
    take_screenshot(page, "instructor_pending_assignments")

    # Find the approved tournament
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()

    # Click on tournament
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)

    # Accept assignment
    page.get_by_role("button", name="Accept Assignment").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "instructor_accepted_assignment")

    # Verify acceptance success
    expect(page.get_by_text("Assignment accepted")).to_be_visible()


def test_f5_admin_opens_enrollment(page: Page):
    """Test 5: Admin opens enrollment (READY_FOR_ENROLLMENT → OPEN_FOR_ENROLLMENT)."""

    logout(page)
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Find the tournament
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)

    # Verify current status is READY_FOR_ENROLLMENT
    expect(page.get_by_text("READY_FOR_ENROLLMENT")).to_be_visible()

    take_screenshot(page, "before_open_enrollment")

    # Open enrollment (might be a button or status transition)
    page.get_by_role("button", name="Open Enrollment").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "after_open_enrollment")

    # Verify status changed to OPEN_FOR_ENROLLMENT
    expect(page.get_by_text("OPEN_FOR_ENROLLMENT")).to_be_visible()


def test_f6_player1_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 6: First player redeems enrollment coupon and enrolls."""

    player = test_data.get_player(index=0)
    coupon_code = "E2E-ENROLL-500-USER1"

    logout(page)
    login(page, player["email"], player["password"])

    # Redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Coupon Code").fill(coupon_code)
    page.get_by_role("button", name="Redeem").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "player1_coupon_redeemed_app_based")

    expect(page.get_by_text("+500 credits added")).to_be_visible()

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player1_enrolled_app_based")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_f7_player2_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 7: Second player redeems enrollment coupon and enrolls."""

    player = test_data.get_player(index=1)
    coupon_code = "E2E-ENROLL-500-USER2"

    logout(page)
    login(page, player["email"], player["password"])

    # Redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Coupon Code").fill(coupon_code)
    page.get_by_role("button", name="Redeem").click()
    page.wait_for_timeout(2000)

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player2_enrolled_app_based")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_f8_player3_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 8: Third player redeems enrollment coupon and enrolls."""

    player = test_data.get_player(index=2)
    coupon_code = "E2E-ENROLL-500-USER3"

    logout(page)
    login(page, player["email"], player["password"])

    # Redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Coupon Code").fill(coupon_code)
    page.get_by_role("button", name="Redeem").click()
    page.wait_for_timeout(2000)

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player3_enrolled_app_based")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_f9_admin_approves_all_enrollments(page: Page):
    """Test 9: Admin approves all 3 pending enrollments."""

    logout(page)
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Find the tournament and view enrollments
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)

    # Look for Enrollments tab
    page.get_by_text("Enrollments").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "admin_views_enrollments_app_based")

    # Verify 3 PENDING enrollments
    pending_enrollments = page.get_by_text("PENDING").count()
    assert pending_enrollments == 3, f"Expected 3 PENDING enrollments, found {pending_enrollments}"

    # Approve each enrollment
    approve_buttons = page.get_by_role("button", name="Approve").all()
    for i, button in enumerate(approve_buttons[:3]):
        button.click()
        page.wait_for_timeout(2000)
        take_screenshot(page, f"admin_approved_enrollment_app_based_{i+1}")

    # Verify all are CONFIRMED
    page.wait_for_timeout(2000)
    confirmed_enrollments = page.get_by_text("CONFIRMED").count()
    assert confirmed_enrollments == 3, f"Expected 3 CONFIRMED enrollments, found {confirmed_enrollments}"

    take_screenshot(page, "all_enrollments_confirmed_app_based")


def test_f10_player1_verifies_confirmed_status(page: Page, test_data):
    """Test 10: Player 1 verifies their enrollment is CONFIRMED."""

    player = test_data.get_player(index=0)
    logout(page)
    login(page, player["email"], player["password"])

    # Navigate to My Tournaments
    page.get_by_text("My Tournaments").click()
    page.wait_for_timeout(2000)

    take_screenshot(page, "player1_my_tournaments_app_based")

    # Verify tournament is listed with CONFIRMED status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("CONFIRMED")).to_be_visible()

    take_screenshot(page, "player1_enrollment_confirmed_app_based")
