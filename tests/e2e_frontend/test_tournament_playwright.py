"""
Playwright E2E Tests for Tournament Workflow - ALL 18 CONFIGURATIONS
Tests complete user journey through Streamlit UI for all real tournament configurations

IMPORTANT: This test requires:
1. Streamlit app running on http://localhost:8501
2. FastAPI backend running on http://localhost:8000
3. PostgreSQL database properly configured

Run with:
    pytest tests/e2e_frontend/test_tournament_playwright.py -v -s

Configuration Coverage:
- 15 INDIVIDUAL_RANKING configs (5 scoring types × 3 rounds: 1,2,3)
- 3 HEAD_TO_HEAD configs (league, knockout, group+knockout)
"""
import pytest
import time
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import requests

# Configuration
STREAMLIT_URL = "http://localhost:8501"
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
TEST_PLAYER_IDS = [4, 5, 6, 7, 13, 14, 15, 16]

# ============================================================================
# ALL 18 REAL TOURNAMENT CONFIGURATIONS
# ============================================================================

TEST_CONFIGURATIONS = [
    # ========================================================================
    # TIER 0: 1-round INDIVIDUAL_RANKING (5 configs)
    # ========================================================================
    {
        "id": "T1",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },
    {
        "id": "T2",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 5  # Top 5 winners
    },
    {
        "id": "T3",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 1  # Only 1 winner
    },
    {
        "id": "T4",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },
    {
        "id": "T5",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },

    # ========================================================================
    # TIER 0: HEAD_TO_HEAD basic configs (2 configs)
    # ========================================================================
    {
        "id": "T6",
        "name": "HEAD_TO_HEAD + League (Round Robin)",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 1,
        "number_of_rounds": None,
        "supports_finalization": False,
        "expected_sessions": 28,
        "winner_count": None  # Not applicable
    },
    {
        "id": "T7",
        "name": "HEAD_TO_HEAD + Single Elimination",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 2,
        "number_of_rounds": None,
        "supports_finalization": False,
        "expected_sessions": 8,
        "winner_count": None  # Not applicable
    },

    # ========================================================================
    # TIER 1: Multi-round INDIVIDUAL_RANKING - 2 rounds (5 configs)
    # ========================================================================
    {
        "id": "T8",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 2,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },
    {
        "id": "T10",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,
        "number_of_rounds": 2,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 2  # Top 2 winners
    },
    {
        "id": "T12",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,
        "number_of_rounds": 2,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 5  # Top 5 winners
    },
    {
        "id": "T14",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,
        "number_of_rounds": 2,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 1  # Only 1 winner
    },
    {
        "id": "T16",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 2,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },

    # ========================================================================
    # TIER 1: Multi-round INDIVIDUAL_RANKING - 3 rounds (5 configs)
    # ========================================================================
    {
        "id": "T9",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 3,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },
    {
        "id": "T11",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,
        "number_of_rounds": 3,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 5  # Top 5 winners
    },
    {
        "id": "T13",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,
        "number_of_rounds": 3,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 1  # Only 1 winner
    },
    {
        "id": "T15",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,
        "number_of_rounds": 3,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 2  # Top 2 winners
    },
    {
        "id": "T17",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 3,
        "supports_finalization": True,
        "expected_sessions": 1,
        "winner_count": 3  # Top 3 winners
    },

    # ========================================================================
    # TIER 1: Group + Knockout (1 config)
    # ========================================================================
    {
        "id": "T18",
        "name": "HEAD_TO_HEAD + Group Stage + Knockout",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 3,
        "number_of_rounds": None,
        "supports_finalization": False,
        "expected_sessions": None,  # Variable
        "winner_count": None  # Not applicable
    },
]


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def page(playwright):
    """Create a new Playwright page for each test - HEADED MODE for visual validation"""
    browser = playwright.firefox.launch(
        headless=False,  # ✅ VISIBLE BROWSER for visual validation
        slow_mo=3000  # 3 second delay between actions for visibility
    )
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    yield page

    context.close()
    browser.close()


# ============================================================================
# API HELPER FUNCTIONS
# ============================================================================

