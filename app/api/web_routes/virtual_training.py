"""Virtual Training web routes — Phase 2 Color Reaction MVP."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User
from ...models.virtual_training import VirtualTrainingAttempt, VirtualTrainingGame
from ...services.virtual_training_service import VirtualTrainingService
from .helpers import require_student_onboarding
from .student_features import _spec_ctx
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["virtual-training"])


# ── Hub ───────────────────────────────────────────────────────────────────────

@router.get("/virtual-training", response_class=HTMLResponse)
async def virtual_training_hub(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Virtual Training hub — lists active mini-games."""
    guard = require_student_onboarding(user)
    if guard:
        return guard

    active_games = VirtualTrainingService.get_games(db)
    return templates.TemplateResponse(
        "virtual_training_hub.html",
        {
            "request": request,
            "user": user,
            **_spec_ctx(user, db),
            "active_games": active_games,
        },
    )


# ── Color Reaction game page ──────────────────────────────────────────────────

@router.get("/virtual-training/color-reaction", response_class=HTMLResponse)
async def virtual_training_color_reaction(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Color Reaction game page — instructions + Vanilla JS game loop."""
    guard = require_student_onboarding(user)
    if guard:
        return guard

    game = VirtualTrainingService.get_game(db, "color_reaction")
    if game is None or not game.is_active:
        return templates.TemplateResponse(
            "virtual_training_hub.html",
            {
                "request": request,
                "user": user,
                **_spec_ctx(user, db),
                "active_games": VirtualTrainingService.get_games(db),
                "error": "Color Reaction is not available at this time.",
            },
        )

    # Daily attempt count for the UI (show remaining attempts)
    today_start = datetime.combine(
        datetime.now(timezone.utc).date(),
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)
    attempts_today = (
        db.query(VirtualTrainingAttempt)
        .filter(
            VirtualTrainingAttempt.user_id == user.id,
            VirtualTrainingAttempt.game_id == game.id,
            VirtualTrainingAttempt.started_at >= today_start,
            VirtualTrainingAttempt.is_valid == True,  # noqa: E712
        )
        .count()
    )

    return templates.TemplateResponse(
        "virtual_training_color_reaction.html",
        {
            "request": request,
            "user": user,
            **_spec_ctx(user, db),
            "game": game,
            "attempts_today": attempts_today,
            "max_daily_attempts": game.max_daily_attempts,
            "attempts_remaining": max(0, game.max_daily_attempts - attempts_today),
        },
    )


# ── Submit attempt (JSON API) ─────────────────────────────────────────────────

@router.post("/virtual-training/color-reaction/submit")
async def virtual_training_color_reaction_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Record a Color Reaction attempt. Returns attempt_id, xp_awarded, is_valid."""
    guard = require_student_onboarding(user)
    if guard:
        return JSONResponse({"error": "onboarding required"}, status_code=403)

    game = VirtualTrainingService.get_game(db, "color_reaction")
    if game is None or not game.is_active:
        return JSONResponse({"error": "game not available"}, status_code=404)

    body = await request.json()

    # Daily cap guard
    today_start = datetime.combine(
        datetime.now(timezone.utc).date(),
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)
    valid_today = (
        db.query(VirtualTrainingAttempt)
        .filter(
            VirtualTrainingAttempt.user_id == user.id,
            VirtualTrainingAttempt.game_id == game.id,
            VirtualTrainingAttempt.started_at >= today_start,
            VirtualTrainingAttempt.is_valid == True,  # noqa: E712
        )
        .count()
    )
    if valid_today >= game.max_daily_attempts:
        return JSONResponse(
            {"error": "daily_cap", "message": "Daily attempt limit reached for this game."},
            status_code=429,
        )

    # Build idempotency key from client-supplied started_at so retries are safe
    started_at_raw = body.get("started_at", "")
    idem_key = f"vt_cr_u{user.id}_{started_at_raw}"

    attempt = VirtualTrainingService.record_attempt(
        db=db,
        user_id=user.id,
        game=game,
        data=body,
        idempotency_key=idem_key,
    )

    db.commit()

    return JSONResponse({
        "attempt_id": attempt.id,
        "is_valid": attempt.is_valid,
        "invalid_reason": attempt.invalid_reason,
        "xp_awarded": attempt.xp_awarded,
        "skill_deltas": attempt.skill_deltas,
        "attempt_index_today": attempt.attempt_index_today,
        "score_normalized": attempt.score_normalized,
    })


# ── Result page ───────────────────────────────────────────────────────────────

@router.get("/virtual-training/color-reaction/result/{attempt_id}",
            response_class=HTMLResponse)
async def virtual_training_color_reaction_result(
    attempt_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Result screen for a completed Color Reaction attempt."""
    guard = require_student_onboarding(user)
    if guard:
        return guard

    attempt = (
        db.query(VirtualTrainingAttempt)
        .filter(
            VirtualTrainingAttempt.id == attempt_id,
            VirtualTrainingAttempt.user_id == user.id,
        )
        .first()
    )
    if attempt is None:
        return templates.TemplateResponse(
            "virtual_training_hub.html",
            {
                "request": request,
                "user": user,
                **_spec_ctx(user, db),
                "active_games": VirtualTrainingService.get_games(db),
                "error": "Attempt not found.",
            },
        )

    game = db.query(VirtualTrainingGame).filter(
        VirtualTrainingGame.id == attempt.game_id
    ).first()

    return templates.TemplateResponse(
        "virtual_training_result.html",
        {
            "request": request,
            "user": user,
            **_spec_ctx(user, db),
            "attempt": attempt,
            "game": game,
        },
    )


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/virtual-training/history", response_class=HTMLResponse)
async def virtual_training_history(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Attempt history — last 20 valid attempts across all VT games."""
    guard = require_student_onboarding(user)
    if guard:
        return guard

    attempts = (
        db.query(VirtualTrainingAttempt)
        .filter(
            VirtualTrainingAttempt.user_id == user.id,
            VirtualTrainingAttempt.is_valid == True,  # noqa: E712
        )
        .order_by(VirtualTrainingAttempt.completed_at.desc())
        .limit(20)
        .all()
    )

    # Build game lookup map to avoid N+1 in template
    game_ids = {a.game_id for a in attempts}
    games = {
        g.id: g
        for g in db.query(VirtualTrainingGame)
        .filter(VirtualTrainingGame.id.in_(game_ids))
        .all()
    } if game_ids else {}

    return templates.TemplateResponse(
        "virtual_training_history.html",
        {
            "request": request,
            "user": user,
            **_spec_ctx(user, db),
            "attempts": attempts,
            "games": games,
        },
    )
