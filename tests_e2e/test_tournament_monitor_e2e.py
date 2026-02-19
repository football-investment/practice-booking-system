"""
Tournament Monitor Headless E2E Tests
======================================

Comprehensive Playwright test suite for the OPS Tournament Monitor page.
Tests all wizard steps, tournament launch, live monitoring panel, and regressions.

Auth strategy:
    URL-param injection (development mode only):
    GET /Tournament_Monitor?token=<JWT>&user=<JSON>
    restore_session_from_url() in Tournament_Monitor.py picks this up automatically.
    This is the designed E2E testing mechanism — no UI login form required.

Run:
    pytest tests_e2e/test_tournament_monitor_e2e.py -v --tb=short
    pytest tests_e2e/test_tournament_monitor_e2e.py -m tournament_monitor -v
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=800 pytest tests_e2e/test_tournament_monitor_e2e.py -v -s -k test_wizard

Coverage groups:
    A - Wizard Flow (steps 1-6, navigation, state preservation)
    B - OPS Tournament Launch (API-backed, tracking panel)
    C - Live Monitoring Panel (cards, grid, leaderboard, controls)
    D - Regression (navigation loop, stale slider, auth, display bugs)
"""

import json
import os
import time
import urllib.parse
import requests
import pytest
from playwright.sync_api import Page, expect

# ── Constants ────────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
MONITOR_PATH = "/Tournament_Monitor"

# Timeouts
_LOAD_TIMEOUT = 30_000       # 30s for page loads
_STREAMLIT_SETTLE = 2        # seconds to wait after Streamlit rerun