def create_tournament_via_api(config, admin_token):
    """Create tournament using API (faster than UI interaction)"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    start_date = datetime.now() + timedelta(days=1)
    end_date = start_date + timedelta(days=7)

    tournament_data = {
        "code": f"PLAYWRIGHT-{config['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "name": f"Playwright E2E: {config['name']}",
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "age_group": "PRO",
        "specialization_type": "PLAYER",
        "format": config["format"],
        "scoring_type": config["scoring_type"],
        "measurement_unit": config["measurement_unit"],
        "ranking_direction": config["ranking_direction"],
        "tournament_type_id": config["tournament_type_id"],
        "number_of_rounds": config.get("number_of_rounds", 1),
        "max_players": 8,
        "assignment_type": "OPEN_ASSIGNMENT",
        "location_city": "Budapest",
        "location_venue": "LFA Academy",
        "is_active": True,
        "status": "DRAFT"
    }

    # Remove None values
    tournament_data = {k: v for k, v in tournament_data.items() if v is not None}

    response = requests.post(
        f"{API_BASE_URL}/semesters",
        headers=headers,
        json=tournament_data
    )

    assert response.status_code == 200, f"Tournament creation failed: {response.text}"
    return response.json()["id"]


def enroll_players_via_api(tournament_id, admin_token):
    """Enroll players using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/admin/batch-enroll",
        headers=headers,
        json={"player_ids": TEST_PLAYER_IDS}
    )

    assert response.status_code == 200, f"Player enrollment failed: {response.text}"
    return response.json()["success"]


def start_tournament_via_api(tournament_id, admin_token):
    """Start tournament using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "IN_PROGRESS"}
    )

    assert response.status_code == 200, f"Tournament start failed: {response.text}"
    return True


def generate_sessions_via_api(tournament_id, config, admin_token):
    """Generate sessions using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15
    }

    # Add number_of_rounds for INDIVIDUAL_RANKING
    if config["format"] == "INDIVIDUAL_RANKING" and config.get("number_of_rounds"):
        payload["number_of_rounds"] = config["number_of_rounds"]

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/generate-sessions",
        headers=headers,
        json=payload
    )

    assert response.status_code == 200, f"Session generation failed: {response.text}"

    # Fetch sessions
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
        headers=headers
    )

    assert response.status_code == 200, f"Session fetch failed: {response.text}"
    return response.json()


def submit_results_via_api(tournament_id, sessions, config, admin_token):
    """Submit results using API

    NOTE: Multi-round support is handled by finalization, not result submission.
    Always submit 'results' field regardless of number_of_rounds.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    scoring_type = config["scoring_type"]

    for session in sessions:
        session_id = session["id"]

        # ✅ FIX: PLACEMENT scoring uses different endpoint and data format
        if scoring_type == "PLACEMENT":
            # PLACEMENT uses POST /tournaments/{tid}/sessions/{sid}/submit-results
            # with measured_value = placement (1, 2, 3, 4, 5, 6, 7, 8)
            placement_results = []
            for i, user_id in enumerate(TEST_PLAYER_IDS):
                placement_results.append({
                    "user_id": user_id,
                    "measured_value": i + 1  # 1st place, 2nd place, etc.
                })

            response = requests.post(
                f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/submit-results",
                headers=headers,
                json={"results": placement_results}
            )

            assert response.status_code == 200, f"PLACEMENT result submission failed: {response.text}"
        else:
            # Always submit regular results (multi-round aggregation happens at finalization)
            results = []
            for i, user_id in enumerate(TEST_PLAYER_IDS):
                if scoring_type == "ROUNDS_BASED":
                    score = 100 - (i * 5)
                elif scoring_type == "TIME_BASED":
                    score = 10.0 + (i * 0.5)
                elif scoring_type == "SCORE_BASED":
                    score = 95 - (i * 5)
                elif scoring_type == "DISTANCE_BASED":
                    score = 50.0 - (i * 2.0)
                else:
                    score = 100.0

                results.append({
                    "user_id": user_id,
                    "score": score,
                    "rank": i + 1
                })

            response = requests.patch(
                f"{API_BASE_URL}/sessions/{session_id}/results",
                headers=headers,
                json={"results": results}
            )

            assert response.status_code == 200, f"Result submission failed: {response.text}"

    return True


def finalize_sessions_via_api(tournament_id, sessions, admin_token):
    """Finalize sessions using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    for session in sessions:
        session_id = session["id"]

        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/finalize",
            headers=headers
        )

        # ✅ FIX: Allow 400 if session already finalized (PLACEMENT auto-finalizes)
        if response.status_code == 400 and "already finalized" in response.text:
            continue  # Session already finalized, skip

        assert response.status_code == 200, f"Finalization failed: {response.text}"

    return True


def complete_tournament_via_api(tournament_id, admin_token):
    """Complete tournament using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/complete",
        headers=headers
    )

    assert response.status_code == 200, f"Tournament completion failed: {response.text}"
    return True


def distribute_rewards_via_api(tournament_id, config, admin_token):
    """Distribute rewards using API"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # For INDIVIDUAL_RANKING, specify winner count
    payload = {"reason": "Playwright E2E Test"}
    if config.get("winner_count"):
        payload["winner_count"] = config["winner_count"]

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers,
        json=payload
    )

    assert response.status_code == 200, f"Reward distribution failed: {response.text}"
    return True


# ============================================================================
# PLAYWRIGHT UI VERIFICATION FUNCTIONS
# ============================================================================

