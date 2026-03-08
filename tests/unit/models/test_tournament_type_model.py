"""
Unit tests for app/models/tournament_type.py

Branch coverage targets:

validate_player_count():
  - player_count < min_players              → (False, error msg)
  - max_players set and player_count > max  → (False, error msg)
  - max_players is None                     → skip upper-bound check
  - requires_power_of_two and NOT pow2      → (False, error msg)
  - requires_power_of_two and IS pow2       → passes check
  - all checks pass                         → (True, "")

estimate_duration():
  - code == "league"                        → round-robin math
  - code == "knockout"                      → single-elim math
  - code == "knockout" + third_place_playoff→ adds 1 match
  - code == "group_knockout" + config found → full calculation
  - code == "group_knockout" + no config    → zero matches
  - code == "swiss"                         → log2 rounds
"""

import pytest
import math

from app.models.tournament_type import TournamentType


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tt(**overrides):
    """Build a transient TournamentType with safe defaults."""
    t = TournamentType()
    t.id = 1
    t.code = "league"
    t.display_name = "League (Round Robin)"
    t.min_players = 4
    t.max_players = None
    t.requires_power_of_two = False
    t.session_duration_minutes = 90
    t.break_between_sessions_minutes = 15
    t.config = {}
    for k, v in overrides.items():
        setattr(t, k, v)
    return t


# ============================================================================
# validate_player_count()
# ============================================================================

class TestValidatePlayerCount:

    def test_too_few_players_returns_false(self):
        t = _tt(min_players=4)
        valid, msg = t.validate_player_count(2)
        assert valid is False
        assert "4" in msg

    def test_exactly_min_players_passes(self):
        t = _tt(min_players=4)
        valid, msg = t.validate_player_count(4)
        assert valid is True
        assert msg == ""

    def test_exceeds_max_players_returns_false(self):
        t = _tt(max_players=8)
        valid, msg = t.validate_player_count(10)
        assert valid is False
        assert "8" in msg

    def test_no_max_players_skips_upper_check(self):
        t = _tt(max_players=None)
        valid, _ = t.validate_player_count(1000)
        assert valid is True

    def test_power_of_two_check_fails_for_non_pow2(self):
        t = _tt(requires_power_of_two=True, min_players=2)
        valid, msg = t.validate_player_count(6)  # 6 is not power of 2
        assert valid is False
        assert "power-of-2" in msg.lower() or "power" in msg.lower()

    def test_power_of_two_check_passes_for_pow2(self):
        t = _tt(requires_power_of_two=True, min_players=2)
        valid, msg = t.validate_player_count(8)
        assert valid is True

    def test_all_checks_pass(self):
        t = _tt(min_players=4, max_players=16, requires_power_of_two=False)
        valid, msg = t.validate_player_count(8)
        assert valid is True
        assert msg == ""


# ============================================================================
# estimate_duration()
# ============================================================================

class TestEstimateDuration:

    # -----------------------------------------------------------------------
    # League (round-robin)
    # -----------------------------------------------------------------------

    def test_league_4_players_even(self):
        t = _tt(code="league")
        result = t.estimate_duration(4)
        assert result["total_matches"] == 6    # 4*(4-1)//2
        assert result["total_rounds"] == 3     # 4-1 (even)

    def test_league_5_players_odd(self):
        t = _tt(code="league")
        result = t.estimate_duration(5)
        assert result["total_matches"] == 10   # 5*(5-1)//2
        assert result["total_rounds"] == 5     # odd: n rounds

    # -----------------------------------------------------------------------
    # Knockout (single elimination)
    # -----------------------------------------------------------------------

    def test_knockout_4_players_no_third_place(self):
        t = _tt(code="knockout", config={})
        result = t.estimate_duration(4)
        assert result["total_matches"] == 3    # 4-1
        assert result["total_rounds"] == 2     # ceil(log2(4))

    def test_knockout_with_third_place_playoff(self):
        t = _tt(code="knockout", config={"third_place_playoff": True})
        result = t.estimate_duration(4)
        assert result["total_matches"] == 4    # 3 + 1 playoff

    def test_knockout_without_third_place_config(self):
        t = _tt(code="knockout", config={"third_place_playoff": False})
        result = t.estimate_duration(4)
        assert result["total_matches"] == 3

    def test_knockout_missing_third_place_key(self):
        t = _tt(code="knockout", config={})
        result = t.estimate_duration(8)
        assert result["total_matches"] == 7    # 8-1

    # -----------------------------------------------------------------------
    # Group + Knockout
    # -----------------------------------------------------------------------

    def test_group_knockout_with_config(self):
        t = _tt(
            code="group_knockout",
            config={
                "group_configuration": {
                    "8_players": {
                        "groups": 2,
                        "players_per_group": 4,
                        "qualifiers": 2,
                    }
                }
            },
        )
        result = t.estimate_duration(8)
        # Group stage: 2 × (4*3//2=6) = 12 matches
        # Knockout: 2×2=4 qualifiers → 3 matches
        assert result["total_matches"] == 15

    def test_group_knockout_no_matching_config(self):
        t = _tt(code="group_knockout", config={"group_configuration": {}})
        result = t.estimate_duration(8)
        assert result["total_matches"] == 0
        assert result["total_rounds"] == 0

    # -----------------------------------------------------------------------
    # Swiss
    # -----------------------------------------------------------------------

    def test_swiss_4_players(self):
        t = _tt(code="swiss")
        result = t.estimate_duration(4)
        expected_rounds = math.ceil(math.log2(4))  # 2
        expected_matches = (4 * expected_rounds) // 2  # 4
        assert result["total_rounds"] == expected_rounds
        assert result["total_matches"] == expected_matches

    # -----------------------------------------------------------------------
    # Return shape
    # -----------------------------------------------------------------------

    def test_result_contains_required_keys(self):
        t = _tt(code="league")
        result = t.estimate_duration(4)
        assert "total_matches" in result
        assert "total_rounds" in result
        assert "estimated_duration_minutes" in result
        assert "estimated_duration_days" in result
