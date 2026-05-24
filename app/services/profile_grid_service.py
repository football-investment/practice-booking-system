"""Profile Grid Service — Phase 1 slot registry and module validation.

Slots map to zones in the public profile 5-column grid:
  left_1/2/3   → left rail (top → bottom)
  right_1/2/3  → right rail (top → bottom)
  bottom_1/2/3 → bottom area (left → right)

Phase 1 module types: video_youtube, video_tiktok (link-only).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.services.highlight_video_service import extract_any_video

SLOT_REGISTRY: list[dict] = [
    {"slot_id": "left_1",   "zone": "left",   "label": "Left — Top",      "sort_order":  1},
    {"slot_id": "left_2",   "zone": "left",   "label": "Left — Middle",   "sort_order":  2},
    {"slot_id": "left_3",   "zone": "left",   "label": "Left — Bottom",   "sort_order":  3},
    {"slot_id": "right_1",  "zone": "right",  "label": "Right — Top",     "sort_order": 10},
    {"slot_id": "right_2",  "zone": "right",  "label": "Right — Middle",  "sort_order": 11},
    {"slot_id": "right_3",  "zone": "right",  "label": "Right — Bottom",  "sort_order": 12},
    {"slot_id": "bottom_1", "zone": "bottom", "label": "Bottom — Left",   "sort_order": 20},
    {"slot_id": "bottom_2", "zone": "bottom", "label": "Bottom — Center", "sort_order": 21},
    {"slot_id": "bottom_3", "zone": "bottom", "label": "Bottom — Right",  "sort_order": 22},
]

SLOT_IDS: frozenset[str] = frozenset(s["slot_id"] for s in SLOT_REGISTRY)
MAX_SLOTS: int = len(SLOT_REGISTRY)   # 9
TITLE_MAX_LEN: int = 80

_HTML_TAG_RE = re.compile(r"<[^>]+>")


# ── Validation helpers ─────────────────────────────────────────────────────────

def validate_slot_id(slot_id: str) -> None:
    """Raise ValueError if slot_id is not in the Phase 1 registry."""
    if slot_id not in SLOT_IDS:
        raise ValueError(
            f"Unknown slot_id: {slot_id!r}. Valid slot IDs: {sorted(SLOT_IDS)}"
        )


def sanitize_title(title: str) -> str:
    """Strip HTML tags and enforce max length. Raises ValueError if too long."""
    cleaned = _HTML_TAG_RE.sub("", title).strip()
    if len(cleaned) > TITLE_MAX_LEN:
        raise ValueError(f"Title must be {TITLE_MAX_LEN} characters or fewer.")
    return cleaned


def build_video_module(video_url: str, title: str = "") -> dict[str, Any]:
    """Validate video_url, build and return a module dict.

    Accepts YouTube (watch/shorts/youtu.be) and canonical TikTok URLs.
    Short TikTok URLs (vm./vt.tiktok.com) raise ValueError.
    source_url is stored for audit only and is never used as an iframe src.
    """
    try:
        parsed = extract_any_video(video_url)
    except ValueError:
        raise
    if parsed is None:
        raise ValueError(
            "Invalid or unsupported video URL. Paste a YouTube link "
            "(youtube.com/watch?v=… or youtu.be/…) "
            "or the full TikTok video link (tiktok.com/@user/video/…)."
        )
    clean_title = sanitize_title(title) if title else ""
    provider = parsed["provider"]
    return {
        "type":       f"video_{provider}",
        "title":      clean_title,
        "provider":   provider,
        "video_id":   parsed["video_id"],
        "source_url": video_url,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Profile grid mutation helpers (pure — return new dicts, never mutate) ─────

def set_slot(profile_grid: dict | None, slot_id: str, module: dict) -> dict:
    """Return a new profile_grid dict with slot_id set to module.

    Replaces an existing entry for slot_id or appends a new one.
    Raises ValueError if slot count would exceed MAX_SLOTS.
    """
    validate_slot_id(slot_id)
    slots: list[dict] = list((profile_grid or {}).get("slots", []))
    existing_ids = {s["slot_id"] for s in slots}
    if slot_id in existing_ids:
        slots = [
            {"slot_id": slot_id, "module": module} if s["slot_id"] == slot_id else s
            for s in slots
        ]
    else:
        if len(slots) >= MAX_SLOTS:
            raise ValueError(
                f"Maximum {MAX_SLOTS} slots already filled. Remove one before adding."
            )
        slots.append({"slot_id": slot_id, "module": module})
    return {"version": 1, "slots": slots}


def remove_slot(profile_grid: dict | None, slot_id: str) -> dict | None:
    """Return a new profile_grid dict with slot_id removed.

    Returns None when the resulting slot list is empty (no profile_grid key stored).
    """
    validate_slot_id(slot_id)
    if not profile_grid:
        return None
    slots = [s for s in profile_grid.get("slots", []) if s["slot_id"] != slot_id]
    return {"version": 1, "slots": slots} if slots else None


# ── Grid state builders (read-only) ───────────────────────────────────────────

def _slot_map(profile_grid: dict | None) -> dict[str, dict | None]:
    """Return {slot_id: module_or_None} for valid occupied slots."""
    if not profile_grid:
        return {}
    return {
        s["slot_id"]: s.get("module")
        for s in profile_grid.get("slots", [])
        if isinstance(s.get("slot_id"), str) and s["slot_id"] in SLOT_IDS
    }


def build_draft_grid_state(draft: Any) -> list[dict]:
    """Return all 9 slots with their draft module state.

    Each entry: {slot_id, zone, label, sort_order, module, is_empty}.
    Used by the designer page GET handler.
    """
    occupied = _slot_map((draft.draft_data or {}).get("profile_grid"))
    return [
        {
            **slot_def,
            "module":   occupied.get(slot_def["slot_id"]),
            "is_empty": slot_def["slot_id"] not in occupied,
        }
        for slot_def in SLOT_REGISTRY
    ]


def build_published_grid_state(draft: Any) -> list[dict] | None:
    """Return occupied published slots, or None if no published profile_grid.

    Returns None (not an empty list) when profile_grid is absent so callers can
    distinguish "no grid configured" from "grid exists but all slots empty".
    Only filled slots are returned — used for public profile rendering.
    """
    pg = (draft.published_data or {}).get("profile_grid") if draft is not None else None
    if not pg:
        return None
    occupied = _slot_map(pg)
    if not occupied:
        return None
    return [
        {
            **slot_def,
            "module":   occupied[slot_def["slot_id"]],
            "is_empty": False,
        }
        for slot_def in SLOT_REGISTRY
        if slot_def["slot_id"] in occupied
    ]


def grid_fingerprint(profile_grid: dict | None) -> frozenset:
    """Stable fingerprint for is_published() comparison.

    Format per slot: "slot_id:provider:video_id"
    """
    if not profile_grid:
        return frozenset()
    return frozenset(
        "{sid}:{prov}:{vid}".format(
            sid=s.get("slot_id", ""),
            prov=(s.get("module") or {}).get("provider", ""),
            vid=(s.get("module") or {}).get("video_id", ""),
        )
        for s in profile_grid.get("slots", [])
    )
