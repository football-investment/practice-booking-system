"""Card Studio unified shell routes (CS-S0 / CS-S2A).

Single unified studio shell with card-type switcher.
CS-S0 MVP: Welcome Card mode fully functional.
CS-S2A: Player Card mode — preview-only shell (no write functions).
Challenge mode remains Coming Soon.

Canonical routes:
  GET /card-studio              → shell (Welcome default)
  GET /card-studio/welcome      → shell, Welcome mode
  GET /card-studio/welcome?format=X → shell, Welcome mode, specific format
  GET /card-studio/player       → shell, Player mode (CS-S2A preview MVP)

Backward-compat routes remain in card_editor.py unchanged.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.license import UserLicense
from ...models.user import User
from ...services.card_design_service import get_owned_design_ids
from ...services.card_design_service import (
    WELCOME_CARD_FORMATS,
    get_card_family,
)
from ...services.mood_photo_service import get_mood_photos_for_user
from ...services.card_theme_service import get_all_themes as _get_all_themes
from ...services.card_draft_service import CardDraftService as _CardDraftService
from .card_editor import (
    _WC_FORMAT_BY_ID,
    _WC_RATIO,
    _WC_VALID_IDS,
    _MOOD_SLOT_META,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["card-studio"])

# ── Helpers ───────────────────────────────────────────────────────────────────

_STUDIO_NAV_CTX = {
    "spec_dashboard_url":  "/dashboard/lfa-football-player",
    "spec_dashboard_icon": "⚽",
    "spec_profile_url":    "/profile/lfa-football-player",
    "spec_profile_icon":   "🪪",
}

_WELCOME_FORMATS_ORDERED = WELCOME_CARD_FORMATS  # 7 formats, canonical order


def _license_guard(db: Session, user_id: int):
    """Return active LFA license or None."""
    return db.query(UserLicense).filter(
        UserLicense.user_id == user_id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
    ).first()


def _resolve_welcome_context(db: Session, user, format_id: str | None):
    """
    Resolve all context needed for Welcome mode in the unified shell.
    Returns (context_dict, redirect_url_or_None).
    redirect_url: caller must issue 303 redirect if set.
    """
    lic = _license_guard(db, user.id)
    if not lic:
        return None, "/dashboard?info=complete_lfa_onboarding_first"
    if not lic.onboarding_completed:
        return None, "/specialization/lfa-player/onboarding"

    owned_set = set(get_owned_design_ids(db, user.id, "welcome_card")) & _WC_VALID_IDS
    owned_formats_ordered = [f for f in _WELCOME_FORMATS_ORDERED if f.design_id in owned_set]
    if not owned_formats_ordered:
        return None, "/shop?type=welcome_card"

    first_owned_id = owned_formats_ordered[0].design_id

    if format_id is None or format_id not in owned_set:
        return None, f"/card-studio/welcome?format={first_owned_id}"

    fmt = _WC_FORMAT_BY_ID[format_id]
    ratio_class = _WC_RATIO.get(fmt.preview_platform, "mfg-ratio-11")

    # CS-COLOR-1A: read active theme from Welcome Card draft, default to "default"
    welcome_draft = _CardDraftService.get_draft(db, user.id, "welcome_card")
    active_theme  = welcome_draft.draft_theme or "default"

    # CS-COLOR-1A: free themes only (no shop/unlock scope in COLOR-1)
    card_themes = [t for t in _get_all_themes(db) if not t.is_premium]

    preview_url = f"/profile/onboarding-card?platform={fmt.preview_platform}&theme={active_theme}"
    export_url  = f"/profile/onboarding-card/export?platform={fmt.preview_platform}&theme={active_theme}"

    owned_format_rows = [
        {
            "design_id":   f.design_id,
            "label":       f.label,
            "style_tag":   f.style_tag,
            "dims":        f.dims,
            "preview_url": f"/profile/onboarding-card?platform={f.preview_platform}&theme={active_theme}",
            "active":      f.design_id == format_id,
        }
        for f in owned_formats_ordered
    ]

    mood_photos = get_mood_photos_for_user(user.id, db)

    ctx = {
        "active_type":        "welcome",
        "active_format":      format_id,
        "active_theme":       active_theme,
        "card_themes":        card_themes,
        "fmt":                fmt,
        "ratio_class":        ratio_class,
        "preview_url":        preview_url,
        "export_url":         export_url,
        "owned_format_rows":  owned_format_rows,
        "wc_photo_url":           lic.wc_photo_url,
        "wc_photo_portrait_url":  lic.wc_photo_portrait_url,
        "wc_photo_landscape_url": lic.wc_photo_landscape_url,
        "mood_photos":            mood_photos,
        "mood_slot_meta":         _MOOD_SLOT_META,
        **_STUDIO_NAV_CTX,
    }
    return ctx, None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/card-studio", response_class=HTMLResponse)
async def card_studio_default(
    request: Request,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    """Card Studio landing — defaults to Welcome mode for CS-S0.

    Renders the unified shell with Welcome Card active.
    Player and Challenge shown as Coming Soon.
    """
    # CS-S0: default to Welcome — redirect to canonical with first owned format
    lic = _license_guard(db, user.id)
    if not lic or not lic.onboarding_completed:
        target = "/dashboard?info=complete_lfa_onboarding_first" if not lic else "/specialization/lfa-player/onboarding"
        return RedirectResponse(url=target, status_code=303)

    owned_set = set(get_owned_design_ids(db, user.id, "welcome_card")) & _WC_VALID_IDS
    if owned_set:
        first = next((f.design_id for f in _WELCOME_FORMATS_ORDERED if f.design_id in owned_set), None)
        if first:
            return RedirectResponse(url=f"/card-studio/welcome?format={first}", status_code=303)

    return RedirectResponse(url="/shop?type=welcome_card", status_code=303)


@router.get("/card-studio/welcome", response_class=HTMLResponse)
async def card_studio_welcome(
    request:   Request,
    format_id: str | None = Query(default=None, alias="format"),
    db:        Session    = Depends(get_db),
    user:      User       = Depends(get_current_user_web),
):
    """Unified Studio shell — Welcome Card mode (CS-S0 fully functional)."""
    ctx, redirect = _resolve_welcome_context(db, user, format_id)
    if redirect:
        return RedirectResponse(url=redirect, status_code=303)

    return templates.TemplateResponse(
        "card_studio_shell.html",
        {"request": request, "user": user, **ctx},
    )


# ── CS-S2A: Player Card mode (preview-only MVP) ───────────────────────────────

def _resolve_player_context(db: Session, user):
    """Build context for Player Card shell (CS-S2A: preview-only, no write).

    Guards: LFA license + onboarding complete.
    Reads CardDraft(player_card) for active variant/theme — read-only.
    """
    lic = _license_guard(db, user.id)
    if not lic:
        return None, "/dashboard?info=complete_lfa_onboarding_first"
    if not lic.onboarding_completed:
        return None, "/specialization/lfa-player/onboarding"

    # Read active variant + theme from draft (read-only, no write in CS-S2A)
    try:
        draft = _CardDraftService.get_draft(db, user.id, "player_card")
        active_variant = draft.draft_variant or "fclassic"
        active_theme   = draft.draft_theme   or "default"
    except Exception:
        active_variant = "fclassic"
        active_theme   = "default"

    # Preview URL: native player card render with current draft state
    preview_url = (
        f"/players/{user.id}/card"
        f"?preview={active_variant}&theme={active_theme}&native_export=1"
    )

    ctx = {
        "active_type":     "player",
        "active_variant":  active_variant,
        "active_theme":    active_theme,
        "preview_url":     preview_url,
        "legacy_editor_url": "/card-editor/player",
        **_STUDIO_NAV_CTX,
    }
    return ctx, None


@router.get("/card-studio/player", response_class=HTMLResponse)
async def card_studio_player(
    request: Request,
    db:      Session = Depends(get_db),
    user:    User    = Depends(get_current_user_web),
):
    """CS-S2A: Player Card Studio — preview-only MVP.

    Read-only: shows current player card preview iframe.
    Write functions (photo upload, variant/platform/theme change, publish, export)
    are deferred to CS-S2B..D.
    Legacy editor CTA links to /card-editor/player for full write access.
    """
    ctx, redirect = _resolve_player_context(db, user)
    if redirect:
        return RedirectResponse(url=redirect, status_code=303)

    return templates.TemplateResponse(
        "card_studio_shell.html",
        {"request": request, "user": user, **ctx},
    )
