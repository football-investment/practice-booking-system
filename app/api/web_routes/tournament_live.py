"""
Tournament Live Monitoring
==========================

Two endpoints:

  GET  /admin/tournaments/{id}/live
       Admin/instructor HTML dashboard — real-time progress for large tournaments.

  WS   /ws/tournaments/{id}/live?token=<bearer-token>
       WebSocket stream.  Browser connects here after loading the dashboard.
       Forwards Redis Pub/Sub messages as JSON text frames.

Auth notes
----------
* The dashboard page uses cookie auth (standard web flow).
* The WebSocket uses a Bearer token in the query-string (`?token=…`) because
  WebSocket upgrade requests cannot carry custom headers in most browsers.
* Allowed roles for both: ADMIN, SPORT_DIRECTOR, INSTRUCTOR.

Rate limiting / throttle
------------------------
The WebSocket handler applies a server-side send-throttle of
``WS_THROTTLE_INTERVAL`` seconds between successive frames.  Under high-volume
conditions (e.g. 500 000-session tournaments with batch result imports) Redis
may produce thousands of events per second.  The throttle:

  1. Uses a ``maxsize=1`` asyncio.Queue to buffer the Redis stream.
  2. When the queue is already full the *old* item is dropped and replaced with
     the newest event so the client always sees the latest aggregate state.
  3. After each send the consumer sleeps for ``WS_THROTTLE_INTERVAL`` before
     reading the next item, capping throughput at ≤ 1 / WS_THROTTLE_INTERVAL
     frames per second.

Result: at 1000+ events/s the WebSocket client receives at most 5 frames/s
(200 ms default), each showing the current completed/total counters.

Observability
-------------
* ``stats`` dict tracks received / forwarded / dropped counts per WS connection.
* Every ``WS_STATS_INTERVAL`` s (default 30 s) a ``throttle_stats`` event is
  sent to the client so the dashboard can surface the drop rate.
* Every ``WS_IDLE_CHECK_INTERVAL`` s (default 60 s) pitches with no activity
  for more than ``PITCH_IDLE_ALERT_S`` seconds (default 300 s = 5 min) receive
  a ``pitch_idle_alert`` event pushed directly to the connected client.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_web
from app.core.auth import verify_token
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.core.redis_pubsub import subscribe_tournament_updates, get_idle_pitches

logger = logging.getLogger(__name__)

router = APIRouter()

_BASE = Path(__file__).resolve().parent.parent.parent  # app/
templates = Jinja2Templates(directory=str(_BASE / "templates"))

_ALLOWED_ROLES = {UserRole.ADMIN, UserRole.SPORT_DIRECTOR, UserRole.INSTRUCTOR}

# ── Rate-limit constants (override in tests via monkeypatch) ─────────────────
WS_THROTTLE_INTERVAL: float = 0.2   # 200 ms → max 5 frames/sec per connection
WS_STATS_INTERVAL: float = 30.0     # emit throttle_stats every 30 s
WS_IDLE_CHECK_INTERVAL: float = 60.0  # check idle pitches every 60 s
PITCH_IDLE_ALERT_S: float = 300.0   # 5 min without activity → alert


# ── Throttle helper (testable standalone) ────────────────────────────────────

async def _throttled_stream(
    source: AsyncIterator[str],
    interval: float = WS_THROTTLE_INTERVAL,
    stats: Optional[dict] = None,
) -> AsyncIterator[str]:
    """
    Async generator that rate-limits a message stream.

    Wraps *source* so that at most one message is yielded per *interval*
    seconds.  When messages arrive faster than the interval, only the *latest*
    is kept; stale intermediate messages are discarded.

    This is the core of the WS send-throttle.  It is a standalone function so
    it can be unit-tested without a real WebSocket or Redis connection.

    Args:
        source:   Async iterable of raw message strings (e.g. from Redis).
        interval: Minimum seconds between successive yields.  0.0 disables
                  throttling (useful in tests).
        stats:    Optional mutable dict for observability counters.
                  Expected keys: ``received``, ``forwarded``, ``dropped``.
                  Incremented in-place by this function.

    Yields:
        str — the latest buffered message, at most once per ``interval``.
    """
    # Single-slot queue: always holds the most-recent message
    queue: asyncio.Queue[object] = asyncio.Queue(maxsize=1)
    _DONE = object()  # sentinel to signal source exhaustion

    async def _producer() -> None:
        try:
            async for item in source:
                if stats is not None:
                    stats["received"] = stats.get("received", 0) + 1
                if queue.full():
                    try:
                        queue.get_nowait()  # Drop stale item
                        if stats is not None:
                            stats["dropped"] = stats.get("dropped", 0) + 1
                    except asyncio.QueueEmpty:
                        pass
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    # Consumer removed it between our checks — harmless
                    if stats is not None:
                        stats["dropped"] = stats.get("dropped", 0) + 1
        finally:
            # Signal consumer that the source is exhausted
            # (May block briefly if queue is full; that's fine)
            await queue.put(_DONE)

    producer_task = asyncio.create_task(_producer())

    try:
        while True:
            item = await queue.get()
            if item is _DONE:
                break
            if stats is not None:
                stats["forwarded"] = stats.get("forwarded", 0) + 1
            yield item  # type: ignore[misc]
            if interval > 0:
                await asyncio.sleep(interval)
    finally:
        producer_task.cancel()
        try:
            await asyncio.shield(producer_task)
        except (asyncio.CancelledError, Exception):
            pass


# ── Admin HTML page ────────────────────────────────────────────────────────

@router.get("/admin/tournaments/{tournament_id}/live", response_class=HTMLResponse)
async def tournament_live_dashboard(
    request: Request,
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web),
):
    """
    Admin live monitoring dashboard for a specific tournament.

    Shows per-campus/pitch progress, active instructors, and a live feed of
    the last 20 completed sessions.  Updates arrive via WebSocket.
    """
    if current_user.role not in _ALLOWED_ROLES:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard")

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if tournament is None:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Tournament not found", status_code=404)

    total_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.semester_id == tournament_id)
        .count()
    )
    completed_sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.session_status == "completed",
        )
        .count()
    )

    return templates.TemplateResponse(
        "admin/tournament_live.html",
        {
            "request": request,
            "user": current_user,
            "tournament": tournament,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
        },
    )


# ── WebSocket endpoint ─────────────────────────────────────────────────────

@router.websocket("/ws/tournaments/{tournament_id}/live")
async def tournament_live_ws(
    websocket: WebSocket,
    tournament_id: int,
    token: str = Query(..., description="Bearer access token"),
    db: Session = Depends(get_db),
):
    """
    WebSocket stream for tournament live monitoring.

    **Authentication**: Bearer JWT in the ``token`` query parameter.
    Connection is rejected with close-code 4001 for invalid tokens and
    4003 for insufficient role.

    **Throttle**: at most ``WS_THROTTLE_INTERVAL`` seconds between frames;
    stale intermediate events are dropped so the client always sees the
    latest aggregate state.

    **Payload**: each text frame is a JSON object conforming to
    :class:`~app.core.redis_pubsub.TournamentUpdateEvent`.

    **Observability events** (server-injected, not from Redis):
    - ``throttle_stats``: sent every ``WS_STATS_INTERVAL`` s with drop-rate.
    - ``pitch_idle_alert``: sent when a pitch has no activity > ``PITCH_IDLE_ALERT_S``.
    """
    # ── Authenticate ────────────────────────────────────────────────────────
    username = verify_token(token, "access")
    if username is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user = db.query(User).filter(User.email == username).first()
    if user is None or not user.is_active or user.role not in _ALLOWED_ROLES:
        await websocket.close(code=4003, reason="Forbidden")
        return

    await websocket.accept()
    logger.info(
        "WS connected: tournament=%d user=%d role=%s",
        tournament_id, user.id, user.role,
    )

    # ── Observability counters ───────────────────────────────────────────────
    stats: dict = {"received": 0, "forwarded": 0, "dropped": 0}

    # ── Background task: emit throttle_stats every WS_STATS_INTERVAL s ──────
    async def _stats_reporter() -> None:
        try:
            while True:
                await asyncio.sleep(WS_STATS_INTERVAL)
                received = stats["received"]
                forwarded = stats["forwarded"]
                dropped = stats["dropped"]
                drop_rate = round(dropped / received * 100, 1) if received else 0.0
                payload = json.dumps({
                    "type": "throttle_stats",
                    "received": received,
                    "forwarded": forwarded,
                    "dropped": dropped,
                    "drop_rate_pct": drop_rate,
                })
                try:
                    await websocket.send_text(payload)
                    logger.debug(
                        "WS stats tournament=%d: recv=%d fwd=%d drop=%d (%.1f%%)",
                        tournament_id, received, forwarded, dropped, drop_rate,
                    )
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    # ── Background task: emit pitch_idle_alert every WS_IDLE_CHECK_INTERVAL s
    async def _idle_watcher() -> None:
        try:
            while True:
                await asyncio.sleep(WS_IDLE_CHECK_INTERVAL)
                idle_pitches = get_idle_pitches(tournament_id, PITCH_IDLE_ALERT_S)
                for entry in idle_pitches:
                    alert = json.dumps({
                        "type": "pitch_idle_alert",
                        "pitch_id": entry["pitch_id"],
                        "campus_id": entry.get("campus_id"),
                        "idle_seconds": entry["idle_seconds"],
                        "tournament_id": tournament_id,
                    })
                    try:
                        await websocket.send_text(alert)
                        logger.warning(
                            "Pitch idle alert: tournament=%d pitch=%d idle=%ds",
                            tournament_id, entry["pitch_id"], entry["idle_seconds"],
                        )
                    except Exception:
                        return
        except asyncio.CancelledError:
            pass

    stats_task = asyncio.create_task(_stats_reporter())
    idle_task = asyncio.create_task(_idle_watcher())

    # ── Stream (throttled) ──────────────────────────────────────────────────
    try:
        throttled = _throttled_stream(
            subscribe_tournament_updates(tournament_id),
            interval=WS_THROTTLE_INTERVAL,
            stats=stats,
        )
        async for message in throttled:
            await websocket.send_text(message)

    except WebSocketDisconnect:
        logger.info("WS disconnected: tournament=%d user=%d", tournament_id, user.id)
    except Exception as exc:
        logger.error("WS error tournament=%d: %s", tournament_id, exc)
        try:
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
    finally:
        stats_task.cancel()
        idle_task.cancel()
        received = stats["received"]
        forwarded = stats["forwarded"]
        dropped = stats["dropped"]
        drop_rate = round(dropped / received * 100, 1) if received else 0.0
        logger.info(
            "WS session ended: tournament=%d user=%d "
            "recv=%d fwd=%d drop=%d (%.1f%% drop rate)",
            tournament_id, user.id, received, forwarded, dropped, drop_rate,
        )
        if dropped > 0:
            logger.warning(
                "WS dropped events: tournament=%d dropped=%d — "
                "client received latest state only (no data loss for final counts)",
                tournament_id, dropped,
            )
