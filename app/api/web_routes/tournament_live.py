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
"""
from __future__ import annotations

import asyncio
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
from app.core.redis_pubsub import subscribe_tournament_updates

logger = logging.getLogger(__name__)

router = APIRouter()

_BASE = Path(__file__).resolve().parent.parent.parent  # app/
templates = Jinja2Templates(directory=str(_BASE / "templates"))

_ALLOWED_ROLES = {UserRole.ADMIN, UserRole.SPORT_DIRECTOR, UserRole.INSTRUCTOR}

# ── Rate-limit constant (override in tests via monkeypatch) ──────────────────
WS_THROTTLE_INTERVAL: float = 0.2  # 200 ms → max 5 frames/sec per connection


# ── Throttle helper (testable standalone) ────────────────────────────────────

async def _throttled_stream(
    source: AsyncIterator[str],
    interval: float = WS_THROTTLE_INTERVAL,
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

    Yields:
        str — the latest buffered message, at most once per ``interval``.
    """
    # Single-slot queue: always holds the most-recent message
    queue: asyncio.Queue[object] = asyncio.Queue(maxsize=1)
    _DONE = object()  # sentinel to signal source exhaustion

    async def _producer() -> None:
        try:
            async for item in source:
                if queue.full():
                    try:
                        queue.get_nowait()  # Drop stale item
                    except asyncio.QueueEmpty:
                        pass
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    # Consumer removed it between our checks — harmless
                    pass
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

    # ── Stream (throttled) ──────────────────────────────────────────────────
    try:
        throttled = _throttled_stream(
            subscribe_tournament_updates(tournament_id),
            interval=WS_THROTTLE_INTERVAL,
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
