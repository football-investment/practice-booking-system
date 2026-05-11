"""
Unit tests for app/utils/football_positions.py

FP-01: POSITIONS_17 has exactly 17 entries
FP-02: VALID_POSITION_VALUES has exactly 17 members
FP-03: POSITIONS_17 entries cover exactly 4 groups
FP-04: positions_grouped() returns 4 groups in correct order
FP-05: positions_grouped() group sizes = 5, 5, 5, 2
FP-06: normalize_position — legacy uppercase STRIKER → striker
FP-07: normalize_position — legacy MIDFIELDER → centre_midfield
FP-08: normalize_position — legacy DEFENDER → centre_back
FP-09: normalize_position — legacy GOALKEEPER → goalkeeper
FP-10: normalize_position — already canonical passes through
FP-11: normalize_position — unknown value returns None
FP-12: normalize_position — empty string returns None
FP-13: normalize_positions — valid list normalises all values
FP-14: normalize_positions — mixed legacy + canonical
FP-15: normalize_positions — empty list returns None
FP-16: normalize_positions — unknown value returns None
FP-17: normalize_positions — preserves order (positions[0] = primary)
FP-18: position_label — known value returns label
FP-19: position_label — unknown value returns the value itself
FP-20: position_short — known values return correct abbreviations
FP-21: position_short — goalkeeper group abbreviations
"""
import pytest
from app.utils.football_positions import (
    POSITIONS_17,
    VALID_POSITION_VALUES,
    LEGACY_POSITION_MAP,
    normalize_position,
    normalize_positions,
    position_label,
    position_short,
    positions_grouped,
)


# ── FP-01 / FP-02: registry sizes ────────────────────────────────────────────

def test_fp01_positions_17_has_17_entries():
    assert len(POSITIONS_17) == 17


def test_fp02_valid_position_values_has_17_members():
    assert len(VALID_POSITION_VALUES) == 17


# ── FP-03: 4 groups covered ───────────────────────────────────────────────────

def test_fp03_positions_cover_exactly_4_groups():
    groups = {p["group"] for p in POSITIONS_17}
    assert groups == {"forward", "midfielder", "defender", "goalkeeper"}


# ── FP-04: positions_grouped structure ───────────────────────────────────────

def test_fp04_positions_grouped_returns_4_groups():
    groups = positions_grouped()
    assert len(groups) == 4
    assert [g["key"] for g in groups] == ["forward", "midfielder", "defender", "goalkeeper"]
    assert groups[0]["label"] == "Forwards"
    assert groups[1]["label"] == "Midfielders"
    assert groups[2]["label"] == "Defenders"
    assert groups[3]["label"] == "Goalkeepers"


# ── FP-05: group sizes ────────────────────────────────────────────────────────

def test_fp05_group_sizes():
    groups = {g["key"]: len(g["positions"]) for g in positions_grouped()}
    assert groups["forward"]    == 5
    assert groups["midfielder"] == 5
    assert groups["defender"]   == 5
    assert groups["goalkeeper"] == 2


# ── FP-06..09: legacy uppercase mapping ──────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("STRIKER",    "striker"),
    ("MIDFIELDER", "centre_midfield"),
    ("DEFENDER",   "centre_back"),
    ("GOALKEEPER", "goalkeeper"),
])
def test_fp06_fp09_legacy_uppercase_mapping(raw, expected):
    assert normalize_position(raw) == expected


# ── FP-10: canonical passthrough ─────────────────────────────────────────────

@pytest.mark.parametrize("canonical", [
    "striker", "left_wing", "right_wing", "centre_forward", "second_striker",
    "attacking_midfield", "centre_midfield", "defensive_midfield",
    "left_midfield", "right_midfield",
    "centre_back", "left_back", "right_back", "left_wing_back", "right_wing_back",
    "goalkeeper", "sweeper_keeper",
])
def test_fp10_canonical_passes_through(canonical):
    assert normalize_position(canonical) == canonical


# ── FP-11 / FP-12: invalid inputs ────────────────────────────────────────────

def test_fp11_unknown_value_returns_none():
    assert normalize_position("UNKNOWN") is None
    assert normalize_position("winger") is None
    assert normalize_position("forward") is None    # group key, not a position value


def test_fp12_empty_string_returns_none():
    assert normalize_position("") is None


# ── FP-13..17: normalize_positions ───────────────────────────────────────────

def test_fp13_valid_list_normalises_all():
    result = normalize_positions(["striker", "left_wing", "centre_back"])
    assert result == ["striker", "left_wing", "centre_back"]


def test_fp14_mixed_legacy_and_canonical():
    result = normalize_positions(["STRIKER", "left_wing", "GOALKEEPER"])
    assert result == ["striker", "left_wing", "goalkeeper"]


def test_fp15_empty_list_returns_none():
    assert normalize_positions([]) is None


def test_fp16_unknown_value_returns_none():
    assert normalize_positions(["striker", "bad_position"]) is None
    assert normalize_positions(["bad_one"]) is None


def test_fp17_preserves_order():
    raw = ["right_wing", "striker", "centre_back"]
    result = normalize_positions(raw)
    assert result is not None
    assert result[0] == "right_wing"    # primary preserved at [0]
    assert result[1] == "striker"
    assert result[2] == "centre_back"


# ── FP-18 / FP-19: position_label ────────────────────────────────────────────

def test_fp18_known_label():
    assert position_label("striker")            == "Striker"
    assert position_label("left_wing")          == "Left Wing"
    assert position_label("sweeper_keeper")     == "Sweeper Keeper"
    assert position_label("defensive_midfield") == "Defensive Midfielder"
    assert position_label("centre_back")        == "Centre Back"


def test_fp19_unknown_label_returns_value_itself():
    assert position_label("some_unknown_pos") == "some_unknown_pos"


# ── FP-20 / FP-21: position_short ────────────────────────────────────────────

def test_fp20_forward_and_midfield_shorts():
    assert position_short("striker")            == "ST"
    assert position_short("centre_forward")     == "CF"
    assert position_short("left_wing")          == "LW"
    assert position_short("right_wing")         == "RW"
    assert position_short("second_striker")     == "SS"
    assert position_short("attacking_midfield") == "AM"
    assert position_short("centre_midfield")    == "CM"
    assert position_short("defensive_midfield") == "DM"
    assert position_short("left_midfield")      == "LM"
    assert position_short("right_midfield")     == "RM"
    assert position_short("centre_back")        == "CB"
    assert position_short("left_back")          == "LB"
    assert position_short("right_back")         == "RB"
    assert position_short("left_wing_back")     == "LWB"
    assert position_short("right_wing_back")    == "RWB"


def test_fp21_goalkeeper_shorts():
    assert position_short("goalkeeper")     == "GK"
    assert position_short("sweeper_keeper") == "SK"
