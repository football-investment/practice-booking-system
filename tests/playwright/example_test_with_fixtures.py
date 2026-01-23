"""
Example E2E Test Using JSON Test Data Fixtures

Demonstrates how to use the test_data fixture for cleaner, more maintainable tests.
"""

import pytest
from playwright.sync_api import Page


def test_example_login_with_fixture_data(page: Page, test_data, admin_credentials):
    """
    Example: Login using fixture data instead of hardcoded credentials.

    Old way:
        ADMIN_EMAIL = "admin@lfa.com"  # Hardcoded
        ADMIN_PASSWORD = "admin123"    # Hardcoded

    New way:
        Uses test_data fixture which loads from JSON
    """
    # Access admin credentials via fixture
    email = admin_credentials["email"]
    password = admin_credentials["password"]

    # Or directly from test_data
    admin = test_data.get_admin()
    assert admin["email"] == email

    # Login
    page.goto("http://localhost:8501")
    page.wait_for_timeout(2000)
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Login").click()
    page.wait_for_timeout(3000)

    # Verify login succeeded
    page.get_by_text("Welcome").wait_for(timeout=5000)


def test_example_get_tournament_data(test_data):
    """
    Example: Get tournament data from fixtures.
    """
    # Get APPLICATION_BASED tournament
    app_based_tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")
    assert app_based_tournament["assignment_type"] == "APPLICATION_BASED"
    assert app_based_tournament["max_players"] == 5

    # Get OPEN_ASSIGNMENT tournament
    open_tournament = test_data.get_tournament(assignment_type="OPEN_ASSIGNMENT")
    assert open_tournament["assignment_type"] == "OPEN_ASSIGNMENT"

    # Get tournament with calculated dates
    tournament_with_dates = test_data.get_tournament_with_dates(assignment_type="APPLICATION_BASED")
    assert "start_date" in tournament_with_dates
    assert "end_date" in tournament_with_dates
    print(f"Tournament starts: {tournament_with_dates['start_date']}")


def test_example_get_players(test_data):
    """
    Example: Access player data.
    """
    # Get specific player by email
    player1 = test_data.get_player(email="pwt.k1sqx1@f1stteam.hu")
    assert player1["first_name"] == "Player"
    assert player1["onboarding_completed"] is True

    # Get player by index
    player2 = test_data.get_player(index=1)
    assert player2["email"] == "pwt.p3t1k3@f1stteam.hu"

    # Get all players
    all_players = test_data.get_all_players()
    assert len(all_players) == 3


def test_example_get_coupons(test_data):
    """
    Example: Access coupon data.
    """
    # Get coupon by code
    coupon = test_data.get_coupon(code="E2E-ENROLL-500-USER1")
    assert coupon["value"] == 500
    assert coupon["type"] == "CREDIT"

    # Get coupon assigned to specific player
    player_coupon = test_data.get_coupon(assigned_to="pwt.k1sqx1@f1stteam.hu")
    assert player_coupon["code"] == "E2E-ENROLL-500-USER1"

    # Get all coupons for a player
    player_coupons = test_data.get_coupons_for_player("pwt.k1sqx1@f1stteam.hu")
    assert len(player_coupons) >= 1


def test_example_get_locations(test_data):
    """
    Example: Access location and campus data.
    """
    # Get location by name
    location = test_data.get_location(name="Budapest Sports Complex")
    assert location["city"] == "Budapest"
    assert len(location["campuses"]) >= 2

    # Get campus
    campus = test_data.get_campus(location_name="Budapest Sports Complex", campus_index=0)
    assert campus["name"] == "Main Campus"


def test_example_get_instructor_with_licenses(test_data):
    """
    Example: Access instructor with license data.
    """
    # Get instructor
    instructor = test_data.get_instructor(email="grandmaster@lfa.com")
    assert instructor["role"] == "INSTRUCTOR"

    # Check licenses
    licenses = instructor["licenses"]
    assert len(licenses) >= 2

    # Find LFA_COACH license
    coach_license = next((lic for lic in licenses if lic["specialization_type"] == "LFA_COACH"), None)
    assert coach_license is not None
    assert coach_license["current_level"] == 8
    assert coach_license["is_active"] is True


# ============================================================================
# HOW TO USE IN REAL TESTS
# ============================================================================

def test_real_example_tournament_creation(page: Page, test_data, admin_credentials):
    """
    Real example: Create a tournament using fixture data.

    Benefits:
    1. No hardcoded values
    2. Easy to change test data (just edit JSON)
    3. Reusable across multiple tests
    4. Type-safe with schema validation
    """
    # Login as admin
    page.goto("http://localhost:8501")
    page.wait_for_timeout(2000)
    page.get_by_label("Email").fill(admin_credentials["email"])
    page.get_by_label("Password", exact=True).fill(admin_credentials["password"])
    page.get_by_role("button", name="Login").click()
    page.wait_for_timeout(3000)

    # Get tournament template from fixtures
    tournament = test_data.get_tournament_with_dates(assignment_type="APPLICATION_BASED")

    # Navigate to tournament creation
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(3000)

    # Fill form using fixture data
    # (This is where you'd fill tournament name, age_group, max_players, etc. from the fixture)

    # All data comes from JSON - easy to maintain!
    print(f"Creating tournament: {tournament['name']}")
    print(f"Age group: {tournament['age_group']}")
    print(f"Max players: {tournament['max_players']}")
    print(f"Enrollment cost: {tournament['enrollment_cost']}")
