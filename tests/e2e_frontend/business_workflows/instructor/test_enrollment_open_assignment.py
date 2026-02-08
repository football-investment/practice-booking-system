"""
Playwright E2E Test: Tournament Enrollment Flow - OPEN_ASSIGNMENT

✅ STATUS: ENABLED - Domain gap resolved (2026-01-12)

Tests the complete player enrollment workflow with OPEN_ASSIGNMENT tournament type.

WORKFLOW:
1. Admin creates OPEN_ASSIGNMENT tournament via UI (directly assigns instructor)
2. Tournament is immediately OPEN_FOR_ENROLLMENT
3. Three players redeem enrollment coupons (500 credits each)
4. Three players enroll in tournament via UI
5. Admin approves enrollments via UI
6. Players verify CONFIRMED enrollment status

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

TOURNAMENT_NAME = f"E2E Test Tournament - Open Assignment {datetime.now().strftime('%Y%m%d%H%M%S')}"


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
    # Look for logout button in sidebar or main area
    try:
        page.get_by_role("button", name="Logout").click()
        page.wait_for_timeout(2000)
    except:
        # Try alternative logout method
        page.goto("http://localhost:8501")
        page.wait_for_timeout(2000)


def take_screenshot(page: Page, name: str):
    """Helper to take screenshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    page.screenshot(path=f"tests/e2e/screenshots/{name}_{timestamp}.png")


