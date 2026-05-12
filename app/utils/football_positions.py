"""
Football position definitions for the LFA Player onboarding system.

21-position taxonomy: 4 groups × (5, 7, 7, 2 positions each).
DB values are snake_case strings (e.g. "striker", "left_centre_back").

Taxonomy history:
  v1 (17 positions): original — centre_back/centre_midfield as single nodes
  v2 (21 positions): LCB/RCB split → left_centre_back/right_centre_back;
                     LCM/RCM split → left_centre_midfield/right_centre_midfield.
  Legacy values (centre_back, centre_midfield, second_striker) remain in
  VALID_POSITION_VALUES and LEGACY_POSITION_MAP for backward compatibility.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ── Canonical position registry ───────────────────────────────────────────────

# (group_key, value, label, short)
_POSITIONS: List[Tuple[str, str, str, str]] = [
    # Forwards (5)
    ("forward",    "striker",               "Striker",                "ST"),
    ("forward",    "centre_forward",        "Centre Forward",         "CF"),
    ("forward",    "left_wing",             "Left Wing",              "LW"),
    ("forward",    "right_wing",            "Right Wing",             "RW"),
    ("forward",    "second_striker",        "Second Striker",         "SS"),
    # Midfielders (7)
    ("midfielder", "attacking_midfield",    "Attacking Midfielder",   "AM"),
    ("midfielder", "centre_midfield",       "Central Midfielder",     "CM"),
    ("midfielder", "defensive_midfield",    "Defensive Midfielder",   "DM"),
    ("midfielder", "left_midfield",         "Left Midfielder",        "LM"),
    ("midfielder", "right_midfield",        "Right Midfielder",       "RM"),
    ("midfielder", "left_centre_midfield",  "Left Centre Midfielder", "LCM"),
    ("midfielder", "right_centre_midfield", "Right Centre Midfielder","RCM"),
    # Defenders (7)
    ("defender",   "centre_back",           "Centre Back",            "CB"),
    ("defender",   "left_back",             "Left Back",              "LB"),
    ("defender",   "right_back",            "Right Back",             "RB"),
    ("defender",   "left_wing_back",        "Left Wing Back",         "LWB"),
    ("defender",   "right_wing_back",       "Right Wing Back",        "RWB"),
    ("defender",   "left_centre_back",      "Left Centre-Back",       "LCB"),
    ("defender",   "right_centre_back",     "Right Centre-Back",      "RCB"),
    # Goalkeepers (2)
    ("goalkeeper", "goalkeeper",            "Goalkeeper",             "GK"),
    ("goalkeeper", "sweeper_keeper",        "Sweeper Keeper",         "SK"),
]

POSITIONS_21: List[Dict] = [
    {"group": g, "value": v, "label": l, "short": s}
    for g, v, l, s in _POSITIONS
]

VALID_POSITION_VALUES: frozenset = frozenset(p["value"] for p in POSITIONS_21)

# Maps legacy 4-value uppercase strings → canonical snake_case.
# All 21 canonical values also map to themselves (idempotent passthrough).
LEGACY_POSITION_MAP: Dict[str, str] = {
    "STRIKER":    "striker",
    "MIDFIELDER": "centre_midfield",
    "DEFENDER":   "centre_back",
    "GOALKEEPER": "goalkeeper",
    **{p["value"]: p["value"] for p in POSITIONS_21},
}

_GROUP_LABELS: Dict[str, str] = {
    "forward":    "Forwards",
    "midfielder": "Midfielders",
    "defender":   "Defenders",
    "goalkeeper": "Goalkeepers",
}

_GROUP_ORDER = ["forward", "midfielder", "defender", "goalkeeper"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize_position(raw: str) -> Optional[str]:
    """Return canonical snake_case value or None if unrecognised."""
    if not raw:
        return None
    canonical = LEGACY_POSITION_MAP.get(raw) or LEGACY_POSITION_MAP.get(raw.upper())
    return canonical


def normalize_positions(raw_list: List[str]) -> Optional[List[str]]:
    """
    Normalise a list of raw position strings.

    Returns None if any value is unrecognised or if the list is empty.
    Preserves order; position[0] is treated as primary by convention.
    """
    if not raw_list:
        return None
    result = []
    for raw in raw_list:
        canon = normalize_position(raw)
        if canon is None:
            return None
        result.append(canon)
    return result


def position_label(value: str) -> str:
    """Return human-readable label for a canonical position value."""
    for p in POSITIONS_21:
        if p["value"] == value:
            return p["label"]
    return value


def position_short(value: str) -> str:
    """Return abbreviation (e.g. 'ST') for a canonical position value."""
    for p in POSITIONS_21:
        if p["value"] == value:
            return p["short"]
    return value.upper()[:3]


def positions_grouped() -> List[Dict]:
    """
    Return positions organised by group for Jinja2 rendering.

    Shape: [{"key": "forward", "label": "Forwards", "positions": [...]}, ...]
    """
    groups: Dict[str, List[Dict]] = {g: [] for g in _GROUP_ORDER}
    for p in POSITIONS_21:
        groups[p["group"]].append(p)
    return [
        {"key": key, "label": _GROUP_LABELS[key], "positions": groups[key]}
        for key in _GROUP_ORDER
    ]
