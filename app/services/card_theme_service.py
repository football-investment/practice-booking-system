"""
Player Card Theme Service
=========================
Manages colour themes for the public LFA Football Player card.

Free themes (default, midnight, arctic) are always available.
Premium themes (gold, emerald, crimson) require credit purchase.

Adding a new theme requires only a new entry in THEMES below.
The browser card reads ThemeDefinition fields directly via a Jinja2 :root
injection block in player_card_base.html — no separate CSS class needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .credit_service import CreditService
from .card_draft_service import CardDraftService


@dataclass(frozen=True)
class ThemeDefinition:
    id: str
    label: str
    is_premium: bool
    credit_cost: int
    # Core CSS custom-property values — injected as inline :root vars in templates
    panel_bg: str       # --card-panel-bg  (fifa-left gradient)
    body_bg: str        # --card-body-bg   (skills + events section)
    tab_bg: str         # --card-tab-bg    (tab bar)
    accent: str         # --card-accent    (active tab underline, badge tints)
    page_bg: str        # --card-page-bg   (page chrome behind the card)
    # Dot colour shown in the dashboard theme picker
    dot_color: str
    # True when body_bg is light-coloured — templates emit dark-on-light tokens
    is_light_body_bg: bool = False
    # Per-theme tokens that vary within the dark palette (light themes use rgba(0,0,0,...))
    text_faint: str = 'rgba(255,255,255,0.35)'   # --card-text-faint  (labels, titles)
    val_neutral: str = 'rgba(255,255,255,0.85)'  # --card-val-neutral (skill values)
    skill_up: str = '#48bb78'                     # --card-skill-up
    skill_dn: str = '#fc8181'                     # --card-skill-dn


# ── Theme registry ────────────────────────────────────────────────────────────
THEMES: dict[str, ThemeDefinition] = {
    "default": ThemeDefinition(
        id="default", label="Slate", is_premium=False, credit_cost=0,
        panel_bg="linear-gradient(155deg, #1a2744 0%, #2a3a5c 60%, #1e3a4a 100%)",
        body_bg="#1a202c", tab_bg="#2d3748", accent="#667eea",
        page_bg="#0f1923", dot_color="#667eea",
    ),
    "midnight": ThemeDefinition(
        id="midnight", label="Midnight", is_premium=False, credit_cost=0,
        panel_bg="linear-gradient(155deg, #0d0d0d 0%, #1a1a2e 60%, #16213e 100%)",
        body_bg="#0f0f0f", tab_bg="#1a1a1a", accent="#00d4ff",
        page_bg="#050505", dot_color="#00d4ff",
        text_faint='rgba(255,255,255,0.35)', val_neutral='rgba(255,255,255,0.85)',
    ),
    "arctic": ThemeDefinition(
        id="arctic", label="Arctic", is_premium=False, credit_cost=0,
        panel_bg="linear-gradient(155deg, #1a2744 0%, #2a3a5c 60%, #1e3a4a 100%)",
        body_bg="#f7fafc", tab_bg="#edf2f7", accent="#4299e1",
        page_bg="#e2e8f0", dot_color="#4299e1",
        is_light_body_bg=True,
        text_faint='rgba(0,0,0,0.30)', val_neutral='rgba(0,0,0,0.70)',
        skill_up='#276749', skill_dn='#c53030',
    ),
    "gold": ThemeDefinition(
        id="gold", label="Gold", is_premium=True, credit_cost=500,
        panel_bg="linear-gradient(155deg, #3d2200 0%, #5c3500 60%, #3d2200 100%)",
        body_bg="#1e1500", tab_bg="#2d1f00", accent="#f6ad3c",
        page_bg="#120d00", dot_color="#f6ad3c",
        text_faint='rgba(255,255,255,0.48)', val_neutral='rgba(255,255,255,0.68)',
    ),
    "emerald": ThemeDefinition(
        id="emerald", label="Emerald", is_premium=True, credit_cost=500,
        panel_bg="linear-gradient(155deg, #0a2d0a 0%, #144d1e 60%, #0a2d14 100%)",
        body_bg="#0d1f0d", tab_bg="#142b14", accent="#4cde82",
        page_bg="#060f06", dot_color="#4cde82",
        text_faint='rgba(255,255,255,0.48)', val_neutral='rgba(255,255,255,0.68)',
    ),
    "crimson": ThemeDefinition(
        id="crimson", label="Crimson", is_premium=True, credit_cost=500,
        panel_bg="linear-gradient(155deg, #3d0a0a 0%, #5c1414 60%, #3d0a14 100%)",
        body_bg="#1e0d0d", tab_bg="#2d1010", accent="#ff6b6b",
        page_bg="#120404", dot_color="#ff6b6b",
        text_faint='rgba(255,255,255,0.38)', val_neutral='rgba(255,255,255,0.65)',
        skill_up='#68d391', skill_dn='#ffb3b3',
    ),
}

# Ordered list for the picker UI (free first, then premium)
THEME_ORDER = ["default", "midnight", "arctic", "gold", "emerald", "crimson"]


# ── Public API ────────────────────────────────────────────────────────────────

def get_theme(theme_id: str) -> ThemeDefinition:
    """Return theme by ID, falling back to 'default' for unknown IDs."""
    return THEMES.get(theme_id, THEMES["default"])


def get_all_themes() -> list[ThemeDefinition]:
    """Return all themes in display order."""
    return [THEMES[tid] for tid in THEME_ORDER if tid in THEMES]


def is_unlocked(user_license, theme_id: str) -> bool:
    """
    Return True if the user may use this theme.
    Free themes are always unlocked.
    Premium themes require the theme_id to be in user_license.unlocked_card_themes.
    """
    theme = THEMES.get(theme_id)
    if theme is None:
        return False
    if not theme.is_premium:
        return True
    unlocked = user_license.unlocked_card_themes or []
    return theme_id in unlocked


def apply_theme(db, user_license, theme_id: str) -> None:
    """
    Set the active draft theme on the player CardDraft and commit.
    Raises ValueError if theme unknown or not yet unlocked.
    """
    if theme_id not in THEMES:
        raise ValueError(f"Unknown theme: {theme_id!r}")
    if not is_unlocked(user_license, theme_id):
        theme = THEMES[theme_id]
        raise ValueError(
            f"Theme '{theme.label}' is locked. Required: {theme.credit_cost} CR"
        )
    draft = CardDraftService.get_player_card_draft(db, user_id=user_license.user_id)
    CardDraftService.update_draft_theme(db, draft, theme_id)


def unlock_theme(db, user, user_license, theme_id: str) -> None:
    """
    Unlock a premium theme for the user.

    Uses CreditService.deduct() which wraps the balance UPDATE and the CT INSERT
    inside a single SAVEPOINT — both succeed or both roll back together.

    Raises ValueError (InsufficientCreditsError) if theme unknown, already
    unlocked, or insufficient balance.
    """
    if theme_id not in THEMES:
        raise ValueError(f"Unknown theme: {theme_id!r}")
    theme = THEMES[theme_id]
    if not theme.is_premium:
        return  # free themes don't need unlocking
    unlocked: list = list(user_license.unlocked_card_themes or [])
    if theme_id in unlocked:
        return  # already unlocked — idempotent

    # Ensure the draft row exists before the credit SAVEPOINT so any draft-creation
    # commit is isolated from the credit + unlock transaction below.
    draft = CardDraftService.get_player_card_draft(db, user_id=user_license.user_id)

    # Atomic deduction + CT insert (SAVEPOINT guarantees coupling).
    # InsufficientCreditsError propagates to the caller unchanged.
    CreditService(db).deduct(
        user=user,
        amount=theme.credit_cost,
        transaction_type="THEME_UNLOCK",
        description=f"Card theme unlock: {theme.label}",
        idempotency_key=f"theme_unlock_{user.id}_{theme_id}",
    )

    # Update unlocked list and stage draft theme (commit=False keeps one outer commit)
    unlocked.append(theme_id)
    user_license.unlocked_card_themes = unlocked
    CardDraftService.update_draft_theme(db, draft, theme_id, commit=False)

    db.commit()
