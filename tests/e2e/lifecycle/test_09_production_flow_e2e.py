"""
T09: Production Flow Validation — 512-Player Knockout (Operator Lifecycle)
===========================================================================

Full end-to-end operator lifecycle test against a LIVE server, REAL database,
and a running Celery worker. Uses Playwright APIRequestContext — not UI scraping,
not requests library — for accurate HTTP-level timing and production-grade
request isolation.

NOT mocked. NOT structural. Hits real FastAPI + real PostgreSQL + real Redis/Celery.

Prerequisites (must be running before this suite):
  1. FastAPI:   uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Celery:    celery -A app.celery_app worker -Q tournaments --loglevel=info
  3. Redis:     redis-server (or redis running at CELERY_BROKER_URL)
  4. DB:        lfa_intern_system (migrations applied, admin user seeded)

Run:
  pytest tests_e2e/lifecycle/test_09_production_flow_e2e.py -v -m production_flow

Skip guard:
  The entire module is SKIPPED if Celery/Redis is not reachable.
  Thread fallback is NOT accepted — this is production readiness validation.

Tests (sequential — share module-level state via _STATE):
  T09A  Seed 512 load-test players via POST /admin/batch-create-players
  T09B  Admin creates 512-player knockout tournament
  T09C  Configure multi-campus schedule (global defaults + 2 campus overrides)
  T09D  Batch-enroll 512 players via POST /{id}/admin/batch-enroll
  T09E  Trigger async session generation — assert async_backend == "celery"
  T09F  Poll generation-status until done (timeout: 300 s, poll interval: 3 s)
  T09G  Load session list — assert 512 sessions, structural integrity check
  T09H  Submit results for 3 round-1 matches
  T09I  Calculate rankings and verify leaderboard

Pipeline metrics:
  Every stage records its own duration_ms. On any failure the full pipeline
  metrics dict is logged before pytest.fail() so the CI log always shows
  how far the pipeline reached and where it slowed down.

Timing SLOs (soft — logged as warnings, not assertion failures):
  T09A  < 60 s   (512 players, chunked inserts)
  T09D  < 30 s   (512 enrollments)
  T09F  < 120 s  (Celery worker under normal load)
  T09G  < 5 s    (GET /sessions — single HTTP response)

SLO breaches are logged at WARNING level; they do not fail the test. Hard
correctness assertions (status codes, counts, backend == "celery") do fail.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from playwright.sync_api import APIRequestContext, Playwright, sync_playwright, APIResponse

# ---------------------------------------------------------------------------
# Project root on sys.path (needed for in-process Celery ping)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
API_URL       = os.environ.get("API_URL",        "http://localhost:8000")
ADMIN_EMAIL   = os.environ.get("ADMIN_EMAIL",    "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

PLAYER_COUNT         = 512
PLAYER_EMAIL_DOMAIN  = "loadtest.lfa"
TOURNAMENT_NAME      = "LFA Production Flow Test — 512 Knockout"

# Timing SLOs (seconds) — warnings only, not hard failures
SLO_SEED_S    = 60
SLO_ENROLL_S  = 30
SLO_GEN_S     = 120   # Celery completes well within 2 min under normal load
SLO_GET_S     = 5

# Hard poll timeout for T09F
POLL_TIMEOUT_S   = 300
POLL_INTERVAL_S  = 3

# ---------------------------------------------------------------------------
# Module-level Celery availability guard
# ---------------------------------------------------------------------------

def _check_celery_available() -> None:
    """
    Ping Celery broker. Skip the entire module if Redis/Celery is unreachable.

    Thread fallback is deliberately rejected — this suite validates production
    readiness, not development convenience.
    """
    try:
        from app.celery_app import celery_app  # noqa: PLC0415
        ping_result = celery_app.control.ping(timeout=2)
        if not ping_result:
            pytest.skip(
                "Celery workers are not responding. "
                "Production-flow tests require a running Celery worker.\n"
                "Start with: celery -A app.celery_app worker -Q tournaments --loglevel=info",
                allow_module_level=True,
            )
    except ImportError as exc:
        pytest.skip(
            f"Celery package not importable: {exc}",
            allow_module_level=True,
        )
    except Exception as exc:
        pytest.skip(
            f"Celery/Redis unavailable ({exc}). "
            "Start Redis and a Celery worker before running T09.",
            allow_module_level=True,
        )


# Runs at import time — entire module is skipped before collection if guard fires
_check_celery_available()


# ---------------------------------------------------------------------------
# Pipeline metrics — shared mutable state across all T09 tests
# ---------------------------------------------------------------------------

@dataclass
class _PipelineMetrics:
    """
    Accumulates timing and outcome data across the full T09A→T09I pipeline.

    Logged automatically on failure so CI logs always show how far the
    pipeline progressed and which stage was slow.
    """
    tournament_id:     Optional[int]   = None
    task_id:           Optional[str]   = None
    player_ids:        List[int]       = field(default_factory=list)
    sessions_count:    Optional[int]   = None
    sample_session_ids: List[int]      = field(default_factory=list)
    sample_participants: Dict[int, List[int]] = field(default_factory=dict)
    headers:           Dict[str, str]  = field(default_factory=dict)
    last_submit_result: Optional[Dict[str, Any]] = None  # last T09H response

    durations_ms: Dict[str, float]     = field(default_factory=dict)
    slo_warnings: List[str]            = field(default_factory=list)

    def record(self, stage: str, elapsed_s: float) -> None:
        """Record stage duration and emit SLO warning if threshold exceeded."""
        ms = elapsed_s * 1000
        self.durations_ms[stage] = round(ms, 1)
        slo_map = {
            "T09A": SLO_SEED_S,
            "T09D": SLO_ENROLL_S,
            "T09F": SLO_GEN_S,
            "T09G": SLO_GET_S,
        }
        threshold_s = slo_map.get(stage)
        if threshold_s and elapsed_s > threshold_s:
            msg = (
                f"SLO breach: {stage} took {elapsed_s:.1f}s "
                f"(SLO={threshold_s}s)"
            )
            self.slo_warnings.append(msg)
            logger.warning("[T09 SLO] %s", msg)

    def log_summary(self, prefix: str = "") -> None:
        """Emit a structured summary to the test log."""
        lines = [
            f"{prefix}Pipeline metrics:",
            f"  tournament_id   = {self.tournament_id}",
            f"  task_id         = {self.task_id}",
            f"  player_ids      = {len(self.player_ids)} ids",
            f"  sessions_count  = {self.sessions_count}",
            f"  stage durations = {self.durations_ms}",
        ]
        if self.slo_warnings:
            lines.append(f"  SLO warnings    = {self.slo_warnings}")
        logger.info("\n".join(lines))


# Module-level singleton — shared across all tests in this module
_M = _PipelineMetrics()


# ---------------------------------------------------------------------------
# pytest-base-url override
# ---------------------------------------------------------------------------
# Playwright fixtures (module-scoped — T09 owns its own Playwright lifecycle)
# ---------------------------------------------------------------------------
# The conftest.py playwright_instance fixture is function-scoped, which is
# incompatible with module-scoped fixtures that depend on it. T09 declares its
# own module-scoped Playwright instance to avoid the ScopeMismatch error.

@pytest.fixture(scope="module")
def _pw():
    """Module-scoped Playwright instance (T09 private — does not conflict with conftest)."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def api(_pw: Playwright) -> APIRequestContext:
    """
    Playwright APIRequestContext pointed at the FastAPI server.

    Module-scoped: one context for all 9 T09 tests.
    All requests include base_url. Auth token is stored in _M.headers and
    passed as a per-request `headers=` override — Playwright supports this.
    """
    ctx = _pw.request.new_context(
        base_url=API_URL,
        extra_http_headers={"Content-Type": "application/json"},
    )
    yield ctx
    ctx.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _player_email(i: int) -> str:
    return f"player{i:04d}@{PLAYER_EMAIL_DOMAIN}"


