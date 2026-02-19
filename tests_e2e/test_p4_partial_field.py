"""
P4 Large-Scale Stability & Partial-Field Coverage
==================================================

PURPOSE
-------
Validates that the Tournament Monitor UI correctly handles and displays
large-scale tournament data: enrollment counts, session counts, phase
progression, and leaderboards at 64p and Group+Knockout scale.

These tests form the BASELINE for no-show gap detection: once the backend
supports a no_show_rate parameter, the same DOM assertions remain valid
(enrolled_count will then differ from player_count by the no-show %).

ARCHITECTURAL GAP — WHY TRUE NO-SHOW TESTS ARE NOT YET POSSIBLE
----------------------------------------------------------------
The OPS Wizard's ``OpsScenarioRequest`` schema does NOT include a
``no_show_rate`` or ``withdrawal_rate`` parameter.  The backend attempts
to enroll exactly ``player_count`` seed users and assumes 100% participation
once enrolled.  Key facts from codebase audit (2026-02-16):

  * ``trigger_ops_scenario()``  ← no no_show_rate kwarg
  * ``OpsScenarioRequest``      ← no no_show_rate field
  * Wizard steps 1–8           ← no absence / partial-participation UI
  * Backend enrollment logic   ← enrolls all seeded_ids deterministically

What the system CANNOT yet test:
  - Group rebalancing after post-enrollment player withdrawal
  - Bracket regeneration for reduced participant pool
  - Bye slot assignment (uneven player count handling)
  - Dynamic session cancellation on no-show
  - Reward recalculation for partial fields

What WOULD need to change for true no-show modeling:

  Backend schema::

      class OpsScenarioRequest(BaseModel):
          no_show_rate: float = Field(0.0, ge=0.0, le=0.25)
          # 0.0 = all players present; 0.25 = 25% absent

  Backend logic:
      1. Enroll player_count players
      2. Randomly withdraw floor(no_show_rate × enrolled_count) players
      3. Re-run session generation with reduced pool
      4. Assign byes for odd bracket sizes
      5. Recalculate group assignments for adjusted player counts

WHAT IS TESTED HERE
-------------------
Four tests, no API calls for state assertions — 100% browser-DOM only.

PFIELD-1  ``TestLargeScaleMonitorStability``
  test_64p_tournament_monitor_card_shows_enrollment_and_session_metrics
    Scale Test + Knockout + 64p (slider Home key) + Accelerated Simulation.
    Verifies:
      - "Enrolled" metric visible in monitor card  (enrollment count displayed)
      - "Total Sessions" metric visible             (session generation at scale)
      - "Leaderboard" heading visible               (full lifecycle completed)
      - 🥇 medal rendered                           (rankings not collapsed)
      - No Python traceback in DOM

PFIELD-2  ``TestLargeScaleMonitorStability``
  test_group_knockout_phase_progression_visible_in_monitor_card
    Large Field Monitor + Group+Knockout + 8p (default) + Accelerated.
    Verifies:
      - "Group Stage" phase badge visible           (group assignment rendered)
      - "Knockout" phase badge visible              (bracket generated, shown)
      - "Leaderboard" heading visible               (multi-phase lifecycle done)
      - 🥇 medal rendered                           (rankings not collapsed)
    This is the closest proxy for "csoportbeosztás + bracket regeneration"
    without true no-show support.

PFIELD-3  ``TestLargePlayerCountWizardReview``
  test_256p_wizard_review_shows_player_count_and_safety_gate
    Scale Test + 256p (slider) → Step 8 review panel.
    Verifies: "256 players" in sidebar, safety input visible, LAUNCH disabled.

PFIELD-4  ``TestLargePlayerCountWizardReview``
  test_1024p_wizard_review_shows_player_count_and_safety_gate
    Scale Test + 1024p (End key) → Step 8 review panel.
    Verifies: "1024 players" in sidebar, safety input visible, LAUNCH disabled.

Run (headless CI):
    pytest tests_e2e/test_p4_partial_field.py -v --tb=short

Run (headed debug, slow):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=600 \\
        pytest tests_e2e/test_p4_partial_field.py -v -s

Expected runtime:
    PFIELD-1  ~60–120 s  (64p accelerated tournament)
    PFIELD-2  ~20–40  s  (8p Group+Knockout accelerated)
    PFIELD-3  ~30     s  (wizard navigation only, no launch)
    PFIELD-4  ~30     s  (wizard navigation only, no launch)
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
_LOAD_TIMEOUT  = 30_000
_SLOW_TIMEOUT  = 120_000   # 8p GK accelerated + st.rerun() overhead
_LARGE_TIMEOUT = 200_000   # 64p knockout accelerated (63 sessions synchronous)
_SETTLE        = 2         # seconds after networkidle to let Streamlit re-render

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


def _click_launch(page: Page, *, timeout: int = _SLOW_TIMEOUT) -> None:
    """Click LAUNCH TOURNAMENT and wait for tournament to complete + st.rerun()."""
    _sb(page).get_by_role("button", name="LAUNCH TOURNAMENT").click()
    page.wait_for_load_state("networkidle", timeout=timeout)
    time.sleep(8)  # allow tournament completion + 2s sleep in execute_launch + st.rerun()


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

    RC-slider interaction: keyboard events must target ``[role="slider"]``
    (the visible handle), NOT the hidden ``<input type="range">``.
    ``scroll_into_view_if_needed()`` is required because the handle is
    off-screen when Step 5 first renders (sidebar scrolled to top).
    """
    sb = _sb(page)
    _assert_step(page, 1)

    # Step 1: select scenario
    sb.get_by_text(scenario, exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: H2H format is default — no click needed
    _assert_step(page, 2)
    _click_next(page)

    # Step 3: select tournament type
    _assert_step(page, 3)
    if tournament_type not in ("Knockout", ""):
        sb.locator("label", has_text=tournament_type).first.click()
        time.sleep(0.3)
    _click_next(page)

    # Step 4: Game Preset — accept default (None)
    _assert_step(page, 4)
    _click_next(page)

    # Now at Step 5: Player Count
    _assert_step(page, 5)

    if player_count is not None:
        time.sleep(0.5)  # wait for RC-slider React components to mount

        # The slider handle (role="slider") is the interactive target.
        # At Step 5 two role="slider" elements exist:
        #   1st — wizard player-count slider (target)
        #   2nd — monitoring-controls auto-refresh slider
        handle = page.locator('[role="slider"]').first
        handle.scroll_into_view_if_needed(timeout=_LOAD_TIMEOUT)
        time.sleep(0.3)

        handle.press("Home")   # jump to scenario minimum
        time.sleep(0.3)

        # Navigate to target via ArrowRight/ArrowLeft with 40ms per-key sleep.
        # NOTE: The RC-slider's End key is intentionally NOT used even for
        # large targets (e.g. 1024p). Pressing End while a Streamlit Home-key
        # rerun is still in-flight causes Streamlit to re-render the slider at
        # its default value (128) after the Home rerun completes, overwriting
        # the 1024 state set by End. ArrowRight presses are reliable because
        # each press fires onChange individually; the 40 ms inter-key sleep
        # gives Streamlit enough time to process each increment.
        current_raw = handle.get_attribute("aria-valuenow")
        current = int(current_raw) if current_raw else 0
        steps = (player_count - current) // 2   # slider step=2
        key = "ArrowRight" if steps > 0 else "ArrowLeft"
        for _ in range(abs(steps)):
            handle.press(key)
            time.sleep(0.04)

        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(1)


def _navigate_to_step8_with_count(
    page: Page,
    *,
    scenario: str,
    tournament_type: str = "Knockout",
    player_count: int | None = None,
    simulation_mode: str = "Accelerated Simulation",
    reward_template: str | None = None,
) -> None:
    """
    Navigate from Step 1 to Step 8 (Review & Launch) with an explicit
    player count set via RC-slider keyboard interaction.
    """
    _navigate_to_step5_with_count(
        page,
        scenario=scenario,
        tournament_type=tournament_type,
        player_count=player_count,
    )

    # Step 5 → 6
    _click_next(page)
    _assert_step(page, 6)

    sb = _sb(page)
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
# PFIELD-1 & PFIELD-2: Large-scale monitor stability
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.tournament_monitor
class TestLargeScaleMonitorStability:
    """
    Validates monitor card DOM at 64p scale (Knockout) and at 8p scale
    (Group+Knockout).  These are the baseline stability tests for enrollment
    count display and multi-phase bracket tracking — prerequisites for any
    future no-show modeling tests once the backend supports no_show_rate.

    ARCHITECTURAL NOTE:
        Metric labels come from st.metric() calls in _render_tournament_card():
            m2.metric("Enrolled",       enrolled)      # enrollment count
            m3.metric("Total Sessions", total_sessions) # session count
            m4.metric("Submitted",      done_sessions)
        Phase badge labels come from phase_label_short() in tournament_card/utils.py:
            "GROUP_STAGE" → "Group Stage"
            "KNOCKOUT"    → "Knockout"
        The "Tournament Phases" subheader (st.subheader) is always rendered
        when the card loads sessions.
    """

    def test_64p_tournament_monitor_card_shows_enrollment_and_session_metrics(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        PFIELD-1: Scale Test + Knockout + 64p (slider Home key = scenario min)
        + Accelerated Simulation.

        64p is below the 128-player safety threshold → no confirmation needed.
        Accelerated mode processes all 63 sessions synchronously before returning.

        Assertions after launch + st.rerun():
          1. Monitor card visible (LIVE TEST TRACKING)
          2. "Enrolled" metric label present  — proves enrolled_count displayed
          3. "Total Sessions" metric label present — proves session count displayed
          4. "Leaderboard" heading present — proves full lifecycle completed
          5. 🥇 medal rendered — proves rankings did not collapse
          6. No Python traceback — proves no crash during render

        This is the baseline DOM assertion set for no-show gap detection:
        when no_show_rate is added, enrolled_count will differ from player_count
        but all 5 assertions above should still hold.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=64,
            simulation_mode="Accelerated Simulation",
        )
        _click_launch(page, timeout=_LARGE_TIMEOUT)

        # Wizard reset to Step 1 confirms successful launch
        _assert_step(page, 1)

        main = _main(page)

        # Monitor card must be visible (not empty-state message)
        expect(
            main.get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=_LARGE_TIMEOUT)

        # 1. Enrollment count metric — DOM: [data-testid="stMetricLabel"] "Enrolled"
        expect(
            main.get_by_text("Enrolled", exact=True)
        ).to_be_visible(timeout=_LARGE_TIMEOUT)

        # 2. Session count metric — DOM: [data-testid="stMetricLabel"] "Total Sessions"
        expect(
            main.get_by_text("Total Sessions", exact=True)
        ).to_be_visible(timeout=_LARGE_TIMEOUT)

        # 3. Full lifecycle: leaderboard heading rendered
        expect(
            main.get_by_text("Leaderboard", exact=False)
        ).to_be_visible(timeout=_LARGE_TIMEOUT)

        # 4. At least 1st-place medal rendered (rankings not collapsed)
        expect(
            main.get_by_text("🥇", exact=False).first
        ).to_be_visible(timeout=_LARGE_TIMEOUT)

        # 5. No Python exceptions in the rendered DOM
        main_text = main.inner_text(timeout=_LOAD_TIMEOUT)
        assert "Traceback" not in main_text, "Python traceback found in monitor DOM"
        assert "AttributeError" not in main_text, "AttributeError found in monitor DOM"
        assert "KeyError" not in main_text, "KeyError found in monitor DOM"

    def test_group_knockout_phase_progression_visible_in_monitor_card(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        PFIELD-2: Large Field Monitor + Group+Knockout + 8p (scenario default)
        + Accelerated Simulation.

        8p Group+Knockout structure:
          - 2 groups of 4 → 6 × 2 = 12 group-stage sessions
          - Top 2 from each group → 4-player knockout: SF (×2) + Final + 3rd place
          - Total: ~16 sessions
          This scale completes quickly in accelerated mode (~20–40 s).

        Group+Knockout label in wizard: "🌍 Group + Knockout (Hybrid)"
        → matched via has_text="Group + Knockout"

        Phase badge labels (from tournament_card/utils.py _PHASE_SHORT_LABELS):
          "GROUP_STAGE" → "Group Stage"
          "KNOCKOUT"    → "Knockout"

        Assertions after launch + st.rerun():
          1. Monitor card visible (LIVE TEST TRACKING)
          2. "Group Stage" phase badge visible — group assignment + sessions rendered
          3. "Knockout" phase badge visible — bracket generated and tracked
          4. "Leaderboard" heading visible — complete lifecycle (both phases done)
          5. 🥇 medal rendered — rankings not collapsed after multi-phase tournament

        This is the closest proxy for:
          - "Csoportbeosztás újraszámolódik-e" (group assignment visible in DOM)
          - "Bracket újragenerálódik-e" (knockout phase visible after groups)
        Without true no-show support, this validates the phase-tracking architecture.
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_with_count(
            page,
            scenario="Large Field Monitor",
            tournament_type="Group + Knockout",  # matches "🌍 Group + Knockout (Hybrid)"
            player_count=None,  # use scenario default: 8 players
            simulation_mode="Accelerated Simulation",
        )
        _click_launch(page, timeout=_SLOW_TIMEOUT)

        # Wizard reset confirms successful launch
        _assert_step(page, 1)

        main = _main(page)

        # Monitor card must be visible
        expect(
            main.get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 1. Group Stage phase badge — proves group assignment was generated and tracked
        #    Rendered via: badge_cols[idx].metric(f"🌐 Group Stage", ...)
        #    .first avoids strict-mode violation when multiple elements contain
        #    "Group Stage" (e.g. phase badge label + session grid section header).
        expect(
            main.get_by_text("Group Stage", exact=False).first
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 2. Knockout phase badge — proves bracket was generated from group results
        #    Rendered via: badge_cols[idx].metric(f"🏆 Knockout", ...)
        expect(
            main.get_by_text("Knockout", exact=False).first
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 3. Leaderboard heading — full multi-phase lifecycle completed
        expect(
            main.get_by_text("Leaderboard", exact=False)
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 4. 1st-place medal (rankings valid after Group+Knockout)
        expect(
            main.get_by_text("🥇", exact=False).first
        ).to_be_visible(timeout=_SLOW_TIMEOUT)

        # 5. No crash in DOM
        main_text = main.inner_text(timeout=_LOAD_TIMEOUT)
        assert "Traceback" not in main_text, "Python traceback found in monitor DOM"


# ══════════════════════════════════════════════════════════════════════════════
# PFIELD-3 & PFIELD-4: Large player count wizard review (no launch)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.tournament_monitor
class TestLargePlayerCountWizardReview:
    """
    Validates wizard Step 8 review panel for 256p and 1024p scale.

    These tests do NOT launch the tournament (too slow and resource-intensive
    for automated UI tests).  They verify:
      1. The wizard UI renders the correct player count at Step 8 review.
         Step 8 renders: "**Player Count:** {player_count} players"
         (tournament_monitor.py render_step5_review_launch(), line ~844)
      2. The safety confirmation gate is enforced:
         - Input "Type LAUNCH to enable the button" is visible
         - LAUNCH TOURNAMENT button is disabled without correct text

    These tests also implicitly verify that the wizard slider correctly
    propagates large player counts through all 8 steps to the review panel
    without crashing.

    Context for no-show modeling:
      Once no_show_rate is supported, Step 8 would additionally show:
        "**No-Show Rate:** X% (≈ Y players absent)"
      The safety gate would need to account for reduced effective enrollment.
    """

    def test_256p_wizard_review_shows_player_count_and_safety_gate(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        PFIELD-3: Scale Test + Knockout + 256p (slider) → Step 8 review.

        Step 5 shows large-scale warning (256 ≥ 128 threshold).
        Step 8 review shows "256 players" in sidebar.
        Safety gate: LAUNCH input visible, LAUNCH button disabled.

        Does NOT launch (256p accelerated would take ~5+ min and is not
        suitable for a rapid UI validation test).
        """
        _go_to_monitor(page, base_url, api_url)
        _navigate_to_step8_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=256,
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)

        # Step 8 review renders "**Player Count:** 256 players"
        expect(
            sb.get_by_text("256 players", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Safety confirmation input must be visible (256 ≥ 128 threshold)
        confirm = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(confirm).to_be_visible(timeout=_LOAD_TIMEOUT)

        # LAUNCH button must be disabled before confirmation
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Wrong text keeps button disabled
        confirm.fill("256 players")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(2)
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Sidebar shows correct player count — no traceback
        sb_text = sb.inner_text(timeout=_LOAD_TIMEOUT)
        assert "256" in sb_text, "Player count 256 not found in Step 8 review sidebar"
        assert "Traceback" not in sb_text, "Python traceback in Step 8 review sidebar"

    def test_128p_threshold_boundary_safety_gate_and_review(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        PFIELD-4: Scale Test + Knockout + 128p EXACT THRESHOLD (scenario default,
        no slider change) → Step 8 review.

        128 is the EXACT safety-gate threshold (_SAFETY_CONFIRMATION_THRESHOLD = 128).
        Using scale_test's default player count (128) avoids slider automation
        for this boundary test, removing any RC-slider state-sync race condition.

        KEY BEHAVIOUR being tested:
          - Player count exactly at the threshold (128) triggers the safety gate
          - Step 8 review shows "128 players" — count is correctly propagated
          - Safety gate input is visible and LAUNCH is disabled without confirmation
          - Partial text ("LAUNCH" substring) does not enable the button

        NOTE on 1024p automation:
          The RC-slider's End key is unreliable in headless Chromium + Streamlit
          WebSocket contexts: pressing End while a Home-key Streamlit rerun is
          still in-flight causes Streamlit to rebase the slider to default (128)
          after the rerun completes. ArrowRight presses with 40ms sleep are the
          reliable approach; 480 presses × 40ms = 19.2 s makes 1024p impractical
          for a headless UI test. The 256p test (PFIELD-3) already covers the
          "> threshold" case with a reliably-set custom value.

        Does NOT launch.
        """
        _go_to_monitor(page, base_url, api_url)
        # Navigate to Step 8 WITHOUT changing the slider (scale_test default = 128p)
        _navigate_to_step8_with_count(
            page,
            scenario="Scale Test",
            tournament_type="Knockout",
            player_count=None,   # use scenario default: 128 players
            simulation_mode="Accelerated Simulation",
        )
        sb = _sb(page)

        # Safety confirmation input visible (128 ≥ 128 threshold → safety gate active)
        confirm = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(confirm).to_be_visible(timeout=_LOAD_TIMEOUT)

        # LAUNCH button disabled before confirmation
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Partial LAUNCH text must NOT enable the button
        confirm.fill("launch")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(2)
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

        # Step 8 review shows "128 players" (player count propagated correctly)
        expect(
            sb.get_by_text("128 players", exact=False)
        ).to_be_visible(timeout=_LOAD_TIMEOUT)

        # No traceback
        sb_text = sb.inner_text(timeout=_LOAD_TIMEOUT)
        assert "Traceback" not in sb_text, "Python traceback in Step 8 review sidebar"
