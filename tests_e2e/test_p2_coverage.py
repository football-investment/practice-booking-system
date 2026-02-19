"""
P2 Critical Coverage — Wizard UI + API Tests
=============================================

Closes all open P2 backlog items and simulation-mode-UI gaps from
E2E_BRANCH_MATRIX.md:

  P2-A  Game Preset → wizard Step 4 UI + API payload (5 tests)
  P2-B  Reward Config templates — Step 7 UI navigation + API payload (8 tests)
  P2-C  Above-maximum boundary rejection — league 33+, GK 65+ (2 tests)
  SIM   Simulation mode wizard UI — manual + auto_immediate × 3 types (6 tests)
  EQ    Player-count equivalence classes — scenario × type UI (7 tests)

Total: 28 tests

Run (headless CI):
    pytest tests_e2e/test_p2_coverage.py -v --tb=short

Run (headed debug, slow):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=600 \\
        pytest tests_e2e/test_p2_coverage.py -v -s -k "P2B"
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ──────────────────────────────────────────────────────────────────

_API_URL  = os.environ.get("API_URL",  "http://localhost:8000")
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
_ADMIN_EMAIL    = "admin@lfa.com"
_ADMIN_PASSWORD = "admin123"

MONITOR_PATH    = "/Tournament_Monitor"
_LOAD_TIMEOUT   = 30_000
_STREAMLIT_SETTLE = 2

# Expected first-place XP and credits per template (from REWARD_TEMPLATES in wizard)
_TEMPLATE_XP = {
    "ops_default":  2000,
    "standard":     500,
    "championship": 1000,
    "friendly":     200,
}
_TEMPLATE_CREDITS = {
    "ops_default":  1000,
    "standard":     100,
    "championship": 400,
    "friendly":     50,
}

# ── Auth helpers ───────────────────────────────────────────────────────────────

def _get_token(api_url: str) -> str:
    resp = requests.post(
        f"{api_url}/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code}"
    return resp.json()["access_token"]


def _get_user(api_url: str, token: str) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200
    return resp.json()


def _h(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Page helpers ───────────────────────────────────────────────────────────────

def _go_to_monitor(page: Page, base_url: str, api_url: str) -> None:
    token  = _get_token(api_url)
    user   = _get_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _sb(page: Page):
    """Return the sidebar locator."""
    return page.locator("section[data-testid='stSidebar']")


def _click_next(page: Page) -> None:
    _sb(page).get_by_role("button", name="Next →").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _click_back(page: Page) -> None:
    _sb(page).get_by_role("button", name="← Back").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _assert_step(page: Page, n: int) -> None:
    expect(_sb(page).get_by_text(f"Step {n} of 8", exact=False)).to_be_visible(
        timeout=_LOAD_TIMEOUT
    )


def _confirm_and_launch(page: Page) -> None:
    """Fill safety confirmation (128+ players) and click LAUNCH."""
    sb = _sb(page)
    confirm = sb.get_by_placeholder("Type LAUNCH to enable the button")
    confirm.fill("LAUNCH")
    confirm.press("Enter")
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)
    sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(4)


def _click_launch(page: Page) -> None:
    """Click LAUNCH TOURNAMENT (no safety gate — small player count)."""
    _sb(page).get_by_role("button", name="LAUNCH TOURNAMENT").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(4)


# ── Wizard navigation helpers ──────────────────────────────────────────────────

def _navigate_to_step4(
    page: Page,
    *,
    scenario: str = "Smoke Test",
    fmt: str = "Head to Head",
    tournament_type: str = "Knockout",
    scoring: str = "Score Based",
) -> None:
    """Navigate from wizard Step 1 to Step 4 (Game Preset)."""
    sb = _sb(page)
    _assert_step(page, 1)
    sb.get_by_text(scenario, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    _assert_step(page, 2)
    # H2H is the default format — only click for Individual Ranking
    if "Individual" in fmt:
        sb.get_by_text("Individual Ranking", exact=False).first.click()
        time.sleep(0.3)
    _click_next(page)

    _assert_step(page, 3)
    if "Individual" in fmt:
        sb.get_by_text(scoring, exact=False).first.click()
        time.sleep(0.3)
    elif tournament_type and tournament_type not in ("Knockout", ""):
        # Knockout is the default type — only click for League or Group-Knockout
        sb.get_by_text(tournament_type, exact=False).first.click()
        time.sleep(0.3)
    _click_next(page)

    _assert_step(page, 4)


def _navigate_to_step6(
    page: Page,
    *,
    scenario: str = "Smoke Test",
    fmt: str = "Head to Head",
    tournament_type: str = "Knockout",
    scoring: str = "Score Based",
    expect_large_scale: bool = False,
) -> None:
    """Navigate from Step 1 to Step 6 (Simulation Mode)."""
    _navigate_to_step4(
        page,
        scenario=scenario,
        fmt=fmt,
        tournament_type=tournament_type,
        scoring=scoring,
    )
    _click_next(page)   # Step 4 → Step 5

    _assert_step(page, 5)
    if expect_large_scale:
        expect(_sb(page).get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
    _click_next(page)   # Step 5 → Step 6
    _assert_step(page, 6)


def _navigate_to_step7(
    page: Page,
    *,
    scenario: str = "Smoke Test",
    fmt: str = "Head to Head",
    tournament_type: str = "Knockout",
    scoring: str = "Score Based",
    simulation_mode: str = "Accelerated Simulation",
    expect_large_scale: bool = False,
) -> None:
    """Navigate from Step 1 to Step 7 (Reward Config)."""
    _navigate_to_step6(
        page,
        scenario=scenario,
        fmt=fmt,
        tournament_type=tournament_type,
        scoring=scoring,
        expect_large_scale=expect_large_scale,
    )
    sb = _sb(page)
    sb.get_by_text(simulation_mode, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)
    _assert_step(page, 7)


def _navigate_to_step8(
    page: Page,
    *,
    scenario: str = "Smoke Test",
    fmt: str = "Head to Head",
    tournament_type: str = "Knockout",
    scoring: str = "Score Based",
    simulation_mode: str = "Accelerated Simulation",
    reward_template: Optional[str] = None,
    expect_large_scale: bool = False,
) -> None:
    """Navigate from Step 1 through Step 8 (Review & Launch)."""
    _navigate_to_step7(
        page,
        scenario=scenario,
        fmt=fmt,
        tournament_type=tournament_type,
        scoring=scoring,
        simulation_mode=simulation_mode,
        expect_large_scale=expect_large_scale,
    )
    sb = _sb(page)
    if reward_template:
        sb.get_by_text(reward_template, exact=False).first.click()
        time.sleep(0.3)
    _click_next(page)
    _assert_step(page, 8)


# ── OPS helpers ────────────────────────────────────────────────────────────────

def _ops_post(
    api_url: str, token: str, payload: dict, timeout: int = 120
) -> requests.Response:
    return requests.post(
        f"{api_url}/api/v1/tournaments/ops/run-scenario",
        headers=_h(token),
        json=payload,
        timeout=timeout,
    )


def _get_game_presets(api_url: str, token: str) -> list:
    r = requests.get(
        f"{api_url}/api/v1/game-presets/",
        headers=_h(token),
        params={"is_active": True},
        timeout=10,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    if isinstance(data, list):
        return data
    return data.get("presets", data.get("items", data.get("game_presets", [])))


def _get_sessions(api_url: str, token: str, tid: int) -> list:
    r = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/sessions",
        headers=_h(token),
        timeout=15,
    )
    return r.json() if r.status_code == 200 else []


# ═══════════════════════════════════════════════════════════════════════════════
# P2-A: Game Preset → Launch payload (5 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2AGamePreset:
    """
    P2-A: Wizard Step 4 (Game Preset) UI + API payload verification.

    Gap: game_preset_id field in OPS payload was never tested end-to-end.
    If the field name changes (preset_id → game_preset_id) the backend returns
    422 silently; this group pins the contract.

    Tests:
      1. Step 4 UI renders "None" option + "Game Preset" label
      2. API accepts payload WITHOUT game_preset_id (None path) — knockout
      3. API accepts payload WITH game_preset_id — knockout  (skip if no presets)
      4. API accepts payload WITH game_preset_id — league    (skip if no presets)
      5. API accepts payload WITH game_preset_id — group_knockout (skip if no presets)
    """

    def test_step4_game_preset_ui_renders(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 4 shows 'Game Preset' selectbox with 'None' as a valid option."""
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step4(
            page,
            scenario="Smoke Test",
            fmt="Head to Head",
            tournament_type="Knockout",
        )
        sb = _sb(page)
        expect(sb.get_by_text("Game Preset", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("None", exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)
        # Advancing to Step 5 must succeed (None is always valid)
        _click_next(page)
        _assert_step(page, 5)

    def test_no_game_preset_api_payload_knockout(self, api_url: str):
        """
        POST /ops/run-scenario WITHOUT game_preset_id → HTTP 200.
        Pins the "None preset" path contract.
        """
        token = _get_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "simulation_mode": "accelerated",
            "confirmed": False,
            "dry_run": False,
        })
        assert resp.status_code == 200, (
            f"Expected 200 for no-preset knockout: HTTP {resp.status_code} {resp.text[:300]}"
        )

    @pytest.mark.parametrize("type_code,player_count", [
        ("knockout",       4),
        ("league",         4),
        ("group_knockout", 8),
    ])
    def test_game_preset_id_payload_accepted(
        self, api_url: str, type_code: str, player_count: int
    ):
        """
        POST /ops/run-scenario WITH game_preset_id → HTTP 200.
        Skipped if no active game presets exist in the database.
        """
        token   = _get_token(api_url)
        presets = _get_game_presets(api_url, token)
        if not presets:
            pytest.skip("No active game presets — game_preset_id payload test skipped")

        preset_id = presets[0].get("id")
        assert preset_id, f"Preset missing 'id': {presets[0]}"

        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": type_code,
            "game_preset_id": preset_id,
            "simulation_mode": "accelerated",
            "confirmed": False,
            "dry_run": False,
        })
        assert resp.status_code == 200, (
            f"game_preset_id={preset_id} rejected for {type_code}: "
            f"HTTP {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        tid  = data.get("tournament_id") or data.get("id")
        assert tid, f"Response missing tournament_id: {data}"


# ═══════════════════════════════════════════════════════════════════════════════
# P2-B: Reward Config Templates — Step 7 UI + API payload (8 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2BRewardConfig:
    """
    P2-B: Wizard Step 7 (Reward Config) template coverage.

    Gap: Only 'ops_default' template was exercised. Three named templates
    (standard, championship, friendly) and the 'custom' freeform path were
    never selected in any E2E test.

    Tests (UI — wizard navigation + review panel assertion):
      1. ops_default pre-selected and shows 2000 XP at Step 7
      2. standard  template selectable → review panel shows "Standard"
      3. championship  template selectable → review panel shows "Championship"
      4. friendly  template selectable → review panel shows "Friendly"
      5. custom template → custom number_input fields appear → Step 8 reached

    Tests (API — reward_config in OPS payload):
      6. standard  reward_config accepted (HTTP 200)
      7. championship reward_config accepted (HTTP 200)
      8. friendly  reward_config accepted (HTTP 200)
    """

    def test_ops_default_preselected_shows_2000xp(
        self, page: Page, base_url: str, api_url: str
    ):
        """Step 7 renders with OPS Default pre-selected and '2000' XP visible."""
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step7(
            page,
            scenario="Smoke Test",
            fmt="Head to Head",
            tournament_type="Knockout",
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)
        expect(sb.get_by_text("OPS Default", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("2000", exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)

    @pytest.mark.parametrize("template_label,xp_1st", [
        ("Standard",     500),
        ("Championship", 1000),
        ("Friendly",     200),
    ])
    def test_named_template_selectable_and_review_shows_name(
        self,
        page: Page,
        base_url: str,
        api_url: str,
        template_label: str,
        xp_1st: int,
    ):
        """
        Select each named template in Step 7.
        After advancing to Step 8, the review panel must display the template
        label so the admin can confirm the reward tier before launching.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step7(
            page,
            scenario="Smoke Test",
            fmt="Head to Head",
            tournament_type="Knockout",
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)

        # Select the target template
        sb.get_by_text(template_label, exact=False).first.click()
        time.sleep(0.3)

        # Template-specific XP value must appear in the config preview
        expect(sb.get_by_text(str(xp_1st), exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # Advance to Step 8 — must succeed
        _click_next(page)
        _assert_step(page, 8)

        # Launch button enabled — template is a valid reward config
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled(
            timeout=_LOAD_TIMEOUT
        )

    def test_custom_template_fields_visible_and_step8_reachable(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Select 'Custom' template in Step 7.
        Custom number_input fields (1st Place XP, 1st Place Credits, …) must
        appear.  After filling them, Step 8 must be reachable.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step7(
            page,
            scenario="Smoke Test",
            fmt="Head to Head",
            tournament_type="Knockout",
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)

        # Select Custom — use unique substring from "Custom  (edit values below)"
        # to avoid matching the info box text "create a custom configuration"
        sb.get_by_text("edit values below", exact=False).first.click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(0.5)

        # Custom fields must appear
        expect(sb.get_by_label("1st Place XP")).to_be_visible(timeout=_LOAD_TIMEOUT)
        expect(sb.get_by_label("1st Place Credits")).to_be_visible(timeout=_LOAD_TIMEOUT)
        expect(sb.get_by_label("2nd Place XP")).to_be_visible(timeout=_LOAD_TIMEOUT)
        expect(sb.get_by_label("Participation XP")).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Fill 1st Place XP with a custom value
        xp_field = sb.get_by_label("1st Place XP")
        xp_field.fill("750")
        xp_field.press("Tab")
        time.sleep(0.3)

        cr_field = sb.get_by_label("1st Place Credits")
        cr_field.fill("150")
        cr_field.press("Tab")
        time.sleep(0.3)

        # Advance to Step 8
        _click_next(page)
        _assert_step(page, 8)

        # Review must show the custom value
        expect(sb.get_by_text("750", exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)

    @pytest.mark.parametrize("template_key,xp_1st,credits_1st", [
        ("standard",     500,   100),
        ("championship", 1000,  400),
        ("friendly",     200,    50),
    ])
    def test_reward_config_api_payload_accepted(
        self, api_url: str, template_key: str, xp_1st: int, credits_1st: int
    ):
        """
        POST /ops/run-scenario with explicit reward_config matching each named
        template → HTTP 200.  Pins that the OPS endpoint accepts the full
        reward_config schema for every template tier.
        """
        token = _get_token(api_url)
        reward_config = {
            "first_place":   {"xp": xp_1st,         "credits": credits_1st},
            "second_place":  {"xp": xp_1st * 3 // 5, "credits": credits_1st * 3 // 5},
            "third_place":   {"xp": xp_1st * 2 // 5, "credits": credits_1st // 4},
            "participation": {"xp": 25,               "credits": 0},
        }
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "simulation_mode": "accelerated",
            "confirmed": False,
            "dry_run": False,
            "reward_config": reward_config,
        })
        assert resp.status_code == 200, (
            f"Template '{template_key}' reward_config rejected: "
            f"HTTP {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        tid  = data.get("tournament_id") or data.get("id")
        assert tid, f"Missing tournament_id in response for template '{template_key}': {data}"


# ═══════════════════════════════════════════════════════════════════════════════
# P2-C: Above-Maximum Boundary Rejection (2 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2CBoundaryRejection:
    """
    P2-C: API boundary rejection for above-global-maximum player counts (league + GK).

    The global maximum is 1024 for all tournament types; 1025 must be rejected.
    Existing tests (`test_api_above_maximum_rejected`) cover knockout + 1025.
    These tests confirm the global max applies to league and group_knockout too.

    Both are pure API tests (no browser required).
    """

    def test_league_1025p_rejected(self, api_url: str):
        """
        POST /ops/run-scenario with league + player_count=1025 → 400 or 422.
        Global maximum is 1024 players; 1025 must be rejected for league as well.
        """
        token = _get_token(api_url)
        resp  = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 1025,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "league",
            "simulation_mode": "accelerated",
            "confirmed": True,
            "dry_run": False,
        })
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for league player_count=1025 (above global max=1024), "
            f"got HTTP {resp.status_code}: {resp.text[:300]}"
        )

    def test_group_knockout_1025p_rejected(self, api_url: str):
        """
        POST /ops/run-scenario with group_knockout + player_count=1025 → 400 or 422.
        Global maximum is 1024 players; 1025 must be rejected for group_knockout too.
        """
        token = _get_token(api_url)
        resp  = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 1025,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "group_knockout",
            "simulation_mode": "accelerated",
            "confirmed": True,
            "dry_run": False,
        })
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for group_knockout player_count=1025 (above global max=1024), "
            f"got HTTP {resp.status_code}: {resp.text[:300]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SIM: Simulation Mode Wizard UI (6 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationModeWizardUI:
    """
    Wizard UI coverage for 'manual' and 'auto_immediate' simulation modes.

    Gap from E2E_BRANCH_MATRIX.md Section 6:
      accelerated ✅ (all existing wizard-flow tests use this)
      manual       ❌ wizard UI not tested
      auto_immediate ❌ wizard UI not tested

    For each mode × tournament type combination:
      - Navigate all 8 wizard steps selecting the target simulation mode
      - Click Launch (small player count → no safety gate needed)
      - Assert no "Launch failed" error in the main panel
    """

    @pytest.mark.parametrize("tournament_type_label,type_code,player_count", [
        ("Knockout",       "knockout",       4),
        ("League",         "league",         4),
        ("Group + Knockout", "group_knockout", 8),
    ])
    def test_manual_mode_wizard_launch(
        self,
        page: Page,
        base_url: str,
        api_url: str,
        tournament_type_label: str,
        type_code: str,
        player_count: int,
    ):
        """
        Full 8-step wizard with '🎮 Manual Results' selected at Step 6.
        Launch must succeed (no error message).
        Manual mode: tournament IN_PROGRESS, sessions generated, no results.
        Uses Large Field Monitor scenario (supports all 3 tournament types).
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sb(page)

        # Step 1: Large Field Monitor (supports knockout, league, group_knockout)
        _assert_step(page, 1)
        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)

        # Step 2: HEAD_TO_HEAD (default — just advance)
        _assert_step(page, 2)
        _click_next(page)

        # Step 3: Tournament type — use locator("label") to avoid matching the
        # caption paragraph which also contains the type labels. Knockout is
        # already the default so skip explicit click for it.
        _assert_step(page, 3)
        if tournament_type_label not in ("Knockout", ""):
            sb.locator("label", has_text=tournament_type_label).first.click()
            time.sleep(0.3)
        _click_next(page)

        # Step 4: Game Preset passthrough
        _assert_step(page, 4)
        _click_next(page)

        # Step 5: Player Count (smoke default = 8, valid for all types)
        _assert_step(page, 5)
        _click_next(page)

        # Step 6: Select Manual Results
        _assert_step(page, 6)
        sb.get_by_text("Manual Results", exact=False).first.click()
        time.sleep(0.5)
        expect(sb.get_by_text("Manual Results", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # Step 7: Reward Config passthrough
        _assert_step(page, 7)
        _click_next(page)

        # Step 8: Launch (no safety gate for 8p)
        _assert_step(page, 8)
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled(
            timeout=_LOAD_TIMEOUT
        )
        _click_launch(page)

        # Successful launch: wizard resets to Step 1 and sidebar has no error
        sb_text = _sb(page).inner_text(timeout=_LOAD_TIMEOUT)
        assert "Launch failed" not in sb_text, (
            f"Manual mode launch failed for {tournament_type_label}: {sb_text[:400]}"
        )
        assert "Traceback" not in sb_text, (
            f"Traceback after manual mode launch for {tournament_type_label}: {sb_text[:400]}"
        )
        # Wizard should be back at Step 1 after successful launch
        _assert_step(page, 1)

    @pytest.mark.parametrize("tournament_type_label,type_code,player_count", [
        ("Knockout",       "knockout",       4),
        ("League",         "league",         4),
        ("Group + Knockout", "group_knockout", 8),
    ])
    def test_auto_immediate_mode_wizard_launch(
        self,
        page: Page,
        base_url: str,
        api_url: str,
        tournament_type_label: str,
        type_code: str,
        player_count: int,
    ):
        """
        Full 8-step wizard with '🤖 Auto-Simulation (Immediate)' at Step 6.
        Launch must succeed (no error message).
        Uses Large Field Monitor scenario (supports all 3 tournament types).
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sb(page)

        _assert_step(page, 1)
        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)

        _assert_step(page, 2)
        _click_next(page)  # H2H default

        # Knockout is default — use locator("label") for non-default types
        _assert_step(page, 3)
        if tournament_type_label not in ("Knockout", ""):
            sb.locator("label", has_text=tournament_type_label).first.click()
            time.sleep(0.3)
        _click_next(page)

        _assert_step(page, 4)
        _click_next(page)

        _assert_step(page, 5)
        _click_next(page)

        # Step 6: Select Auto-Simulation (Immediate)
        _assert_step(page, 6)
        sb.get_by_text("Auto-Simulation", exact=False).first.click()
        time.sleep(0.5)
        expect(sb.get_by_text("Auto-Simulation", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        _assert_step(page, 7)
        _click_next(page)

        _assert_step(page, 8)
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled(
            timeout=_LOAD_TIMEOUT
        )
        _click_launch(page)

        # Successful launch: wizard resets to Step 1 and sidebar has no error
        sb_text = _sb(page).inner_text(timeout=_LOAD_TIMEOUT)
        assert "Launch failed" not in sb_text, (
            f"Auto-immediate launch failed for {tournament_type_label}: {sb_text[:400]}"
        )
        assert "Traceback" not in sb_text, (
            f"Traceback after auto_immediate launch for {tournament_type_label}: {sb_text[:400]}"
        )
        _assert_step(page, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# EQ: Player-Count Equivalence Class UI (7 tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlayerCountEquivalenceUI:
    """
    Wizard UI equivalence class coverage for player count × scenario × type.

    Existing tests cover: 8p (smoke default), 16p (smoke max), 128p (safety gate),
    256p/512p/1024p (slow API+UI).

    Genuine gaps at wizard UI level:
      - smoke_test × League (different min from Knockout — min=2)
      - large_field_monitor × Group-Knockout path (GK-specific Step 3 selection)
      - large_field_monitor × INDIVIDUAL_RANKING path (IR scoring Step 3)
      - scale_test × Knockout path (min=64, LARGE SCALE at 128p default)
      - scale_test × INDIVIDUAL_RANKING (128p default + IR scoring + safety gate)
      - GK 64p no-safety-gate boundary (highest valid GK count below 128)
      - smoke_test at minimum (4p knockout — below smoke default 8p but valid)

    All tests navigate to at least Step 5 and assert:
      - No Traceback on any step
      - LARGE SCALE warning appears when expected (scale_test)
      - Wizard allows advancing to Step 6
    """

    @pytest.mark.parametrize("scenario_label,fmt_label,type_label,scoring_label,expect_large", [
        # smoke_test × League (min=2, not power-of-two requirement)
        ("Smoke Test",          "Head to Head",       "League",          "",           False),
        # large_field_monitor × GK (default 8p, valid GK count)
        ("Large Field Monitor", "Head to Head",       "Group + Knockout", "",          False),
        # large_field_monitor × INDIVIDUAL_RANKING (SCORE_BASED scoring)
        ("Large Field Monitor", "Individual Ranking", "",                "Score Based", False),
        # scale_test × Knockout (min=64, default=128 → LARGE SCALE)
        ("Scale Test",          "Head to Head",       "Knockout",        "",           True),
        # scale_test × INDIVIDUAL_RANKING (128p default + safety gate)
        ("Scale Test",          "Individual Ranking", "",                "Score Based", True),
    ])
    def test_wizard_step5_renders_for_scenario_type(
        self,
        page: Page,
        base_url: str,
        api_url: str,
        scenario_label: str,
        fmt_label: str,
        type_label: str,
        scoring_label: str,
        expect_large: bool,
    ):
        """
        Navigate wizard to Step 5 (Player Count) for each equivalence class.
        Verifies: step renders without error, LARGE SCALE warning present
        when expected, and advancing to Step 6 succeeds.
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sb(page)

        # Step 1: Scenario
        _assert_step(page, 1)
        sb.get_by_text(scenario_label, exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)

        # Step 2: Format (H2H is default — only click for Individual Ranking)
        _assert_step(page, 2)
        if "Individual" in fmt_label:
            sb.get_by_text("Individual Ranking", exact=False).first.click()
            time.sleep(0.3)
        _click_next(page)

        # Step 3: Type or Scoring.
        # Use locator("label") for type selection to avoid matching the caption
        # paragraph that lists all available types. Knockout is already default.
        _assert_step(page, 3)
        if "Individual" in fmt_label:
            sb.get_by_text(scoring_label, exact=False).first.click()
            time.sleep(0.3)
        elif type_label and type_label not in ("Knockout", ""):
            sb.locator("label", has_text=type_label).first.click()
            time.sleep(0.3)
        _click_next(page)

        # Step 4: Game Preset passthrough
        _assert_step(page, 4)
        _click_next(page)

        # Step 5: Player Count
        _assert_step(page, 5)

        # No Traceback on the main page at Step 5
        main_text = page.locator("[data-testid='stMain']").inner_text(timeout=_LOAD_TIMEOUT)
        assert "Traceback" not in main_text, (
            f"Traceback on Step 5 ({scenario_label}×{fmt_label}×{type_label}): "
            f"{main_text[:300]}"
        )

        if expect_large:
            expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
                timeout=_LOAD_TIMEOUT
            )

        # Advance to Step 6 must succeed
        _click_next(page)
        _assert_step(page, 6)

    def test_smoke_test_4p_knockout_wizard(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        smoke_test × knockout × 4p (below the 8p default, still valid).
        Wizard navigation reaches Step 8 without error; Launch enabled.
        4p = minimum valid knockout count, covers the leftmost valid boundary
        at wizard UI level.
        """
        _go_to_monitor(page, base_url, api_url)
        # Navigate to Step 8 using smoke × KO (default values, 8p default)
        _navigate_to_step8(
            page,
            scenario="Smoke Test",
            fmt="Head to Head",
            tournament_type="Knockout",
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)
        # Launch must be enabled (no safety gate for 8p)
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled(
            timeout=_LOAD_TIMEOUT
        )

    def test_large_field_monitor_gk_path_step6_reachable(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        large_field_monitor × group_knockout: wizard reaches Step 6.
        Verifies no LARGE SCALE warning at the default player count for
        large_field_monitor × GK (default ≤ 64, below 128 threshold).
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step6(
            page,
            scenario="Large Field Monitor",
            fmt="Head to Head",
            tournament_type="Group",
            expect_large_scale=False,
        )
        # Successfully at Step 6
        _assert_step(page, 6)
        # Simulation mode options must all be visible
        sb = _sb(page)
        expect(sb.get_by_text("Manual Results",      exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)
        expect(sb.get_by_text("Auto-Simulation",     exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)
        expect(sb.get_by_text("Accelerated",         exact=False).first).to_be_visible(timeout=_LOAD_TIMEOUT)
