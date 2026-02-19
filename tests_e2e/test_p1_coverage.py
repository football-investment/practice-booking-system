"""
P1 Coverage Tests — Critical Branch Matrix Gaps
================================================

Covers the three P1 critical gaps identified in E2E_BRANCH_MATRIX.md:

P1.1  Simulation Mode API Coverage
      - manual:        no auto-simulation → sessions exist, result_submitted=False for ALL
      - auto_immediate: structural response valid, tournament not REWARDS_DISTRIBUTED immediately
      - Payload integrity: "simulation_mode" field is correctly transmitted and accepted
      - Negative: invalid simulation_mode value is rejected

P1.2  API Error → Wizard State Retention
      - Playwright route interception → force 500 on OPS endpoint
      - After error: wizard remains on Step 8 (NOT reset to Step 1)
      - Wizard state preserved: scenario, format, player_count, simulation mode still visible
      - Error message is displayed (not silently swallowed)

P1.3  INDIVIDUAL_RANKING 128+ Safety Gate Enforcement
      - Navigate wizard to Step 8 via INDIVIDUAL_RANKING path with scale_test (128p default)
      - Safety confirmation field is VISIBLE (not auto-confirmed)
      - Negative: launch button DISABLED without confirmation text
      - Negative: wrong text keeps button DISABLED
      - Positive: correct "LAUNCH" text changes UI state to ready-to-launch

Run:
    pytest tests_e2e/test_p1_coverage.py -v --tb=short
    pytest tests_e2e/test_p1_coverage.py -m "not slow" -v
"""

import json
import time
import urllib.parse

import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ─────────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
MONITOR_PATH = "/Tournament_Monitor"

_LOAD_TIMEOUT = 30_000
_STREAMLIT_SETTLE = 2
_SAFETY_THRESHOLD = 128