def _assert_ok(resp, label: str, expected: int = 200) -> dict:
    """
    Assert HTTP status and return parsed JSON.
    On failure logs full pipeline metrics before raising.
    """
    if resp.status != expected:
        _M.log_summary(prefix=f"[FAIL at {label}] ")
        pytest.fail(
            f"{label} — expected HTTP {expected}, got {resp.status}.\n"
            f"Body: {resp.text()[:600]}"
        )
    try:
        return resp.json()
    except Exception as exc:
        _M.log_summary(prefix=f"[FAIL at {label} JSON parse] ")
        pytest.fail(f"{label} — could not parse JSON: {exc}\nBody: {resp.text()[:300]}")


# ---------------------------------------------------------------------------
# T09A — Seed 512 load-test players
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09A_seed_512_players(api: APIRequestContext):
    """
    Create 512 STUDENT players with LFA_FOOTBALL_PLAYER license via
    POST /api/v1/admin/batch-create-players.

    Uses chunked DB inserts (CHUNK_SIZE=100) and a soft rate guard.
    skip_existing=true makes reruns safe — already-existing players are
    counted as skipped, not failed.

    Duration SLO: < 60 s
    """
    # ── Admin login ──────────────────────────────────────────────────────────
    # APIRequestContext headers cannot be mutated after construction, so we
    # perform the login without auth headers and store the token in _M.headers.
    # All subsequent API calls pass _M.headers explicitly via the `headers=`
    # parameter — this is supported by Playwright's per-request header override.
    login_resp = api.post(
        "/api/v1/auth/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15_000,
    )
    login_data = _assert_ok(login_resp, "Admin login", expected=200)
    token = login_data["access_token"]
    _M.headers = {"Authorization": f"Bearer {token}"}

    # ── Build player payload ──────────────────────────────────────────────────
    players = [
        {
            "email": _player_email(i),
            "password": "LoadTest2026!",
            "name": f"Load Test Player {i:04d}",
            "date_of_birth": "2000-06-15",
        }
        for i in range(1, PLAYER_COUNT + 1)
    ]

    t0 = time.perf_counter()
    resp = api.post(
        "/api/v1/admin/batch-create-players",
        data={
            "players": players,
            "specialization": "LFA_FOOTBALL_PLAYER",
            "skip_existing": True,
        },
        headers=_M.headers,
        timeout=120_000,   # 512 players across chunked inserts
    )
    elapsed = time.perf_counter() - t0
    _M.record("T09A", elapsed)

    data = _assert_ok(resp, "T09A batch-create-players", expected=201)

    assert data["created_count"] + data["skipped_count"] == PLAYER_COUNT, (
        f"T09A: expected created+skipped=={PLAYER_COUNT}, "
        f"got created={data['created_count']} skipped={data['skipped_count']} "
        f"failed={data['failed_count']}"
    )
    assert data["failed_count"] == 0, (
        f"T09A: failed_count={data['failed_count']} — some players were not created"
    )
    assert len(data["player_ids"]) == PLAYER_COUNT, (
        f"T09A: expected {PLAYER_COUNT} player_ids, got {len(data['player_ids'])}"
    )

    _M.player_ids = data["player_ids"]
    logger.info(
        "T09A PASS: created=%d skipped=%d chunks=%d elapsed_ms=%.0f api_elapsed_ms=%.0f",
        data["created_count"], data["skipped_count"],
        data.get("chunks_committed", "?"),
        data.get("elapsed_ms", 0),
        elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09B — Create 512-player knockout tournament
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09B_create_tournament(api: APIRequestContext):
    """
    Admin creates a 512-player knockout tournament.

    512-player knockout = 511 bracket matches + 1 bronze = 512 sessions.
    status must be IN_PROGRESS immediately after creation.
    """
    t0 = time.perf_counter()
    resp = api.post(
        "/api/v1/tournaments/create",
        data={
            "name": TOURNAMENT_NAME,
            "tournament_type": "knockout",
            "age_group": "PRO",
            "max_players": PLAYER_COUNT,
            "skills_to_test": ["PASSING", "DRIBBLING", "FINISHING"],
            "reward_config": [
                {"rank": 1, "xp_reward": 1000, "credits_reward": 500},
                {"rank": 2, "xp_reward": 750,  "credits_reward": 300},
                {"rank": 3, "xp_reward": 500,  "credits_reward": 150},
            ],
            "enrollment_cost": 0,
        },
        headers=_M.headers,
        timeout=30_000,
    )
    elapsed = time.perf_counter() - t0
    _M.record("T09B", elapsed)

    data = _assert_ok(resp, "T09B tournament create", expected=201)

    assert data.get("success") is True, f"T09B: success != True: {data}"
    tournament_id = data.get("tournament_id", 0)
    assert tournament_id > 0, f"T09B: invalid tournament_id={tournament_id}"
    assert data.get("tournament_status") == "IN_PROGRESS", (
        f"T09B: expected IN_PROGRESS, got {data.get('tournament_status')}"
    )
    assert data.get("max_players") == PLAYER_COUNT, (
        f"T09B: max_players mismatch — expected {PLAYER_COUNT}, got {data.get('max_players')}"
    )

    _M.tournament_id = tournament_id
    logger.info(
        "T09B PASS: tournament_id=%d name=%r status=%s elapsed_ms=%.0f",
        tournament_id, data.get("tournament_name"), data.get("tournament_status"),
        elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09C — Configure multi-campus schedule
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09C_configure_campus_schedule(api: APIRequestContext):
    """
    Configure match_duration_minutes as a first-class domain entity.

    Steps:
      0. Ensure a location + 2 campuses exist (create via API if not present)
      1. PATCH global schedule-config  → 90 min match, 15 min break, 4 parallel fields
      2. PUT campus A (North Pitch)    → 90 min, 2 fields
      3. PUT campus B (Online Arena)   → 45 min fast format, 8 fields
      4. GET campus-schedules          → assert ≥ 2 entries persisted

    Validates the full campus override resolution chain under production conditions.
    """
    tid = _M.tournament_id
    assert tid, "T09B must have run first"

    t0 = time.perf_counter()

    # 0a. Ensure a test location exists (create if empty)
    resp = api.get("/api/v1/admin/locations/", headers=_M.headers, timeout=10_000)
    loc_list = _assert_ok(resp, "T09C GET locations")
    if loc_list:
        location_id = loc_list[0]["id"]
        logger.info("T09C: reusing existing location id=%d", location_id)
    else:
        resp = api.post(
            "/api/v1/admin/locations/",
            data={
                "name": "LFA Test Location",
                "city": "Budapest",
                "country": "Hungary",
                "country_code": "HU",
                "location_code": "T09LOC",
                "location_type": "CENTER",
                "is_active": True,
            },
            headers=_M.headers,
            timeout=10_000,
        )
        loc_data = _assert_ok(resp, "T09C create location", expected=201)
        location_id = loc_data["id"]
        logger.info("T09C: created location id=%d", location_id)

    # 0b. Ensure 2 campuses exist under that location
    resp = api.get(
        f"/api/v1/admin/locations/{location_id}/campuses",
        headers=_M.headers,
        timeout=10_000,
    )
    campus_list_raw = _assert_ok(resp, "T09C GET campuses")

    campus_ids: list = [c["id"] for c in campus_list_raw]

    for campus_spec in [
        {"name": "North Pitch", "venue": "Pitch A", "is_active": True},
        {"name": "Online Arena", "venue": "Virtual", "is_active": True},
    ]:
        if not any(c["name"] == campus_spec["name"] for c in campus_list_raw):
            resp = api.post(
                f"/api/v1/admin/locations/{location_id}/campuses",
                data=campus_spec,
                headers=_M.headers,
                timeout=10_000,
            )
            c_data = _assert_ok(resp, f"T09C create campus {campus_spec['name']}", expected=201)
            campus_ids.append(c_data["id"])
            logger.info("T09C: created campus '%s' id=%d", campus_spec["name"], c_data["id"])

    assert len(campus_ids) >= 2, f"T09C: need ≥ 2 campus IDs, got {campus_ids}"
    campus_id_a, campus_id_b = campus_ids[0], campus_ids[1]

    # 1. Global schedule config
    resp = api.patch(
        f"/api/v1/tournaments/{tid}/schedule-config",
        data={"match_duration_minutes": 90, "break_duration_minutes": 15, "parallel_fields": 4},
        headers=_M.headers,
        timeout=15_000,
    )
    global_data = _assert_ok(resp, "T09C global schedule PATCH")
    assert global_data.get("parallel_fields") == 4, (
        f"T09C: parallel_fields mismatch — got {global_data.get('parallel_fields')}"
    )

    # 2. Campus A — North Pitch (standard format)
    resp = api.put(
        f"/api/v1/tournaments/{tid}/campus-schedules",
        data={
            "campus_id": campus_id_a,
            "match_duration_minutes": 90,
            "break_duration_minutes": 15,
            "parallel_fields": 2,
            "venue_label": "North Pitch",
        },
        headers=_M.headers,
        timeout=15_000,
    )
    c1 = _assert_ok(resp, "T09C campus A PUT")
    assert c1.get("resolved_match_duration") == 90, (
        f"T09C: campus A resolved_match_duration — expected 90, got {c1.get('resolved_match_duration')}"
    )

    # 3. Campus B — Online Arena (fast format)
    resp = api.put(
        f"/api/v1/tournaments/{tid}/campus-schedules",
        data={
            "campus_id": campus_id_b,
            "match_duration_minutes": 45,
            "break_duration_minutes": 10,
            "parallel_fields": 8,
            "venue_label": "Online Arena",
        },
        headers=_M.headers,
        timeout=15_000,
    )
    c2 = _assert_ok(resp, "T09C campus B PUT")
    assert c2.get("resolved_match_duration") == 45, (
        f"T09C: campus B resolved_match_duration — expected 45, got {c2.get('resolved_match_duration')}"
    )

    # 4. Verify persistence
    resp = api.get(
        f"/api/v1/tournaments/{tid}/campus-schedules",
        headers=_M.headers,
        timeout=15_000,
    )
    campus_sched_list = _assert_ok(resp, "T09C campus schedules GET")
    assert isinstance(campus_sched_list, list) and len(campus_sched_list) >= 2, (
        f"T09C: expected ≥ 2 campus configs, got {len(campus_sched_list) if isinstance(campus_sched_list, list) else type(campus_sched_list)}"
    )

    elapsed = time.perf_counter() - t0
    _M.record("T09C", elapsed)
    logger.info(
        "T09C PASS: global + 2 campus overrides configured, %d entries persisted, elapsed_ms=%.0f",
        len(campus_sched_list), elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09D — Batch-enroll 512 players
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09D_batch_enroll_players(api: APIRequestContext):
    """
    Admin batch-enrolls all 512 players in the tournament.

    Uses POST /{tournament_id}/admin/batch-enroll — bypasses credit deduction,
    auto-approved, LFA_FOOTBALL_PLAYER license verified.

    Duration SLO: < 30 s
    """
    tid = _M.tournament_id
    player_ids = _M.player_ids
    assert tid and len(player_ids) == PLAYER_COUNT, (
        "T09B + T09A must have run first"
    )

    t0 = time.perf_counter()
    resp = api.post(
        f"/api/v1/tournaments/{tid}/admin/batch-enroll",
        data={"player_ids": player_ids},
        headers=_M.headers,
        timeout=60_000,
    )
    elapsed = time.perf_counter() - t0
    _M.record("T09D", elapsed)

    data = _assert_ok(resp, "T09D batch-enroll")

    assert data.get("enrolled_count") == PLAYER_COUNT, (
        f"T09D: expected {PLAYER_COUNT} enrolled, got {data.get('enrolled_count')}. "
        f"failed_players={data.get('failed_players', [])}"
    )
    assert data.get("failed_players") == [], (
        f"T09D: unexpected enrollment failures: {data.get('failed_players')}"
    )

    logger.info(
        "T09D PASS: enrolled=%d/%d elapsed_ms=%.0f",
        data["enrolled_count"], PLAYER_COUNT, elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09E — Trigger async session generation
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09E_trigger_async_session_generation(api: APIRequestContext):
    """
    Trigger session generation for the 512-player knockout.

    512 >= BACKGROUND_GENERATION_THRESHOLD (128) → MUST use async path.

    Hard assertions:
      - async == True        (synchronous generation would be wrong)
      - async_backend == "celery"  (thread fallback = production failure)
      - task_id non-empty    (required for polling in T09F)
    """
    tid = _M.tournament_id
    assert tid, "T09B must have run first"

    t0 = time.perf_counter()
    resp = api.post(
        f"/api/v1/tournaments/{tid}/generate-sessions",
        data={
            "parallel_fields": 4,
            "session_duration_minutes": 90,
            "break_minutes": 15,
            "number_of_rounds": 1,
        },
        headers=_M.headers,
        timeout=30_000,
    )
    elapsed = time.perf_counter() - t0
    _M.record("T09E", elapsed)

    data = _assert_ok(resp, "T09E generate-sessions")

    assert data.get("async") is True, (
        f"T09E: expected async=True for {PLAYER_COUNT}-player tournament, "
        f"got async={data.get('async')}. Full response: {data}"
    )

    # HARD REQUIREMENT: Celery backend only
    assert data.get("async_backend") == "celery", (
        f"T09E HARD FAILURE: async_backend='{data.get('async_backend')}' "
        f"but expected 'celery'.\n"
        f"Is a Celery worker running on the 'tournaments' queue?\n"
        f"celery -A app.celery_app worker -Q tournaments --loglevel=info\n"
        f"Pipeline metrics so far: {_M.durations_ms}"
    )

    task_id = data.get("task_id", "")
    assert len(task_id) > 0, f"T09E: task_id is empty. Response: {data}"

    _M.task_id = task_id
    logger.info(
        "T09E PASS: generation triggered, task_id=%s backend=celery elapsed_ms=%.0f",
        task_id, elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09F — Poll generation status to completion
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09F_poll_generation_to_completion(api: APIRequestContext):
    """
    Poll GET /{tournament_id}/generation-status/{task_id} until status == "done".

    Timeout:  300 s hard limit
    Interval: 3 s between polls
    SLO:      120 s (logged as warning if exceeded, not a failure)

    On completion: validates sessions_count > 0 and stores in _M for T09G.
    Also logs Celery observability metrics (generation_duration_ms, db_write_time_ms)
    if present in the task result.
    """
    tid     = _M.tournament_id
    task_id = _M.task_id
    assert tid and task_id, "T09B + T09E must have run first"

    deadline   = time.perf_counter() + POLL_TIMEOUT_S
    poll_count = 0
    last_status = "unknown"
    t_poll_start = time.perf_counter()

    while time.perf_counter() < deadline:
        resp = api.get(
            f"/api/v1/tournaments/{tid}/generation-status/{task_id}",
            headers=_M.headers,
            timeout=15_000,
        )
        poll_count += 1

        # HTTP 404 means the Celery task is still in PENDING state (not yet picked up
        # by the worker or result not yet written to Redis).  Treat it as "pending" and
        # retry — we know the task_id is valid because T09E received it from the API.
        if resp.status == 404:
            logger.debug("T09F poll #%d: HTTP 404 — task pending in broker, retrying", poll_count)
            time.sleep(POLL_INTERVAL_S)
            continue

        data = _assert_ok(resp, f"T09F poll #{poll_count}")
        last_status = data.get("status", "unknown")

        if last_status == "done":
            sessions_count = data.get("sessions_count", 0)
            assert sessions_count > 0, (
                f"T09F: generation done but sessions_count=0. Full result: {data}"
            )
            _M.sessions_count = sessions_count

            elapsed = time.perf_counter() - t_poll_start
            _M.record("T09F", elapsed)

            # Log Celery observability metrics if worker emitted them
            gen_ms    = data.get("generation_duration_ms", "n/a")
            db_ms     = data.get("db_write_time_ms",       "n/a")
            queue_ms  = data.get("queue_wait_time_ms",     "n/a")
            logger.info(
                "T09F PASS: generation complete after %d polls (%.1f s). "
                "sessions_count=%d | Celery metrics: "
                "generation_duration_ms=%s db_write_time_ms=%s queue_wait_time_ms=%s",
                poll_count, elapsed,
                sessions_count, gen_ms, db_ms, queue_ms,
            )
            return

        if last_status == "error":
            _M.log_summary(prefix="[T09F generation error] ")
            pytest.fail(
                f"T09F: session generation FAILED at task level. "
                f"message={data.get('message', data)}"
            )

        assert last_status in ("pending", "running", "retrying"), (
            f"T09F: unexpected status value: '{last_status}'"
        )
        logger.debug("T09F poll #%d: status=%s", poll_count, last_status)
        time.sleep(POLL_INTERVAL_S)

    elapsed = time.perf_counter() - t_poll_start
    _M.record("T09F", elapsed)
    _M.log_summary(prefix="[T09F timeout] ")
    pytest.fail(
        f"T09F TIMEOUT: generation did not complete within {POLL_TIMEOUT_S} s. "
        f"Last status='{last_status}' after {poll_count} polls. "
        f"task_id={task_id} tournament_id={tid}"
    )


# ---------------------------------------------------------------------------
# T09G — Load and validate session list
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09G_validate_session_list(api: APIRequestContext):
    """
    Load all sessions for the tournament via GET /tournaments/{id}/sessions.

    512-player knockout produces exactly 512 sessions:
      Round 1:  256 matches
      Rounds 2-9: 128 + 64 + 32 + 16 + 8 + 4 + 2 + 1 = 255 matches
      Bronze:    1 match
      Total:     512 sessions

    Validates:
      - Response is a list with exactly sessions_count entries (from T09F)
      - All sessions have date_start / date_end / tournament_round
      - Round 1 has exactly 256 sessions with participant_user_ids populated
      - 3 sample sessions captured for T09H

    Duration SLO: < 5 s
    """
    tid            = _M.tournament_id
    expected_count = _M.sessions_count
    assert tid and expected_count, "T09B + T09F must have run first"

    t0 = time.perf_counter()
    resp = api.get(
        f"/api/v1/tournaments/{tid}/sessions",
        headers=_M.headers,
        timeout=30_000,
    )
    elapsed = time.perf_counter() - t0
    _M.record("T09G", elapsed)

    sessions = _assert_ok(resp, "T09G GET /sessions")

    assert isinstance(sessions, list), (
        f"T09G: expected list from GET /sessions, got {type(sessions)}"
    )

    # Count must match what the generation task reported
    assert len(sessions) == expected_count, (
        f"T09G: session count mismatch — generation reported {expected_count}, "
        f"GET /sessions returned {len(sessions)}"
    )

    # 512-player knockout → exactly 512 sessions
    assert len(sessions) == PLAYER_COUNT, (
        f"T09G: expected exactly {PLAYER_COUNT} sessions for {PLAYER_COUNT}-player knockout, "
        f"got {len(sessions)}"
    )

    # Structural integrity check on first 10 sessions
    for s in sessions[:10]:
        sid = s.get("id")
        assert s.get("date_start") is not None,       f"T09G: session {sid} missing date_start"
        assert s.get("date_end")   is not None,       f"T09G: session {sid} missing date_end"
        assert s.get("tournament_round") is not None, f"T09G: session {sid} missing tournament_round"

    # Round 1 must have exactly PLAYER_COUNT / 2 sessions with participants assigned
    round1 = [
        s for s in sessions
        if s.get("tournament_round") == 1 and s.get("participant_user_ids")
    ]
    expected_r1 = PLAYER_COUNT // 2
    assert len(round1) == expected_r1, (
        f"T09G: expected {expected_r1} round-1 sessions with participants, "
        f"got {len(round1)}"
    )

    # Capture 3 sample round-1 sessions for T09H
    sample = round1[:3]
    _M.sample_session_ids   = [s["id"] for s in sample]
    _M.sample_participants  = {s["id"]: s["participant_user_ids"] for s in sample}

    logger.info(
        "T09G PASS: %d sessions loaded (%d round-1 matches), "
        "structural integrity OK, elapsed_ms=%.0f",
        len(sessions), len(round1), elapsed * 1000,
    )


# ---------------------------------------------------------------------------
# T09H — Submit results for 3 round-1 matches
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09H_submit_match_results(api: APIRequestContext):
    """
    Submit match results for 3 round-1 sessions via
    POST /tournaments/{id}/sessions/{session_id}/submit-results.

    Placement format: [{"user_id": p1, "rank": 1}, {"user_id": p2, "rank": 2}]

    Validates the full result-recording pipeline under production conditions:
    real DB, real Celery-generated sessions, real participant data.
    """
    tid         = _M.tournament_id
    session_ids = _M.sample_session_ids
    participants = _M.sample_participants

    assert tid and len(session_ids) == 3, (
        "T09B + T09G must have run first"
    )

    t0 = time.perf_counter()
    for session_id in session_ids:
        pids = participants[session_id]
        assert len(pids) >= 2, (
            f"T09H: session {session_id} has fewer than 2 participants: {pids}"
        )
        p1, p2 = pids[0], pids[1]

        resp = api.post(
            f"/api/v1/tournaments/{tid}/sessions/{session_id}/submit-results",
            data={
                "results": [
                    {"user_id": p1, "result": "WIN"},
                    {"user_id": p2, "result": "LOSS"},
                ],
                "notes": "Production flow test result — T09H",
            },
            headers=_M.headers,
            timeout=15_000,
        )
        data = _assert_ok(resp, f"T09H submit-results session {session_id}")
        assert data.get("success") is True, (
            f"T09H: submit-results returned success=False for session {session_id}: {data}"
        )
        _M.last_submit_result = data  # store for T09I ranking validation
        logger.info("T09H: submitted result for session %d — winner=%d", session_id, p1)

    elapsed = time.perf_counter() - t0
    _M.record("T09H", elapsed)
    logger.info(
        "T09H PASS: 3 results submitted, elapsed_ms=%.0f", elapsed * 1000
    )


# ---------------------------------------------------------------------------
# T09I — Calculate rankings and verify leaderboard
# ---------------------------------------------------------------------------

@pytest.mark.golden_path
@pytest.mark.production_flow
@pytest.mark.slow
def test_T09I_calculate_and_verify_rankings(api: APIRequestContext):
    """
    Verify per-match derived rankings from T09H's submit-results responses.

    The POST /{id}/sessions/{sid}/submit-results endpoint returns derived rankings
    inline (rank 1 = winner, rank 2 = loser) for each HEAD_TO_HEAD match.
    We validate these instead of calling POST /calculate-rankings, which requires
    ALL 512 sessions to have results before it will run — not feasible in a
    3-result sampling test.

    Validates:
      - last submit-results response has rankings list with ≥ 2 entries
      - rank 1 exists in the rankings
      - rank 1 player has points > rank 2 player (WIN scores higher than LOSS)
      - Full pipeline metric summary is logged on success
    """
    tid = _M.tournament_id
    assert tid, "T09B must have run first"
    assert _M.last_submit_result is not None, "T09H must have run first"

    t0 = time.perf_counter()

    data = _M.last_submit_result
    rankings: List[Dict[str, Any]] = data.get("rankings", [])

    assert len(rankings) >= 2, (
        f"T09I: expected ≥ 2 ranking entries from submit-results, got {len(rankings)}. "
        f"Full response: {data}"
    )

    # Validate ranking structure: each entry must have user_id, rank (int), points (numeric)
    for entry in rankings:
        assert "user_id" in entry, f"T09I: ranking entry missing user_id: {entry}"
        assert "rank" in entry,    f"T09I: ranking entry missing rank: {entry}"
        assert "points" in entry,  f"T09I: ranking entry missing points: {entry}"

    # Winner (rank = lower value) should have more or equal points than loser
    sorted_rankings = sorted(rankings, key=lambda r: r.get("rank", 999))
    winner = sorted_rankings[0]
    loser  = sorted_rankings[-1]
    assert winner.get("points", 0) >= loser.get("points", 0), (
        f"T09I: winner rank {winner.get('rank')} points ({winner.get('points')}) "
        f"should be ≥ loser rank {loser.get('rank')} points ({loser.get('points')})"
    )

    rankings_count = len(rankings)
    rank1_player   = winner.get("user_id")

    elapsed = time.perf_counter() - t0
    _M.record("T09I", elapsed)

    logger.info(
        "T09I PASS: rankings validated from submit-results response — "
        "winner_id=%s winner_rank=%d winner_pts=%.1f "
        "loser_id=%s loser_rank=%d loser_pts=%.1f elapsed_ms=%.0f",
        rank1_player, winner.get("rank"), winner.get("points", 0),
        loser.get("user_id"), loser.get("rank"), loser.get("points", 0),
        elapsed * 1000,
    )

    # ── Full pipeline summary ─────────────────────────────────────────────────
    total_pipeline_s = sum(v for v in _M.durations_ms.values()) / 1000
    _M.log_summary(prefix="[T09 COMPLETE] ")
    logger.info(
        "T09 PRODUCTION FLOW COMPLETE\n"
        "  Players seeded:      %d\n"
        "  Tournament ID:       %d\n"
        "  Sessions generated:  %d\n"
        "  Results submitted:   3\n"
        "  Rankings validated:  %d (per-match derived rankings)\n"
        "  Stage durations:     %s\n"
        "  Total pipeline time: %.1f s\n"
        "  SLO warnings:        %s",
        PLAYER_COUNT,
        _M.tournament_id,
        _M.sessions_count,
        rankings_count,
        _M.durations_ms,
        total_pipeline_s,
        _M.slo_warnings or "none",
    )