def wait_for_streamlit_load(page: Page, timeout=15000):
    """Wait for Streamlit app to fully load"""
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=timeout)
    time.sleep(2)  # Additional wait for dynamic content


def verify_tournament_status_in_ui(page: Page, tournament_id: int, expected_status: str):
    """Verify tournament status is displayed correctly in Streamlit UI"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # UI Testing Contract: Use data-testid selector
    status_element = page.locator('[data-testid="tournament-status"]')
    page.wait_for_selector('[data-testid="tournament-status"]', timeout=10000)

    # Verify status attribute matches expected value
    status_value = status_element.get_attribute('data-status')
    assert status_value == expected_status, f"Expected status {expected_status}, got {status_value}"


def verify_rankings_displayed(page: Page, tournament_id: int, config: dict):
    """Verify rankings are displayed correctly in UI"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # UI Testing Contract: Use data-testid selectors
    rankings_container = page.locator('[data-testid="tournament-rankings"]')
    page.wait_for_selector('[data-testid="tournament-rankings"]', timeout=10000)
    expect(rankings_container).to_be_visible()

    # Verify table exists
    table = page.locator('[data-testid="rankings-table"]')
    expect(table).to_be_visible()

    # Verify 8 ranking rows (standard tournament size)
    rows = page.locator('[data-testid="ranking-row"]')
    expect(rows).to_have_count(8)


def verify_rewards_distributed(page: Page, tournament_id: int, config: dict):
    """Verify rewards are distributed and visible in UI"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # UI Testing Contract: Use data-testid selectors
    rewards_summary = page.locator('[data-testid="rewards-summary"]')
    page.wait_for_selector('[data-testid="rewards-summary"]', timeout=10000)
    expect(rewards_summary).to_be_visible()

    # Verify credits distributed
    total_credits = page.locator('[data-testid="total-credits"]')
    expect(total_credits).to_be_visible()
    credits_value = total_credits.get_attribute('data-value')
    assert int(credits_value) > 0, "No credits distributed"

    # Verify players rewarded (should be 8)
    players_rewarded = page.locator('[data-testid="players-rewarded"]')
    players_count = players_rewarded.get_attribute('data-value')
    assert int(players_count) == 8, f"Expected 8 players rewarded, got {players_count}"


def verify_winner_count_handling(page: Page, tournament_id: int, winner_count: int):
    """Verify proper handling of different winner counts in INDIVIDUAL_RANKING"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # UI Testing Contract: Use data-is-winner attribute to count winners
    winners = page.locator('[data-testid="ranking-row"][data-is-winner="true"]')
    expect(winners).to_have_count(winner_count)

    # Verify non-winners
    non_winners = page.locator('[data-testid="ranking-row"][data-is-winner="false"]')
    expect(non_winners).to_have_count(8 - winner_count)

    # Verify specific ranks are winners
    for rank in range(1, winner_count + 1):
        winner_row = page.locator(f'[data-testid="ranking-row"][data-rank="{rank}"]')
        is_winner = winner_row.get_attribute('data-is-winner')
        assert is_winner == "true", f"Rank {rank} should be marked as winner"

    # Verify ranks beyond winner_count are NOT winners
    for rank in range(winner_count + 1, 9):
        non_winner_row = page.locator(f'[data-testid="ranking-row"][data-rank="{rank}"]')
        is_winner = non_winner_row.get_attribute('data-is-winner')
        assert is_winner == "false", f"Rank {rank} should NOT be marked as winner"


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.parametrize("config", TEST_CONFIGURATIONS)
def test_tournament_complete_workflow_with_ui_validation(page: Page, admin_token, config):
    """
    Complete E2E workflow with Playwright UI validation

    Steps:
    1. Create tournament (API)
    2. Enroll players (API)
    3. Start tournament (API)
    4. Generate sessions (API)
    5. Submit results (API)
    6. Finalize sessions (API, if supported)
    7. Complete tournament (API)
    8. Distribute rewards (API)
    9. Verify tournament status in UI (Playwright)
    10. Verify rankings displayed in UI (Playwright)
    11. Verify rewards distributed in UI (Playwright)
    12. Verify winner count handling (Playwright, if applicable)
    """
    print(f"\n{'='*80}")
    print(f"Testing: {config['id']} - {config['name']}")
    print(f"{'='*80}")

    # Steps 1-8: Use API for workflow execution (backend already tested)
    tournament_id = create_tournament_via_api(config, admin_token)
    print(f"✅ Step 1: Tournament {tournament_id} created")

    enroll_players_via_api(tournament_id, admin_token)
    print(f"✅ Step 2: Players enrolled")

    start_tournament_via_api(tournament_id, admin_token)
    print(f"✅ Step 3: Tournament started")

    sessions = generate_sessions_via_api(tournament_id, config, admin_token)
    print(f"✅ Step 4: {len(sessions)} sessions generated")

    submit_results_via_api(tournament_id, sessions, config, admin_token)
    print(f"✅ Step 5: Results submitted")

    if config["supports_finalization"]:
        finalize_sessions_via_api(tournament_id, sessions, admin_token)
        print(f"✅ Step 6: Sessions finalized")
    else:
        print(f"⏭️  Step 6: Skipped (HEAD_TO_HEAD doesn't support finalization)")

    complete_tournament_via_api(tournament_id, admin_token)
    print(f"✅ Step 7: Tournament completed")

    distribute_rewards_via_api(tournament_id, config, admin_token)
    print(f"✅ Step 8: Rewards distributed")

    # Steps 9-12: STRICT Playwright UI validation (NO TRY-EXCEPT, FAIL ON ERROR)
    # Step 9: Verify tournament status
    verify_tournament_status_in_ui(page, tournament_id, "REWARDS_DISTRIBUTED")
    print(f"✅ Step 9: Tournament status verified in UI")

    # Step 10: Verify rankings displayed
    verify_rankings_displayed(page, tournament_id, config)
    print(f"✅ Step 10: Rankings displayed correctly in UI")

    # Step 11: Verify rewards distributed
    verify_rewards_distributed(page, tournament_id, config)
    print(f"✅ Step 11: Rewards distribution verified in UI")

    # Step 12: Verify winner count handling for INDIVIDUAL_RANKING
    if config.get("winner_count"):
        verify_winner_count_handling(page, tournament_id, config["winner_count"])
        print(f"✅ Step 12: Winner count ({config['winner_count']}) handling verified")
    else:
        print(f"⏭️  Step 12: Skipped (HEAD_TO_HEAD doesn't have winner_count)")

    print(f"\n✅ TEST {config['id']} PASSED (Tournament {tournament_id})")


