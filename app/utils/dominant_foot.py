"""Dominant foot badge computation.

Badge codes:
  "Rl"  — right-footed   (right_pct ≥ 65 %)
  "rL"  — left-footed    (left_pct  ≥ 65 %)
  "RL"  — two-footed     (both 45–65 %)
  "rl"  — unassessed / neither foot clearly dominant

Returns "rl" for any None/zero inputs so callers never receive None.
"""
from __future__ import annotations


_RIGHT_DOMINANT_THRESHOLD = 65.0
_LEFT_DOMINANT_THRESHOLD  = 65.0
_BALANCED_LOW             = 45.0
_BALANCED_HIGH            = 65.0


def calculate_dominant_badge(
    right_score: float | None,
    left_score:  float | None,
) -> str:
    """Return a two-character dominant-foot badge for display on player cards."""
    if not right_score and not left_score:
        return "rl"

    r = right_score or 0.0
    l = left_score  or 0.0
    total = r + l
    if total == 0:
        return "rl"

    right_pct = r / total * 100
    left_pct  = l / total * 100

    if right_pct >= _RIGHT_DOMINANT_THRESHOLD:
        return "Rl"
    if left_pct >= _LEFT_DOMINANT_THRESHOLD:
        return "rL"
    if _BALANCED_LOW <= right_pct <= _BALANCED_HIGH and _BALANCED_LOW <= left_pct <= _BALANCED_HIGH:
        return "RL"
    return "rl"
