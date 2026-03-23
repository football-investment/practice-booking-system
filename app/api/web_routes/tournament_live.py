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
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

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

    # Aggregate stats for initial page render
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

    Clients authenticate via the `token` query parameter (the same JWT used
    for Bearer auth).  The connection is rejected with 4001 if the token is
    invalid or the user lacks permission.

    Each message sent by the server is a JSON object:
    {
      "type": "session_result",
      "session_id": <int>,
      "campus_id": <int|null>,
      "pitch_id": <int|null>,
      "round_number": <int|null>,
      "status": "completed",
      "completed_count": <int>,
      "total_count": <int>,
      "progress_pct": <float>
    }
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

    # ── Stream ──────────────────────────────────────────────────────────────
    try:
        async for message in subscribe_tournament_updates(tournament_id):
            await websocket.send_text(message)
    except WebSocketDisconnect:
        logger.info("WS disconnected: tournament=%d user=%d", tournament_id, user.id)
    except Exception as exc:
        logger.error("WS error tournament=%d: %s", tournament_id, exc)
        try:
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
