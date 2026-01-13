"""
Playwright E2E Test: Tournament Game Types - Complete Coverage

✅ STATUS: ENABLED - Game types implemented (2026-01-12)

Tests all 4 game types with tournament creation and game management:
1. League Match
2. King of the Court
3. Group Stage + Placement Matches
4. Elimination Bracket

WORKFLOW (for each test):
1. Admin creates tournament with specific settings
2. Admin navigates to Manage Games
3. Admin creates game with specific game type
4. Verify game appears with correct type

PREREQUISITES:
- Database snapshot: after_onboarding.sql
- Admin user exists
- Location and Campus exist
"""

import pytest
import re
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta, time


# Test configuration
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


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


def create_tournament_base(page: Page, tournament_name: str, max_players: int, price: int, assignment_type: str):
    """
    Helper to create a tournament with base settings.
    Returns tournament name for later reference.
    """
    # Navigate to Tournaments tab
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.wait_for_timeout(2000)

    # Click Create Tournament tab
    page.get_by_role("tab", name="➕ Create Tournament").click()
    page.wait_for_timeout(2000)

    # ========================================================================
    # SECTION 1: Location & Campus (OUTSIDE form)
    # ========================================================================
    # Select Location
    page.get_by_text("Location *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option").first.click()
    page.wait_for_timeout(1500)

    # Select Campus
    page.get_by_text("Campus *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option").first.click()
    page.wait_for_timeout(1500)

    # ========================================================================
    # SECTION 2: Form Fields (INSIDE form)
    # ========================================================================
    # Fill tournament form
    page.get_by_placeholder("e.g., Winter Football Cup").fill(tournament_name)
    page.wait_for_timeout(500)

    # Tournament Date (7 days from now)
    tournament_date = (datetime.now() + timedelta(days=7)).strftime("%m/%d/%Y")
    page.get_by_label("Tournament Date *").fill(tournament_date)
    page.wait_for_timeout(500)

    # Age Group
    page.get_by_text("Age Group *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name="YOUTH").click()
    page.wait_for_timeout(500)

    # Assignment Type
    page.get_by_text("Assignment Type *").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name=assignment_type).click()
    page.wait_for_timeout(1500)

    # Max Players
    page.get_by_label("Max Players *").click()
    page.get_by_label("Max Players *").fill(str(max_players))
    page.wait_for_timeout(500)

    # Price (Credits)
    page.get_by_label("Price (Credits) *").click()
    page.get_by_label("Price (Credits) *").fill(str(price))
    page.wait_for_timeout(500)

    # ========================================================================
    # CONDITIONAL: Select Instructor for OPEN_ASSIGNMENT
    # ========================================================================
    if assignment_type == "OPEN_ASSIGNMENT":
        page.get_by_text("Select Instructor *").click()
        page.wait_for_timeout(1000)
        # Select the first instructor option (should be Grandmaster)
        page.get_by_role("option").first.click()
        page.wait_for_timeout(1000)

    # Submit tournament creation
    page.get_by_role("button", name="🏆 Create Tournament").click()
    page.wait_for_timeout(3000)

    # Verify success
    expect(page.get_by_text(re.compile("Tournament created successfully", re.IGNORECASE))).to_be_visible(timeout=10000)

    return tournament_name


def navigate_to_manage_games(page: Page, tournament_name: str):
    """Navigate to Manage Games tab for a specific tournament."""
    # Navigate to Manage Games tab
    page.get_by_role("tab", name="⚙️ Manage Games").click()
    page.wait_for_timeout(2000)

    # Select tournament from dropdown
    page.get_by_text("Select Tournament").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name=re.compile(tournament_name, re.IGNORECASE)).click()
    page.wait_for_timeout(2000)


