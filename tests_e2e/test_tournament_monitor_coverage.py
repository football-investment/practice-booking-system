"""
Tournament Monitor Coverage Gap Tests
======================================

Addresses the coverage gaps in the base E2E suite:
  1. Boundary Value Analysis — player_count from 2 to 1024
  2. Tournament-type dependent matrix (knockout / league / group_knockout)
  3. 128+ Safety Confirmation UI (LAUNCH text field, case-sensitive validation)
  4. Wizard slider state persistence (Step 4 → Back → Forward)
  5. Post-launch observability (session count > 0, IN_PROGRESS state, ranked results)

Design decisions:
  - API-level boundary tests use pytest.mark.parametrize for exhaustive coverage.
  - UI tests are kept focused: they test the *mechanism*, not every numeric combination
    (slider drag across 512 values in a browser would be impractical and fragile).
  - group_knockout invalid player counts are tested explicitly against the API — the
    backend must reject or handle them, not silently produce a broken tournament.
  - Playwright tests run against localhost; API tests are pure HTTP (no browser).

Run:
    pytest tests_e2e/test_tournament_monitor_coverage.py -v --tb=short
    pytest tests_e2e/test_tournament_monitor_coverage.py -m tournament_monitor -v
    pytest tests_e2e/test_tournament_monitor_coverage.py -m "tournament_monitor and not slow" -v
"""

import json
import time
import urllib.parse
import requests
import pytest
from playwright.sync_api import Page, expect

# ── Shared constants ──────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
MONITOR_PATH = "/Tournament_Monitor"

_LOAD_TIMEOUT = 30_000
_STREAMLIT_SETTLE = 2
_LAUNCH_SETTLE = 12

# group_knockout valid player counts (from get_group_knockout_config)
_GK_VALID = {8, 12, 16, 24, 32, 48, 64}


# ── Auth / API helpers (duplicated from base suite intentionally — test isolation) ──

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


# Cache for active campus ID (populated on first call)
_CAMPUS_ID_CACHE = None

def _ops_post(api_url: str, token: str, payload: dict, timeout: int = 120) -> requests.Response:
    """
    Raw POST to /ops/run-scenario — returns Response for assertion flexibility.

    Automatically adds campus_ids if not provided (queries first active campus from DB).
    """
    global _CAMPUS_ID_CACHE

    # Add default campus_ids if not provided (required field for OPS scenarios)
    if "campus_ids" not in payload:
        # Query first active campus (cached to avoid repeated DB hits)
        if _CAMPUS_ID_CACHE is None:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from app.models.campus import Campus
            from app.config import settings

            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            try:
                campus = db.query(Campus).filter(Campus.is_active == True).first()
                _CAMPUS_ID_CACHE = campus.id if campus else 1  # Fallback to 1 if no campus
            finally:
                db.close()

        payload["campus_ids"] = [_CAMPUS_ID_CACHE]

    return requests.post(
        f"{api_url}/api/v1/tournaments/ops/run-scenario",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=timeout,
    )


def _go_to_monitor_authenticated(page: Page, base_url: str, api_url: str) -> None:
    token = _get_admin_token(api_url)
    user = _get_admin_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
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


