"""Authoritative export constants for the FIFA Classic / Welcome Card card system.

All platform dimensions, template-bucket routing, and animated-capability
declarations live here.  Every other module imports from this file — never
defines its own copy.

Invariants enforced by tests/unit/services/test_card_constants.py:
  - EXPORT_FORMAT_BUCKETS.keys() == CANVAS_SIZES.keys() − {"default"}
  - Every platform_id in ANIMATED_EXPORT_CAPABLE exists in CANVAS_SIZES
"""
from __future__ import annotations

# ── Canvas dimensions ─────────────────────────────────────────────────────────
# Social canvas sizes keyed by platform preset id.
#
# "default" export canvas — measured 2026-05-12 via Playwright at 820px viewport
# using ?native_export=1 (native-export-mode CSS: card fills width at auto height).
# Conditions: FIFA Classic card, 4 SKILL_CATEGORIES (Outfield 19, Set Pieces 3,
# Mental 14, Physical Fitness 8 skills), lower-section split layout (3fr skills /
# 2fr position panel).  card-wrap.getBoundingClientRect() = 820×613 px.
# Export path: render_url uses ?native_export=1; _sync_take_screenshot clips
# to the card-wrap bounding rect — height is content-determined at render time.
# The 613 here is a documented baseline; the clip always uses the live bounding
# rect so new skills or theme changes never produce a truncated export.
CANVAS_SIZES: dict[str, tuple[int, int]] = {
    "default":            ( 820,  613),   # native FIFA Classic; clip = card-wrap bbox
    "instagram_square":   (1080, 1080),
    "instagram_portrait": (1080, 1350),
    "instagram_story":    (1080, 1920),
    "tiktok":             (1080, 1920),
    "facebook_square":    (1080, 1080),
    "facebook_landscape": (1200,  630),
    "og":                 (1200,  630),
    "banner_custom":      (1500,  500),
    "facebook_post":      (1200,  630),
}

# ── Export template routing ───────────────────────────────────────────────────
# Maps platform preset id → template bucket directory.
# Template path resolved as: public/export/{bucket}/{card_variant_id}.html
EXPORT_FORMAT_BUCKETS: dict[str, str] = {
    "instagram_square":   "square",
    "facebook_square":    "square",
    "instagram_portrait": "portrait",
    "instagram_story":    "story",
    "tiktok":             "tiktok",
    "facebook_landscape": "landscape",
    "og":                 "landscape",
    "banner_custom":      "banner",
    "facebook_post":      "landscape",
}

# ── Animated video export capability registry ─────────────────────────────────
# (variant_id, platform_id) pairs that have a dedicated animated export
# template.  All other combinations return 422 — no fallback, no silent
# degradation.
ANIMATED_EXPORT_CAPABLE: frozenset[tuple[str, str]] = frozenset({
    ("fifa",  "instagram_square"),
    ("pulse", "instagram_square"),
})


def is_animated_capable(variant_id: str, platform_id: str) -> bool:
    """Return True if (variant_id, platform_id) supports animated video export."""
    return (variant_id, platform_id) in ANIMATED_EXPORT_CAPABLE


# ── Gallery / editor platform ID lists ───────────────────────────────────────

# Platforms shown in the Welcome Card gallery.
# Explicit inclusion list — facebook_square, og, and facebook_post are
# intentionally excluded: fb_square duplicates IG Square sizing, og duplicates
# fb_landscape sizing, and facebook_post requires a 3-column layout template
# not present in Welcome Card.
WC_GALLERY_PLATFORM_IDS: tuple[str, ...] = (
    "instagram_square",
    "instagram_portrait",
    "instagram_story",
    "tiktok",
    "facebook_landscape",
    "banner_custom",
)

# Platforms shown in the Dashboard Card Editor platform picker.
# "default" is excluded — it has no canvas size and is not an export target.
# facebook_post was previously missing from the editor UI (functional gap).
CARD_EDITOR_PLATFORM_IDS: tuple[str, ...] = (
    "instagram_square",
    "instagram_portrait",
    "instagram_story",
    "tiktok",
    "facebook_square",
    "facebook_landscape",
    "og",
    "banner_custom",
    "facebook_post",
)
