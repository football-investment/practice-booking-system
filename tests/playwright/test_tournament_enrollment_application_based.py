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

TEST_PLAYERS = [
    {"email": "pwt.k1sqx1@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER1"},
    {"email": "pwt.p3t1k3@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER2"},
    {"email": "pwt.V4lv3rd3jr@f1stteam.hu", "password": "TestPass123!", "coupon": "E2E-ENROLL-500-USER3"},
]

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
    """Test 1: Admin creates APPLICATION_BASED tournament (SEEKING_INSTRUCTOR status)."""

    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "admin_logged_in_app_based")

    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Click Create Tournament TAB (Streamlit role-based selector with emoji)
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(2000)

    # Fill tournament form
    page.get_by_label("Tournament Name").fill(TOURNAMENT_NAME)

    # Select assignment type: APPLICATION_BASED
    page.get_by_label("Assignment Type").select_option("APPLICATION_BASED")
    page.wait_for_timeout(1000)

    # Select location and campus
    page.get_by_label("Location").select_option("Budapest")
    page.wait_for_timeout(1000)
    page.get_by_label("Campus").select_option("Main Test Campus")

    # Set dates
    start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
    page.get_by_label("Start Date").fill(start_date)
    page.get_by_label("End Date").fill(end_date)

    # Set max players and price
    page.get_by_label("Max Players").fill("5")
    page.get_by_label("Price (Credits)").fill("500")

    take_screenshot(page, "tournament_form_filled_app_based")

    # Submit tournament creation
    page.get_by_role("button", name="Create Tournament").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "tournament_created_app_based")

    # Verify success message
    expect(page.get_by_text("Tournament created successfully")).to_be_visible()

    # Verify tournament appears in list with SEEKING_INSTRUCTOR status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("SEEKING_INSTRUCTOR")).to_be_visible()


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


def test_f6_player1_redeems_coupon_and_enrolls(page: Page):
    """Test 6: First player redeems enrollment coupon and enrolls."""

    player = TEST_PLAYERS[0]

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


def test_f7_player2_redeems_coupon_and_enrolls(page: Page):
    """Test 7: Second player redeems enrollment coupon and enrolls."""

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

    # Browse and enroll
    page.get_by_text("Browse Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_text(TOURNAMENT_NAME).click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Enroll").click()
    page.wait_for_timeout(3000)

    take_screenshot(page, "player2_enrolled_app_based")
    expect(page.get_by_text("Successfully enrolled")).to_be_visible()


def test_f8_player3_redeems_coupon_and_enrolls(page: Page):
    """Test 8: Third player redeems enrollment coupon and enrolls."""

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


def test_f10_player1_verifies_confirmed_status(page: Page):
    """Test 10: Player 1 verifies their enrollment is CONFIRMED."""

    logout(page)
    login(page, TEST_PLAYERS[0]["email"], TEST_PLAYERS[0]["password"])

    # Navigate to My Tournaments
    page.get_by_text("My Tournaments").click()
    page.wait_for_timeout(2000)

    take_screenshot(page, "player1_my_tournaments_app_based")

    # Verify tournament is listed with CONFIRMED status
    expect(page.get_by_text(TOURNAMENT_NAME)).to_be_visible()
    expect(page.get_by_text("CONFIRMED")).to_be_visible()

    take_screenshot(page, "player1_enrollment_confirmed_app_based")
