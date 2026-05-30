"""Card Editor routes — family-specific customizer/export pages.

Phase WCE-1:  Welcome Card Customizer (preview + export wrapper, no draft).
Phase CE-3.1: Card Studio landing — /card-editor entry point.
Future: /card-editor/player/{collection_id}, /card-editor/challenge/{id}
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...services.card_design_service import (
    CHALLENGE_CARD_FORMATS,
    WELCOME_CARD_FORMATS,
    get_owned_design_ids,
    is_design_accessible,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["card-editor"])

# Lookup map: design_id → NonPlayerCardFormatDefinition
_WC_FORMAT_BY_ID = {f.design_id: f for f in WELCOME_CARD_FORMATS}

# Aspect-ratio CSS class per preview_platform
_WC_RATIO: dict[str, str] = {
    "instagram_portrait":  "mfg-ratio-45",
    "instagram_story":     "mfg-ratio-916",
    "instagram_square":    "mfg-ratio-11",
    "tiktok":              "mfg-ratio-916",
    "facebook_square":     "mfg-ratio-11",
    "facebook_landscape":  "mfg-ratio-169",
    "banner_custom":       "mfg-ratio-169",
}

# Valid design-ID sets for WC / CC (used in landing ownership count)
_WC_VALID_IDS: frozenset[str] = frozenset(f.design_id for f in WELCOME_CARD_FORMATS)
_CC_VALID_IDS: frozenset[str] = frozenset(f.design_id for f in CHALLENGE_CARD_FORMATS)


# ── Card Studio Landing ───────────────────────────────────────────────────────

@router.get("/card-editor", response_class=HTMLResponse)
async def card_studio_landing(
    request: Request,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user_web),
):
    """Card Studio landing — family picker entry point (CE-3.1).

    Shows owned-design counts for all three card families and routes the user
    to the appropriate editor or shop.  No family-specific license guard here;
    each family editor enforces its own guard.
    """
    pc_owned_count = len(get_owned_design_ids(db, user.id, "player_card"))

    wc_owned_count = len(
        set(get_owned_design_ids(db, user.id, "welcome_card")) & _WC_VALID_IDS
    )
    cc_owned_count = len(
        set(get_owned_design_ids(db, user.id, "challenge_card")) & _CC_VALID_IDS
    )

    any_owned = pc_owned_count > 0 or wc_owned_count > 0 or cc_owned_count > 0

    return templates.TemplateResponse(
        "card_studio_landing.html",
        {
            "request":         request,
            "user":            user,
            "pc_owned_count":  pc_owned_count,
            "wc_owned_count":  wc_owned_count,
            "cc_owned_count":  cc_owned_count,
            "any_owned":       any_owned,
            # Standard LFA spec nav context (used by spec_subpage_hdr.html)
            "spec_dashboard_url":  "/dashboard/lfa-football-player",
            "spec_dashboard_icon": "⚽",
            "spec_profile_url":    "/profile/lfa-football-player",
            "spec_profile_icon":   "🪪",
        },
    )


# ── Welcome Card Customizer ───────────────────────────────────────────────────

@router.get("/card-editor/welcome/{format_id}", response_class=HTMLResponse)
async def welcome_card_editor(
    format_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User  = Depends(get_current_user_web),
):
    """Welcome Card Customizer — preview + export wrapper for an owned format.

    Guards (in order):
      1. Authenticated (get_current_user_web)
      2. LFA_FOOTBALL_PLAYER license + onboarding complete
      3. format_id in WELCOME_CARD_FORMATS → 404 otherwise
      4. CDO ownership (is_design_accessible) → redirect shop if not owned
         Admin bypass: skipped for UserRole.ADMIN
    """
    # ── Guard 2: license + onboarding ────────────────────────────────────────
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
    ).first()
    if not license:
        return RedirectResponse(
            url="/dashboard?info=complete_lfa_onboarding_first", status_code=303
        )
    if not license.onboarding_completed:
        return RedirectResponse(
            url="/specialization/lfa-player/onboarding", status_code=303
        )

    # ── Guard 3: known format ─────────────────────────────────────────────────
    fmt = _WC_FORMAT_BY_ID.get(format_id)
    if fmt is None:
        raise HTTPException(status_code=404, detail=f"Unknown Welcome Card format: {format_id!r}")

    # ── Guard 4: ownership ────────────────────────────────────────────────────
    if user.role != UserRole.ADMIN:
        if not is_design_accessible(db, user.id, "welcome_card", format_id):
            return RedirectResponse(
                url="/shop/cards/welcome?error=not_owned", status_code=303
            )

    ratio_class = _WC_RATIO.get(fmt.preview_platform, "mfg-ratio-11")
    preview_url = f"/profile/onboarding-card?platform={fmt.preview_platform}"
    export_url  = f"/profile/onboarding-card/export?platform={fmt.preview_platform}"

    return templates.TemplateResponse(
        "card_editor_welcome.html",
        {
            "request":     request,
            "user":        user,
            "fmt":         fmt,
            "format_id":   format_id,
            "ratio_class": ratio_class,
            "preview_url": preview_url,
            "export_url":  export_url,
        },
    )