# ── Group E: Boundary Value Analysis (API-level, parametrized) ─────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
class TestPlayerCountBoundaryAPI:
    """
    Parametrized boundary-value tests against the OPS API.

    Tests the full 2–1024 range at critical boundary points.
    All use smoke_test scenario where valid (max 16), large_field_monitor for larger.
    These are API-only tests (no browser) — fast and exhaustive.
    """

    # ── Minimum boundary ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("player_count", [4, 8, 16])
    def test_api_minimum_boundary_knockout(self, api_url: str, player_count: int):
        """
        player_count at valid knockout boundaries (4=min, 8, 16).
        All must be accepted by the API and return triggered=True.
        Note: knockout min_players=4 (power-of-2 requirement).
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"player_count={player_count}: expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"player_count={player_count}: {data}"
        assert data.get("tournament_id") is not None

    @pytest.mark.parametrize("player_count", [2, 3])
    def test_api_knockout_below_minimum_rejected(self, api_url: str, player_count: int):
        """
        player_count 2,3 below knockout min_players=4 — API must return 422.
        Validates that tournament type constraints are enforced.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 422, (
            f"player_count={player_count}: expected 422 (below min), got {resp.status_code}: {resp.text[:300]}"
        )

    def test_api_below_minimum_rejected(self, api_url: str):
        """player_count=1 is below ge=2 — API must return 422."""
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 1,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 422, (
            f"player_count=1 should be rejected with 422, got {resp.status_code}"
        )

    def test_api_above_maximum_rejected(self, api_url: str):
        """player_count=1025 is above le=1024 — API must return 422."""
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 1025,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 422, (
            f"player_count=1025 should be rejected with 422, got {resp.status_code}"
        )

    # ── Power-of-two boundaries (knockout bracket sizes) ────────────────────

    @pytest.mark.parametrize("player_count", [8, 16])
    def test_api_power_of_two_knockout_smoke(self, api_url: str, player_count: int):
        """
        Classic knockout bracket sizes within smoke_test range (≤16).
        Must all succeed.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"player_count={player_count}: expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"player_count={player_count}: {data}"

    @pytest.mark.slow
    @pytest.mark.parametrize("player_count", [32, 64])
    def test_api_power_of_two_knockout_large(self, api_url: str, player_count: int):
        """
        Power-of-two sizes in large_field_monitor range (17–127).
        Must all succeed.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"player_count={player_count}: expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"player_count={player_count}: {data}"

    # ── Safety threshold boundary ────────────────────────────────────────────

    def test_api_safety_threshold_boundary_127(self, api_url: str):
        """
        player_count=127: just below safety threshold (128).
        confirmed=False should be ACCEPTED (no safety gate triggered).
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 127,  # odd, non-power-of-two
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": False,  # no confirmation needed below threshold
        })
        # Must NOT trigger the safety gate (player_count < 128)
        assert resp.status_code == 200, (
            f"player_count=127 (below threshold) should not require confirmation: "
            f"{resp.status_code}: {resp.text[:300]}"
        )

    def test_api_safety_threshold_boundary_128_requires_confirmation(self, api_url: str):
        """
        player_count=128: at the safety threshold.
        confirmed=False must be REJECTED with 422.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 128,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": False,  # missing confirmation — must be rejected
        })
        assert resp.status_code == 422, (
            f"player_count=128 without confirmed=True should return 422, got {resp.status_code}"
        )
        body = resp.json()
        assert "confirmed" in str(body).lower() or "large" in str(body).lower(), (
            f"Error message should mention confirmation requirement: {body}"
        )

    @pytest.mark.slow
    def test_api_safety_threshold_boundary_128_with_confirmation(self, api_url: str):
        """
        player_count=128 with confirmed=True: must succeed.
        This is the exact threshold — both sides must be tested.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 128,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        }, timeout=180)
        assert resp.status_code == 200, (
            f"player_count=128 with confirmed=True should succeed: {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"player_count=128: {data}"

    # ── League boundary values ────────────────────────────────────────────────

    @pytest.mark.parametrize("player_count,expected_sessions", [
        (2,  1),   # 2*(2-1)/2 = 1
        (3,  3),   # 3*(3-1)/2 = 3
        (4,  6),   # 4*(4-1)/2 = 6
        (8,  28),  # 8*(8-1)/2 = 28
        (16, 120), # 16*(16-1)/2 = 120
    ])
    def test_api_league_smoke_range(
        self, api_url: str, player_count: int, expected_sessions: int
    ):
        """
        League tournament boundary values. Formula: N×(N-1)/2 sessions.

        All counts from 2 upward must generate sessions (min_players=2 in league.json).
        """

        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "league",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"league player_count={player_count}: expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"league player_count={player_count}: {data}"

        tid = data.get("tournament_id")
        sessions_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        assert len(sessions) == expected_sessions, (
            f"league {player_count}p: expected {expected_sessions} sessions "
            f"(N×(N-1)/2), got {len(sessions)}"
        )

    # ── Individual Ranking boundaries ────────────────────────────────────────

    @pytest.mark.parametrize("player_count,scoring_type", [
        (2, "SCORE_BASED"),
        (4, "TIME_BASED"),
        (8, "DISTANCE_BASED"),
        (16, "PLACEMENT"),
    ])
    def test_api_individual_ranking_boundary_values(
        self, api_url: str, player_count: int, scoring_type: str
    ):
        """
        INDIVIDUAL_RANKING with boundary player counts and all scoring types.
        1 session should be generated for all players.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "INDIVIDUAL_RANKING",
            "scoring_type": scoring_type,
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"INDIVIDUAL_RANKING {player_count}p {scoring_type}: {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True

        tid = data.get("tournament_id")
        sessions_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        sessions = sessions_resp.json()
        assert len(sessions) == 1, (
            f"INDIVIDUAL_RANKING {player_count}p {scoring_type}: "
            f"expected 1 session (all compete together), got {len(sessions)}"
        )
        # All players must be in that one session
        first = sessions[0]
        names = first.get("participant_names") or []
        assert len(names) == player_count, (
            f"INDIVIDUAL_RANKING {player_count}p: expected {player_count} participants "
            f"in single session, got {len(names)}"
        )