def test_e1_admin_creates_open_assignment_tournament(page: Page):
    """Test 1: Admin creates OPEN_ASSIGNMENT tournament via Streamlit UI

    ✅ REAL UI AUTOMATION: Creates tournament through actual Streamlit form interaction

    APPROACH:
    1. Admin logs in and navigates to Create Tournament tab
    2. Fills out form using proper Streamlit selector strategies
    3. Submits form and waits for success message
    4. Validates tournament exists in database
    """
    import psycopg2

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "admin_logged_in")

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "tournament_management_page")

    # Click Create Tournament TAB
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(3000)
    take_screenshot(page, "create_tournament_tab_open")

    # ========================================================================
    # SECTION 1: Location & Campus Selection (OUTSIDE form - lines 104-149)
    # ========================================================================
    print("📍 Step 1: Selecting Location...")

    # Wait for page to fully load - look for the selectbox by its label
    page.wait_for_timeout(2000)

    # Streamlit selectboxes can be targeted using:
    # 1. data-testid attribute with the key parameter
    # 2. Or by finding the select element within the labeled div
    # The selectbox with key="tourn_location_sel" should have data-testid="stSelectbox"

    try:
        # Wait for Location selectbox to appear
        # Streamlit selectboxes are rendered as <select> within a div
        # Try to find by the visible label and then the select element
        location_label = page.locator("label:has-text('Location *')").first
        location_label.wait_for(timeout=10000)

        # The select element should be near this label
        # Streamlit renders selectbox as a button-like div that opens a listbox
        # Click on the div that contains the selectbox
        location_selectbox = page.locator("label:has-text('Location *')").locator("..").locator("[data-baseweb='select']").first
        location_selectbox.click()
        page.wait_for_timeout(1000)

        # Now the dropdown should be open, select first option
        page.locator("[role='option']").first.click()
        page.wait_for_timeout(1500)
        print("   ✅ Location selected")
    except Exception as e:
        print(f"   ❌ Location selection failed: {e}")
        take_screenshot(page, "location_selection_error")
        raise

    print("🏫 Step 2: Selecting Campus...")

    # Campus selectbox appears after location is selected
    try:
        campus_label = page.locator("label:has-text('Campus *')").first
        campus_label.wait_for(timeout=10000)

        campus_selectbox = page.locator("label:has-text('Campus *')").locator("..").locator("[data-baseweb='select']").first
        campus_selectbox.click()
        page.wait_for_timeout(1000)

        # Select first campus option
        page.locator("[role='option']").first.click()
        page.wait_for_timeout(1500)
        print("   ✅ Campus selected")
    except Exception as e:
        print(f"   ❌ Campus selection failed: {e}")
        take_screenshot(page, "campus_selection_error")
        raise

    # ========================================================================
    # SECTION 2: Form Fields (INSIDE form - starts at line 153)
    # ========================================================================
    print("📝 Step 3: Filling tournament form...")

    # Tournament Name (text_input - line 173-178)
    try:
        tournament_name_input = page.get_by_placeholder("e.g., Winter Football Cup")
        tournament_name_input.click()
        tournament_name_input.fill(TOURNAMENT_NAME)
        page.wait_for_timeout(500)
        print(f"   ✅ Tournament name: {TOURNAMENT_NAME}")
    except Exception as e:
        print(f"   ❌ Tournament name input failed: {e}")
        take_screenshot(page, "tournament_name_error")
        raise

    # Tournament Date (date_input - line 188-194)
    # Streamlit date_input with key="tournament_date_input" renders as an input field
    try:
        tournament_date = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")
        # Find the date input - Streamlit renders it with a label, find input nearby
        date_label = page.locator("label:has-text('Tournament Date *')").first
        # The input should be after or near this label
        date_input = date_label.locator("..").locator("input[type='text']").first
        date_input.click()
        date_input.fill(tournament_date)
        page.wait_for_timeout(500)
        print(f"   ✅ Tournament date: {tournament_date}")
    except Exception as e:
        print(f"   ❌ Tournament date input failed: {e}")
        take_screenshot(page, "tournament_date_error")
        raise

    # Age Group (selectbox - lines 198-203)
    print("👶 Step 4: Selecting Age Group...")
    try:
        age_label = page.locator("label:has-text('Age Group *')").first
        age_label.wait_for(timeout=10000)

        age_selectbox = page.locator("label:has-text('Age Group *')").locator("..").locator("[data-baseweb='select']").first
        age_selectbox.click()
        page.wait_for_timeout(1000)

        # Select YOUTH option
        page.locator("[role='option']:has-text('YOUTH')").click()
        page.wait_for_timeout(500)
        print("   ✅ Age Group: YOUTH")
    except Exception as e:
        print(f"   ❌ Age Group selection failed: {e}")
        take_screenshot(page, "age_group_error")
        raise

    # Assignment Type (selectbox - lines 213-218)
    print("🎯 Step 5: Selecting Assignment Type...")
    try:
        assignment_label = page.locator("label:has-text('Assignment Type *')").first
        assignment_label.wait_for(timeout=10000)

        assignment_selectbox = page.locator("label:has-text('Assignment Type *')").locator("..").locator("[data-baseweb='select']").first
        assignment_selectbox.click()
        page.wait_for_timeout(1000)

        page.locator("[role='option']:has-text('OPEN_ASSIGNMENT')").click()
        page.wait_for_timeout(1500)
        print("   ✅ Assignment Type: OPEN_ASSIGNMENT")
    except Exception as e:
        print(f"   ❌ Assignment Type selection failed: {e}")
        take_screenshot(page, "assignment_type_error")
        raise

    # Max Players (number_input - lines 222-229)
    try:
        max_players_label = page.locator("label:has-text('Max Players *')").first
        max_players_input = max_players_label.locator("..").locator("input[type='number']").first
        max_players_input.click()
        max_players_input.fill("5")
        page.wait_for_timeout(500)
        print("   ✅ Max Players: 5")
    except Exception as e:
        print(f"   ❌ Max Players input failed: {e}")
        take_screenshot(page, "max_players_error")
        raise

    # Price (Credits) (number_input - lines 233-240)
    try:
        price_label = page.locator("label:has-text('Price (Credits) *')").first
        price_input = price_label.locator("..").locator("input[type='number']").first
        price_input.click()
        price_input.fill("500")
        page.wait_for_timeout(500)
        print("   ✅ Price: 500 credits")
    except Exception as e:
        print(f"   ❌ Price input failed: {e}")
        take_screenshot(page, "price_error")
        raise

    take_screenshot(page, "tournament_form_filled")
    print("✅ All form fields filled!")

    # ========================================================================
    # SECTION 3: Submit Form & Verify Creation
    # ========================================================================
    print("🚀 Step 6: Submitting tournament creation form...")

    # Submit tournament creation (form submit button - line 389)
    try:
        submit_button = page.locator("button:has-text('🏆 Create Tournament')").first
        submit_button.click()
        page.wait_for_timeout(5000)  # Wait for API call and Streamlit rerun
        print("   ✅ Form submitted")
    except Exception as e:
        print(f"   ❌ Form submission failed: {e}")
        take_screenshot(page, "submit_error")
        raise

    take_screenshot(page, "after_tournament_creation")

    # Verify success message (line 77 - success message display)
    print("✅ Step 7: Verifying success message...")
    try:
        # Look for success message
        success_message = page.locator("text=/Tournament created successfully/i")
        expect(success_message).to_be_visible(timeout=10000)
        print("   ✅ Success message visible")
    except Exception as e:
        print(f"   ❌ Success message not found: {e}")
        take_screenshot(page, "no_success_message")
        raise

    # ========================================================================
    # SECTION 4: Backend Database Validation (CRITICAL)
    # ========================================================================
    print("🔍 Step 8: Validating tournament in database...")

    import psycopg2

    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # Query for the tournament we just created
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
        assert assignment_type == "OPEN_ASSIGNMENT", f"Expected OPEN_ASSIGNMENT, got {assignment_type}"
        assert max_players == 5, f"Expected max_players=5, got {max_players}"
        assert enrollment_cost == 500, f"Expected enrollment_cost=500, got {enrollment_cost}"

        print("   ✅ ALL DATABASE VALUES VERIFIED!")
        print("=" * 70)
        print("✅ TEST PASSED: Tournament created successfully via Streamlit UI and verified in database")
        print("=" * 70)
    else:
        print("   ❌ TOURNAMENT NOT FOUND IN DATABASE!")
        print("   This means the Streamlit form submission did NOT create the tournament in the backend")
        take_screenshot(page, "tournament_not_in_database")
        raise AssertionError("Tournament not found in database after successful UI creation")


