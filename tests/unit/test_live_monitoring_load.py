"""
Live Monitoring Load + Concurrency Tests — LM-LOAD-01 through LM-LOAD-06

LM-LOAD-01  1000 concurrent publish calls with Redis unreachable → no exception
LM-LOAD-02  _throttled_stream drops stale messages under burst load
LM-LOAD-03  _throttled_stream with interval=0 passes all messages through
LM-LOAD-04  publish payload satisfies TournamentUpdateEvent schema (all required fields)
LM-LOAD-05  WS throttle limits to ≤ max_events when burst arrives faster than interval
LM-LOAD-06  Redis sync client resets on publish error (re-tries connection next call)

Design notes
------------
* LM-LOAD-01 uses 50 threads each doing 20 publishes — simulates 50 concurrent
  result-submission HTTP requests (realistic for a 1000-player batch import).
* LM-LOAD-02 / 03 / 05 test the async throttle logic via pytest-asyncio without
  a real Redis or WebSocket.  The ``_throttled_stream`` function is unit-testable
  because it is a standalone async generator.
* All tests mock or bypass Redis; no live Redis server is required.
"""
from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-01: 1000 concurrent publish calls with Redis down → no exception
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_LOAD_01_1000_concurrent_publishes_redis_down():
    """
    Simulates 50 concurrent HTTP result-submission workers each calling
    publish_tournament_update 20 times while Redis is unavailable.

    Expected: zero exceptions raised; all calls return silently.
    """
    from app.core.redis_pubsub import publish_tournament_update

    errors: list[Exception] = []

    def _publish_batch(start: int) -> None:
        for i in range(start, start + 20):
            try:
                publish_tournament_update(
                    tournament_id=1,
                    payload={
                        "type": "session_result",
                        "session_id": i,
                        "campus_id": (i % 4) + 1,
                        "pitch_id": (i % 8) + 1,
                        "round_number": i,
                        "status": "completed",
                        "completed_count": i,
                        "total_count": 1000,
                        "progress_pct": round(i / 1000, 4),
                        "completed_at": "2026-03-24T10:00:00Z",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    # Force Redis to be unavailable by patching _get_sync_client to return None
    with patch(
        "app.core.redis_pubsub._get_sync_client",
        return_value=None,
    ):
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(_publish_batch, i * 20) for i in range(50)]
            for fut in futures:
                fut.result()

    assert len(errors) == 0, f"Unexpected exceptions: {errors}"


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-02: throttled_stream drops stale under burst — interval > 0
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_LM_LOAD_02_throttled_stream_drops_stale_under_burst():
    """
    Produce 50 rapid messages into _throttled_stream with a non-zero interval.

    The single-slot queue means stale items are discarded; only the *latest*
    is forwarded after the sleep expires.

    With interval=0.001 s (1 ms) and synchronous production, all 50 messages
    are queued before the consumer wakes from the first sleep, so only a
    handful of messages (not 50) should be received.
    """
    from app.api.web_routes.tournament_live import _throttled_stream

    async def burst_source() -> AsyncIterator[str]:
        for i in range(50):
            yield json.dumps({"type": "session_result", "completed_count": i})
            # No await → all messages produced synchronously before consumer runs

    received: list[str] = []
    async for msg in _throttled_stream(burst_source(), interval=0.001):
        received.append(msg)

    # Must receive at least 1 (the consumer always gets at least one item)
    assert len(received) >= 1
    # Must receive strictly fewer than 50 (stale items were dropped)
    assert len(received) < 50, (
        f"Expected throttle to drop stale items but got all {len(received)} messages"
    )
    # The LAST message from the source must appear exactly once
    last_msg = json.dumps({"type": "session_result", "completed_count": 49})
    assert last_msg in received, "Latest event was not forwarded"


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-03: throttled_stream with interval=0 passes all messages
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_LM_LOAD_03_throttled_stream_interval_zero_passes_all():
    """
    With interval=0 no throttle is applied; every message must arrive.
    Used for testing environments where we want all events.
    """
    from app.api.web_routes.tournament_live import _throttled_stream

    N = 20

    async def ordered_source() -> AsyncIterator[str]:
        for i in range(N):
            yield json.dumps({"seq": i})
            await asyncio.sleep(0)  # yield control to event loop

    received: list[str] = []
    async for msg in _throttled_stream(ordered_source(), interval=0):
        received.append(msg)

    assert len(received) == N
    # Verify ordering is preserved
    for i, msg in enumerate(received):
        assert json.loads(msg)["seq"] == i


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-04: publish payload satisfies TournamentUpdateEvent schema
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_LOAD_04_publish_payload_schema_complete():
    """
    Verify that the payload built by _publish_session_result contains ALL
    fields required by TournamentUpdateEvent.
    """
    from app.core.redis_pubsub import TournamentUpdateEvent
    required_keys = set(TournamentUpdateEvent.__annotations__.keys())

    captured: list[dict] = []

    with patch(
        "app.api.api_v1.endpoints.sessions.results.publish_tournament_update",
        side_effect=lambda tid, payload: captured.append(payload),
    ):
        # Build a minimal mock session and db
        session = MagicMock()
        session.semester_id = 1
        session.id = 42
        session.campus_id = 2
        session.pitch_id = 5
        session.tournament_round = 7
        session.session_status = "completed"

        db = MagicMock()
        # completed query → 1, total query → 2
        db.query.return_value.filter.return_value.count.side_effect = [1, 2]

        from app.api.api_v1.endpoints.sessions.results import _publish_session_result
        _publish_session_result(db, session)

    assert len(captured) == 1
    payload = captured[0]

    missing = required_keys - set(payload.keys())
    assert not missing, f"Payload missing TournamentUpdateEvent fields: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-05: WS throttle limits output count under high-frequency burst
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_LM_LOAD_05_ws_throttle_rate_cap():
    """
    Simulate a 100-event burst arriving every 1 ms.
    With a 50 ms throttle interval the consumer should receive at most
    ceil(100 * 0.001 / 0.050) + 1 ≈ 3 messages
    (much fewer than 100).

    This verifies the rate-cap semantics of _throttled_stream under realistic
    high-frequency conditions.
    """
    from app.api.web_routes.tournament_live import _throttled_stream

    async def fast_source() -> AsyncIterator[str]:
        for i in range(100):
            yield json.dumps({"completed_count": i, "total_count": 100})
            await asyncio.sleep(0.001)  # 1 ms between events

    received: list[str] = []
    async for msg in _throttled_stream(fast_source(), interval=0.05):
        received.append(msg)

    # With 100 events * 1ms each = 100ms total, at 50ms throttle: ~2 sends
    # Generous upper bound: fewer than 20 (not 100)
    assert len(received) < 20, (
        f"Throttle should cap output; got {len(received)} messages"
    )
    # Must have received at least 1
    assert len(received) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# LM-LOAD-06: Redis sync client resets after publish error
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_LOAD_06_sync_client_resets_after_publish_error():
    """
    If publish() raises (e.g. Redis connection dropped mid-flight), the
    module-level _sync_client is reset to None so the next call re-establishes
    the connection instead of repeatedly failing on a dead socket.
    """
    import app.core.redis_pubsub as _mod

    # Save original client state
    orig = _mod._sync_client

    try:
        # Inject a fake client whose publish() raises
        fake_client = MagicMock()
        fake_client.publish.side_effect = ConnectionError("Redis gone")
        _mod._sync_client = fake_client

        # Should not raise
        _mod.publish_tournament_update(99, {"type": "test"})

        # Client must have been reset so next call re-tries
        assert _mod._sync_client is None, (
            "_sync_client should be reset to None after a publish error"
        )
    finally:
        # Restore original state
        _mod._sync_client = orig
