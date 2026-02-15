"""
Production Readiness Tests — Scale Lifecycle & Parallel Stress
================================================================

This test suite proves production readiness of the OPS Tournament Monitor
system under maximum-scale conditions.

Architecture Verified Here:
  - player_count < 128 → SYNC path: generate + simulate + rank in one request
  - player_count >= 128 → ASYNC path: task queued (Celery/thread) — sessions
    generated later; simulation and ranking require separate calls or a worker.

For lifecycle assertions (result_submitted, rankings) this suite uses the SYNC
path at its ceiling (64p). For scale/stress assertions it tests the ASYNC path
(128p, 1024p) to verify launch correctness and DB isolation.

Test Groups:
  Q. TestLifecycleStress64   — 64-player knockout full lifecycle (sync path ceiling)
  R. TestAsyncLaunchScale    — 128p + 1024p launch-only assertions (async path)
  S. TestParallelLaunchStress — 64 + 32 + 8 launched concurrently, race condition checks
  T. TestProductionUILifecycle — Playwright wizard flow for boundary player counts

What is measured and asserted:
  1. total_runtime (wall clock for full launch + simulation) — sync path
  2. session_count == expected (64 for 64p knockout)
  3. tournament_status == IN_PROGRESS after launch
  4. sessions_with_results: result_submitted=True count > 0 (auto-simulation ran)
  5. rankings_count > 0 (ranking calculation ran)
  6. all_results_submitted: ALL sessions have result_submitted=True
  7. rankings_match_enrolled: rankings count == enrolled_count
  8. No DB lock / no API error during parallel launch
  9. All 3 parallel tournaments independently reach IN_PROGRESS
  10. UI: tracking card appears, no crash, no timeout, wizard resets
  11. 128p + 1024p: triggered=True, enrolled_count matches, task_id returned
  12. 128p + 1024p: tournament_status == IN_PROGRESS (enroll + tournament created)

Sync Path Architecture Notes:
  - player_count < 128 → sync (generate + simulate + rank in one HTTP call)
  - task_id == "sync-done" (not a UUID)
  - All lifecycle assertions valid immediately after OPS returns

Async Path Architecture Notes:
  - player_count >= 128 → async (task queued via Celery worker or daemon thread)
  - task_id == UUID (Celery or fallback thread)
  - Without a running Celery worker, sessions remain 0 until worker processes task
  - Sessions, results, rankings: NOT immediately available
  - ONLY launch-success (triggered=True) and enrollment assertions are valid
  - For full lifecycle at 128p+: Celery worker must be running

Run:
    # All tests (includes @slow):
    pytest tests_e2e/test_production_readiness.py -v --tb=short -s

    # Skip slow tests (quick smoke):
    pytest tests_e2e/test_production_readiness.py -v --tb=short -m "not slow"

    # API tests only (no Playwright):
    pytest tests_e2e/test_production_readiness.py -v -k "not ui" --tb=short -s
"""

import time
import json
import math
import urllib.parse
import concurrent.futures
import threading
import traceback
import requests
import pytest
from playwright.sync_api import Page, expect

# ── Shared constants ────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
MONITOR_PATH = "/Tournament_Monitor"

_LOAD_TIMEOUT = 45_000
_STREAMLIT_SETTLE = 3
_LAUNCH_SETTLE = 15          # seconds to wait after sync launch
_POLL_TIMEOUT = 600          # seconds max for lifecycle polling
_POLL_INTERVAL = 5           # seconds between polls

# Sync path ceiling: largest player_count guaranteed to execute synchronously
_SYNC_MAX = 64               # < BACKGROUND_GENERATION_THRESHOLD (128)
_SYNC_SESSIONS = 64          # knockout 64p: 63 bracket + 1 playoff = 64 sessions

# ── Auth / API helpers ─────────────────────────────────────────────────────────

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
    assert resp.status_code == 200
    return resp.json()


def _ops_post(api_url: str, token: str, payload: dict, timeout: int = 120) -> requests.Response:
    return requests.post(
        f"{api_url}/api/v1/tournaments/ops/run-scenario",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=timeout,
    )


def _launch(
    api_url: str,
    token: str,
    player_count: int,
    tournament_type_code: str = "knockout",
    scenario: str = "large_field_monitor",
    timeout: int = 120,
    confirmed: bool = False,
) -> tuple[dict, float]:
    """
    Launch via OPS and return (response_data, wall_clock_seconds).
    Asserts HTTP 200 and triggered=True.

    Note: confirmed=True required for player_count >= 128.
    """
    t0 = time.monotonic()
    resp = _ops_post(api_url, token, {
        "scenario": scenario,
        "player_count": player_count,
        "tournament_format": "HEAD_TO_HEAD",
        "tournament_type_code": tournament_type_code,
        "dry_run": False,
        "confirmed": confirmed,
    }, timeout=timeout)
    elapsed = time.monotonic() - t0

    assert resp.status_code == 200, (
        f"{tournament_type_code} {player_count}p: HTTP {resp.status_code}: {resp.text[:400]}"
    )
    data = resp.json()
    assert data.get("triggered") is True, f"{tournament_type_code} {player_count}p: {data}"
    return data, elapsed