def add_game(page: Page, game_title: str, game_type: str, duration_minutes: int = 90):
    """
    Add a new game to the selected tournament.

    Args:
        page: Playwright page object
        game_title: Title of the game
        game_type: One of the 4 game types
        duration_minutes: Game duration (default 90)
    """
    # Click Add New Game button
    page.get_by_role("button", name="➕ Add New Game").click()
    page.wait_for_timeout(2000)

    # Fill game details
    page.get_by_label("Game Title").fill(game_title)
    page.wait_for_timeout(500)

    # Select Game Type
    page.get_by_text("Game Type").click()
    page.wait_for_timeout(1000)
    page.get_by_role("option", name=game_type).click()
    page.wait_for_timeout(1000)

    # Set start and end time (based on duration)
    start_time = time(14, 0)  # 14:00
    end_hour = 14 + (duration_minutes // 60)
    end_minute = duration_minutes % 60
    end_time = time(end_hour, end_minute)

    # Note: Time inputs might need specific selectors based on Streamlit rendering
    # This is a placeholder - adjust based on actual UI

    # Click Create Game button
    page.get_by_role("button", name="➕ Create Game").click()
    page.wait_for_timeout(3000)

    # Verify success
    expect(page.get_by_text(re.compile("Game created successfully", re.IGNORECASE))).to_be_visible(timeout=10000)


# =============================================================================
# TEST 1: League Match
# =============================================================================

def test_game_type_league_match(page: Page):
    """
    Test: Create tournament and add League Match game type

    Tournament Settings:
    - Max Players: 20
    - Price: 300 credits
    - Assignment Type: APPLICATION_BASED

    Game Settings:
    - Type: League Match
    - Duration: 5 minutes (300 seconds)
    """
    tournament_name = f"League Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "league_admin_logged_in")

    # Create tournament
    create_tournament_base(
        page=page,
        tournament_name=tournament_name,
        max_players=20,
        price=300,
        assignment_type="APPLICATION_BASED"
    )
    take_screenshot(page, "league_tournament_created")

    # Navigate to Manage Games
    navigate_to_manage_games(page, tournament_name)
    take_screenshot(page, "league_manage_games")

    # Add League Match game
    add_game(
        page=page,
        game_title="Round 1 - League Match",
        game_type="League Match",
        duration_minutes=5
    )
    take_screenshot(page, "league_game_added")

    # Verify game appears in list
    expect(page.get_by_text("Round 1 - League Match")).to_be_visible()
    expect(page.get_by_text("League Match")).to_be_visible()


# =============================================================================
# TEST 2: King of the Court
# =============================================================================

def test_game_type_king_of_court(page: Page):
    """
    Test: Create tournament and add King of the Court game type

    Tournament Settings:
    - Max Players: 12
    - Price: 250 credits
    - Assignment Type: OPEN_ASSIGNMENT

    Game Settings:
    - Type: King of the Court
    - Duration: 3 minutes (180 seconds)
    """
    tournament_name = f"King Court Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "king_admin_logged_in")

    # Create tournament
    create_tournament_base(
        page=page,
        tournament_name=tournament_name,
        max_players=12,
        price=250,
        assignment_type="OPEN_ASSIGNMENT"
    )
    take_screenshot(page, "king_tournament_created")

    # Navigate to Manage Games
    navigate_to_manage_games(page, tournament_name)
    take_screenshot(page, "king_manage_games")

    # Add King of the Court game
    add_game(
        page=page,
        game_title="Challenge Round 1",
        game_type="King of the Court",
        duration_minutes=3
    )
    take_screenshot(page, "king_game_added")

    # Verify game appears in list
    expect(page.get_by_text("Challenge Round 1")).to_be_visible()
    expect(page.get_by_text("King of the Court")).to_be_visible()


# =============================================================================
# TEST 3: Group Stage + Placement Matches
# =============================================================================

def test_game_type_group_stage_placement(page: Page):
    """
    Test: Create tournament and add Group Stage + Placement game type

    Tournament Settings:
    - Max Players: 16
    - Price: 400 credits
    - Assignment Type: APPLICATION_BASED

    Game Settings:
    - Type: Group Stage + Placement Matches
    - Duration: 5 minutes (300 seconds)
    """
    tournament_name = f"Group Stage Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "group_admin_logged_in")

    # Create tournament
    create_tournament_base(
        page=page,
        tournament_name=tournament_name,
        max_players=16,
        price=400,
        assignment_type="APPLICATION_BASED"
    )
    take_screenshot(page, "group_tournament_created")

    # Navigate to Manage Games
    navigate_to_manage_games(page, tournament_name)
    take_screenshot(page, "group_manage_games")

    # Add Group Stage game
    add_game(
        page=page,
        game_title="Group A - Match 1",
        game_type="Group Stage + Placement Matches",
        duration_minutes=5
    )
    take_screenshot(page, "group_game_added")

    # Verify game appears in list
    expect(page.get_by_text("Group A - Match 1")).to_be_visible()
    expect(page.get_by_text("Group Stage + Placement Matches")).to_be_visible()


# =============================================================================
# TEST 4: Elimination Bracket
# =============================================================================

def test_game_type_elimination_bracket(page: Page):
    """
    Test: Create tournament and add Elimination Bracket game type

    Tournament Settings:
    - Max Players: 8
    - Price: 500 credits
    - Assignment Type: OPEN_ASSIGNMENT

    Game Settings:
    - Type: Elimination Bracket
    - Duration: 3 minutes (180 seconds)
    """
    tournament_name = f"Elimination Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "elimination_admin_logged_in")

    # Create tournament
    create_tournament_base(
        page=page,
        tournament_name=tournament_name,
        max_players=8,
        price=500,
        assignment_type="OPEN_ASSIGNMENT"
    )
    take_screenshot(page, "elimination_tournament_created")

    # Navigate to Manage Games
    navigate_to_manage_games(page, tournament_name)
    take_screenshot(page, "elimination_manage_games")

    # Add Elimination Bracket game
    add_game(
        page=page,
        game_title="Quarterfinal 1",
        game_type="Elimination Bracket",
        duration_minutes=3
    )
    take_screenshot(page, "elimination_game_added")

    # Verify game appears in list
    expect(page.get_by_text("Quarterfinal 1")).to_be_visible()
    expect(page.get_by_text("Elimination Bracket")).to_be_visible()


# =============================================================================
# COMPREHENSIVE TEST: All Game Types in One Tournament
# =============================================================================

def test_all_game_types_comprehensive(page: Page):
    """
    Test: Create one tournament and add all 4 game types

    Tournament Settings:
    - Max Players: 24
    - Price: 350 credits
    - Assignment Type: APPLICATION_BASED

    Games:
    1. League Match (5 min)
    2. King of the Court (3 min)
    3. Group Stage + Placement (5 min)
    4. Elimination Bracket (3 min)
    """
    tournament_name = f"Comprehensive Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Login as admin
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    take_screenshot(page, "comprehensive_admin_logged_in")

    # Create tournament
    create_tournament_base(
        page=page,
        tournament_name=tournament_name,
        max_players=24,
        price=350,
        assignment_type="APPLICATION_BASED"
    )
    take_screenshot(page, "comprehensive_tournament_created")

    # Navigate to Manage Games
    navigate_to_manage_games(page, tournament_name)
    take_screenshot(page, "comprehensive_manage_games")

    # Add all 4 game types
    game_types = [
        ("Round 1 - League", "League Match", 5),
        ("Challenge Round", "King of the Court", 3),
        ("Group Stage A", "Group Stage + Placement Matches", 5),
        ("Quarterfinal", "Elimination Bracket", 3)
    ]

    for game_title, game_type, duration in game_types:
        add_game(page, game_title, game_type, duration)
        page.wait_for_timeout(2000)
        take_screenshot(page, f"comprehensive_game_added_{game_type.replace(' ', '_')}")

    # Verify all games appear
    for game_title, game_type, _ in game_types:
        expect(page.get_by_text(game_title)).to_be_visible()
        expect(page.get_by_text(game_type)).to_be_visible()

    take_screenshot(page, "comprehensive_all_games_added")
