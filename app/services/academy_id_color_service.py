"""
Academy ID dedicated colour service — Phase 1 (free colours only).

This module is completely isolated from the Player Card, Welcome Card, and
Challenge Card colour/theme systems.  It must NOT import from:
  - card_color_service
  - card_theme_service
  - shop_catalog_service

The academy_id colour family uses card_type_id = 'academy_id' in
card_color_ownership (Phase 2 will add premium colours there).
Phase 1 only stores the active colour in user_licenses.academy_id_color.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from ..models.license import UserLicense


# ── Phase 1 Palette — Free colours only ──────────────────────────────────────
# Visually distinct from Player Card themes (default/midnight/arctic/gold/…).
# ID-card aesthetic: official document palette — restrained, authoritative.

@dataclass(frozen=True)
class AcademyIDColor:
    id:          str
    label:       str
    dot_color:   str   # hex — shown in the iOS swatch picker
    sort_order:  int
    # Forward-compatible fields for Phase 2 (always False/0 in Phase 1)
    is_premium:  bool = False
    credit_cost: int  = 0


ACADEMY_ID_COLORS: list[AcademyIDColor] = [
    AcademyIDColor(
        id="official",
        label="Official",
        dot_color="#b8a06a",   # warm gold — the default card look
        sort_order=0,
    ),
    AcademyIDColor(
        id="ivory",
        label="Ivory",
        dot_color="#d4c5a0",   # soft warm white
        sort_order=1,
    ),
    AcademyIDColor(
        id="charcoal",
        label="Charcoal",
        dot_color="#3a3a3a",   # near-black, elegant dark surface
        sort_order=2,
    ),
]

_VALID_COLOR_IDS: frozenset[str] = frozenset(c.id for c in ACADEMY_ID_COLORS)


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_all_colors() -> list[AcademyIDColor]:
    """Return the full Phase-1 palette, ordered by sort_order."""
    return ACADEMY_ID_COLORS


def get_active_color_id(user_license: UserLicense) -> str:
    """
    Return the active Academy ID colour for this licence.

    Falls back to 'official' if the stored value is missing or unknown
    (handles pre-migration rows and any future data inconsistency).
    """
    stored = getattr(user_license, "academy_id_color", None) or "official"
    return stored if stored in _VALID_COLOR_IDS else "official"


def is_valid_color(color_id: str) -> bool:
    return color_id in _VALID_COLOR_IDS


# ── Write helpers ─────────────────────────────────────────────────────────────

def set_active_color(
    db: Session,
    user_license: UserLicense,
    color_id: str,
) -> str:
    """
    Persist the selected colour for this licence.

    Raises ValueError for unknown colour IDs.
    Phase 1: all colours are free — no ownership or credit check required.
    Phase 2: premium colour guard will be added before this write.

    Returns the validated colour ID.
    """
    if color_id not in _VALID_COLOR_IDS:
        raise ValueError(
            f"Unknown Academy ID colour: {color_id!r}. "
            f"Valid options: {sorted(_VALID_COLOR_IDS)}"
        )
    user_license.academy_id_color = color_id
    db.commit()
    return color_id
