"""
P3 Critical Coverage — Post-Launch UI & Phase B Gap Closure
============================================================

Closes remaining Phase B gaps identified in the 2026-02-15 UI audit.
All tests are 100% UI-driven Playwright; no API calls for state assertion.

  SIM-POST    After wizard LAUNCH → tournament card visible in monitor main area
              (manual / auto_immediate / accelerated)                   3 tests

  LIFECYCLE   Championship template full lifecycle:
              wizard selection → accelerated launch → leaderboard visible
              in browser DOM with correct XP                            1 test

  GATE-L      Safety gate League 128p via wizard UI
              (scale_test scenario, default player_count=128)           1 test

  GATE-GK     EXCLUDED — architecturally impossible:
              Group+Knockout max=64 players < 128 safety threshold.
              The safety gate can never be reached for GK by design.

  PCOUNT      Player count 32p / 64p / 256p / 1024p via slider UI      4 tests

Total: 9 tests

Run (headless CI):
    pytest tests_e2e/test_p3_coverage.py -v --tb=short

Run (headed debug, slow):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=600 \\
        pytest tests_e2e/test_p3_coverage.py -v -s
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse

import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ──────────────────────────────────────────────────────────────────

_API_URL  = os.environ.get("API_URL",  "http://localhost:8000")
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
_ADMIN_EMAIL    = "admin@lfa.com"
_ADMIN_PASSWORD = "admin123"

MONITOR_PATH  = "/Tournament_Monitor"
_LOAD_TIMEOUT = 30_000
_SLOW_TIMEOUT = 90_000   # accelerated mode may take up to ~90 s end-to-end
_SETTLE       = 2        # seconds after networkidle to let Streamlit re-render

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


# ── Page helpers ───────────────────────────────────────────────────────────────

def _go_to_monitor(page: Page, base_url: str, api_url: str) -> None:
    token  = _get_token(api_url)
    user   = _get_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_SETTLE)


def _sb(page: Page):
    return page.locator("section[data-testid='stSidebar']")


def _main(page: Page):
    return page.locator("[data-testid='stMain']")


def _click_next(page: Page) -> None:
    _sb(page).get_by_role("button", name="Next →").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_SETTLE)


def _assert_step(page: Page, n: int) -> None:
    expect(_sb(page).get_by_text(f"Step {n} of 8", exact=False)).to_be_visible(
        timeout=_LOAD_TIMEOUT
    )


def _click_launch(page: Page) -> None:
    """Click LAUNCH TOURNAMENT (no safety gate — small player count)."""
    _sb(page).get_by_role("button", name="LAUNCH TOURNAMENT").click()
    page.wait_for_load_state("networkidle", timeout=_SLOW_TIMEOUT)
    time.sleep(6)   # allow accelerated tournament to complete + st.rerun()


def _confirm_and_launch(page: Page) -> None:
    """Fill safety confirmation (128+ players) and click LAUNCH."""
    sb = _sb(page)
    confirm = sb.get_by_placeholder("Type LAUNCH to enable the button")
    confirm.fill("LAUNCH")
    confirm.press("Enter")
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_SETTLE)
    sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
    page.wait_for_load_state("networkidle", timeout=_SLOW_TIMEOUT)
    time.sleep(6)


# ── Wizard navigation helpers ──────────────────────────────────────────────────

def _navigate_to_step5_with_count(
    page: Page,
    *,
    scenario: str,
    tournament_type: str = "Knockout",
    player_count: int | None = None,
) -> None:
    """
    Navigate to Step 5 (Player Count) and optionally set the slider.

    Slider interaction uses keyboard:
      Home  → scenario minimum
      End   → scenario maximum (1024)
      Arrow keys (step=2) → specific values
    """
    sb = _sb(page)
    _assert_step(page, 1)

    # Step 1: select scenario
    sb.get_by_text(scenario, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: H2H is default — no click needed
    _assert_step(page, 2)
    _click_next(page)

    # Step 3: select tournament type (Knockout is default)
    _assert_step(page, 3)
    if tournament_type not in ("Knockout", ""):
        sb.locator("label", has_text=tournament_type).first.click()
        time.sleep(0.3)
    _click_next(page)

    # Step 4: Game Preset — accept default (None), proceed
    _assert_step(page, 4)
    _click_next(page)

    # Now at Step 5: Player Count
    _assert_step(page, 5)

    if player_count is not None:
        # Streamlit renders st.slider() via the RC-slider React library.
        # Keyboard navigation is handled by the RC-slider HANDLE element
        # (role="slider"), NOT the hidden <input type="range"> used only
        # for accessibility purposes.
        #
        # The handle is below the viewport when the wizard Step 5 first
        # renders (sidebar scrolled to top). scroll_into_view_if_needed()
        # brings it into view; then locator.press() focuses it and sends
        # the keyboard event in one call.
        #
        # At Step 5 there are exactly TWO role="slider" elements:
        #   1st — wizard player-count slider  (what we want)
        #   2nd — monitoring-controls auto-refresh slider
        time.sleep(0.5)  # wait for Step 5 React components to mount

        handle = page.locator('[role="slider"]').first
        handle.scroll_into_view_if_needed(timeout=_LOAD_TIMEOUT)
        time.sleep(0.3)

        # Navigate to minimum first
        handle.press("Home")
        time.sleep(0.3)

        if player_count == 1024:
            handle.press("End")
        else:
            # Read current position (aria-valuenow is updated by RC-slider)
            current_raw = handle.get_attribute("aria-valuenow")
            current = int(current_raw) if current_raw else 0
            steps = (player_count - current) // 2
            key = "ArrowRight" if steps > 0 else "ArrowLeft"
            for _ in range(abs(steps)):
                handle.press(key)
                time.sleep(0.04)

        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(1)


def _navigate_to_step8_sim(
    page: Page,
    *,
    scenario: str = "Smoke Test",
    tournament_type: str = "Knockout",
    simulation_mode: str = "Accelerated Simulation",
    reward_template: str | None = None,
) -> None:
    """
    Navigate from Step 1 to Step 8 (Review & Launch).
    Uses H2H format, custom scenario/type/simulation/template.
    """
    sb = _sb(page)
    _assert_step(page, 1)

    sb.get_by_text(scenario, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: H2H default
    _assert_step(page, 2)
    _click_next(page)

    # Step 3
    _assert_step(page, 3)
    if tournament_type not in ("Knockout", ""):
        sb.locator("label", has_text=tournament_type).first.click()
        time.sleep(0.3)
    _click_next(page)

    # Step 4: Game Preset
    _assert_step(page, 4)
    _click_next(page)

    # Step 5: Player Count (use scenario default)
    _assert_step(page, 5)
    _click_next(page)

    # Step 6: Simulation Mode
    _assert_step(page, 6)
    sb.get_by_text(simulation_mode, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 7: Reward Config
    _assert_step(page, 7)
    if reward_template:
        sb.get_by_text(reward_template, exact=False).first.click()
        time.sleep(0.3)
    _click_next(page)

    # Step 8: Review & Launch
    _assert_step(page, 8)


# ══════════════════════════════════════════════════════════════════════════════
# SIM-POST: Post-launch tournament state visible via browser DOM
# ══════════════════════════════════════════════════════════════════════════════

class TestSimPostLaunchMonitor:
    """
    After wizard LAUNCH, the newly created tournament must appear in the
    Tournament Monitor main area without any API assertions from the test.

    The wizard auto-tracks the tournament in Streamlit session state
    (_ops_tracked_tournaments). On st.rerun(), the monitor renders a
    "🔴 LIVE TEST TRACKING" section in the main area for each tracked
    tournament.

    Assertion: main area contains "LIVE TEST TRACKING" (not empty state).
    This is 100% browser-DOM verification — no API calls for state.
    """

    def test_manual_mode_tournament_appears_in_monitor(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Manual Results mode: after launch, tournament card appears in
        main area (not empty-state message).
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_sim(
            page,
            scenario="Smoke Test",
            simulation_mode="Manual Results",
        )
        _click_launch(page)

        # Wizard resets to Step 1 on success
        _assert_step(page, 1)

        # Main area must show the live tracking panel (not the empty state)
        expect(
            _main(page).get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # Double-check: empty-state message is gone
        expect(
            _main(page).get_by_text(
                "No active test tournaments to track", exact=False
            )
        ).not_to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_auto_immediate_mode_tournament_appears_in_monitor(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Auto-Immediate Simulation mode: tournament auto-starts in the
        background; card must still appear in monitor main area.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_sim(
            page,
            scenario="Smoke Test",
            simulation_mode="Auto-Simulation",
        )
        _click_launch(page)

        _assert_step(page, 1)

        expect(
            _main(page).get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        expect(
            _main(page).get_by_text(
                "No active test tournaments to track", exact=False
            )
        ).not_to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_accelerated_mode_leaderboard_visible_in_monitor(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Accelerated Simulation: the run-scenario endpoint completes the
        entire tournament before returning. After wizard rerun, the monitor
        must show the completed tournament's Leaderboard heading.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_sim(
            page,
            scenario="Smoke Test",
            simulation_mode="Accelerated Simulation",
        )
        _click_launch(page)

        _assert_step(page, 1)

        # Accelerated mode completes synchronously → tournament is
        # REWARDS_DISTRIBUTED by the time the monitor renders.
        expect(
            _main(page).get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        expect(
            _main(page).get_by_text("Leaderboard", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)


# ══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE: Reward template full lifecycle via browser
# ══════════════════════════════════════════════════════════════════════════════

class TestRewardLifecycleBrowser:
    """
    Full end-to-end reward lifecycle driven entirely through the wizard UI.

    Flow: Step 1 scenario → Step 7 Championship template selection →
          Step 8 review shows correct XP → LAUNCH → monitor renders leaderboard.

    Two-stage verification:
      1. Pre-launch (sidebar): wizard review panel shows "1000 XP" for Championship
         — proves the template was actually selected and the wizard captured it.
      2. Post-launch (main area): leaderboard heading + 🥇 medal visible
         — proves the tournament completed (REWARDS_DISTRIBUTED) and
           the monitor correctly renders player rankings.

    Championship template: 1st place = 1000 XP, 400 credits.
    """

    def test_championship_lifecycle_leaderboard_renders(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Stage 1 (pre-launch): Step 8 wizard review in sidebar shows 1000 XP.
        Stage 2 (post-launch): leaderboard heading + 1st-place medal in main area.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_sim(
            page,
            scenario="Smoke Test",
            simulation_mode="Accelerated Simulation",
            reward_template="Championship",
        )

        # ── Stage 1: pre-launch sidebar check ────────────────────────────────
        # The Step 8 review panel renders:
        #   "**Rewards:** 🥇 1000 XP / 400 cr  *(and lower tiers)*"
        # This confirms Championship template was accepted by the wizard.
        expect(
            _sb(page).get_by_text("1000", exact=False).first
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

        # ── Launch ────────────────────────────────────────────────────────────
        _click_launch(page)
        _assert_step(page, 1)   # wizard reset confirms successful launch

        # ── Stage 2: post-launch main area check ──────────────────────────────
        # Leaderboard heading proves tournament reached REWARDS_DISTRIBUTED
        expect(
            _main(page).get_by_text("Leaderboard", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 🥇 medal proves at least one player ranking is rendered in the DOM
        expect(
            _main(page).get_by_text("🥇", exact=False).first
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # No Python traceback allowed
        main_text = _main(page).inner_text(timeout=_LOAD_TIMEOUT)
        assert "Traceback" not in main_text
        assert "AttributeError" not in main_text


# ══════════════════════════════════════════════════════════════════════════════
# GATE-L: Safety gate League 128+ via wizard UI
# ══════════════════════════════════════════════════════════════════════════════

class TestSafetyGateLeague128p:
    """
    Safety gate for League format with 128 players.

    Scenario: scale_test (default_player_count=128, min=64, max=1024).
    The player count slider defaults to 128 — safety threshold exactly met.
    At Step 8, the LAUNCH button must be disabled until "LAUNCH" is typed.

    NOTE on GK 128p safety gate:
        Group+Knockout valid player counts are: 8, 12, 16, 24, 32, 48, 64.
        Maximum is 64, which is below the 128-player safety threshold.
        Triggering the safety gate for GK is architecturally impossible —
        this is by design, not a test coverage gap.
    """

    def test_league_128p_safety_field_visible_and_launch_gated(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        scale_test + League + 128p (default) → Step 8 shows safety
        confirmation field; LAUNCH button disabled without correct text.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_sim(
            page,
            scenario="Scale Test",
            tournament_type="League",
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)

        # Safety confirmation input must be visible
        confirm = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(confirm).to_be_visible(timeout=_LOAD_TIMEOUT)

        # LAUNCH button must be disabled before confirmation
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Wrong text keeps button disabled
        confirm.fill("launch tournament")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_SETTLE)
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Correct text enables button
        confirm.fill("LAUNCH")
        confirm.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_SETTLE)
        expect(launch_btn).to_be_enabled(timeout=_LOAD_TIMEOUT)


# ══════════════════════════════════════════════════════════════════════════════
# PCOUNT: Player count boundary classes via slider UI
# ══════════════════════════════════════════════════════════════════════════════

class TestPlayerCountSliderUI:
    """
    Verifies wizard Step 5 (Player Count) handles boundary equivalence
    classes via actual slider interaction (keyboard navigation).

    Slider characteristics: step=2, range depends on scenario.
      large_field_monitor: min=4, max=1024, default=8
      scale_test:          min=64, max=1024, default=128

    Coverage:
      32p   — below safety threshold, no large-scale warning
      64p   — below threshold, scale_test minimum
      256p  — above threshold, large-scale warning expected
      1024p — maximum, large-scale warning expected

    Note: 4p / 8p / 16p / 128p are already covered in P1/P2 suites.
    """

    def test_wizard_32p_accepted_no_large_scale_warning(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        large_field_monitor + Knockout + 32p:
        Step 5 shows no large-scale warning; Step 6 reachable.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step5_with_count(
            page,
            scenario="Large Field Monitor",
            tournament_type="Knockout",
            player_count=32,
        )
        sb = _sb(page)
        # No large-scale warning at 32p
        expect(
            sb.get_by_text("LARGE SCALE OPERATION", exact=False)
        ).not_to_be_visible(timeout=_LOAD_TIMEOUT)

        # Can proceed to Step 6
        _click_next(page)
        _assert_step(page, 6)

    def test_wizard_64p_accepted_no_large_scale_warning(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        scale_test + Knockout + 64p (Home key → minimum):
        Step 5 shows no large-scale warning; Step 6 reachable.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step5_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=64,
        )
        sb = _sb(page)
        # No large-scale warning at 64p
        expect(
            sb.get_by_text("LARGE SCALE OPERATION", exact=False)
        ).not_to_be_visible(timeout=_LOAD_TIMEOUT)

        # Can proceed to Step 6
        _click_next(page)
        _assert_step(page, 6)

    def test_wizard_256p_shows_large_scale_warning(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        scale_test + Knockout + 256p:
        Step 5 shows large-scale warning (256 >= 128 threshold).
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step5_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=256,
        )
        sb = _sb(page)
        # Large-scale warning must be visible at 256p
        expect(
            sb.get_by_text("LARGE SCALE OPERATION", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Can still proceed to Step 6
        _click_next(page)
        _assert_step(page, 6)

    def test_wizard_1024p_shows_large_scale_warning(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        scale_test + Knockout + 1024p (End key → maximum):
        Step 5 shows large-scale warning at maximum player count.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step5_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=1024,
        )
        sb = _sb(page)
        # Large-scale warning must be visible at 1024p
        expect(
            sb.get_by_text("LARGE SCALE OPERATION", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Can still proceed to Step 6
        _click_next(page)
        _assert_step(page, 6)