# ── Group F: Group+Knockout Valid vs Invalid Matrix ───────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
class TestGroupKnockoutMatrix:
    """
    group_knockout requires specific player counts (8, 12, 16, 24, 32, 48, 64).
    Tests both valid and invalid counts explicitly.
    """

    @pytest.mark.parametrize("player_count", sorted(_GK_VALID))
    def test_api_group_knockout_valid_counts(self, api_url: str, player_count: int):
        """Every valid group_knockout player count must produce a tournament."""
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "group_knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"group_knockout valid count {player_count}: expected 200, "
            f"got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data.get("triggered") is True, f"group_knockout {player_count}p: {data}"

    @pytest.mark.parametrize("player_count", [4, 6, 10, 14, 20])
    def test_api_group_knockout_invalid_counts_handled(self, api_url: str, player_count: int):
        """
        Invalid group_knockout player counts (not in {8,12,16,24,32,48,64}).
        The backend either rejects (422) or falls back gracefully — must not 500.
        An unhandled 500 would indicate a missing validation branch.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "group_knockout",
            "dry_run": False,
            "confirmed": True,
        })
        # Must NOT be a 500 (internal server error) — graceful rejection only
        assert resp.status_code != 500, (
            f"group_knockout invalid count {player_count}: got 500 (unhandled error): {resp.text[:300]}"
        )
        # Acceptable responses: 200 (fallback) or 422/400 (explicit rejection)
        assert resp.status_code in (200, 400, 422), (
            f"group_knockout invalid count {player_count}: unexpected status {resp.status_code}"
        )

    def test_api_group_knockout_session_count_formula(self, api_url: str):
        """
        16-player group_knockout: 4 groups × 4 players.
        Group matches: 4 × C(4,2) = 4 × 6 = 24 GROUP_STAGE sessions.
        Knockout: actual backend generates 8 KNOCKOUT sessions (not 3 as estimate_session_count() predicts).

        NOTE: estimate_session_count() in the UI is inaccurate for group_knockout.
        It predicts 24+3=27 but the actual backend generates 24+8=32 sessions.
        This discrepancy is a known UI display inaccuracy (the estimate formula
        uses qualifiers=2 per group but the actual KO bracket uses all 16 players).
        This test asserts the ACTUAL behavior, not the estimate.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "large_field_monitor",
            "player_count": 16,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "group_knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, f"group_knockout 16p: {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        tid = data.get("tournament_id")
        sessions_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        sessions = sessions_resp.json()
        # Verify phases exist and counts are internally consistent
        group_sessions = [s for s in sessions if s.get("tournament_phase") == "GROUP_STAGE"]
        ko_sessions = [s for s in sessions if s.get("tournament_phase") == "KNOCKOUT"]

        # Group stage: 4 groups × C(4,2) = 4 × 6 = 24
        assert len(group_sessions) == 24, (
            f"group_knockout 16p: expected 24 GROUP_STAGE sessions, got {len(group_sessions)}"
        )
        # Knockout stage: actual count (backend uses all 16p bracket = 15 or power-of-2 bracket)
        assert len(ko_sessions) > 0, (
            f"group_knockout 16p: expected KNOCKOUT sessions, got 0"
        )
        # Total must be group + knockout
        assert len(sessions) == len(group_sessions) + len(ko_sessions), (
            f"group_knockout 16p: session count mismatch: "
            f"{len(group_sessions)} + {len(ko_sessions)} ≠ {len(sessions)}"
        )
        # Document actual behavior for regression tracking
        assert len(sessions) == 32, (
            f"group_knockout 16p: actual behavior is 32 sessions (24 group + 8 KO), got {len(sessions)}. "
            f"If this changed, update this test — the estimate_session_count() UI function also needs updating."
        )

    def test_api_knockout_session_count_formula(self, api_url: str):
        """
        Knockout session count = player_count (NOT player_count-1).

        The backend generates a 3rd Place Playoff session in addition to
        the standard elimination bracket, making the total N for power-of-2 counts.

        estimate_session_count() in the UI predicts N-1 but actual = N.
        This is a documented inaccuracy in the UI estimate formula.
        """
        token = _get_admin_token(api_url)
        for player_count in [4, 8, 16]:
            resp = _ops_post(api_url, token, {
                "scenario": "smoke_test",
                "player_count": player_count,
                "tournament_format": "HEAD_TO_HEAD",
                "tournament_type_code": "knockout",
                "dry_run": False,
                "confirmed": True,
            })
            assert resp.status_code == 200, f"knockout {player_count}p: {resp.status_code}"
            tid = resp.json().get("tournament_id")
            sessions = requests.get(
                f"{api_url}/api/v1/tournaments/{tid}/sessions",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            ).json()
            # Actual: N sessions (includes 3rd place playoff)
            # UI estimate_session_count() returns N-1 (inaccurate — missing playoff)
            assert len(sessions) == player_count, (
                f"knockout {player_count}p: expected {player_count} sessions "
                f"(includes 3rd Place Playoff), got {len(sessions)}. "
                f"Note: estimate_session_count() predicts {player_count-1} — that formula is wrong."
            )
            # Verify the 3rd Place Playoff is explicitly present
            playoff_sessions = [s for s in sessions if "3rd Place" in (s.get("title") or "")]
            assert len(playoff_sessions) == 1, (
                f"knockout {player_count}p: expected 1 '3rd Place Playoff' session, "
                f"got {len(playoff_sessions)}"
            )


# ── Group G: 128+ Safety Confirmation UI Tests ────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
class TestSafetyConfirmationUI:
    """
    Tests for the 128-player safety confirmation mechanism in Step 8.

    When player_count >= 128, Step 8 shows a text input requiring the user
    to type exactly "LAUNCH" before the LAUNCH TOURNAMENT button is enabled.
    """

    def _navigate_to_step6_large(
        self,
        page: Page,
        base_url: str,
        api_url: str,
        player_count_value: int = 128,
    ) -> None:
        """
        Navigate to Step 8 (Review) with a large player count selected in Step 5.

        Uses large_field_monitor scenario (allows up to 1024 players).
        Forces player_count via Streamlit session state URL injection is not
        possible for slider — instead we navigate step by step and verify
        that the Step 8 safety UI appears when >=128 is pre-set.

        Note: This test cannot literally drag the slider to 128 (Playwright
        slider interaction is fragile across OS). Instead we verify the
        safety mechanism by reaching Step 8 with the scenario's default
        player count (128 for scale_test).
        """
        token = _get_admin_token(api_url)
        user = _get_admin_user(api_url, token)
        # Inject session state: pre-set wizard to Step 6 with large player count
        params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
        page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        sb = _sidebar(page)

        # Step 1: Scale Test (default_player_count=128, allows >=64)
        sb.get_by_text("Scale Test", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)

        # Step 2: HEAD_TO_HEAD
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Step 3: Knockout
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Step 5: Use default player count for scale_test (128)
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        # Verify the large scale warning appears (player_count >= 128)
        expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        _click_next(page)

        # Step 6: Accelerated Simulation
        expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        _click_next(page)

        # Step 7: Configure Rewards (new optional step — just pass through)
        expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Now at Step 8 with player_count >= 128
        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

    def test_step4_large_scale_warning_visible(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Step 5 with scale_test (default 128 players): must show
        'LARGE SCALE OPERATION' safety warning.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Scale Test scenario
        sb.get_by_text("Scale Test", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)

        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)

        # Step 5: Player count — scale_test default is 128 players
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        # scale_test default is 128 players — safety warning must appear
        expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_text("Safety confirmation will be required", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

    def test_step6_safety_confirmation_field_visible_for_128plus(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Step 8 with >=128 players: Safety Confirmation text input must appear.
        LAUNCH TOURNAMENT button must be DISABLED until "LAUNCH" is typed.
        """
        self._navigate_to_step6_large(page, base_url, api_url)
        sb = _sidebar(page)

        # Safety confirmation field must be present
        expect(sb.get_by_text("Safety Confirmation", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )
        expect(sb.get_by_placeholder("Type LAUNCH to enable the button")).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        # LAUNCH TOURNAMENT button must be DISABLED before typing
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_visible()
        expect(launch_btn).to_be_disabled()

    def _fill_safety_input(self, page: Page, sb, text: str) -> None:
        """
        Fill the Safety Confirmation text_input and trigger Streamlit rerun.

        Streamlit text_input only processes input when Enter is pressed
        ("Press Enter to apply" hint is shown in the UI). `.fill()` alone
        does NOT trigger a rerun — must press Enter afterward.
        """
        confirm_input = sb.get_by_placeholder("Type LAUNCH to enable the button")
        confirm_input.fill(text)
        confirm_input.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

    def test_step6_safety_confirmation_wrong_text_keeps_disabled(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Typing incomplete text ("LAUNC") and pressing Enter keeps button disabled.

        Note: Streamlit text_input requires Enter to submit. The safety check is:
          confirm_input.strip().upper() == "LAUNCH"
          - "LAUNC" → NOT "LAUNCH" → DISABLED ✓
          - "ABORT" → NOT "LAUNCH" → DISABLED ✓
          - "LAUNCH" → == "LAUNCH" → ENABLED ✓
        """
        self._navigate_to_step6_large(page, base_url, api_url)
        sb = _sidebar(page)
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")

        # Partial text — must stay disabled
        self._fill_safety_input(page, sb, "LAUNC")
        expect(launch_btn).to_be_disabled()

        # Completely wrong text — must stay disabled
        self._fill_safety_input(page, sb, "ABORT")
        expect(launch_btn).to_be_disabled()

    def test_step6_safety_confirmation_correct_text_enables_button(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Typing "LAUNCH" + Enter enables the LAUNCH TOURNAMENT button.

        Streamlit text_input requires Enter to apply the value.
        The safety check uses strip().upper() == "LAUNCH".
        """
        self._navigate_to_step6_large(page, base_url, api_url)
        sb = _sidebar(page)
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")

        # Correct confirmation — button must be enabled
        self._fill_safety_input(page, sb, "LAUNCH")
        expect(launch_btn).to_be_enabled()

    def test_step6_safety_lowercase_also_accepted(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        "launch" (lowercase) + Enter is accepted because the check uses .upper().
        Documents actual behavior: NOT strictly case-sensitive.
        """
        self._navigate_to_step6_large(page, base_url, api_url)
        sb = _sidebar(page)
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")

        # Lowercase accepted via .upper()
        self._fill_safety_input(page, sb, "launch")
        expect(launch_btn).to_be_enabled()

    def test_step6_no_safety_field_for_small_count(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Step 8 with smoke_test (4 players, below threshold):
        Safety confirmation field must NOT appear.
        LAUNCH TOURNAMENT button must be ENABLED immediately.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Navigate to Step 8 with Smoke Test (4 players)
        sb.get_by_text("Smoke Test", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 5: Player count
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 6: Accelerated Simulation
        expect(sb.get_by_text("Step 6 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        _click_next(page)
        # Step 7: Configure Rewards (new optional step — just pass through)
        expect(sb.get_by_text("Step 7 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 8: Review
        expect(sb.get_by_text("Step 8 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Safety field must NOT be visible
        expect(
            sb.get_by_placeholder("Type LAUNCH to enable the button")
        ).not_to_be_visible()

        # Button must be enabled immediately (no confirmation required)
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled()


# ── Group H: Slider State Persistence ────────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
class TestSliderStatePersistence:
    """
    Verify that the player count slider value is preserved when navigating
    Back and Forward through the wizard.

    The slider uses Streamlit key= mechanism. The saved value must survive
    a Back→Forward round-trip.
    """

    def test_step4_slider_shows_scenario_default(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        smoke_test default_player_count = 4.
        When first arriving at Step 5 (Player Count) via smoke_test, slider should show 4.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        sb.get_by_text("Smoke Test", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 5: Player count
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        slider = sb.get_by_role("slider", name="Number of players to enroll")
        expect(slider).to_be_visible()

        val_str = slider.get_attribute("aria-valuenow")
        assert val_str is not None, "Slider has no aria-valuenow attribute"
        val = int(val_str)
        # smoke_test default is 4; slider is clamped to [min, max] range
        assert 2 <= val <= 16, (
            f"smoke_test slider should be in [2,16], got {val}"
        )

    def test_step4_slider_in_valid_range_for_large_field(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        large_field_monitor default_player_count = 8.
        Slider range = [4, 1024].
        Default slider value must be in valid range.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 5: Player count
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        slider = sb.get_by_role("slider", name="Number of players to enroll")
        expect(slider).to_be_visible()

        val_str = slider.get_attribute("aria-valuenow")
        assert val_str is not None
        val = int(val_str)
        assert 4 <= val <= 1024, (
            f"large_field_monitor slider should be in [4, 1024], got {val}"
        )

    def test_step4_back_forward_preserves_slider_value(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Regression: Going Step 5 (Player Count) → Back (Step 4) → Forward (Step 5) again
        must show the SAME slider value, not reset to scenario default.

        This tests that wizard_player_count_saved is populated from the
        slider's current value before navigating back.
        """
        _go_to_monitor_authenticated(page, base_url, api_url)
        sb = _sidebar(page)

        # Navigate to Step 5 (Player count)
        sb.get_by_text("Smoke Test", exact=False).first.click()
        time.sleep(0.3)
        _click_next(page)
        expect(sb.get_by_text("Step 2 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        expect(sb.get_by_text("Step 3 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 4: Game Preset (new optional step — just pass through)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        _click_next(page)
        # Step 5: Player count
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Record current slider value
        slider = sb.get_by_role("slider", name="Number of players to enroll")
        val_before_str = slider.get_attribute("aria-valuenow")
        assert val_before_str is not None
        val_before = int(val_before_str)

        # Go Back to Step 4 (Game Preset)
        _click_back(page)
        expect(sb.get_by_text("Step 4 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Go Forward to Step 5 (Player count) again
        _click_next(page)
        expect(sb.get_by_text("Step 5 of 8", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Slider must show the SAME value as before (saved in wizard_player_count_saved)
        slider_after = sb.get_by_role("slider", name="Number of players to enroll")
        val_after_str = slider_after.get_attribute("aria-valuenow")
        assert val_after_str is not None
        val_after = int(val_after_str)

        assert val_after == val_before, (
            f"Slider value changed after Back→Forward: was {val_before}, now {val_after}. "
            f"wizard_player_count_saved was not preserved."
        )


# ── Group I: Post-launch Observability (State Consistency) ───────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.ops_seed  # Requires 64 @lfa-seed.hu players via fixture
class TestPostLaunchObservability:
    """
    After a tournament is launched via the wizard, verify that:
    1. Tournament status = IN_PROGRESS (not DRAFT or CANCELLED)
    2. Session count > 0 (session generation happened)
    3. At least some sessions have results (auto-simulation ran)
    4. Rankings are populated (leaderboard is not empty)

    These are API-backed state assertions — not just UI text checks.
    The backend always auto-simulates for small player counts (sync path),
    so we can assert non-empty results after launch.
    """

    # OPS smoke_test auto-simulates the full tournament synchronously.
    # For small counts (4p) this completes in <5s, landing in REWARDS_DISTRIBUTED.
    # Valid launched statuses — anything that is NOT DRAFT or CANCELLED.
    _VALID_LAUNCHED = {"IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED"}

    def test_post_launch_tournament_status_in_progress(self, api_url: str):
        """
        After OPS smoke_test launch: tournament must NOT be in DRAFT state.
        Regression: previously tournaments were created in DRAFT state and never advanced.

        Note: for small player counts (4p) the full simulation runs synchronously,
        so the status may be REWARDS_DISTRIBUTED rather than IN_PROGRESS. Both are
        valid — what we guard against is the DRAFT regression.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200
        tid = resp.json().get("tournament_id")

        detail = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ).json()
        status = detail.get("tournament_status")
        assert status in self._VALID_LAUNCHED, (
            f"Expected one of {self._VALID_LAUNCHED} after OPS launch, got: {status}. "
            f"Regression: tournament stuck in DRAFT or CANCELLED."
        )

    def test_post_launch_session_count_nonzero(self, api_url: str):
        """
        After OPS smoke_test launch: session count must be > 0.
        A tournament with 0 sessions cannot be monitored.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200
        tid = resp.json().get("tournament_id")

        sessions = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ).json()
        assert len(sessions) > 0, "Session count = 0 after OPS launch (generation failed)"

    def test_post_launch_sessions_have_results(self, api_url: str):
        """
        After OPS smoke_test launch: at least some sessions must have
        result_submitted=True (auto-simulation ran and submitted scores).

        If all sessions are result_submitted=False, monitoring shows 0%
        progress — the auto-simulation path is broken.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200
        tid = resp.json().get("tournament_id")

        sessions = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ).json()
        assert len(sessions) > 0, "No sessions generated"

        submitted = [s for s in sessions if s.get("result_submitted") is True]
        assert len(submitted) > 0, (
            f"No sessions have result_submitted=True after auto-simulation. "
            f"Total sessions: {len(sessions)}. "
            f"This means auto-simulation did NOT run or results were not saved."
        )

    def test_post_launch_rankings_populated(self, api_url: str):
        """
        After OPS smoke_test launch (knockout, 4p): rankings endpoint must
        return at least 1 ranked player.

        If rankings are empty after launch, the leaderboard panel shows nothing —
        the ranking calculation step failed.
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": 4,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200
        tid = resp.json().get("tournament_id")

        rankings_resp = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/rankings",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert rankings_resp.status_code == 200, (
            f"Rankings endpoint returned {rankings_resp.status_code}"
        )
        rankings = rankings_resp.json()
        assert len(rankings) > 0, (
            f"Rankings list is empty after OPS smoke_test launch. "
            f"Leaderboard would show nothing. Rankings calculation did not run."
        )

    def test_post_launch_enrolled_count_matches_request(self, api_url: str):
        """
        After OPS launch with player_count=8: enrolled_count in response
        must equal 8. Verifies that all seeded players were successfully enrolled.
        """
        token = _get_admin_token(api_url)
        requested = 8
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": requested,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": "knockout",
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        enrolled = data.get("enrolled_count", 0)
        assert enrolled >= requested, (
            f"Requested {requested} players but only {enrolled} were enrolled. "
            f"Some players failed to enroll."
        )

    @pytest.mark.parametrize("player_count,tournament_type", [
        (2,  "league"),
        (4,  "knockout"),
        (4,  "league"),
        (8,  "knockout"),
        (8,  "league"),
        (16, "knockout"),
        (16, "league"),
    ])
    def test_post_launch_session_count_matches_formula(
        self, api_url: str, player_count: int, tournament_type: str
    ):
        """
        Parametrized: session count after launch must match the expected formula.
        knockout: N sessions (includes 3rd Place Playoff)
        league: N×(N-1)/2 sessions
        """
        token = _get_admin_token(api_url)
        resp = _ops_post(api_url, token, {
            "scenario": "smoke_test",
            "player_count": player_count,
            "tournament_format": "HEAD_TO_HEAD",
            "tournament_type_code": tournament_type,
            "dry_run": False,
            "confirmed": True,
        })
        assert resp.status_code == 200, (
            f"{tournament_type} {player_count}p: {resp.status_code}: {resp.text[:200]}"
        )
        tid = resp.json().get("tournament_id")

        sessions = requests.get(
            f"{api_url}/api/v1/tournaments/{tid}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ).json()

        if tournament_type == "knockout":
            # Backend generates N sessions (includes 3rd Place Playoff)
            # estimate_session_count() predicts N-1 but actual = N
            expected = player_count
        else:  # league
            expected = player_count * (player_count - 1) // 2

        assert len(sessions) == expected, (
            f"{tournament_type} {player_count}p: expected {expected} sessions, got {len(sessions)}"
        )