# NOTE: _LAUNCH_SETTLE (old time.sleep(10)) has been removed.
# Root cause: Streamlit uses WebSocket, not HTTP, so page.wait_for_load_state("networkidle")
# never truly settles while auto-refresh is active. The arbitrary 10s sleep was masking
# a race condition between st.rerun() and the tracking-panel render cycle.
# Replacement: _poll_ops_tournament_created() + Playwright expect() with explicit timeout.


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_admin_token(api_url: str) -> str:
    """Authenticate as admin and return JWT token."""
    resp = requests.post(
        f"{api_url}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


def _get_admin_user(api_url: str, token: str) -> dict:
    """Fetch admin user data from /users/me."""
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to fetch user: {resp.text}"
    return resp.json()


def _go_to_monitor_authenticated(page: Page, base_url: str, api_url: str) -> None:
    """
    Navigate to Tournament Monitor with auth injected via URL params.

    Uses the designed E2E mechanism: session_manager.restore_session_from_url()
    reads ?token=...&user=... and injects them into st.session_state.
    """
    token = _get_admin_token(api_url)
    user = _get_admin_user(api_url, token)

    # URL-encode the token and user JSON for query params
    user_json = json.dumps(user)
    params = urllib.parse.urlencode({"token": token, "user": user_json})
    url = f"{base_url}{MONITOR_PATH}?{params}"

    page.goto(url, timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


# ── Navigation helpers ────────────────────────────────────────────────────────

def _sidebar(page: Page):
    """Return the sidebar locator."""
    return page.locator("section[data-testid='stSidebar']")


def _click_next(page: Page) -> None:
    """Click the wizard Next button (in sidebar) and wait for Streamlit rerun.

    Does NOT use page.wait_for_load_state("networkidle") — Streamlit communicates
    via WebSocket, which keeps the network perpetually "active" while auto-refresh
    is running.  Instead, the caller is responsible for asserting the next step
    label via expect(), which Playwright retries automatically.
    """
    _sidebar(page).get_by_role("button", name="Next →").click()
    time.sleep(_STREAMLIT_SETTLE)


def _click_back(page: Page) -> None:
    """Click the wizard Back button (in sidebar) and wait for Streamlit rerun."""
    _sidebar(page).get_by_role("button", name="← Back").click()
    time.sleep(_STREAMLIT_SETTLE)


def _poll_ops_tournament_created(
    api_url: str,
    token: str,
    before_count: int,
    timeout_s: int = 60,
) -> bool:
    """
    Poll /api/v1/tournaments until a new OPS- tournament appears.

    Returns True as soon as the API confirms the tournament exists.
    Returns False if timeout is exceeded.

    Why API polling instead of UI waiting:
    - The OPS run-scenario API is synchronous: when it returns, the tournament
      exists in the DB with all sessions generated.
    - Streamlit's st.rerun() fires AFTER the API call completes, so polling the
      API is a deterministic success signal — independent of WebSocket timing.
    - Once the API confirms creation, the UI assertion only needs a short timeout.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{api_url}/api/v1/tournaments",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 20},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("items", [])
                ops_count = sum(
                    1 for t in items
                    if str(t.get("name", "") or t.get("tournament_name", "")).startswith("OPS-")
                )
                if ops_count > before_count:
                    return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def _get_ops_tournament_count(api_url: str, token: str) -> int:
    """Return the current number of OPS- prefixed tournaments in the system."""
    try:
        resp = requests.get(
            f"{api_url}/api/v1/tournaments",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 100},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("items", [])
            return sum(
                1 for t in items
                if str(t.get("name", "") or t.get("tournament_name", "")).startswith("OPS-")
            )
    except requests.RequestException:
        pass
    return 0


def _navigate_wizard_to_step(
    page: Page,
    base_url: str,
    api_url: str,
    target_step: int,
    tournament_format: str = "HEAD_TO_HEAD",
    scenario: str = "Smoke Test",
) -> None:
    """
    Navigate the wizard from Step 1 to a given step using default selections.

    8-step wizard (updated for Iteration 3):
        1 - Select Test Scenario
        2 - Select Tournament Format
        3 - Select Tournament Type (H2H) / Select Scoring Method (Individual)
        4 - Select Game Preset           (optional — default: None)
        5 - Select Player Count          (slider)
        6 - Select Simulation Mode
        7 - Configure Rewards            (optional — default: OPS Default)
        8 - Review Configuration & Launch

    Args:
        target_step: 1-8
        tournament_format: "HEAD_TO_HEAD" or "INDIVIDUAL_RANKING"
        scenario: label text for Step 1 radio ("Smoke Test" by default — fast 4p test)
    """
    _go_to_monitor_authenticated(page, base_url, api_url)
    if target_step == 1:
        return

    # Step 1 → 2: Select scenario (default: Smoke Test — avoids long 32-session runs)
    _sidebar(page).get_by_text(scenario, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)
    if target_step == 2:
        return

    # Step 2 → 3: Format selection
    if tournament_format == "INDIVIDUAL_RANKING":
        # Click Individual Ranking radio option (scoped to sidebar)
        _sidebar(page).get_by_text("Individual Ranking", exact=False).first.click()
        time.sleep(0.5)
    # HEAD_TO_HEAD is selected by default — no click needed
    _click_next(page)
    if target_step == 3:
        return

    # Step 3 → 4: Tournament Type (H2H) or Scoring (Individual) — both have default selection
    _click_next(page)
    if target_step == 4:
        return

    # Step 4 → 5: Game Preset (optional, default "None" is always valid)
    _click_next(page)
    if target_step == 5:
        return

    # Step 5 → 6: Player Count (slider has default value, always valid)
    _click_next(page)
    if target_step == 6:
        return

    # Step 6 → 7: Explicitly select Accelerated Simulation (auto_simulate=True,
    # complete_lifecycle=True) — NEVER leave this as the default "manual" which
    # produces no results and leaves the tournament stuck waiting for human input.
    _sidebar(page).get_by_text("Accelerated Simulation", exact=False).first.click()
    time.sleep(0.5)
    _click_next(page)
    if target_step == 7:
        return

    # Step 7 → 8: Rewards (OPS Default is pre-selected, always valid — just click Next)
    _click_next(page)


# ── OPS API helper ────────────────────────────────────────────────────────────

def _trigger_ops_tournament(
    api_url: str,
    token: str,
    scenario: str = "smoke_test",
    player_count: int = 4,
    tournament_format: str = "HEAD_TO_HEAD",
    tournament_type_code: str = "knockout",
    scoring_type: str = None,
) -> dict:
    """
    Trigger an OPS tournament via API and return the response dict.
    Uses smoke_test scenario (small player count, fast) by default.
    """
    payload = {
        "scenario": scenario,
        "player_count": player_count,
        "tournament_format": tournament_format,
        "dry_run": False,
        "confirmed": True,
    }
    if tournament_type_code and tournament_format == "HEAD_TO_HEAD":
        payload["tournament_type_code"] = tournament_type_code
    if scoring_type and tournament_format == "INDIVIDUAL_RANKING":
        payload["scoring_type"] = scoring_type

    resp = requests.post(
        f"{api_url}/api/v1/tournaments/ops/run-scenario",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=120,
    )
    assert resp.status_code == 200, f"OPS trigger failed ({resp.status_code}): {resp.text}"
    return resp.json()


# ── Group A: Wizard Flow Tests ───────────────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestWizardFlow:
    """Step-by-step wizard navigation tests."""

    def test_wizard_step1_renders_correct_content(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 1: 3 scenario options visible, Next button enabled."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")

        # Step label (partial match — full text is "Step 1 of 8: Select Test Scenario")
        expect(sidebar.get_by_text("Step 1 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # All 3 scenario options present in sidebar radio (labels include emoji)
        expect(sidebar.get_by_text("Large Field Monitor", exact=False).first).to_be_visible()
        expect(sidebar.get_by_text("Smoke Test", exact=False).first).to_be_visible()
        expect(sidebar.get_by_text("Scale Test", exact=False).first).to_be_visible()

        # Next button enabled (radio has default selection)
        expect(sidebar.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step2_format_selection(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 2: Format options visible, Back/Next buttons present."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=2)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Head-to-Head", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Individual Ranking", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step3_hth_tournament_type(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 3 (HEAD_TO_HEAD path): tournament type options visible."""
        _navigate_wizard_to_step(
            page, base_url, api_url, target_step=3, tournament_format="HEAD_TO_HEAD"
        )
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Knockout", exact=False).first).to_be_visible()
        expect(sb.get_by_text("League", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step3_individual_scoring(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 3 (INDIVIDUAL_RANKING path): scoring method options visible."""
        _navigate_wizard_to_step(
            page, base_url, api_url, target_step=3, tournament_format="INDIVIDUAL_RANKING"
        )
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Score Based", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Time Based", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Distance Based", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Placement", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step4_game_preset(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 4 (NEW): Game Preset selectbox visible, None option available, always valid."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=4)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # Selectbox "Game Preset" visible (optional step — default is None)
        expect(sb.get_by_text("Game Preset", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()
        # Step is always valid (optional), Next must be enabled
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step5_player_count(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 5: player count slider visible with valid default value."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=5)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # Streamlit slider renders as role="slider"; use label to disambiguate from auto-refresh slider
        expect(sb.get_by_role("slider", name="Number of players to enroll")).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step6_simulation_mode(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 6: 3 simulation mode options visible; Accelerated Simulation can be selected."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=6)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # All 3 simulation options visible
        expect(sb.get_by_text("Manual Results", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Auto-Simulation", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Accelerated Simulation", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

        # Verify Accelerated Simulation can be selected and shows its description
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        # After selecting Accelerated, description text should appear in sidebar
        expect(sb.get_by_text("Entire tournament lifecycle simulated instantly", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_step7_reward_config(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 7 (NEW): Reward templates visible, OPS Default pre-selected, always valid."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=7)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # All reward templates visible
        expect(sb.get_by_text("OPS Default", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Standard", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Championship", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Friendly", exact=False).first).to_be_visible()
        expect(sb.get_by_text("Custom", exact=False).first).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()
        # Step is always valid (default template pre-selected), Next must be enabled
        expect(sb.get_by_role("button", name="Next →")).to_be_enabled()

    def test_wizard_step8_review_launch(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 8: summary shows correct selections (Accelerated Simulation), Launch button present."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=8)
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("TOURNAMENT SUMMARY", exact=False)).to_be_visible()
        # HEAD_TO_HEAD path shows "Head-to-Head" in summary
        expect(sb.get_by_text("Head-to-Head", exact=False).first).to_be_visible()
        # Accelerated Simulation should appear in the summary (set by _navigate_wizard_to_step)
        expect(sb.get_by_text("Accelerated Simulation", exact=False).first).to_be_visible()
        # Launch button (has emoji in label)
        expect(
            sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        ).to_be_visible()
        expect(sb.get_by_role("button", name="← Back")).to_be_visible()

    def test_wizard_step8_individual_ranking_review(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 8 (INDIVIDUAL_RANKING path): summary shows Individual Ranking."""
        _navigate_wizard_to_step(
            page, base_url, api_url, target_step=8, tournament_format="INDIVIDUAL_RANKING"
        )
        sb = _sidebar(page)

        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Individual Ranking", exact=False).first).to_be_visible()
        expect(
            sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        ).to_be_visible()

    def test_wizard_back_navigation_step2_to_step1(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 2 returns to Step 1."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=2)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 1 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step3_to_step2(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 3 returns to Step 2."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=3)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step4_to_step3(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 4 (Game Preset) returns to Step 3 (Tournament Type)."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=4)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step5_to_step4(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 5 (Player Count) returns to Step 4 (Game Preset)."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=5)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 4 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step6_to_step5(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 6 (Simulation) returns to Step 5 (Player Count)."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=6)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 5 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step7_to_step6(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 7 (Rewards) returns to Step 6 (Simulation)."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=7)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 6 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_back_navigation_step8_to_step7(
        self, page: Page, base_url: str, api_url: str
    ):
        """Back from Step 8 (Review) returns to Step 7 (Rewards)."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=8)
        _click_back(page)
        expect(_sidebar(page).get_by_text("Step 7 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_no_navigation_loop(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Regression: Selecting tournament type in Step 3 and going Next
        must NOT loop back to Step 1 or Step 2.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Step 1 → 2
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Step 2 → 3 (HEAD_TO_HEAD default)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Click League in Step 3 to trigger state change
        league_option = sb.get_by_text("League", exact=False).first
        if league_option.is_visible():
            league_option.click()
            time.sleep(0.5)

        # Step 3 → 4 (Game Preset) — must NOT go back to Step 1 or 2
        _click_next(page)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_wizard_progress_bar_updates(
        self, page: Page, base_url: str, api_url: str
    ):
        """Progress bar shows completed steps (✅) for Steps 1-2 when on Step 3."""
        _navigate_wizard_to_step(page, base_url, api_url, target_step=3)
        sb = _sidebar(page)

        # At Step 3: Steps 1 and 2 should show ✅
        completed = sb.locator("text=✅").all()
        assert len(completed) >= 2, (
            f"Expected ≥2 completed steps on Step 3, got {len(completed)}"
        )

        # Current step indicator ➡️ should be visible
        expect(sb.get_by_text("➡️", exact=False)).to_be_visible()


# ── Group B: OPS Tournament Launch Tests ────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestOpsLaunch:
    """API-backed launch tests — validate OPS backend and UI integration."""

    def test_api_ops_response_has_required_fields(self, api_url: str):
        """OPS run-scenario returns triggered=True, tournament_id, OPS- prefixed name."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="smoke_test",
            player_count=4,
            tournament_format="HEAD_TO_HEAD",
            tournament_type_code="knockout",
        )
        assert data.get("triggered") is True, f"triggered not True: {data}"
        assert data.get("tournament_id") is not None, f"no tournament_id: {data}"
        assert data.get("tournament_name", "").startswith("OPS-"), (
            f"Name doesn't start with OPS-: {data.get('tournament_name')}"
        )
        assert data.get("enrolled_count", 0) >= 4, (
            f"enrolled_count too low: {data.get('enrolled_count')}"
        )

    def test_api_individual_ranking_launch(self, api_url: str):
        """INDIVIDUAL_RANKING tournament created successfully via OPS API."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="smoke_test",
            player_count=4,
            tournament_format="INDIVIDUAL_RANKING",
            scoring_type="SCORE_BASED",
        )
        assert data.get("triggered") is True, f"triggered not True: {data}"
        assert data.get("tournament_id") is not None, f"no tournament_id: {data}"

    def test_api_smoke_test_scenario(self, api_url: str):
        """smoke_test scenario is accepted and returns triggered=True."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(api_url, token, scenario="smoke_test", player_count=4)
        assert data.get("triggered") is True

    def test_api_large_field_monitor_scenario(self, api_url: str):
        """large_field_monitor scenario accepted, name has OPS- prefix."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="large_field_monitor",
            player_count=8,
            tournament_format="HEAD_TO_HEAD",
            tournament_type_code="knockout",
        )
        assert data.get("triggered") is True
        assert data.get("tournament_name", "").startswith("OPS-")

    def test_api_tournament_is_in_progress_after_launch(self, api_url: str):
        """Tournament created by OPS has tournament_status=IN_PROGRESS (Bug C fix)."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token, scenario="smoke_test", player_count=4
        )
        tid = data.get("tournament_id")
        assert tid, "No tournament_id in response"

        resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert resp.status_code == 200
        detail = resp.json()
        assert detail.get("tournament_status") == "IN_PROGRESS", (
            f"Expected IN_PROGRESS, got: {detail.get('tournament_status')}"
        )

    def test_api_sessions_generated_after_launch(self, api_url: str):
        """4-player knockout OPS tournament generates 4 sessions (includes 3rd Place Playoff)."""
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="smoke_test",
            player_count=4,
            tournament_type_code="knockout",
        )
        tid = data.get("tournament_id")
        assert tid

        resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) > 0, "No sessions generated for 4-player knockout"
        # 4-player knockout generates multiple sessions (SF + Final or QF structure)
        assert len(sessions) >= 3, (
            f"Expected ≥3 sessions for 4p knockout, got {len(sessions)}"
        )

    def test_launch_hth_knockout_appears_in_tracking(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Full wizard flow: Step 1→Smoke Test→Step 2→HTH→Step 3→Knockout→
        Step 4→default players→Step 5→Accelerated Simulation→Step 6→LAUNCH.

        Validates:
        1. Each step label is confirmed before advancing
        2. Accelerated Simulation is explicitly selected (not relying on default)
        3. After launch: wizard resets to Step 1 (success signal)
        4. Launched tournament appears in the tracking panel
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # ── Step 1: Select Smoke Test ────────────────────────────────────────
        expect(sb.get_by_text("Step 1 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        sb.get_by_text("Smoke Test", exact=False).first.click()
        time.sleep(0.5)
        _click_next(page)

        # ── Step 2: HEAD_TO_HEAD (default) ───────────────────────────────────
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # ── Step 3: Knockout (default) ────────────────────────────────────────
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # ── Step 4: Game Preset (optional, default None) ──────────────────────
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # ── Step 5: Player count slider (default) ─────────────────────────────
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # ── Step 6: Explicitly select Accelerated Simulation ──────────────────
        # CRITICAL: never leave this as "Manual Results" default — that produces
        # no auto-results and leaves the monitoring panel showing 0/N submitted.
        expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        # Verify the description text appears confirming selection
        expect(
            sb.get_by_text("Entire tournament lifecycle simulated instantly", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # ── Step 7: Rewards (OPS Default pre-selected, just advance) ──────────
        expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # ── Step 8: Review & Launch ───────────────────────────────────────────
        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # Verify summary shows Accelerated Simulation (not Manual Results)
        expect(sb.get_by_text("Accelerated Simulation", exact=False).first).to_be_visible()

        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_visible()

        # ── Record baseline BEFORE launch ─────────────────────────────────────
        # We need to confirm a NEW tournament was created, not just that
        # any OPS- tournament exists (could be from a previous test run).
        token_for_poll = _get_admin_token(api_url)
        ops_count_before = _get_ops_tournament_count(api_url, token_for_poll)

        launch_btn.click()

        # ── STEP 1: API confirmation (deterministic, independent of Streamlit timing) ──
        # execute_launch() calls trigger_ops_scenario() synchronously, then st.rerun().
        # Polling the API is reliable: once it returns a new OPS- tournament, the
        # backend work is 100% done — regardless of whether Streamlit has re-rendered.
        #
        # OLD (brittle): page.wait_for_load_state("networkidle") + time.sleep(10)
        # NEW: poll API until tournament count increases, max 60s
        api_confirmed = _poll_ops_tournament_created(
            api_url, token_for_poll, before_count=ops_count_before, timeout_s=60
        )
        assert api_confirmed, (
            "OPS tournament did not appear in API within 60s after clicking Launch. "
            "This indicates execute_launch() or trigger_ops_scenario() failed."
        )

        # ── STEP 2: Wizard reset (UI success signal) ──────────────────────────
        # After execute_launch() succeeds, it calls st.rerun() which resets the
        # wizard to Step 1.  Playwright's expect() retries automatically —
        # no sleep needed.  Timeout 30s covers WebSocket round-trip + render time.
        expect(sb.get_by_text("Step 1 of 8", exact=False)).to_be_visible(
            timeout=30_000
        )

        # ── STEP 3: Tournament card visible in monitoring panel ────────────────
        # After wizard reset, the auto-tracked OPS- tournament must appear in the
        # main content area.  Two assertions — belt AND suspenders:
        #
        # (a) Empty-state message gone — basic check (fragile alone: could pass
        #     during a rerun if the panel briefly shows the card then disappears)
        # (b) OPS- prefixed name visible — strong check: requires the card to be
        #     rendered AND the tournament name to be in the DOM simultaneously.
        #
        # Both use Playwright's auto-retry, which handles auto-refresh reruns.
        time.sleep(_STREAMLIT_SETTLE)  # 2s — one WebSocket round-trip for render
        expect(
            page.get_by_text("No active test tournaments", exact=False)
        ).not_to_be_visible(timeout=20_000)
        expect(
            page.get_by_text("OPS-", exact=False).first
        ).to_be_visible(timeout=20_000)


# ── Group C: Live Monitoring Panel Tests ─────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestMonitoringPanel:
    """Live monitoring panel UI tests."""

    def test_monitor_page_loads_for_admin(
        self, page: Page, base_url: str, api_url: str
    ):
        """Tournament Monitor page loads for admin — main heading visible."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        # Use heading role to disambiguate from sidebar nav item
        expect(
            page.get_by_role("heading", name="Tournament Monitor")
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_monitor_sidebar_has_wizard(
        self, page: Page, base_url: str, api_url: str
    ):
        """Sidebar contains the OPS Wizard section."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(sidebar.get_by_text("OPS WIZARD", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_monitor_sidebar_has_monitoring_controls(
        self, page: Page, base_url: str, api_url: str
    ):
        """Sidebar contains Monitoring Controls section."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(sidebar.get_by_text("MONITORING CONTROLS", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_auto_refresh_slider_present_and_in_range(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Auto-refresh slider visible, value in [5, 120].
        Regression: slider used to show stale value 5120.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")

        slider = sidebar.get_by_role("slider", name="Auto-refresh (seconds)")
        expect(slider).to_be_visible(timeout=_LOAD_TIMEOUT)

        slider_value = slider.get_attribute("aria-valuenow")
        if slider_value:
            val = int(slider_value)
            assert 5 <= val <= 120, (
                f"Slider value {val} is out of valid range [5, 120]"
            )

    def test_refresh_now_button_present(
        self, page: Page, base_url: str, api_url: str
    ):
        """'Refresh now' button visible in sidebar."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(
            sidebar.get_by_role("button", name="Refresh now")
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

    @pytest.mark.xfail(
        reason=(
            "Iteration 3 replaced the 'Enable auto-refresh' checkbox with a "
            "Streamlit fragment-based auto-refresh. Checkbox no longer exists. "
            "Test kept for documentation; remove once fragment behaviour is "
            "explicitly validated."
        ),
        strict=False,
    )
    def test_auto_refresh_checkbox_present(
        self, page: Page, base_url: str, api_url: str
    ):
        """'Enable auto-refresh' checkbox visible in sidebar (pre-Iteration-3 UI)."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(
            sidebar.get_by_text("Enable auto-refresh", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_no_active_tests_shows_info_message(
        self, page: Page, base_url: str, api_url: str
    ):
        """When no tracked tests, main area shows informational message."""
        _go_to_monitor_authenticated(page, base_url, api_url)

        # Clear any tracked tests first
        sidebar = page.locator("section[data-testid='stSidebar']")
        clear_btn = sidebar.get_by_role("button", name="Clear All Tracked Tests")
        if clear_btn.is_visible():
            clear_btn.click()
            page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
            time.sleep(_STREAMLIT_SETTLE)

        # Main area should show no-tournaments info
        expect(
            page.get_by_text("No active test tournaments", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_tracked_tests_metric_visible(
        self, page: Page, base_url: str, api_url: str
    ):
        """'Tracked Tests' metric visible in sidebar monitoring controls."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(
            sidebar.get_by_text("Tracked Tests", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_monitor_shows_welcome_for_admin(
        self, page: Page, base_url: str, api_url: str
    ):
        """Sidebar shows 'Welcome, <name>' greeting for admin."""
        _go_to_monitor_authenticated(page, base_url, api_url)
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(sidebar.get_by_text("Welcome,", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )


# ── Group D: Regression Tests ────────────────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.regression
class TestRegressions:
    """Regression tests for previously fixed bugs."""

    def test_wizard_step2_selection_no_loop_regression(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        P0 Regression: Selecting in Step 2 and clicking Next must advance to
        Step 3, NOT loop back to Step 1.
        (Root cause: wizard_scenario_widget value lost when Step 1 not rendered.)
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Go to Step 2
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Select INDIVIDUAL_RANKING (non-default)
        sb.get_by_text("Individual Ranking", exact=False).first.click()
        time.sleep(0.5)

        # Next must advance to Step 3, not loop back to Step 1
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Verify INDIVIDUAL_RANKING scoring step loaded
        expect(sb.get_by_text("Score Based", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_auto_refresh_slider_no_stale_value(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Regression: Auto-refresh slider showing 5120 (stale session state).
        Fixed by clamping stored value to [5, 120].
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)
        slider = sb.get_by_role("slider", name="Auto-refresh (seconds)")
        expect(slider).to_be_visible(timeout=_LOAD_TIMEOUT)

        val_str = slider.get_attribute("aria-valuenow")
        if val_str:
            val = int(val_str)
            assert val != 5120, "Stale auto-refresh value 5120 detected (regression)"
            assert 5 <= val <= 120, (
                f"Slider value {val} outside valid range [5, 120]"
            )

    def test_wizard_state_preserved_across_back_forward(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        State Preservation: Going Back and Forward again preserves previously
        selected INDIVIDUAL_RANKING format (not reset to HEAD_TO_HEAD default).
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Step 1 → 2
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Select INDIVIDUAL_RANKING
        sb.get_by_text("Individual Ranking", exact=False).first.click()
        time.sleep(0.5)

        # Step 2 → 3 (goes to scoring step for INDIVIDUAL_RANKING)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Go Back to Step 2
        _click_back(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Go Forward again — must still route to INDIVIDUAL_RANKING scoring step
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # If INDIVIDUAL_RANKING was preserved, we see "Score Based"
        # If it reset to HEAD_TO_HEAD, we'd see "Knockout"
        expect(sb.get_by_text("Score Based", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_individual_ranking_sessions_have_multiple_participants(
        self, api_url: str
    ):
        """
        Regression (Bug A): INDIVIDUAL_RANKING sessions have all players in one
        session (not one session per player). participant_names should have N>1 entries.
        """
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="smoke_test",
            player_count=4,
            tournament_format="INDIVIDUAL_RANKING",
            scoring_type="SCORE_BASED",
        )
        tid = data.get("tournament_id")
        assert tid

        sessions_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()

        # Find INDIVIDUAL_RANKING sessions
        ind_sessions = [
            s for s in sessions
            if s.get("match_format") == "INDIVIDUAL_RANKING"
            or s.get("tournament_phase") == "INDIVIDUAL_RANKING"
        ]
        assert len(ind_sessions) > 0, (
            "No INDIVIDUAL_RANKING sessions found — session generation failed"
        )

        first = ind_sessions[0]
        names = first.get("participant_names") or []
        assert len(names) > 1, (
            f"INDIVIDUAL_RANKING session should have multiple participants "
            f"(all players together), got {len(names)}: {names}"
        )
        # With 4 players and INDIVIDUAL_RANKING: 1 session, all 4 players in it
        assert len(names) >= 4, (
            f"Expected all 4 players in INDIVIDUAL_RANKING session, got {len(names)}"
        )

    def test_individual_ranking_tournament_has_single_session(
        self, api_url: str
    ):
        """
        Regression: INDIVIDUAL_RANKING generates exactly 1 session for N players
        (all compete together), NOT N separate sessions.
        """
        token = _get_admin_token(api_url)
        data = _trigger_ops_tournament(
            api_url, token,
            scenario="smoke_test",
            player_count=4,
            tournament_format="INDIVIDUAL_RANKING",
            scoring_type="SCORE_BASED",
        )
        tid = data.get("tournament_id")

        sessions_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        # INDIVIDUAL_RANKING: 1 session for all players
        assert len(sessions) == 1, (
            f"INDIVIDUAL_RANKING 4-player should generate 1 session, got {len(sessions)}"
        )