def test_e2_player1_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 2: First player redeems enrollment coupon and enrolls in tournament."""

    player = test_data.get_player(index=0)
    coupon_code = "E2E-ENROLL-500-USER1"

    # Logout admin, login as player1
    logout(page)
    login(page, player["email"], player["password"])
    take_screenshot(page, "player1_logged_in")

    # Navigate to Credits/Profile page to redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)

    # Find and click Redeem Coupon button
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)

    # Enter coupon code
    page.get_by_label("Coupon Code").fill(coupon_code)
    page.get_by_role("button", name="Redeem").click()
    page.wait_for_timeout(2000)

    take_screenshot(page, "player1_coupon_redeemed")

    # Verify coupon success message
    expect(page.get_by_text("+500 credits added")).to_be_visible()
    expect(page.get_by_text("500")).to_be_visible()  # Credit balance

    # Navigate to Browse Tournaments
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "player1_tournament_browser")

    # Find and click on the OPEN_ASSIGNMENT tournament
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "player1_tournament_details")

    # Try to enroll (should succeed now with 500 credits)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player1_enrolled")

    # Verify enrollment success
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()
    expect(page.get_by_text("PENDING")).to_be_visible()

    # Verify credit balance decreased (500 - 500 = 0)
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    expect(page.get_by_text("0", exact=True)).to_be_visible()  # 0 credits remaining


def test_e3_player2_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 3: Second player redeems enrollment coupon and enrolls in tournament."""

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
    take_screenshot(page, "player2_coupon_redeemed")

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player2_enrolled")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_e4_player3_redeems_coupon_and_enrolls(page: Page, test_data):
    """Test 4: Third player redeems enrollment coupon and enrolls in tournament."""

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
    take_screenshot(page, "player3_coupon_redeemed")

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player3_enrolled")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_e5_admin_approves_all_enrollments(page: Page):
    """Test 5: Admin approves all 3 pending enrollments."""

    logout(page)
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Find the tournament and view enrollments
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "admin_views_enrollments")

    # Look for Enrollments tab or section
    page.get_by_text("Enrollments").click()
    page.wait_for_timeout(2000)

    # Verify 3 PENDING enrollments are visible
    pending_enrollments = page.get_by_text("PENDING").count()
    assert pending_enrollments == 3, f"Expected 3 PENDING enrollments, found {pending_enrollments}"

    # Approve each enrollment
    approve_buttons = page.get_by_role("button", name="Approve").all()
    for i, button in enumerate(approve_buttons[:3]):  # Approve first 3
        button.click()
        page.wait_for_timeout(2000)
        take_screenshot(page, f"admin_approved_enrollment_{i+1}")

    # Verify all are now CONFIRMED
    page.wait_for_timeout(2000)
    confirmed_enrollments = page.get_by_text("CONFIRMED").count()
    assert confirmed_enrollments == 3, f"Expected 3 CONFIRMED enrollments, found {confirmed_enrollments}"

    take_screenshot(page, "all_enrollments_confirmed")


def test_e6_player1_verifies_confirmed_status(page: Page, test_data):
    """Test 6: Player 1 verifies their enrollment is CONFIRMED."""

    player = test_data.get_player(index=0)
    logout(page)
    login(page, player["email"], player["password"])

    # Navigate to My Tournaments or My Enrollments
    page.get_by_text("My Tournaments").click()
    page.wait_for_timeout(2000)

    take_screenshot(page, "player1_my_tournaments")

    # Verify tournament is listed with CONFIRMED status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("CONFIRMED")).to_be_visible()

    take_screenshot(page, "player1_enrollment_confirmed")