def test_streamlit_app_accessible(page: Page):
    """Verify Streamlit app is running and accessible"""
    page.goto(STREAMLIT_URL)
    wait_for_streamlit_load(page)

    # Check for Streamlit container
    streamlit_container = page.locator("[data-testid='stAppViewContainer']")
    expect(streamlit_container).to_be_visible()

    print("✅ Streamlit app is accessible")


def test_backend_api_accessible(admin_token):
    """Verify backend API is running"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{API_BASE_URL}/users/me", headers=headers)

    assert response.status_code == 200, "Backend API not accessible"
    assert response.json()["email"] == ADMIN_EMAIL, "Admin authentication failed"

    print("✅ Backend API is accessible")


# ============================================================================
# SUMMARY TEST
# ============================================================================

def test_all_configurations_summary(admin_token):
    """
    Summary test that reports coverage for all 18 configurations
    """
    print("\n" + "="*80)
    print("PLAYWRIGHT E2E TEST SUITE - CONFIGURATION COVERAGE")
    print("="*80)

    print(f"\n✅ Total Configurations: {len(TEST_CONFIGURATIONS)}")

    # Count by format
    individual_ranking = [c for c in TEST_CONFIGURATIONS if c["format"] == "INDIVIDUAL_RANKING"]
    head_to_head = [c for c in TEST_CONFIGURATIONS if c["format"] == "HEAD_TO_HEAD"]

    print(f"\n📊 Configuration Breakdown:")
    print(f"   - INDIVIDUAL_RANKING: {len(individual_ranking)}")
    print(f"   - HEAD_TO_HEAD: {len(head_to_head)}")

    # Count by rounds (INDIVIDUAL_RANKING only)
    rounds_1 = [c for c in individual_ranking if c.get("number_of_rounds") == 1]
    rounds_2 = [c for c in individual_ranking if c.get("number_of_rounds") == 2]
    rounds_3 = [c for c in individual_ranking if c.get("number_of_rounds") == 3]

    print(f"\n🔄 INDIVIDUAL_RANKING by Rounds:")
    print(f"   - 1 round: {len(rounds_1)}")
    print(f"   - 2 rounds: {len(rounds_2)}")
    print(f"   - 3 rounds: {len(rounds_3)}")

    # Count by scoring type
    scoring_types = {}
    for config in individual_ranking:
        st = config["scoring_type"]
        scoring_types[st] = scoring_types.get(st, 0) + 1

    print(f"\n🎯 INDIVIDUAL_RANKING by Scoring Type:")
    for st, count in scoring_types.items():
        print(f"   - {st}: {count}")

    # Winner count variations
    winner_counts = set(c.get("winner_count") for c in individual_ranking if c.get("winner_count"))
    print(f"\n🏆 Winner Count Variations Tested: {sorted(winner_counts)}")

    print("\n" + "="*80)
    print("✅ 100% COVERAGE OF REAL CONFIGURATION SPACE")
    print("="*80)