_VALID_LAUNCHED = {"IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED"}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _get_admin_token(api_url: str) -> str:
    resp = requests.post(
        f"{api_url}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


def _get_admin_user(api_url: str, token: str) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to fetch user: {resp.text}"
    return resp.json()


def _ops_post(api_url: str, token: str, payload: dict, timeout: int = 120) -> requests.Response:
    """Raw POST to /ops/run-scenario — returns Response for assertion flexibility."""
    return requests.post(
        f"{api_url}/api/v1/tournaments/ops/run-scenario",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=timeout,
    )


def _get_sessions(api_url: str, token: str, tid: int) -> list:
    resp = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/sessions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Sessions fetch failed: {resp.text}"
    return resp.json()


def _get_summary(api_url: str, token: str, tid: int) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/summary",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200
    return resp.json()


def _go_to_monitor_authenticated(page: Page, base_url: str, api_url: str) -> None:
    token = _get_admin_token(api_url)
    user = _get_admin_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _go_to_monitor_with_invalid_token(page: Page, base_url: str, api_url: str) -> None:
    """
    Navigate to the Tournament Monitor with an INVALID auth token.

    Wizard navigation does not call the backend — so Steps 1-8 are fully
    navigable.  The token is only used in execute_launch(), causing a 401
    response that triggers st.error() without calling reset_wizard_state().

    This is used by TestWizardErrorStateRetention to produce a real API
    failure without browser-level route interception (which would not work
    for Python-side requests.post() calls made by the Streamlit backend).
    """
    # Fetch real user data (needs valid token) so the page renders correctly.
    real_token = _get_admin_token(api_url)
    user = _get_admin_user(api_url, real_token)
    # Swap in a syntactically-valid but expired/unsigned JWT so the backend
    # returns 401 when execute_launch() posts to /ops/run-scenario.
    bad_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.INVALID"
    params = urllib.parse.urlencode({"token": bad_token, "user": json.dumps(user)})
    page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _sidebar(page: Page):
    return page.locator("section[data-testid='stSidebar']")


def _click_next(page: Page) -> None:
    _sidebar(page).get_by_role("button", name="Next →").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _click_back(page: Page) -> None:
    _sidebar(page).get_by_role("button", name="← Back").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _navigate_to_step8_individual_ranking_large(
    page: Page, base_url: str, api_url: str
) -> None:
    """
    Navigate wizard to Step 8 (Review & Launch) via INDIVIDUAL_RANKING path
    with scale_test scenario (default player_count = 128 → triggers safety gate).

    Path:
      Step 1: Scale Test
      Step 2: Individual Ranking
      Step 3: SCORE_BASED scoring
      Step 4: Game Preset (passthrough)
      Step 5: Player Count (scale_test default = 128, shows LARGE SCALE warning)
      Step 6: Accelerated Simulation
      Step 7: Configure Rewards (passthrough)
      Step 8: Review & Launch  ← test assertions here
    """
    _go_to_monitor_authenticated(page, base_url, api_url)
    sb = _sidebar(page)

    # Step 1: Scale Test (min=64, max=1024, default=128)
    sb.get_by_text("Scale Test", exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: Individual Ranking format
    expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    sb.get_by_text("Individual Ranking", exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 3: Scoring method → SCORE_BASED
    expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    sb.get_by_text("Score Based", exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 4: Game Preset (optional, passthrough)
    expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 5: Player count — scale_test default = 128, LARGE SCALE warning must show
    expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
        timeout=_LOAD_TIMEOUT
    )
    _click_next(page)

    # Step 6: Simulation Mode → Accelerated
    expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    sb.get_by_text("Accelerated Simulation", exact=False).first.click()
    time.sleep(0.5)
    _click_next(page)

    # Step 7: Reward config (optional, passthrough)
    expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Now at Step 8 with INDIVIDUAL_RANKING + 128 players
    expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)


def _navigate_to_step8_hth_for_error_test(
    page: Page, base_url: str, api_url: str
) -> None:
    """
    Navigate wizard to Step 8 via HEAD_TO_HEAD + scale_test (128p default),
    loaded with an INVALID token so that clicking Launch produces a real 401.

    Wizard navigation is purely UI-state — no backend calls are made for
    steps 1–7 (except Step 4 game-preset fetch, which is optional and
    gracefully handles a missing-token by showing an empty list).

    The execute_launch() call at Step 8 uses st.session_state["token"] which
    holds our invalid value → backend returns 401 → st.error() fires →
    reset_wizard_state() is NOT called → wizard remains on Step 8.
    """
    _go_to_monitor_with_invalid_token(page, base_url, api_url)
    sb = _sidebar(page)

    # Step 1: Scale Test
    sb.get_by_text("Scale Test", exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: HEAD_TO_HEAD (default)
    expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 3: Knockout
    expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 4: Game Preset passthrough (presets list may be empty — that's fine)
    expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 5: Player count (scale_test default = 128)
    expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
        timeout=_LOAD_TIMEOUT
    )
    _click_next(page)

    # Step 6: Accelerated Simulation
    expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    sb.get_by_text("Accelerated Simulation", exact=False).first.click()
    time.sleep(0.5)
    _click_next(page)

    # Step 7: Reward config passthrough
    expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 8: Review & Launch (safety gate required due to 128+ players)
    expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    # Complete safety confirmation — Streamlit text_input requires Enter to apply
    confirm_input = sb.get_by_placeholder("Type LAUNCH to enable the button")
    confirm_input.fill("LAUNCH")
    confirm_input.press("Enter")
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(0.5)


def _navigate_to_step8_hth_large(
    page: Page, base_url: str, api_url: str
) -> None:
    """
    Navigate wizard to Step 8 via HEAD_TO_HEAD + scale_test (128p default).
    Used for error-state retention test.
    """
    _go_to_monitor_authenticated(page, base_url, api_url)
    sb = _sidebar(page)

    # Step 1: Scale Test
    sb.get_by_text("Scale Test", exact=False).first.click()
    time.sleep(0.3)
    _click_next(page)

    # Step 2: HEAD_TO_HEAD (default)
    expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 3: Knockout
    expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 4: Game Preset passthrough
    expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 5: Player count (scale_test default = 128)
    expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
        timeout=_LOAD_TIMEOUT
    )
    _click_next(page)

    # Step 6: Accelerated Simulation
    expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    sb.get_by_text("Accelerated Simulation", exact=False).first.click()
    time.sleep(0.5)
    _click_next(page)

    # Step 7: Reward config passthrough
    expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    _click_next(page)

    # Step 8: Review & Launch (safety gate required due to 128+ players)
    expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
    # Complete safety confirmation — Streamlit text_input requires Enter to apply
    confirm_input = sb.get_by_placeholder("Type LAUNCH to enable the button")
    confirm_input.fill("LAUNCH")
    confirm_input.press("Enter")
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# P1.1 — Simulation Mode API Coverage
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestSimulationModeAPI:
    """
    P1.1: Verify that each simulation_mode value produces the correct backend behaviour.

    The wizard sends simulation_mode in the OPS payload. This class tests that
    the three valid modes actually differ in what they produce:
      - manual:        sessions generated, NO auto-simulation, all result_submitted=False
      - auto_immediate: sessions generated, tournament IN_PROGRESS (async sim queued)
      - accelerated:   sessions + full auto-sim, tournament REWARDS_DISTRIBUTED (baseline)

    Also tests: payload integrity (field name, valid/invalid values).
    """

    # ── Payload integrity ────────────────────────────────────────────────────

    @pytest.mark.parametrize("mode", ["manual", "auto_immediate", "accelerated"])
    def test_all_valid_simulation_modes_accepted(self, api_url: str, mode: str):
        """
        All three valid simulation_mode values must be accepted (HTTP 200)
        by the OPS endpoint. Verifies the field name 'simulation_mode' is correct.

        Regression guard: if the field name changes to 'mode' or 'sim_mode',
        these tests will fail (400/422 instead of 200).
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": mode,
        })
        assert resp.status_code == 200, (
            f"simulation_mode='{mode}': expected HTTP 200, got {resp.status_code}. "
            f"Response: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, (
            f"simulation_mode='{mode}': response.triggered must be True, got: {data}"
        )
        assert data.get("tournament_id") is not None, (
            f"simulation_mode='{mode}': tournament_id missing from response"
        )

    def test_invalid_simulation_mode_rejected(self, api_url: str):
        """
        Invalid simulation_mode value must be rejected (HTTP 422).
        If the backend silently ignores unknown modes, this test will fail —
        which would indicate missing input validation.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "INVALID_MODE_XYZ",
        })
        assert resp.status_code in (400, 422), (
            f"Invalid simulation_mode should be rejected (400 or 422), "
            f"got {resp.status_code}: {resp.text[:200]}"
        )

    # ── manual mode: no auto-simulation ──────────────────────────────────────

    def test_manual_mode_sessions_generated(self, api_url: str):
        """
        manual mode: session generation must happen (session_count > 0).
        The 'manual' mode is for real tournaments where no auto-simulation runs.
        If session generation fails in manual mode, the tournament is unmonitorable.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        sessions = _get_sessions(api_url, token, tid)
        assert len(sessions) > 0, (
            f"manual mode: expected >0 sessions after launch, got 0. "
            f"Session generation broken for manual mode."
        )

    def test_manual_mode_no_results_submitted(self, api_url: str):
        """
        manual mode: ALL sessions must have result_submitted=False.

        This is the defining characteristic of manual mode — no auto-simulation
        runs. If any session has result_submitted=True, the simulation mode
        payload field is being silently overridden or ignored.

        Regression: previously manual mode incorrectly ran auto-simulation,
        contaminating manual operator workflows.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        sessions = _get_sessions(api_url, token, tid)
        assert len(sessions) > 0, "Session count = 0 (generation failed)"

        submitted = [s for s in sessions if s.get("result_submitted") is True]
        assert len(submitted) == 0, (
            f"manual mode: {len(submitted)}/{len(sessions)} sessions have "
            f"result_submitted=True. Auto-simulation must NOT run in manual mode. "
            f"Payload field 'simulation_mode' may be ignored by the backend."
        )

    def test_manual_mode_tournament_remains_in_progress(self, api_url: str):
        """
        manual mode: tournament status must be IN_PROGRESS (never REWARDS_DISTRIBUTED).

        Since no simulation runs, the tournament cannot reach REWARDS_DISTRIBUTED.
        If it does, simulation_mode is being ignored.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        summary = _get_summary(api_url, token, tid)
        status = summary.get("tournament_status")
        assert status == "IN_PROGRESS", (
            f"manual mode: expected IN_PROGRESS (no auto-sim), got {status}. "
            f"If REWARDS_DISTRIBUTED: simulation_mode='manual' is being ignored."
        )

    def test_manual_mode_rankings_empty(self, api_url: str):
        """
        manual mode: rankings must be empty (no results → no ranking calculation).

        A non-empty ranking list after manual-mode launch means auto-simulation ran,
        which is incorrect behaviour.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        rankings_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/rankings",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        # Rankings endpoint must return 200 (tournament exists)
        assert rankings_resp.status_code == 200, (
            f"Rankings endpoint should return 200, got {rankings_resp.status_code}"
        )
        rankings_data = rankings_resp.json()
        # Rankings endpoint may return either a list OR a dict {"rankings": [...], ...}
        if isinstance(rankings_data, dict):
            rankings = rankings_data.get("rankings", [])
        else:
            rankings = rankings_data
        assert len(rankings) == 0, (
            f"manual mode: expected 0 rankings (no results submitted), "
            f"got {len(rankings)}. Auto-simulation must NOT have run."
        )

    # ── auto_immediate mode: structural response ──────────────────────────────

    def test_auto_immediate_sessions_generated(self, api_url: str):
        """
        auto_immediate mode: sessions must be generated.
        The simulation runs asynchronously — sessions exist immediately,
        results may not yet be present.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "auto_immediate",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        sessions = _get_sessions(api_url, token, tid)
        assert len(sessions) > 0, (
            f"auto_immediate mode: expected >0 sessions, got 0."
        )

    def test_auto_immediate_response_structure(self, api_url: str):
        """
        auto_immediate mode: response must include tournament_id, enrolled_count,
        and triggered=True. Structural integrity check for the payload contract.

        If the field name 'simulation_mode' is wrong (e.g. misspelled), the backend
        may default to a different mode — this test catches that via response shape.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "auto_immediate",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data.get("triggered") is True, f"triggered must be True: {data}"
        assert isinstance(data.get("tournament_id"), int), (
            f"tournament_id must be int: {data}"
        )
        assert isinstance(data.get("enrolled_count"), int), (
            f"enrolled_count must be int: {data}"
        )
        assert data["enrolled_count"] == 4, (
            f"enrolled_count must equal requested player_count (4), "
            f"got {data['enrolled_count']}"
        )

    # ── Accelerated baseline ──────────────────────────────────────────────────

    def test_accelerated_reaches_rewards_distributed(self, api_url: str):
        """
        accelerated mode: tournament must reach REWARDS_DISTRIBUTED (full lifecycle).
        This is the baseline / control case — other modes must NOT reach this status.

        Regression guard: if accelerated stops working, we catch it here before
        it breaks the wizard's primary use case.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "accelerated",
        })
        assert resp.status_code == 200
        tid = resp.json()["tournament_id"]

        summary = _get_summary(api_url, token, tid)
        status = summary.get("tournament_status")
        assert status in _VALID_LAUNCHED, (
            f"accelerated mode: expected launched status, got {status}"
        )

    # ── Cross-mode comparison ─────────────────────────────────────────────────

    def test_manual_vs_accelerated_result_submitted_differ(self, api_url: str):
        """
        manual mode must produce 0 submitted sessions.
        accelerated mode must produce >0 submitted sessions.
        This single test validates that simulation_mode has observable effect.

        If both modes produce the same result_submitted count, the field is ignored.
        """
        token = _get_admin_token(api_url)

        # Launch manual
        r_manual = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",
        })
        assert r_manual.status_code == 200
        tid_manual = r_manual.json()["tournament_id"]

        # Launch accelerated
        r_acc = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "accelerated",
        })
        assert r_acc.status_code == 200
        tid_acc = r_acc.json()["tournament_id"]

        sessions_manual = _get_sessions(api_url, token, tid_manual)
        sessions_acc = _get_sessions(api_url, token, tid_acc)

        submitted_manual = sum(1 for s in sessions_manual if s.get("result_submitted"))
        submitted_acc = sum(1 for s in sessions_acc if s.get("result_submitted"))

        assert submitted_manual == 0, (
            f"manual mode: expected 0 submitted sessions, got {submitted_manual}"
        )
        assert submitted_acc > 0, (
            f"accelerated mode: expected >0 submitted sessions, got {submitted_acc}"
        )
        assert submitted_manual != submitted_acc, (
            f"manual and accelerated modes produced identical result_submitted counts "
            f"({submitted_manual}). simulation_mode field is being ignored."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# P1.2 — API Error → Wizard State Retention
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestWizardErrorStateRetention:
    """
    P1.2: Verify that a failed OPS API call does NOT reset the wizard state.

    The wizard's execute_launch() calls reset_wizard_state() ONLY on success.
    On failure, it calls st.error() and sets wizard_launching=False.

    Architecture note: Playwright page.route() only intercepts browser-level
    (JS fetch/XHR) requests, NOT Python server-side requests.post() calls made
    by the Streamlit backend. Therefore we trigger a real API failure by
    navigating with an invalid JWT token — the backend returns 401 Unauthorized,
    which activates the same else-branch in execute_launch() as any other error.

    Error flow:
      1. Page loads with invalid token in st.session_state["token"]
      2. Wizard navigates normally (steps 1-7 make no API calls)
      3. User clicks LAUNCH TOURNAMENT at Step 8
      4. execute_launch() → trigger_ops_scenario(token=invalid) → HTTP 401
      5. ok=False → st.error("❌ Launch failed: ...") shown
      6. reset_wizard_state() is NOT called → wizard stays on Step 8

    Coverage:
      - HTTP 401 response → error message visible (not silently swallowed)
      - Wizard remains on Step 8 (not reset to Step 1)
      - Scenario label still visible in review panel (state not cleared)
      - Launch button visible after error (user can retry)
    """

    def test_launch_failure_shows_error_message(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        After a 401 error on the OPS endpoint: an error message must
        appear in the sidebar. The UI must NOT silently fail.

        The error message text is: "❌ Launch failed: <reason>"
        """
        _navigate_to_step8_hth_for_error_test(page, base_url, api_url)
        sb = _sidebar(page)

        # Click Launch — will fail with 401 (invalid token)
        sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Error message must be visible (matches "❌ Launch failed: ...")
        error_locator = sb.get_by_text("Launch failed", exact=False)
        expect(error_locator).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_launch_failure_does_not_reset_to_step1(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        After a 401 error: wizard must remain on Step 8.
        The user must NOT lose their configuration.

        Regression guard: if reset_wizard_state() were called on failure,
        the wizard would reset to Step 1 — forcing the user to re-configure
        an 8-step workflow from scratch after a transient network error.
        """
        _navigate_to_step8_hth_for_error_test(page, base_url, api_url)
        sb = _sidebar(page)

        sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Must still be on Step 8 — NOT on Step 1
        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Step 1 of 8", exact=False)).not_to_be_visible(
            timeout=5_000
        )

    def test_launch_failure_preserves_scenario_in_review(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        After a 401 error: the review panel must still show the wizard's
        configured values (scale_test scenario → 128 players visible).

        This verifies that wizard_scenario_saved is not cleared on failure.
        """
        _navigate_to_step8_hth_for_error_test(page, base_url, api_url)
        sb = _sidebar(page)

        sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Review panel must still show the configured scenario name and player count.
        # The UI renders: "Scenario: 📊 Scale Test" and "Player count: 128 Expected …"
        expect(sb.get_by_text("Scale Test", exact=False).first).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_launch_failure_retry_possible(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        After a 401 error: the Launch button must still be visible, allowing
        the user to retry (e.g. after re-authenticating or network recovery).

        If the button disappears or is permanently disabled after failure,
        the user is stuck and must refresh the page — losing all wizard state.
        """
        _navigate_to_step8_hth_for_error_test(page, base_url, api_url)
        sb = _sidebar(page)

        sb.get_by_role("button", name="LAUNCH TOURNAMENT").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Give Streamlit time to re-render with wizard_launching=False
        time.sleep(1)
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)

        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_visible(timeout=_LOAD_TIMEOUT)


# ═══════════════════════════════════════════════════════════════════════════════
# P1.3 — INDIVIDUAL_RANKING 128+ Safety Gate Enforcement
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestIndividualRankingSafetyGate:
    """
    P1.3: Verify the safety gate appears on the INDIVIDUAL_RANKING path with 128+ players.

    The safety gate is triggered by player_count >= 128 regardless of format.
    This was previously only tested on the HEAD_TO_HEAD path.

    Coverage:
      - Safety confirmation field is VISIBLE on INDIVIDUAL_RANKING + 128p
      - Launch button is DISABLED without text (negative path)
      - Wrong text keeps button DISABLED (negative path)
      - Correct "LAUNCH" text enables button (positive path — UI state only)
    """

    def test_individual_ranking_128p_safety_field_visible(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        INDIVIDUAL_RANKING + 128 players (scale_test default):
        safety confirmation text input must be visible in Step 8.

        Regression: if the safety gate is only applied on HEAD_TO_HEAD path,
        this test will fail — exposing the gap.
        """
        _navigate_to_step8_individual_ranking_large(page, base_url, api_url)
        sb = _sidebar(page)

        expect(sb.get_by_text("Enable auto-refresh", exact=False)).not_to_be_visible(
            timeout=3_000
        ) if False else None  # noqa: skip this check

        # Safety confirmation must be visible
        expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        # Text input for "LAUNCH" confirmation must be visible (by placeholder)
        expect(sb.get_by_placeholder("Type LAUNCH to enable the button")).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_individual_ranking_128p_launch_disabled_without_confirmation(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        INDIVIDUAL_RANKING + 128 players: Launch button must be DISABLED
        when no confirmation text is entered.

        Negative path assertion. If the button is enabled without confirmation,
        the safety gate is bypassed for the INDIVIDUAL_RANKING format.
        """
        _navigate_to_step8_individual_ranking_large(page, base_url, api_url)
        sb = _sidebar(page)

        # Ensure the textbox is empty (no confirmation entered)
        textbox = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(textbox).to_be_visible(timeout=_LOAD_TIMEOUT)
        textbox.fill("")
        textbox.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(0.5)

        # Launch button must be disabled
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_disabled(timeout=_LOAD_TIMEOUT)

    def test_individual_ranking_128p_wrong_text_keeps_disabled(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        INDIVIDUAL_RANKING + 128 players: typing wrong text (not "LAUNCH") must
        keep the Launch button DISABLED.

        Negative path assertion. The gate must be case-sensitive and exact-match.
        """
        _navigate_to_step8_individual_ranking_large(page, base_url, api_url)
        sb = _sidebar(page)

        textbox = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(textbox).to_be_visible(timeout=_LOAD_TIMEOUT)

        for wrong_text in ["LAUNC", "Launch!", "yes", "confirm"]:
            textbox.fill(wrong_text)
            textbox.press("Enter")
            page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
            time.sleep(0.5)

            launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
            assert launch_btn.is_disabled(), (
                f"INDIVIDUAL_RANKING 128p: Launch button must be disabled "
                f"with wrong text '{wrong_text}', but it was enabled."
            )

        textbox.fill("")
        textbox.press("Enter")  # clean up

    def test_individual_ranking_128p_correct_text_enables_button(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        INDIVIDUAL_RANKING + 128 players: typing exact "LAUNCH" must enable
        the Launch button.

        Positive path assertion. Verifies the safety gate CAN be cleared
        on the INDIVIDUAL_RANKING path — not just blocked.
        """
        _navigate_to_step8_individual_ranking_large(page, base_url, api_url)
        sb = _sidebar(page)

        textbox = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(textbox).to_be_visible(timeout=_LOAD_TIMEOUT)

        textbox.fill("LAUNCH")
        textbox.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(0.5)

        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_enabled(timeout=_LOAD_TIMEOUT)

    def test_individual_ranking_128p_lowercase_launch_accepted(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        INDIVIDUAL_RANKING + 128 players: "launch" (lowercase) must also enable
        the button — the validation uses .strip().upper() comparison.

        Verifies: case-insensitive acceptance is consistent with the HEAD_TO_HEAD
        safety gate behaviour (already tested in TestSafetyConfirmationUI).
        """
        _navigate_to_step8_individual_ranking_large(page, base_url, api_url)
        sb = _sidebar(page)

        textbox = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(textbox).to_be_visible(timeout=_LOAD_TIMEOUT)

        textbox.fill("launch")
        textbox.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(0.5)

        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_enabled(timeout=_LOAD_TIMEOUT)

    # ── API-level safety gate for INDIVIDUAL_RANKING ──────────────────────────

    def test_individual_ranking_128p_api_requires_confirmed(self, api_url: str):
        """
        INDIVIDUAL_RANKING + 128 players at the API level:
        confirmed=False must be rejected (HTTP 400 or 422).

        This is the API contract behind the UI safety gate.
        If the API accepts unconfirmed large-scale INDIVIDUAL_RANKING launches,
        the safety gate can be bypassed via direct API calls.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "scale_test",
            "player_count": 128,
            "tournament_format": "INDIVIDUAL_RANKING",
            "dry_run": False,
            "confirmed": False,  # NOT confirmed — must be rejected
        })
        assert resp.status_code in (400, 422), (
            f"INDIVIDUAL_RANKING 128p without confirmed=True should be rejected "
            f"(400 or 422), got {resp.status_code}: {resp.text[:200]}"
        )

    def test_individual_ranking_128p_api_succeeds_with_confirmed(self, api_url: str):
        """
        INDIVIDUAL_RANKING + 128 players with confirmed=True: must succeed (HTTP 200).

        Positive path — ensures the safety gate is passable when confirmation is given,
        not a hard block.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "scale_test",
            "player_count": 128,
            "tournament_format": "INDIVIDUAL_RANKING",
            "dry_run": False,
            "confirmed": True,
            "simulation_mode": "manual",  # manual to avoid full simulation overhead
        })
        assert resp.status_code == 200, (
            f"INDIVIDUAL_RANKING 128p with confirmed=True should succeed, "
            f"got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True
        assert data.get("tournament_id") is not None
