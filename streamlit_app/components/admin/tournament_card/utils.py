"""
Shared utilities for tournament card components.

Common helper functions used by leaderboard, result_entry, and session_grid.
"""

from typing import Dict, Optional

# ─── Phase Constants ─────────────────────────────────────────────────────────

_PHASE_ICONS: Dict[str, str] = {
    "GROUP_STAGE": "🌐",
    "KNOCKOUT": "🏆",
    "FINALS": "👑",
    "PLACEMENT": "🥉",
    "INDIVIDUAL_RANKING": "🏃",
}

_PHASE_SHORT_LABELS: Dict[str, str] = {
    "GROUP_STAGE": "Group Stage",
    "KNOCKOUT": "Knockout",
    "FINALS": "Finals",
    "PLACEMENT": "Placement",
    "INDIVIDUAL_RANKING": "Individual Ranking",
}


# ─── Helper Functions ────────────────────────────────────────────────────────

def phase_icon(phase: Optional[str]) -> str:
    """Get emoji icon for a tournament phase."""
    return _PHASE_ICONS.get(phase or "", "🔹")


def phase_label_short(phase: Optional[str]) -> str:
    """Get short human-readable label for a phase."""
    return _PHASE_SHORT_LABELS.get(phase or "", (phase or "").replace("_", " ").title())


def phase_label(phase: Optional[str], round_: Optional[int]) -> str:
    """Format phase and round into a readable label with emoji."""
    parts = []
    if phase:
        icon = phase_icon(phase)
        label = phase_label_short(phase)
        parts.append(f"{icon} {label}")
    if round_ is not None:
        parts.append(f"R{round_}")
    return " · ".join(parts) if parts else "—"