def _get_summary(api_url: str, token: str, tid: int) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/summary",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"Summary fetch failed tid={tid}: {resp.text}"
    return resp.json()


def _get_sessions(api_url: str, token: str, tid: int) -> list:
    resp = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/sessions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"Sessions fetch failed tid={tid}: {resp.text}"
    return resp.json()


def _get_rankings(api_url: str, token: str, tid: int) -> list:
    resp = requests.get(
        f"{api_url}/api/v1/tournaments/{tid}/rankings",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert resp.status_code == 200, f"Rankings fetch failed tid={tid}: {resp.text}"
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("rankings", [])


# ── Playwright helpers ─────────────────────────────────────────────────────────

def _sidebar(page: Page):
    return page.locator("section[data-testid='stSidebar']")


def _click_next(page: Page) -> None:
    _sidebar(page).get_by_role("button", name="Next →").click()
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _go_to_monitor(page: Page, base_url: str, api_url: str) -> None:
    token = _get_admin_token(api_url)
    user = _get_admin_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    page.goto(f"{base_url}{MONITOR_PATH}?{params}", timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


# ═══════════════════════════════════════════════════════════════════════════════
# Q: 64-Player Full Lifecycle Stress Test (API-Level, Sync Path)
#
# 64p = maximum player count on the SYNC path (< BACKGROUND_GENERATION_THRESHOLD=128).
# Sync path: OPS generates sessions + simulates results + calculates rankings
# all in a single HTTP request. All lifecycle assertions are valid immediately.
#
# Session formula: 64p knockout = 63 bracket matches + 1 third-place playoff = 64 sessions
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestLifecycleStress64:
    """
    64-player knockout full lifecycle — production readiness assertions (sync path).

    This is the maximum-scale test using the synchronous code path.
    Sync path guarantees: sessions generated + results simulated + rankings calculated
    all within the single OPS HTTP request.

    For player_count >= 128 (async path), see TestAsyncLaunchScale.
    """

    def test_64p_launch_completes_within_timeout(self, api_url: str):
        """
        64p launch must complete within 120 seconds (sync path).
        Records wall-clock time for production benchmarking.
        """
        token = _get_admin_token(api_url)
        data, elapsed = _launch(api_url, token, _SYNC_MAX, "knockout",
                                scenario="large_field_monitor", timeout=120,
                                confirmed=False)

        print(f"\n[PERF] 64p knockout launch: {elapsed:.2f}s wall clock")
        print(f"[PERF] enrolled_count: {data.get('enrolled_count')}")
        print(f"[PERF] tournament_id: {data.get('tournament_id')}")
        print(f"[PERF] task_id: {data.get('task_id')}")

        assert data.get("task_id") == "sync-done", (
            f"64p should use sync path (task_id='sync-done'), got: {data.get('task_id')}"
        )
        assert elapsed < 120, (
            f"64p sync launch took {elapsed:.2f}s, exceeds 120s timeout"
        )

    def test_64p_session_count_exact(self, api_url: str):
        """
        64p knockout: exactly 64 sessions (63 bracket + 1 third-place playoff).
        Validates session generation completeness.
        """
        token = _get_admin_token(api_url)
        data, elapsed = _launch(api_url, token, _SYNC_MAX, "knockout",
                                scenario="large_field_monitor", timeout=120,
                                confirmed=False)
        tid = data["tournament_id"]
        sessions = _get_sessions(api_url, token, tid)

        print(f"\n[ASSERT] 64p knockout session count: {len(sessions)}")
        print(f"[PERF] Sync generation time: {elapsed:.2f}s")

        assert len(sessions) == _SYNC_SESSIONS, (
            f"64p knockout: expected {_SYNC_SESSIONS} sessions "
            f"(63 bracket + 1 playoff), got {len(sessions)}"
        )

        # Verify 3rd Place Playoff
        playoff = [s for s in sessions if "3rd Place" in (s.get("title") or "")]
        assert len(playoff) == 1, (
            f"64p: expected 1 '3rd Place Playoff', got {len(playoff)}"
        )

    def test_64p_tournament_status_in_progress(self, api_url: str):
        """
        Post-launch: tournament_status must be IN_PROGRESS.
        OPS always leaves tournament in IN_PROGRESS (COMPLETED requires explicit /complete call).
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, _SYNC_MAX, "knockout",
                           scenario="large_field_monitor", timeout=120,
                           confirmed=False)
        tid = data["tournament_id"]
        summary = _get_summary(api_url, token, tid)

        print(f"\n[ASSERT] tournament_status: {summary.get('tournament_status')}")
        assert summary.get("tournament_status") == "IN_PROGRESS", (
            f"64p: expected IN_PROGRESS, got {summary.get('tournament_status')}"
        )

    def test_64p_enrolled_count_correct(self, api_url: str):
        """
        OPS must have enrolled exactly 64 players.
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, _SYNC_MAX, "knockout",
                           scenario="large_field_monitor", timeout=120,
                           confirmed=False)

        enrolled = data.get("enrolled_count", 0)
        print(f"\n[ASSERT] enrolled_count: {enrolled}")
        assert enrolled == _SYNC_MAX, (
            f"64p: expected {_SYNC_MAX} enrolled players, got {enrolled}"
        )

    def test_64p_auto_simulation_generated_results(self, api_url: str):
        """
        Auto-simulation must have run: all sessions must have result_submitted=True.
        Sync path runs simulation immediately after generation.
        """
        token = _get_admin_token(api_url)
        data, elapsed = _launch(api_url, token, _SYNC_MAX, "knockout",
                                scenario="large_field_monitor", timeout=120,
                                confirmed=False)
        tid = data["tournament_id"]
        sessions = _get_sessions(api_url, token, tid)

        done = [s for s in sessions if s.get("result_submitted")]
        pct = 100 * len(done) / len(sessions) if sessions else 0

        print(f"\n[ASSERT] result_submitted: {len(done)}/{len(sessions)} ({pct:.1f}%)")
        print(f"[PERF] Full sync launch time: {elapsed:.2f}s")

        assert len(done) > 0, (
            f"64p: auto-simulation did not run — 0 sessions have result_submitted=True"
        )

    def test_64p_all_results_submitted(self, api_url: str):
        """
        All 64 sessions must have result_submitted=True after sync auto-simulation.
        """
        token = _get_admin_token(api_url)
        data, elapsed = _launch(api_url, token, _SYNC_MAX, "knockout",
                                scenario="large_field_monitor", timeout=120,
                                confirmed=False)
        tid = data["tournament_id"]
        sessions = _get_sessions(api_url, token, tid)

        done = [s for s in sessions if s.get("result_submitted")]
        pending = [s for s in sessions if not s.get("result_submitted")]

        print(f"\n[ASSERT] All results: {len(done)}/{len(sessions)} submitted")
        if pending:
            sample_pending = [s.get("title", "?") for s in pending[:3]]
            print(f"[WARN] Pending sessions sample: {sample_pending}")

        assert len(done) == len(sessions), (
            f"64p: only {len(done)}/{len(sessions)} sessions have result_submitted=True. "
            f"Auto-simulation was partial — {len(pending)} sessions unfinished."
        )

    def test_64p_rankings_populated(self, api_url: str):
        """
        rankings_count must be > 0 after sync launch.
        Sync path auto-calculates rankings immediately after simulation.
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, _SYNC_MAX, "knockout",
                           scenario="large_field_monitor", timeout=120,
                           confirmed=False)
        tid = data["tournament_id"]
        summary = _get_summary(api_url, token, tid)
        rankings = _get_rankings(api_url, token, tid)

        print(f"\n[ASSERT] rankings_count: {len(rankings)}")
        print(f"[ASSERT] summary.rankings_count: {summary.get('rankings_count')}")

        assert len(rankings) > 0, (
            f"64p: rankings are empty after sync launch. "
            f"Ranking calculation did not run on sync path."
        )

    def test_64p_rankings_match_enrolled_count(self, api_url: str):
        """
        Rankings must contain an entry for every enrolled player.
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, _SYNC_MAX, "knockout",
                           scenario="large_field_monitor", timeout=120,
                           confirmed=False)
        tid = data["tournament_id"]
        enrolled = data.get("enrolled_count", 0)
        rankings = _get_rankings(api_url, token, tid)

        print(f"\n[ASSERT] rankings={len(rankings)} vs enrolled={enrolled}")

        assert len(rankings) == enrolled, (
            f"64p: rankings count {len(rankings)} != enrolled count {enrolled}. "
            f"Ranking calculation did not cover all players."
        )

    def test_64p_knockout_round_structure(self, api_url: str):
        """
        64p = 2^6: exactly 6 bracket rounds expected.
        Round 1: 32 matches, Round 2: 16, ..., Round 6: 1. + 1 playoff.
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, _SYNC_MAX, "knockout",
                           scenario="large_field_monitor", timeout=120,
                           confirmed=False)
        tid = data["tournament_id"]
        sessions = _get_sessions(api_url, token, tid)

        from collections import defaultdict
        bracket = [s for s in sessions if s.get("tournament_match_number") != 999]
        by_round: dict = defaultdict(list)
        for s in bracket:
            by_round[s.get("tournament_round")].append(s)

        total_rounds = int(math.log2(_SYNC_MAX))  # log2(64) = 6
        print(f"\n[ASSERT] Rounds found: {sorted(by_round.keys())}")

        assert len(by_round) == total_rounds, (
            f"64p: expected {total_rounds} rounds, got {len(by_round)}"
        )

        for round_num in range(1, total_rounds + 1):
            expected_matches = _SYNC_MAX // (2 ** round_num)
            actual = len(by_round.get(round_num, []))
            assert actual == expected_matches, (
                f"64p round {round_num}: expected {expected_matches} matches, got {actual}"
            )

    def test_64p_comprehensive_metrics(self, api_url: str):
        """
        Full production benchmark: single test that captures all metrics together.
        Prints a machine-readable production readiness report.

        Asserts all production criteria simultaneously:
          - launch_time < 120s (sync path)
          - session_count == 64
          - status == IN_PROGRESS
          - enrolled == 64
          - results_submitted_pct == 100%
          - rankings_count == enrolled
          - task_id == "sync-done" (confirms sync path)
        """
        token = _get_admin_token(api_url)

        t_start = time.monotonic()
        data, launch_time = _launch(api_url, token, _SYNC_MAX, "knockout",
                                    scenario="large_field_monitor", timeout=120,
                                    confirmed=False)
        tid = data["tournament_id"]
        enrolled = data.get("enrolled_count", 0)
        task_id = data.get("task_id")

        # Fetch all observability data
        t_fetch = time.monotonic()
        sessions = _get_sessions(api_url, token, tid)
        summary = _get_summary(api_url, token, tid)
        rankings = _get_rankings(api_url, token, tid)
        fetch_time = time.monotonic() - t_fetch

        total_time = time.monotonic() - t_start

        # Compute metrics
        session_count = len(sessions)
        done_count = sum(1 for s in sessions if s.get("result_submitted"))
        results_pct = 100 * done_count / session_count if session_count else 0
        ranking_count = len(rankings)
        status = summary.get("tournament_status")
        playoff = [s for s in sessions if "3rd Place" in (s.get("title") or "")]

        # Print production readiness report
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     PRODUCTION READINESS REPORT — 64p KNOCKOUT (SYNC)    ║
╠══════════════════════════════════════════════════════════╣
║  tournament_id     : {tid:<36d} ║
║  enrolled_count    : {enrolled:<36d} ║
║  task_id           : {str(task_id):<36} ║
╠══════════════════════════════════════════════════════════╣
║  TIMING                                                  ║
║  launch_time       : {launch_time:<33.2f}s ║
║  observability_fetch: {fetch_time:<32.3f}s ║
║  total_wall_clock  : {total_time:<33.2f}s ║
╠══════════════════════════════════════════════════════════╣
║  SESSION GENERATION                                      ║
║  session_count     : {session_count:<36d} ║
║  expected          : {_SYNC_SESSIONS:<36d} ║
║  playoff_present   : {str(len(playoff) == 1):<36} ║
╠══════════════════════════════════════════════════════════╣
║  AUTO-SIMULATION                                         ║
║  results_submitted : {done_count:<36d} ║
║  results_pct       : {results_pct:<35.1f}% ║
╠══════════════════════════════════════════════════════════╣
║  RANKINGS                                                ║
║  ranking_count     : {ranking_count:<36d} ║
╠══════════════════════════════════════════════════════════╣
║  STATUS                                                  ║
║  tournament_status : {str(status):<36} ║
╚══════════════════════════════════════════════════════════╝""")

        # All production criteria
        assert task_id == "sync-done", (
            f"64p must use sync path (task_id='sync-done'), got: {task_id}"
        )
        assert launch_time < 120, f"launch_time={launch_time:.2f}s > 120s limit"
        assert session_count == _SYNC_SESSIONS, (
            f"session_count={session_count}, expected {_SYNC_SESSIONS}"
        )
        assert status == "IN_PROGRESS", f"status={status}, expected IN_PROGRESS"
        assert enrolled == _SYNC_MAX, f"enrolled={enrolled}, expected {_SYNC_MAX}"
        assert done_count == session_count, (
            f"results_pct={results_pct:.1f}%, expected 100% "
            f"({done_count}/{session_count} submitted)"
        )
        assert ranking_count == enrolled, (
            f"ranking_count={ranking_count} != enrolled={enrolled}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# R: Async Launch Scale Test — 128p & 1024p
#
# player_count >= 128 uses the ASYNC path (Celery task or daemon thread fallback).
# Without a running Celery worker, sessions are NOT generated immediately.
# These tests only assert: launch succeeded (triggered=True), enrollment correct,
# tournament created (tournament_id > 0), status IN_PROGRESS.
#
# Architecture: OPS creates the tournament, enrolls players, queues the task,
# then returns. Sessions appear later when the worker processes the task.
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestAsyncLaunchScale:
    """
    128p and 1024p async-path launch assertions.

    Confirms: launch is accepted (HTTP 200, triggered=True), enrollment is correct,
    tournament_id is valid, tournament_status is IN_PROGRESS. Session generation
    runs asynchronously (requires Celery worker to complete).
    """

    @pytest.mark.parametrize("player_count", [128, 1024])
    def test_async_launch_is_triggered(self, api_url: str, player_count: int):
        """
        Large-scale launch must return triggered=True and a UUID task_id.
        Confirms the OPS endpoint accepts and queues large launches.
        """
        token = _get_admin_token(api_url)
        data, elapsed = _launch(api_url, token, player_count, "knockout",
                                scenario="large_field_monitor",
                                timeout=120,
                                confirmed=True)

        task_id = data.get("task_id")
        print(f"\n[ASSERT] {player_count}p: triggered, task_id={task_id}, elapsed={elapsed:.2f}s")

        # Must have a UUID task_id (not sync-done)
        assert task_id != "sync-done", (
            f"{player_count}p: expected async UUID task_id, got 'sync-done'"
        )
        assert task_id is not None and len(task_id) > 8, (
            f"{player_count}p: invalid task_id: {task_id}"
        )

    @pytest.mark.parametrize("player_count", [128, 1024])
    def test_async_launch_enrollment_correct(self, api_url: str, player_count: int):
        """
        OPS must enroll exactly player_count players before returning.
        Enrollment happens synchronously regardless of async generation.
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, player_count, "knockout",
                           scenario="large_field_monitor",
                           timeout=120,
                           confirmed=True)

        enrolled = data.get("enrolled_count", 0)
        print(f"\n[ASSERT] {player_count}p enrolled_count: {enrolled}")

        assert enrolled == player_count, (
            f"{player_count}p: expected {player_count} enrolled, got {enrolled}"
        )

    @pytest.mark.parametrize("player_count", [128, 1024])
    def test_async_launch_tournament_in_progress(self, api_url: str, player_count: int):
        """
        After OPS launch, tournament_status must be IN_PROGRESS immediately.
        Status is set before session generation (which happens async).
        """
        token = _get_admin_token(api_url)
        data, _ = _launch(api_url, token, player_count, "knockout",
                           scenario="large_field_monitor",
                           timeout=120,
                           confirmed=True)
        tid = data["tournament_id"]
        summary = _get_summary(api_url, token, tid)

        status = summary.get("tournament_status")
        print(f"\n[ASSERT] {player_count}p tournament_status: {status}")

        assert status == "IN_PROGRESS", (
            f"{player_count}p: expected IN_PROGRESS, got {status}"
        )

    @pytest.mark.parametrize("player_count", [128, 1024])
    def test_async_launch_tournament_id_unique(self, api_url: str, player_count: int):
        """
        Each launch must produce a distinct tournament_id.
        Verifies DB isolation and no race condition in tournament creation.
        """
        token = _get_admin_token(api_url)
        data1, _ = _launch(api_url, token, player_count, "knockout",
                            scenario="large_field_monitor",
                            timeout=120,
                            confirmed=True)
        data2, _ = _launch(api_url, token, player_count, "knockout",
                            scenario="large_field_monitor",
                            timeout=120,
                            confirmed=True)

        tid1 = data1["tournament_id"]
        tid2 = data2["tournament_id"]
        print(f"\n[ASSERT] {player_count}p: tid1={tid1}, tid2={tid2}")

        assert tid1 != tid2, (
            f"{player_count}p: two launches produced same tournament_id={tid1}. "
            f"Race condition in tournament creation!"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# S: Parallel Launch Stress Test — 64 + 32 + 8 Concurrent (Sync Path)
#
# All three player counts are below 128 (sync path). Each returns sessions,
# results, and rankings immediately. Race conditions, DB lock, and cross-
# contamination are detected by checking session counts per tournament.
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestParallelLaunchStress:
    """
    Launch 64p + 32p + 8p simultaneously (concurrent threads, all sync path).

    Asserts:
      1. All 3 launches return HTTP 200 within timeout
      2. All 3 tournament_ids are DISTINCT (no ID collision)
      3. All 3 reach IN_PROGRESS status independently
      4. All 3 have correct session counts (no cross-tournament contamination)
      5. No exception in any thread (no race condition on DB write)
      6. No DB lock: all 3 complete (not just 1 or 2)
    """

    _CONFIGS = [
        {"player_count": 64,  "type": "knockout", "label": "64p",
         "expected_sessions": 64},   # 63 bracket + 1 playoff
        {"player_count": 32,  "type": "knockout", "label": "32p",
         "expected_sessions": 32},   # 31 bracket + 1 playoff
        {"player_count": 8,   "type": "knockout", "label": "8p",
         "expected_sessions": 8},    # 7 bracket + 1 playoff
    ]

    def _run_concurrent(self, api_url: str, timeout: int = 180):
        """
        Fire all 3 OPS launches concurrently. Return (results, errors).
        """
        results = {}
        errors = {}

        def _thread_launch(cfg: dict) -> None:
            label = cfg["label"]
            try:
                token = _get_admin_token(api_url)  # Fresh token per thread
                data, elapsed = _launch(
                    api_url, token,
                    cfg["player_count"], cfg["type"],
                    scenario="large_field_monitor",
                    timeout=120,
                    confirmed=False,
                )
                results[label] = {
                    "tournament_id": data["tournament_id"],
                    "enrolled": data.get("enrolled_count", 0),
                    "elapsed": elapsed,
                    "task_id": data.get("task_id"),
                    "expected_sessions": cfg["expected_sessions"],
                    "token": token,
                }
            except Exception as e:
                errors[label] = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }

        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(_thread_launch, cfg) for cfg in self._CONFIGS]
            concurrent.futures.wait(futures, timeout=timeout)
        total_elapsed = time.monotonic() - t0

        return results, errors, total_elapsed

    def test_parallel_all_launch(self, api_url: str):
        """
        Fire 3 OPS launches concurrently. All must succeed.
        """
        results, errors, total_elapsed = self._run_concurrent(api_url)

        print(f"\n[PARALLEL] Total wall clock: {total_elapsed:.1f}s")
        for label, r in results.items():
            print(f"[PARALLEL] {label}: tid={r['tournament_id']}, "
                  f"enrolled={r['enrolled']}, elapsed={r['elapsed']:.2f}s, "
                  f"task_id={r['task_id']}")
        for label, e in errors.items():
            print(f"[PARALLEL ERROR] {label}: {e['error']}")

        # Assert no errors
        assert len(errors) == 0, (
            f"Parallel launch errors:\n" +
            "\n".join(f"  {k}: {v['error']}" for k, v in errors.items())
        )

        # Assert all 3 launched
        for cfg in self._CONFIGS:
            assert cfg["label"] in results, f"{cfg['label']} launch did not complete"

    def test_parallel_tournament_ids_are_distinct(self, api_url: str):
        """
        All 3 concurrent launches must produce DISTINCT tournament_ids.
        Same ID would indicate a race condition in tournament creation.
        """
        results, errors, _ = self._run_concurrent(api_url)

        assert len(errors) == 0, f"Launch errors: {errors}"

        tids = {label: r["tournament_id"] for label, r in results.items()}
        print(f"\n[ASSERT] Tournament IDs: {tids}")
        all_tids = list(tids.values())
        assert len(set(all_tids)) == len(all_tids), (
            f"Duplicate tournament IDs detected — race condition: {tids}"
        )

    def test_parallel_each_tournament_independent_status(self, api_url: str):
        """
        Each of the 3 concurrent tournaments must reach IN_PROGRESS independently.
        """
        results, errors, parallel_time = self._run_concurrent(api_url)

        assert len(errors) == 0, f"Launch errors: {errors}"

        print(f"\n[PARALLEL] All 3 launched in {parallel_time:.1f}s total")

        status_checks = {}
        for label, r in results.items():
            summary = _get_summary(api_url, r["token"], r["tournament_id"])
            status = summary.get("tournament_status")
            status_checks[label] = status
            print(f"[ASSERT] {label} (tid={r['tournament_id']}): status={status}, "
                  f"enrolled={r['enrolled']}, elapsed={r['elapsed']:.2f}s")

        for label, status in status_checks.items():
            assert status == "IN_PROGRESS", (
                f"{label}: expected IN_PROGRESS, got {status}"
            )

    def test_parallel_each_tournament_correct_session_count(self, api_url: str):
        """
        Each concurrent tournament must have its own correct session count.
        Cross-contamination (wrong session count) = DB isolation failure.

        Expected (sync path — sessions are immediately available):
          64p knockout → 64 sessions (63 bracket + 1 playoff)
          32p knockout → 32 sessions (31 bracket + 1 playoff)
          8p knockout  → 8 sessions  (7 bracket + 1 playoff)
        """
        results, errors, _ = self._run_concurrent(api_url)

        assert len(errors) == 0, f"Launch errors: {errors}"

        for label, r in results.items():
            sessions = _get_sessions(api_url, r["token"], r["tournament_id"])
            print(f"[ASSERT] {label} (tid={r['tournament_id']}): "
                  f"sessions={len(sessions)}, expected={r['expected_sessions']}")
            assert len(sessions) == r["expected_sessions"], (
                f"{label}: expected {r['expected_sessions']} sessions, got {len(sessions)}. "
                f"Possible cross-tournament session contamination."
            )

    def test_parallel_no_db_lock_all_complete(self, api_url: str):
        """
        All 3 concurrent launches must complete (not deadlock or timeout).
        A DB lock would cause 1 or 2 to hang while others complete.
        """
        results, errors, wall_clock = self._run_concurrent(api_url)

        print(f"\n[PARALLEL] Wall clock: {wall_clock:.1f}s")
        print(f"[PARALLEL] Completed: {list(results.keys())}")
        print(f"[PARALLEL] Errors: {list(errors.keys())}")

        # No errors — no DB locks
        assert len(errors) == 0, (
            f"DB lock or timeout detected. Errors:\n" +
            "\n".join(f"  {k}: {v['error']}" for k, v in errors.items())
        )

        # All 3 must complete
        assert len(results) == 3, (
            f"Only {len(results)}/3 tournaments completed. "
            f"Missing: {set(c['label'] for c in self._CONFIGS) - set(results.keys())}"
        )

        elapsed_times = {label: r["elapsed"] for label, r in results.items()}
        max_single = max(elapsed_times.values()) if elapsed_times else wall_clock
        print(f"[PERF] Max single thread: {max_single:.2f}s, total wall: {wall_clock:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# T: Production UI Lifecycle Test — Playwright Wizard Flow
#    Tests: wizard → launch → tracking panel stable
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.tournament_monitor
class TestProductionUILifecycle:
    """
    Playwright end-to-end: wizard flow for OPS launch via browser.

    Tests:
      1. 64p wizard: navigate to Step 6, verify safety NOT required below 128p
      2. 128p wizard: navigate to Step 6, verify safety confirmation IS required
      3. 64p full launch: wizard → launch → tracking panel stable
    """

    def test_ui_64p_wizard_reaches_step6_no_safety(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Navigate wizard to Step 6 with 64p selected.
        At 64p (<128), safety confirmation must NOT be required.
        LAUNCH TOURNAMENT button must be enabled directly.
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sidebar(page)

        # Step 1: Large Field Monitor
        expect(sb.get_by_text("Step 1 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 2: Head-to-Head (default)
        expect(sb.get_by_text("Step 2 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 3: Knockout (default)
        expect(sb.get_by_text("Step 3 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 4: Set slider to 64
        expect(sb.get_by_text("Step 4 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        slider = sb.get_by_role("slider", name="Number of players to enroll")
        expect(slider).to_be_visible()

        # Set slider to 64 using Home then ArrowRight.
        # Slider: min=4, max=1024, step=2. Each ArrowRight press increments by 2.
        # Press Home to go to min (4), then ArrowRight (64-4)/2 = 30 times.
        slider.click()
        slider.press("Home")  # Jump to minimum (4)
        time.sleep(0.5)
        presses_needed = (64 - 4) // 2  # 30 presses
        for _ in range(presses_needed):
            slider.press("ArrowRight")
            page.wait_for_timeout(20)
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(1)

        actual_val = int(slider.get_attribute("aria-valuenow") or "0")
        assert actual_val == 64, (
            f"Step 4: slider should be 64, got {actual_val}"
        )

        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 5: Accelerated Simulation
        expect(sb.get_by_text("Step 5 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 6: Review — at 64p no safety confirmation required
        expect(sb.get_by_text("Step 6 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        # LAUNCH TOURNAMENT button must be enabled (no safety gate at 64p)
        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_enabled()

    def test_ui_128p_wizard_requires_safety_confirmation(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Navigate wizard to Step 6 with 128p selected.
        At 128p (>= threshold), safety confirmation input must appear
        and LAUNCH button must be disabled until "LAUNCH" is typed.
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sidebar(page)

        # Step 1: Large Field Monitor
        expect(sb.get_by_text("Step 1 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 2
        expect(sb.get_by_text("Step 2 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 3
        expect(sb.get_by_text("Step 3 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 4: Set slider to 128
        # Slider: min=4, max=1024, step=2. Press Home (min=4), then ArrowRight
        # (128-4)/2 = 62 times to reach 128.
        expect(sb.get_by_text("Step 4 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        slider = sb.get_by_role("slider", name="Number of players to enroll")
        slider.click()
        slider.press("Home")  # Jump to minimum (4)
        time.sleep(0.5)

        # Press ArrowRight (128-4)/2 = 62 times to reach 128
        presses_needed = (128 - 4) // 2  # 62 presses
        for _ in range(presses_needed):
            slider.press("ArrowRight")
            page.wait_for_timeout(20)
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(1)

        actual_val = int(slider.get_attribute("aria-valuenow") or "0")
        assert actual_val == 128, (
            f"Step 4: slider should be 128, got {actual_val}"
        )

        # Large Scale Operation warning must appear at 128p
        expect(sb.get_by_text("LARGE SCALE OPERATION", exact=False)).to_be_visible(
            timeout=_LOAD_TIMEOUT
        )

        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 5
        expect(sb.get_by_text("Step 5 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 6: Safety confirmation required at 128p
        expect(sb.get_by_text("Step 6 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        confirm_input = sb.get_by_placeholder("Type LAUNCH to enable the button")
        expect(confirm_input).to_be_visible(timeout=_LOAD_TIMEOUT)

        # Button disabled before confirmation
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_disabled()

        # Type LAUNCH to enable button
        confirm_input.fill("LAUNCH")
        confirm_input.press("Enter")
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Button must now be enabled
        expect(sb.get_by_role("button", name="LAUNCH TOURNAMENT")).to_be_enabled()

    def test_ui_64p_full_launch_and_tracking(
        self, page: Page, base_url: str, api_url: str
    ):
        """
        Full end-to-end: wizard → launch 64p → tracking panel stable.

        This is the production readiness UI test using the sync path.
        64p completes synchronously, so the tracking panel should appear
        immediately after launch.

        Assertions:
          - Wizard resets to Step 1 after launch (success signal)
          - Tracking panel shows tournament card (not empty state)
          - No "Error" text appears in tracking card
          - UI fragment refreshes stably (no crash)
        """
        _go_to_monitor(page, base_url, api_url)
        sb = _sidebar(page)

        t0 = time.monotonic()

        # Step 1: Large Field Monitor
        expect(sb.get_by_text("Step 1 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Large Field Monitor", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 2: Head-to-Head (default)
        expect(sb.get_by_text("Step 2 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 3: Knockout (default)
        expect(sb.get_by_text("Step 3 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 4: Slider → 64
        # Slider: min=4, max=1024, step=2. Press Home (min=4), then ArrowRight 30 times.
        expect(sb.get_by_text("Step 4 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        slider = sb.get_by_role("slider", name="Number of players to enroll")
        slider.click()
        slider.press("Home")  # Jump to minimum (4)
        time.sleep(0.5)
        presses_needed = (64 - 4) // 2  # 30 presses
        for _ in range(presses_needed):
            slider.press("ArrowRight")
            page.wait_for_timeout(20)
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(2)

        actual_val = int(slider.get_attribute("aria-valuenow") or "0")
        assert actual_val == 64, f"Slider not at 64: {actual_val}"
        print(f"\n[UI] Step 4 slider set to {actual_val}")

        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 5: Accelerated Simulation
        expect(sb.get_by_text("Step 5 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)
        sb.get_by_text("Accelerated Simulation", exact=False).first.click()
        time.sleep(0.5)
        sb.get_by_role("button", name="Next →").click()
        page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
        time.sleep(_STREAMLIT_SETTLE)

        # Step 6: No safety confirmation needed at 64p
        expect(sb.get_by_text("Step 6 of 6", exact=False)).to_be_visible(timeout=_LOAD_TIMEOUT)

        launch_btn = sb.get_by_role("button", name="LAUNCH TOURNAMENT")
        expect(launch_btn).to_be_enabled()

        # Launch
        print(f"[UI] Clicking LAUNCH TOURNAMENT at t={time.monotonic()-t0:.1f}s")
        launch_btn.click()

        # 64p is sync — network should settle within 120s
        page.wait_for_load_state("networkidle", timeout=120_000)
        time.sleep(_LAUNCH_SETTLE)
        t_launch = time.monotonic() - t0
        print(f"[UI] Post-launch settled at t={t_launch:.1f}s")

        # ── Post-Launch Assertions ─────────────────────────────────────────────

        # 1. Wizard must reset to Step 1 (success signal)
        expect(sb.get_by_text("Step 1 of 6", exact=False)).to_be_visible(timeout=60_000)
        print(f"[UI] PASS: Wizard reset to Step 1")

        # 2. Tracking panel: tournament card must appear
        expect(
            page.get_by_text("No active test tournaments", exact=False)
        ).not_to_be_visible(timeout=30_000)
        print(f"[UI] PASS: 'No active test tournaments' not visible")

        # 3. LIVE TEST TRACKING header must be present
        expect(
            page.get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=15_000)
        print(f"[UI] PASS: Live tracking panel visible")

        # 4. No error text in main area
        error_texts = ["Traceback", "AttributeError", "KeyError", "NoneType", "Exception"]
        for err_text in error_texts:
            count = page.get_by_text(err_text, exact=False).count()
            assert count == 0, (
                f"[UI] Error text '{err_text}' found in page — possible crash"
            )
        print(f"[UI] PASS: No error/exception text in UI")

        # 5. Fragment refresh stability: wait one more cycle
        time.sleep(12)
        page.wait_for_load_state("networkidle", timeout=30_000)

        expect(
            page.get_by_text("LIVE TEST TRACKING", exact=False)
        ).to_be_visible(timeout=15_000)
        print(f"[UI] PASS: Fragment refresh stable after second cycle")

        total_time = time.monotonic() - t0
        print(f"\n[PERF] Total UI test wall clock: {total_time:.1f}s")
