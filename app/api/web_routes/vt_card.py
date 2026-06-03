"""Virtual Training Card routes.

Routes:
  GET /virtual-training/card/preview          → single-game card HTML (eligibility-gated)
  GET /virtual-training/card/export           → single-game card PNG (eligibility-gated)
  GET /virtual-training/card/reward/preview   → reward card HTML (tier eligibility-gated)
  GET /virtual-training/card/reward/export    → reward card PNG (tier eligibility-gated)

Eligibility:
  - Single-game: user must have completed >= game.max_daily_attempts valid standalone
    attempts for the requested game on the requested date.
  - Reward: user must have completed >= tier distinct games today (each game fully
    completed, standalone only).
  - No credit/CDO ownership required — cards are earned by playing.

Platforms:
  - Single-game: vt_landscape (1280×720) | vt_portrait (1080×1920)
  - Reward:      vt_reward_landscape (1280×720) | vt_reward_portrait (1080×1920)
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_optional, get_current_user_web
from ...models.user import User
from ...models.virtual_training import VirtualTrainingGame
from ...services import card_export_service as _export_svc
from ...services.card_constants import VT_CARD_PLATFORMS, VT_REWARD_CARD_PLATFORMS
from ...services.vt_card_eligibility import (
    REWARD_TIERS,
    check_reward_eligibility,
    check_single_game_eligibility,
)

router = APIRouter()
templates = Jinja2Templates(
    directory="app/templates",
)

# ── Template map ───────────────────────────────────────────────────────────────

_VT_TEMPLATE: dict[str, str] = {
    "vt_landscape": "public/export/vt/landscape.html",
    "vt_portrait":  "public/export/vt/portrait.html",
}
_VT_REWARD_TEMPLATE: dict[str, str] = {
    "vt_reward_landscape": "public/export/vt_reward/landscape.html",
    "vt_reward_portrait":  "public/export/vt_reward/portrait.html",
}


# ── Render token auth helpers ─────────────────────────────────────────────────

def _resolve_vt_render_token(token: str, db: Session) -> "User | None":
    """Validate a vtc_render JWT and return the corresponding User, or None."""
    try:
        from jose import jwt as _jwt  # noqa: PLC0415
        from ...config import settings  # noqa: PLC0415
        payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("purpose") != "vtc_render":
            return None
        user_id = int(payload.get("sub") or 0)
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
    except Exception:  # noqa: BLE001
        return None


def _parse_date(date_str: str | None) -> date:
    if date_str is None:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date format: {date_str!r}. Expected YYYY-MM-DD.",
        )


# ── Single-game preview ───────────────────────────────────────────────────────

@router.get("/virtual-training/card/preview", response_class=HTMLResponse)
async def vt_card_preview(
    request: Request,
    game_id: int           = Query(..., description="VirtualTrainingGame.id"),
    platform: str          = Query(..., description="vt_landscape | vt_portrait"),
    date_str: str | None   = Query(default=None, alias="date", description="YYYY-MM-DD"),
    render_token: str | None = Query(default=None),
    db: Session            = Depends(get_db),
    user: "User | None"    = Depends(get_current_user_optional),
):
    if render_token is not None:
        token_user = _resolve_vt_render_token(render_token, db)
        if token_user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired render token")
        user = token_user
    elif user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if platform not in VT_CARD_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported platform: {platform!r}. Valid: {sorted(VT_CARD_PLATFORMS)}",
        )

    day = _parse_date(date_str)
    eligible, count, required = check_single_game_eligibility(db, user.id, game_id, day)
    if not eligible:
        raise HTTPException(
            status_code=403,
            detail=f"Not eligible: {count}/{required} standalone attempts completed for game {game_id}.",
        )

    game = db.query(VirtualTrainingGame).filter(
        VirtualTrainingGame.id == game_id,
        VirtualTrainingGame.is_active == True,  # noqa: E712
    ).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    ctx = {
        "request":          request,
        "game":             game,
        "attempt_date":     day.isoformat(),
        "completed_count":  count,
        "max_attempts":     required,
        "platform":         platform,
    }
    return templates.TemplateResponse(_VT_TEMPLATE[platform], ctx)


# ── Single-game export ────────────────────────────────────────────────────────

@router.get("/virtual-training/card/export")
async def vt_card_export(
    request: Request,
    game_id: int         = Query(..., description="VirtualTrainingGame.id"),
    platform: str        = Query(..., description="vt_landscape | vt_portrait"),
    date_str: str | None = Query(default=None, alias="date", description="YYYY-MM-DD"),
    db: Session          = Depends(get_db),
    user: User           = Depends(get_current_user_web),
):
    from ...config import settings  # noqa: PLC0415
    from ...core.auth import create_vt_card_render_token  # noqa: PLC0415

    if platform not in VT_CARD_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported platform: {platform!r}. Valid: {sorted(VT_CARD_PLATFORMS)}",
        )

    day = _parse_date(date_str)
    eligible, count, required = check_single_game_eligibility(db, user.id, game_id, day)
    if not eligible:
        raise HTTPException(
            status_code=403,
            detail=f"Not eligible: {count}/{required} standalone attempts completed for game {game_id}.",
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_key  = f"vt_card:{game_id}:{user.id}:{client_ip}"
    if not _export_svc.check_export_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Export rate limit exceeded (5 per minute). Please wait before exporting again.",
        )

    token = create_vt_card_render_token(user.id)
    date_param = f"&date={date_str}" if date_str else ""
    render_url = (
        f"http://127.0.0.1:{settings.APP_INTERNAL_PORT}"
        f"/virtual-training/card/preview"
        f"?game_id={game_id}&platform={platform}&render_token={token}{date_param}"
    )

    try:
        png_bytes = await asyncio.to_thread(
            _export_svc._sync_take_screenshot, render_url, platform
        )
    except _export_svc.CardExportTimeoutError:
        raise HTTPException(status_code=504, detail="Card render timed out")

    filename = f"lfa_vt_{game_id}_{day.isoformat()}_{platform}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control":       "no-store",
            "X-Export-Platform":   platform,
            "X-Export-Game-Id":    str(game_id),
        },
    )


# ── Reward preview ────────────────────────────────────────────────────────────

@router.get("/virtual-training/card/reward/preview", response_class=HTMLResponse)
async def vt_reward_card_preview(
    request: Request,
    tier: int              = Query(..., description="Reward tier: 3 | 5 | 10"),
    platform: str          = Query(..., description="vt_reward_landscape | vt_reward_portrait"),
    date_str: str | None   = Query(default=None, alias="date", description="YYYY-MM-DD"),
    render_token: str | None = Query(default=None),
    db: Session            = Depends(get_db),
    user: "User | None"    = Depends(get_current_user_optional),
):
    if render_token is not None:
        token_user = _resolve_vt_render_token(render_token, db)
        if token_user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired render token")
        user = token_user
    elif user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if platform not in VT_REWARD_CARD_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported platform: {platform!r}. Valid: {sorted(VT_REWARD_CARD_PLATFORMS)}",
        )

    if tier not in REWARD_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier: {tier!r}. Valid: {list(REWARD_TIERS)}",
        )

    day = _parse_date(date_str)
    eligible, completed_games = check_reward_eligibility(db, user.id, tier, day)
    if not eligible:
        raise HTTPException(
            status_code=403,
            detail=f"Not eligible for tier-{tier} reward: {completed_games}/{tier} games completed.",
        )

    ctx = {
        "request":          request,
        "tier":             tier,
        "completed_games":  completed_games,
        "attempt_date":     day.isoformat(),
        "platform":         platform,
    }
    return templates.TemplateResponse(_VT_REWARD_TEMPLATE[platform], ctx)


# ── Reward export ─────────────────────────────────────────────────────────────

@router.get("/virtual-training/card/reward/export")
async def vt_reward_card_export(
    request: Request,
    tier: int            = Query(..., description="Reward tier: 3 | 5 | 10"),
    platform: str        = Query(..., description="vt_reward_landscape | vt_reward_portrait"),
    date_str: str | None = Query(default=None, alias="date", description="YYYY-MM-DD"),
    db: Session          = Depends(get_db),
    user: User           = Depends(get_current_user_web),
):
    from ...config import settings  # noqa: PLC0415
    from ...core.auth import create_vt_card_render_token  # noqa: PLC0415

    if platform not in VT_REWARD_CARD_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported platform: {platform!r}. Valid: {sorted(VT_REWARD_CARD_PLATFORMS)}",
        )

    if tier not in REWARD_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier: {tier!r}. Valid: {list(REWARD_TIERS)}",
        )

    day = _parse_date(date_str)
    eligible, completed_games = check_reward_eligibility(db, user.id, tier, day)
    if not eligible:
        raise HTTPException(
            status_code=403,
            detail=f"Not eligible for tier-{tier} reward: {completed_games}/{tier} games completed.",
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_key  = f"vt_reward_card:{tier}:{user.id}:{client_ip}"
    if not _export_svc.check_export_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Export rate limit exceeded (5 per minute). Please wait before exporting again.",
        )

    token = create_vt_card_render_token(user.id)
    date_param = f"&date={date_str}" if date_str else ""
    render_url = (
        f"http://127.0.0.1:{settings.APP_INTERNAL_PORT}"
        f"/virtual-training/card/reward/preview"
        f"?tier={tier}&platform={platform}&render_token={token}{date_param}"
    )

    try:
        png_bytes = await asyncio.to_thread(
            _export_svc._sync_take_screenshot, render_url, platform
        )
    except _export_svc.CardExportTimeoutError:
        raise HTTPException(status_code=504, detail="Card render timed out")

    filename = f"lfa_vt_reward_{tier}_{day.isoformat()}_{platform}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control":       "no-store",
            "X-Export-Platform":   platform,
            "X-Export-Tier":       str(tier),
        },
    )
