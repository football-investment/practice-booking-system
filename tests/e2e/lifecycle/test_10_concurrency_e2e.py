"""
T10: Concurrency Validation — 5 Parallel Tournament Generations
===============================================================

Dispatches 5 knockout tournaments simultaneously (via Python threads) and
polls all of them to completion. Measures queue_wait_time, db_write_time,
and generation_duration per slot and reports worker utilisation / serialisation
overhead in the test log.

At least one tournament uses a multi-campus schedule override.

Prerequisites (same as T09):
  1. FastAPI:   uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Celery:    celery -A app.celery_app worker -Q tournaments --loglevel=info
  3. Redis:     redis-server
  4. DB:        lfa_intern_system (migrations applied, admin user seeded)

Run:
  pytest tests_e2e/lifecycle/test_10_concurrency_e2e.py -v -m concurrency

Markers:
  concurrency   — requires live server + Celery
  production_flow — inherits same infrastructure requirements
  slow          — runtime depends on worker count (typically 60–300 s)

Tests:
  T10A  Seed shared player pools (5 × 64 players)
  T10B  Create 5 knockout tournaments (slot 0 gets multi-campus config)
  T10C  Enroll players into each tournament (concurrent HTTP)
  T10D  Fire 5 generate-sessions calls simultaneously, assert all async/celery
  T10E  Poll all 5 tasks to completion, collect timing metrics
  T10F  Assert structural correctness + report concurrency metrics

Timing SLOs (soft — logged as warnings, not assertion failures):
  Each generation:  < 120 s from dispatch
  All 5 complete:   < 300 s wall-clock
  Queue wait ratio: < 5× single-tournament baseline (logged, not failed)
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
API_URL        = os.environ.get("API_URL",        "http://localhost:8000")
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL",    "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

NUM_SLOTS         = 5          # parallel tournaments
PLAYERS_PER_SLOT  = 128        # 128-player knockout = 127 sessions; must be >=128 to trigger Celery async path
POLL_TIMEOUT_S    = 300
POLL_INTERVAL_S   = 3

# Unique suffix per test run — prevents 409 conflicts on name uniqueness constraint
_RUN_TAG = str(int(time.time()))[-6:]   # last 6 digits of epoch

SLO_EACH_GEN_S   = 120         # each tournament should finish within 2 min
SLO_ALL_DONE_S   = 300         # all 5 should be done within 5 min

PLAYER_EMAIL_DOMAIN = "concurrent.lfa"


# ---------------------------------------------------------------------------
# Module-level Celery guard
# ---------------------------------------------------------------------------

def _check_celery_available() -> None:
    try:
        from app.celery_app import celery_app  # noqa: PLC0415
        ping_result = celery_app.control.ping(timeout=2)
        if not ping_result:
            pytest.skip(
                "Celery workers are not responding. "
                "Concurrency tests require a running Celery worker.\n"
                "Start with: celery -A app.celery_app worker -Q tournaments --loglevel=info",
                allow_module_level=True,
            )
    except ImportError as exc:
        pytest.skip(f"Celery package not importable: {exc}", allow_module_level=True)
    except Exception as exc:
        pytest.skip(f"Celery/Redis unavailable: {exc}", allow_module_level=True)


_check_celery_available()


# ---------------------------------------------------------------------------
# Shared module-level state
# ---------------------------------------------------------------------------

@dataclass
class _SlotState:
    """Per-tournament slot state, populated in sequence T10A → T10F."""
    slot:          int
    player_ids:    List[int]        = field(default_factory=list)
    tournament_id: Optional[int]    = None
    campus_ids:    List[int]        = field(default_factory=list)  # slot 0 only
    task_id:       Optional[str]    = None
    dispatch_ts:   Optional[float]  = None  # time.perf_counter() when generate-sessions fired
    sessions_count: Optional[int]   = None
    # Celery timing metrics forwarded by generation-status (P0 fix)
    generation_duration_ms: Optional[float] = None
    db_write_time_ms:       Optional[float] = None
    queue_wait_time_ms:     Optional[float] = None
    done_ts:       Optional[float]  = None  # time.perf_counter() when done polled
    error:         Optional[str]    = None


@dataclass
class _SharedState:
    headers:       Dict[str, str]   = field(default_factory=dict)
    location_id:   Optional[int]    = None
    slots:         List[_SlotState] = field(default_factory=list)


_M = _SharedState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_ok(resp, label: str, expected: int = 200) -> Any:
    """Assert HTTP status and return parsed JSON."""
    body_text = resp.text()
    assert resp.status == expected, (
        f"{label}: expected HTTP {expected}, got {resp.status}\n{body_text}"
    )
    return resp.json()


def _login(api) -> Dict[str, str]:
    resp = api.post(
        "/api/v1/auth/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15_000,
    )
    data = _assert_ok(resp, "admin login")
    token = data.get("access_token") or data.get("token")
    assert token, f"No access_token in login response: {data}"
    return {"Authorization": f"Bearer {token}"}


def _poll_until_done(slot: _SlotState, headers: Dict[str, str]) -> None:
    """
    Poll generation-status for a single slot until done or error.
    Called from a background thread in T10E.

    Uses `requests` (not Playwright) to avoid greenlet thread-safety issues.
    Playwright's sync_api APIRequestContext cannot be shared across threads.
    """
    import requests as _requests

    url = (
        f"{API_URL}/api/v1/tournaments/{slot.tournament_id}"
        f"/generation-status/{slot.task_id}"
    )
    deadline = time.perf_counter() + POLL_TIMEOUT_S
    poll_count = 0
    while time.perf_counter() < deadline:
        try:
            resp = _requests.get(url, headers=headers, timeout=15)
        except Exception as exc:
            logger.debug("T10E poll slot %d #%d: request error %s", slot.slot, poll_count, exc)
            time.sleep(POLL_INTERVAL_S)
            continue
        poll_count += 1
        if resp.status_code == 404:
            time.sleep(POLL_INTERVAL_S)
            continue
        try:
            data = resp.json()
        except Exception:
            time.sleep(POLL_INTERVAL_S)
            continue
        status = data.get("status", "unknown")
        if status == "done":
            slot.sessions_count         = data.get("sessions_count")
            slot.generation_duration_ms = data.get("generation_duration_ms")
            slot.db_write_time_ms       = data.get("db_write_time_ms")
            slot.queue_wait_time_ms     = data.get("queue_wait_time_ms")
            slot.done_ts                = time.perf_counter()
            return
        elif status == "error":
            slot.error = data.get("message", "unknown error")
            return
        time.sleep(POLL_INTERVAL_S)
    slot.error = f"Timeout after {POLL_TIMEOUT_S}s ({poll_count} polls)"


# ---------------------------------------------------------------------------
# pytest markers
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.concurrency,
    pytest.mark.production_flow,
    pytest.mark.slow,
]


# ---------------------------------------------------------------------------
# T10A — Seed player pools
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10A_seed_players() -> None:
    """
    Seed 5 × 64 = 320 players via POST /admin/batch-create-players.

    Uses skip_existing=True so the suite is idempotent across reruns.
    """
    with sync_playwright() as pw:
        api = pw.request.new_context(base_url=API_URL)
        _M.headers = _login(api)

        all_players: List[Dict[str, Any]] = [
            {
                "email":         f"conc_s{slot:02d}_{i:03d}@{PLAYER_EMAIL_DOMAIN}",
                "password":      "ConcTest2026!",
                "name":          f"Conc Slot{slot} Player{i}",
                "date_of_birth": "2001-03-20",
            }
            for slot in range(NUM_SLOTS)
            for i in range(PLAYERS_PER_SLOT)
        ]

        t0 = time.perf_counter()
        resp = api.post(
            "/api/v1/admin/batch-create-players",
            data={
                "players":        all_players,
                "specialization": "LFA_FOOTBALL_PLAYER",
                "skip_existing":  True,
            },
            headers=_M.headers,
            timeout=120_000,
        )
        elapsed = time.perf_counter() - t0
        data = _assert_ok(resp, "T10A batch-create-players", expected=201)

        total = data["created_count"] + data["skipped_count"]
        assert total == NUM_SLOTS * PLAYERS_PER_SLOT, (
            f"T10A: expected {NUM_SLOTS * PLAYERS_PER_SLOT} players total "
            f"(created+skipped), got created={data['created_count']} "
            f"skipped={data['skipped_count']} failed={data['failed_count']}"
        )
        assert len(data["player_ids"]) == NUM_SLOTS * PLAYERS_PER_SLOT

        # Partition into per-slot lists
        pid_list = data["player_ids"]
        _M.slots = [
            _SlotState(
                slot=s,
                player_ids=pid_list[s * PLAYERS_PER_SLOT : (s + 1) * PLAYERS_PER_SLOT],
            )
            for s in range(NUM_SLOTS)
        ]

        logger.info(
            "T10A: seeded %d players (created=%d skipped=%d) in %.1fs",
            total, data["created_count"], data["skipped_count"], elapsed,
        )
        if elapsed > 60:
            logger.warning("T10A SLO breach: %.1fs > 60s", elapsed)

        api.dispose()


# ---------------------------------------------------------------------------
# T10B — Create 5 tournaments (slot 0 gets multi-campus config)
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10B_create_tournaments() -> None:
    """Create 5 independent 64-player knockout tournaments."""
    assert _M.slots, "T10B: T10A did not populate _M.slots"

    with sync_playwright() as pw:
        api = pw.request.new_context(base_url=API_URL)

        for slot in _M.slots:
            if slot.slot > 0:
                time.sleep(1.1)  # tournament_code has 1s precision — avoid UNIQUE violation
            resp = api.post(
                "/api/v1/tournaments/create",
                data={
                    "name":           f"T10 Conc {_RUN_TAG} Slot {slot.slot}",
                    "tournament_type": "knockout",
                    "age_group":      "PRO",
                    "max_players":    PLAYERS_PER_SLOT,
                    "skills_to_test": ["PASSING", "DRIBBLING"],
                    "reward_config":  [
                        {"rank": 1, "xp_reward": 100, "credits_reward": 50},
                        {"rank": 2, "xp_reward": 50,  "credits_reward": 25},
                    ],
                    "enrollment_cost": 0,
                },
                headers=_M.headers,
                timeout=30_000,
            )
            data = _assert_ok(resp, f"T10B create tournament slot {slot.slot}", expected=201)
            assert data.get("success") is True, f"T10B slot {slot.slot}: {data}"
            slot.tournament_id = data["tournament_id"]
            logger.info("T10B: slot %d → tournament_id=%d", slot.slot, slot.tournament_id)

        # Slot 0: multi-campus config
        slot0 = _M.slots[0]
        tid   = slot0.tournament_id

        # Ensure location exists
        resp = api.get("/api/v1/admin/locations/", headers=_M.headers, timeout=10_000)
        loc_list = _assert_ok(resp, "T10B GET locations")
        if loc_list:
            location_id = loc_list[0]["id"]
        else:
            resp = api.post(
                "/api/v1/admin/locations/",
                data={
                    "name": "T10 Test Location", "city": "Budapest",
                    "country": "Hungary", "country_code": "HU",
                    "location_code": "T10LOC", "location_type": "CENTER",
                    "is_active": True,
                },
                headers=_M.headers,
                timeout=10_000,
            )
            location_id = _assert_ok(resp, "T10B create location", expected=201)["id"]
        _M.location_id = location_id

        # Ensure 2 campuses exist
        resp = api.get(
            f"/api/v1/admin/locations/{location_id}/campuses",
            headers=_M.headers,
            timeout=10_000,
        )
        campus_list = _assert_ok(resp, "T10B GET campuses")
        campus_ids = [c["id"] for c in campus_list]
        for spec in [
            {"name": "Alpha Pitch",  "venue": "Pitch A", "is_active": True},
            {"name": "Beta Arena",   "venue": "Arena B", "is_active": True},
        ]:
            if not any(c["name"] == spec["name"] for c in campus_list):
                r2 = api.post(
                    f"/api/v1/admin/locations/{location_id}/campuses",
                    data=spec,
                    headers=_M.headers,
                    timeout=10_000,
                )
                campus_ids.append(_assert_ok(r2, f"T10B create campus {spec['name']}", expected=201)["id"])
        slot0.campus_ids = campus_ids[:2]
        cid_a, cid_b = slot0.campus_ids

        # Global schedule for slot 0
        resp = api.patch(
            f"/api/v1/tournaments/{tid}/schedule-config",
            data={"match_duration_minutes": 45, "break_duration_minutes": 10, "parallel_fields": 2},
            headers=_M.headers,
            timeout=10_000,
        )
        _assert_ok(resp, "T10B PATCH schedule-config slot0")

        # Campus overrides
        for cid, label, dur, fields in [
            (cid_a, "Alpha Pitch",  45, 2),
            (cid_b, "Beta Arena",   30, 4),
        ]:
            resp = api.put(
                f"/api/v1/tournaments/{tid}/campus-schedules",
                data={
                    "campus_id":              cid,
                    "match_duration_minutes": dur,
                    "break_duration_minutes": 5,
                    "parallel_fields":        fields,
                    "venue_label":            label,
                    "is_active":              True,
                },
                headers=_M.headers,
                timeout=10_000,
            )
            d = _assert_ok(resp, f"T10B campus-schedule {label}")
            assert d["resolved_match_duration"] == dur, (
                f"T10B: campus {label} resolved_match_duration expected {dur}, got {d['resolved_match_duration']}"
            )

        logger.info("T10B: slot 0 multi-campus config applied (campus_ids=%s)", slot0.campus_ids)
        api.dispose()


# ---------------------------------------------------------------------------
# T10C — Enroll players (concurrent HTTP via threads)
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10C_enroll_players() -> None:
    """Batch-enroll players into each tournament concurrently."""
    assert all(s.tournament_id for s in _M.slots), "T10C: T10B did not create tournaments"

    errors: List[str] = []
    lock = threading.Lock()

    def _enroll_slot(slot: _SlotState) -> None:
        with sync_playwright() as pw:
            api = pw.request.new_context(base_url=API_URL)
            resp = api.post(
                f"/api/v1/tournaments/{slot.tournament_id}/admin/batch-enroll",
                data={"player_ids": slot.player_ids},
                headers=_M.headers,
                timeout=60_000,
            )
            try:
                data = _assert_ok(resp, f"T10C enroll slot {slot.slot}")
                enrolled = data.get("enrolled_count", 0)
                if enrolled != PLAYERS_PER_SLOT:
                    with lock:
                        errors.append(
                            f"slot {slot.slot}: enrolled_count={enrolled}, expected {PLAYERS_PER_SLOT}"
                        )
                else:
                    logger.info("T10C: slot %d enrolled %d players", slot.slot, enrolled)
            except AssertionError as exc:
                with lock:
                    errors.append(str(exc))
            finally:
                api.dispose()

    threads = [threading.Thread(target=_enroll_slot, args=(s,), daemon=True) for s in _M.slots]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=90)

    assert not errors, "T10C enrollment errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# T10D — Fire all 5 generate-sessions simultaneously
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10D_trigger_generation() -> None:
    """
    Fire POST /generate-sessions for all 5 tournaments at the same time.

    All must return async=True + async_backend="celery".
    """
    assert all(s.tournament_id for s in _M.slots), "T10D: no tournaments"

    errors: List[str] = []
    lock = threading.Lock()

    def _trigger(slot: _SlotState) -> None:
        with sync_playwright() as pw:
            api = pw.request.new_context(base_url=API_URL)
            try:
                t0 = time.perf_counter()
                resp = api.post(
                    f"/api/v1/tournaments/{slot.tournament_id}/generate-sessions",
                    data={
                        "parallel_fields":          2,
                        "session_duration_minutes": 45,
                        "break_minutes":            10,
                        "number_of_rounds":         1,
                    },
                    headers=_M.headers,
                    timeout=30_000,
                )
                slot.dispatch_ts = t0
                try:
                    data = _assert_ok(resp, f"T10D generate slot {slot.slot}")
                except AssertionError as exc:
                    with lock:
                        errors.append(str(exc))
                    return

                if not data.get("async"):
                    with lock:
                        errors.append(
                            f"slot {slot.slot}: expected async=True, got async={data.get('async')}"
                        )
                    return
                backend = data.get("async_backend", "")
                if backend != "celery":
                    with lock:
                        errors.append(
                            f"slot {slot.slot}: expected async_backend=celery, got {backend!r}. "
                            "Is a Celery worker running?"
                        )
                    return
                slot.task_id = data.get("task_id")
                assert slot.task_id, f"T10D slot {slot.slot}: missing task_id in response"
                logger.info(
                    "T10D: slot %d dispatched task_id=%s (%.0fms HTTP latency)",
                    slot.slot, slot.task_id, (time.perf_counter() - t0) * 1000,
                )
            finally:
                api.dispose()

    threads = [threading.Thread(target=_trigger, args=(s,), daemon=True) for s in _M.slots]
    wall_t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    wall_elapsed = time.perf_counter() - wall_t0

    assert not errors, "T10D trigger errors:\n" + "\n".join(errors)
    assert all(s.task_id for s in _M.slots), "T10D: not all slots received a task_id"
    logger.info("T10D: all 5 tasks dispatched (wall-clock dispatch phase: %.1fs)", wall_elapsed)


# ---------------------------------------------------------------------------
# T10E — Poll all tasks to completion
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10E_poll_to_completion() -> None:
    """
    Poll all 5 generation tasks concurrently until done or timeout.
    Collects timing metrics from each slot.
    """
    assert all(s.task_id for s in _M.slots), "T10E: T10D did not set task_ids"

    threads = [
        threading.Thread(
            target=_poll_until_done,
            args=(slot, _M.headers),
            daemon=True,
        )
        for slot in _M.slots
    ]
    wall_t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=POLL_TIMEOUT_S + 30)
    wall_elapsed = time.perf_counter() - wall_t0

    # Report
    failures = [s for s in _M.slots if s.error]
    if failures:
        for s in failures:
            logger.error("T10E: slot %d FAILED — %s", s.slot, s.error)
        pytest.fail(
            f"T10E: {len(failures)}/{NUM_SLOTS} slots failed:\n"
            + "\n".join(f"  slot {s.slot}: {s.error}" for s in failures)
        )

    logger.info("T10E: all %d generations completed (wall-clock: %.1fs)", NUM_SLOTS, wall_elapsed)
    if wall_elapsed > SLO_ALL_DONE_S:
        logger.warning("T10E SLO breach: wall-clock %.1fs > %ds", wall_elapsed, SLO_ALL_DONE_S)

    # Per-slot timing report
    for slot in _M.slots:
        individual_elapsed = (
            (slot.done_ts - slot.dispatch_ts) if slot.done_ts and slot.dispatch_ts else None
        )
        logger.info(
            "T10E slot %d │ sessions=%s │ wall=%.1fs │ gen_ms=%s │ db_ms=%s │ queue_wait_ms=%s",
            slot.slot,
            slot.sessions_count,
            individual_elapsed if individual_elapsed is not None else -1,
            slot.generation_duration_ms if slot.generation_duration_ms is not None else "n/a",
            slot.db_write_time_ms       if slot.db_write_time_ms       is not None else "n/a",
            slot.queue_wait_time_ms     if slot.queue_wait_time_ms     is not None else "n/a",
        )
        if individual_elapsed and individual_elapsed > SLO_EACH_GEN_S:
            logger.warning(
                "T10E SLO breach: slot %d took %.1fs > %ds",
                slot.slot, individual_elapsed, SLO_EACH_GEN_S,
            )


# ---------------------------------------------------------------------------
# T10F — Structural correctness + concurrency metrics report
# ---------------------------------------------------------------------------

@pytest.mark.concurrency
def test_T10F_validate_and_report() -> None:
    """
    Structural assertions + concurrency observability report.

    Hard assertions:
      - All 5 slots have sessions_count > 0
      - 64-player knockout: sessions_count == 63  (64-1 = 63 matches)
      - No slot has error set

    Soft observability (logged, not failed):
      - queue_wait_time spread across slots (serialisation overhead)
      - db_write_time range (I/O contention)
      - generation_duration range (CPU contention)
    """
    assert len(_M.slots) == NUM_SLOTS, (
        f"T10F: expected {NUM_SLOTS} slots, got {len(_M.slots)} — T10A/T10B did not complete"
    )
    assert all(s.tournament_id for s in _M.slots), "T10F: incomplete state from T10B"
    assert not any(s.error for s in _M.slots), (
        "T10F: slots with errors: "
        + str([(s.slot, s.error) for s in _M.slots if s.error])
    )

    EXPECTED_SESSIONS = PLAYERS_PER_SLOT      # knockout + bronze: 127 matches + 1 bronze = 128

    for slot in _M.slots:
        assert slot.sessions_count is not None and slot.sessions_count > 0, (
            f"T10F: slot {slot.slot} has sessions_count={slot.sessions_count}"
        )
        assert slot.sessions_count == EXPECTED_SESSIONS, (
            f"T10F: slot {slot.slot} expected {EXPECTED_SESSIONS} sessions "
            f"(64-player knockout), got {slot.sessions_count}"
        )

    # --- Concurrency observability report ---
    logger.info("=" * 70)
    logger.info("T10F CONCURRENCY REPORT — %d parallel tournaments", NUM_SLOTS)
    logger.info("=" * 70)
    logger.info("%-8s %-10s %-14s %-14s %-16s", "Slot", "Sessions", "Gen (ms)", "DB write (ms)", "Queue wait (ms)")
    logger.info("-" * 70)

    queue_waits     = []
    db_writes       = []
    gen_durations   = []

    for slot in _M.slots:
        qw  = slot.queue_wait_time_ms
        dbw = slot.db_write_time_ms
        gd  = slot.generation_duration_ms
        logger.info(
            "%-8d %-10s %-14s %-14s %-16s",
            slot.slot,
            str(slot.sessions_count),
            f"{gd:.1f}" if gd is not None else "n/a",
            f"{dbw:.1f}" if dbw is not None else "n/a",
            f"{qw:.1f}" if qw is not None else "n/a",
        )
        if qw  is not None: queue_waits.append(qw)
        if dbw is not None: db_writes.append(dbw)
        if gd  is not None: gen_durations.append(gd)

    logger.info("-" * 70)

    if queue_waits:
        logger.info(
            "Queue wait   │ min=%.1fms  max=%.1fms  spread=%.1fms",
            min(queue_waits), max(queue_waits), max(queue_waits) - min(queue_waits),
        )
    if db_writes:
        logger.info(
            "DB write     │ min=%.1fms  max=%.1fms  spread=%.1fms",
            min(db_writes), max(db_writes), max(db_writes) - min(db_writes),
        )
    if gen_durations:
        logger.info(
            "Gen duration │ min=%.1fms  max=%.1fms  spread=%.1fms",
            min(gen_durations), max(gen_durations), max(gen_durations) - min(gen_durations),
        )

    # Warn if queue wait spread exceeds 5× the minimum (serialisation pressure)
    if queue_waits and len(queue_waits) > 1:
        min_qw = min(queue_waits)
        max_qw = max(queue_waits)
        if min_qw > 0 and max_qw / min_qw > 5:
            logger.warning(
                "T10F: queue_wait spread ratio %.1fx > 5× — possible worker saturation "
                "(max=%.1fms vs min=%.1fms)",
                max_qw / min_qw, max_qw, min_qw,
            )
        elif min_qw == 0 and max_qw > 500:
            logger.warning(
                "T10F: some queue_wait_times are 0 (task started before enqueue latency captured) "
                "but max=%.1fms suggests serialisation pressure",
                max_qw,
            )

    logger.info("=" * 70)
    logger.info(
        "T10F VERDICT: all %d/%d tournaments generated %d sessions each — PASS",
        NUM_SLOTS, NUM_SLOTS, EXPECTED_SESSIONS,
    )
    logger.info("=" * 70)
