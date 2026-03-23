"""
Redis Pub/Sub for Tournament Live Monitoring
============================================

Provides:
  - publish_tournament_update(tournament_id, payload) — sync, safe to call from
    any synchronous FastAPI handler after db.commit().
  - subscribe_tournament_updates(tournament_id) — async async-generator that
    yields JSON strings; used by the WebSocket handler.

Both helpers fail silently when Redis is unavailable so the main app keeps
running even without a live monitoring backend.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import redis
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


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
    Publish a tournament event to Redis.

    Called synchronously inside HTTP result-submission handlers, after
    db.commit().  Failures are logged and swallowed — live monitoring is
    best-effort and must never break the primary result flow.

    Args:
        tournament_id: Semester / tournament ID.
        payload:       Dict that will be JSON-serialised and broadcast.
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


# ── Async subscribe (used by WebSocket handler) ─────────────────────────────

async def subscribe_tournament_updates(
    tournament_id: int,
) -> AsyncIterator[str]:
    """
    Async generator that subscribes to a tournament's update channel and
    yields raw JSON strings as they arrive.

    Usage::

        async for message in subscribe_tournament_updates(42):
            await websocket.send_text(message)

    The generator returns (StopAsyncIteration) when the Redis connection is
    lost or when the caller breaks out of the loop.

    Raises nothing — the WebSocket handler should catch WebSocketDisconnect
    and break the loop itself.
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
