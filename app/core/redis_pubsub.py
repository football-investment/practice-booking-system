"""
Redis Pub/Sub for Tournament Live Monitoring
============================================

Provides:
  - publish_tournament_update(tournament_id, payload) — sync, safe to call from
    any synchronous FastAPI handler after db.commit().
  - subscribe_tournament_updates(tournament_id) — async generator that yields
    JSON strings; used by the WebSocket handler.

Both helpers fail silently when Redis is unavailable so the main app keeps
running even without a live monitoring backend.

──────────────────────────────────────────────────────────────────────────────
WebSocket event schema  (stable contract)
──────────────────────────────────────────────────────────────────────────────

Every message published to the ``tournament:{id}:updates`` Redis channel and
forwarded to connected WebSocket clients has the following JSON shape.  All
fields are **mandatory** unless marked optional.

.. code-block:: json

    {
      "type":            "session_result",   // event discriminator (always this value for now)
      "session_id":      1234,               // integer — completed session PK
      "campus_id":       2,                  // integer | null — campus FK (null = single-campus)
      "pitch_id":        5,                  // integer | null — pitch FK (null = no pitch assigned)
      "round_number":    7,                  // integer | null — tournament_round on the session
      "status":          "completed",        // string  — always "completed" for result submissions
      "completed_count": 423,               // integer — sessions with session_status="completed"
      "total_count":     500500,            // integer — all sessions for this tournament
      "progress_pct":    0.0008,            // float   — completed_count / total_count (0.0 – 1.0)
      "completed_at":    "2026-03-24T…Z"   // string  — ISO-8601 UTC timestamp of this event
    }

Python typed representation (import from this module):

.. code-block:: python

    from app.core.redis_pubsub import TournamentUpdateEvent
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional, TypedDict

import redis
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


# ── Stable event schema (TypedDict) ─────────────────────────────────────────

class TournamentUpdateEvent(TypedDict):
    """
    Canonical schema for a session-result event published on
    ``tournament:{id}:updates``.

    Publishers: ``app.api.api_v1.endpoints.sessions.results._publish_session_result``
    Consumers:  WebSocket handler in ``app.api.web_routes.tournament_live``
                (forwarded as-is to browser clients)
    """

    type: str              # discriminator — always "session_result"
    session_id: int
    campus_id: Optional[int]
    pitch_id: Optional[int]
    round_number: Optional[int]
    status: str            # always "completed"
    completed_count: int
    total_count: int
    progress_pct: float    # 0.0 – 1.0
    completed_at: str      # ISO-8601 UTC


# ── Sync publish (called from HTTP handlers) ────────────────────────────────

_sync_client: redis.Redis | None = None


def _get_sync_client() -> redis.Redis | None:
    """Lazy singleton for the synchronous Redis client."""
    global _sync_client
    if _sync_client is None:
        try:
            _sync_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _sync_client.ping()
        except Exception as exc:
            logger.warning("Redis pub/sub unavailable (sync): %s", exc)
            _sync_client = None
    return _sync_client


def publish_tournament_update(tournament_id: int, payload: dict) -> None:
    """
    Publish a tournament event to Redis channel ``tournament:{id}:updates``.

    Called synchronously inside HTTP result-submission handlers, after
    db.commit().  Failures are logged and swallowed — live monitoring is
    best-effort and must never block or break the primary result flow.

    The ``payload`` dict should conform to :class:`TournamentUpdateEvent`.

    Args:
        tournament_id: Semester / tournament PK.
        payload:       Event dict — will be JSON-serialised and broadcast.
    """
    client = _get_sync_client()
    if client is None:
        return
    channel = f"tournament:{tournament_id}:updates"
    try:
        message = json.dumps(payload)
        client.publish(channel, message)
    except Exception as exc:
        logger.warning("Redis publish failed for channel %s: %s", channel, exc)
        # Reset client so next call re-tries the connection
        global _sync_client
        _sync_client = None


# ── Async subscribe (used by WebSocket handler) ─────────────────────────────

async def subscribe_tournament_updates(
    tournament_id: int,
) -> AsyncIterator[str]:
    """
    Async generator that subscribes to a tournament's update channel and
    yields raw JSON strings as they arrive.

    Each yielded string is a :class:`TournamentUpdateEvent` serialised to JSON.

    The generator returns (exhausts) when:
    - The Redis connection is lost.
    - The caller breaks out of the loop (generator is garbage-collected).

    Raises nothing — all errors are logged and the generator returns cleanly.
    """
    channel = f"tournament:{tournament_id}:updates"
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        async with client.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    yield raw["data"]
    except Exception as exc:
        logger.warning("Redis async subscribe error on %s: %s", channel, exc)
        return
