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

TEST_PLAYERS = [
    {"email": "pwt.k1sqx1@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER1"},
    {"email": "pwt.p3t1k3@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER2"},
    {"email": "pwt.V4lv3rd3jr@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER3"},
]

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
    """Test 1: Admin creates OPEN_ASSIGNMENT tournament and directly assigns instructor."""

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "admin_logged_in")

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "tournament_management_page")

    # Click Create Tournament TAB (Streamlit role-based selector with emoji)
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(2000)
    take_screenshot(page, "create_tournament_tab_open")

    # ========================================================================
    # SECTION 1: Location & Campus (OUTSIDE form - lines 71-116)
    # ========================================================================
    # Use placeholder text to identify Location selectbox (first selectbox on page)
    page.get_by_text("Location *").click()
    page.wait_for_timeout(1000)
    # Click the first location option (Budapest)
    page.get_by_role("option").first.click()
    page.wait_for_timeout(1500)

    # Campus selectbox appears after location is selected (second selectbox)
    page.get_by_text("Campus *").click()
    page.wait_for_timeout(1000)
    # Click the first campus option
    page.get_by_role("option").first.click()
    page.wait_for_timeout(1500)

    # ========================================================================
    # SECTION 2: Form Fields (INSIDE form - starts at line 120)
    # ========================================================================
    # Tournament Name (text_input - lines 125-129)
    page.get_by_placeholder("e.g., Winter Football Cup").fill(TOURNAMENT_NAME)
    page.wait_for_timeout(500)

    # Tournament Date (date_input - lines 131-136)
    tournament_date = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")
    # Use label for date input (Streamlit renders it with proper label)
    page.get_by_label("Tournament Date *").fill(tournament_date)
    page.wait_for_timeout(500)

    # Age Group (selectbox - lines 140-144)
    page.get_by_text("Age Group *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name="YOUTH").click()
    page.wait_for_timeout(500)

    # Assignment Type (selectbox - lines 154-158)
    page.get_by_text("Assignment Type *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name="OPEN_ASSIGNMENT").click()
    page.wait_for_timeout(1500)

    # Max Players (number_input - lines 162-168)
    # Click and clear first, then fill
    page.get_by_label("Max Players *").click()
    page.get_by_label("Max Players *").fill("5")
    page.wait_for_timeout(500)

    # Price (Credits) (number_input - lines 172-178)
    page.get_by_label("Price (Credits) *").click()
    page.get_by_label("Price (Credits) *").fill("500")
    page.wait_for_timeout(500)

    # Select Instructor (selectbox - lines 191-196, conditional on OPEN_ASSIGNMENT)
    page.get_by_text("Select Instructor *").click()
    page.wait_for_timeout(1000)
    # Select the first instructor option (should be Grandmaster)
    page.get_by_role("option").first.click()
    page.wait_for_timeout(1000)

    take_screenshot(page, "tournament_form_filled")

    # Submit tournament creation (Streamlit form submit button)
    page.get_by_role("button", name="🏆 Create Tournament").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "tournament_created")

    # Verify success message
    expect(page.get_by_text(re.compile("Tournament created successfully", re.IGNORECASE))).to_be_visible(timeout=10000)

    # Verify tournament appears in list with OPEN_FOR_ENROLLMENT status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("OPEN_FOR_ENROLLMENT")).to_be_visible()


def test_e2_player1_redeems_coupon_and_enrolls(page: Page):
    """Test 2: First player redeems enrollment coupon and enrolls in tournament."""

    player = TEST_PLAYERS[0]

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
    page.get_by_label("Coupon Code").fill(player["coupon"])
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


def test_e3_player2_redeems_coupon_and_enrolls(page: Page):
    """Test 3: Second player redeems enrollment coupon and enrolls in tournament."""

    player = TEST_PLAYERS[1]

    logout(page)
    login(page, player["email"], player["password"])

    # Redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Coupon Code").fill(player["coupon"])
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


def test_e4_player3_redeems_coupon_and_enrolls(page: Page):
    """Test 4: Third player redeems enrollment coupon and enrolls in tournament."""

    player = TEST_PLAYERS[2]

    logout(page)
    login(page, player["email"], player["password"])

    # Redeem coupon
    page.get_by_text("My Profile").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Redeem Coupon").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Coupon Code").fill(player["coupon"])
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


def test_e6_player1_verifies_confirmed_status(page: Page):
    """Test 6: Player 1 verifies their enrollment is CONFIRMED."""

    logout(page)
    login(page, TEST_PLAYERS[0]["email"], TEST_PLAYERS[0]["password"])

    # Navigate to My Tournaments or My Enrollments
    page.get_by_text("My Tournaments").click()
    page.wait_for_timeout(2000)

    take_screenshot(page, "player1_my_tournaments")

    # Verify tournament is listed with CONFIRMED status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("CONFIRMED")).to_be_visible()

    take_screenshot(page, "player1_enrollment_confirmed")
