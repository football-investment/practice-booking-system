"""
TCM — Tournament Type Constraint Matrix

Pure unit tests for TournamentType.validate_player_count().
No DB required — TournamentType instances are built directly.

Coverage: all 4 tournament types (knockout, league, group_knockout, swiss)
plus formal Pattern-A isolation assertions.

Pattern A (root cause catalog, Sprint 59):
  Using the WRONG tournament type in a boundary/safety-gate test can cause
  validate_player_count() to fire for a DIFFERENT reason than the one under test,
  masking the actual branch. These tests formally document which types fire which
  constraint at which player counts.

TCM-01–04 : knockout
TCM-05–07 : league
TCM-08–11 : group_knockout
TCM-12–14 : swiss
TCM-15–17 : safety-gate / Pattern-A isolation
"""
import pytest
from app.models.tournament_type import TournamentType


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make(code: str, min_p: int, max_p: int | None, pow2: bool) -> TournamentType:
    """Instantiate a TournamentType without a DB session."""
    t = TournamentType()
    t.code = code
    t.display_name = code.title()
    t.min_players = min_p
    t.max_players = max_p
    t.requires_power_of_two = pow2
    t.config = {}
    return t


# Canonical type fixtures (match production seed data)
KNOCKOUT     = _make("knockout",      min_p=4,  max_p=1024, pow2=True)
LEAGUE       = _make("league",        min_p=2,  max_p=1024, pow2=False)
GROUP_KNOCK  = _make("group_knockout",min_p=8,  max_p=64,   pow2=False)
SWISS        = _make("swiss",         min_p=4,  max_p=64,   pow2=False)


# ---------------------------------------------------------------------------
# TCM-01–04  Knockout
# ---------------------------------------------------------------------------

class TestKnockoutConstraints:
    """Single-Elimination (Knockout) — min=4, max=1024, requires_power_of_two=True."""

    def test_tcm01_valid_minimum(self):
        """TCM-01: 4 players (min boundary) is valid."""
        ok, msg = KNOCKOUT.validate_player_count(4)
        assert ok is True
        assert msg == ""

    def test_tcm02_valid_power_of_two(self):
        """TCM-02: typical valid counts — 8, 16, 32, 64."""
        for n in (8, 16, 32, 64):
            ok, msg = KNOCKOUT.validate_player_count(n)
            assert ok is True, f"Expected valid for n={n}, got: {msg}"

    def test_tcm03_invalid_below_minimum(self):
        """TCM-03: 3 players (below min=4) → fail on min_players, not pow2."""
        ok, msg = KNOCKOUT.validate_player_count(3)
        assert ok is False
        assert "at least 4" in msg
        # Confirm: power-of-2 check is NOT the reason (3 would fail pow2 too,
        # but min_players is checked FIRST — only one error is returned)
        assert "power-of-2" not in msg

    def test_tcm04_invalid_non_power_of_two(self):
        """TCM-04: 6 players (valid range but not power-of-2) → fails pow2 check.

        Pattern-A relevance: 127 also fails here (not power-of-2), which would
        MASK a safety-gate test targeting the ≥128 + unconfirmed branch.
        Use 'league' for safety-gate tests, not 'knockout'.
        """
        ok, msg = KNOCKOUT.validate_player_count(6)
        assert ok is False
        assert "power-of-2" in msg

        # 127 is the exact value from test_branch_safety_gate_at_127_no_confirmation_needed
        ok127, msg127 = KNOCKOUT.validate_player_count(127)
        assert ok127 is False
        assert "power-of-2" in msg127  # fails BEFORE reaching the safety gate


# ---------------------------------------------------------------------------
# TCM-05–07  League
# ---------------------------------------------------------------------------

class TestLeagueConstraints:
    """League (Round Robin) — min=2, max=1024, requires_power_of_two=False."""

    def test_tcm05_valid_minimum(self):
        """TCM-05: 2 players (min boundary) is valid."""
        ok, msg = LEAGUE.validate_player_count(2)
        assert ok is True
        assert msg == ""

    def test_tcm06_valid_arbitrary_counts(self):
        """TCM-06: league accepts any integer in [2, 1024], including odd and primes."""
        for n in (2, 3, 5, 7, 10, 50, 127, 1024):
            ok, msg = LEAGUE.validate_player_count(n)
            assert ok is True, f"Expected valid for n={n}, got: {msg}"

    def test_tcm07_invalid_below_minimum(self):
        """TCM-07: 1 player (below min=2) → invalid."""
        ok, msg = LEAGUE.validate_player_count(1)
        assert ok is False
        assert "at least 2" in msg


# ---------------------------------------------------------------------------
# TCM-08–11  Group Knockout
# ---------------------------------------------------------------------------

class TestGroupKnockoutConstraints:
    """Group+Knockout — min=8, max=64, requires_power_of_two=False.

    Note: the valid set {8,12,16,24,32,48,64} is enforced at the SESSION
    GENERATOR level (not in validate_player_count). This class tests only
    the model-layer constraints (min/max).
    """

    def test_tcm08_valid_minimum(self):
        """TCM-08: 8 players (min boundary) is valid at model level."""
        ok, msg = GROUP_KNOCK.validate_player_count(8)
        assert ok is True

    def test_tcm09_valid_maximum(self):
        """TCM-09: 64 players (max boundary) is valid at model level."""
        ok, msg = GROUP_KNOCK.validate_player_count(64)
        assert ok is True

    def test_tcm10_invalid_below_minimum(self):
        """TCM-10: 7 players (below min=8) → invalid."""
        ok, msg = GROUP_KNOCK.validate_player_count(7)
        assert ok is False
        assert "at least 8" in msg

    def test_tcm11_invalid_above_maximum(self):
        """TCM-11: 65 players (above max=64) → invalid.

        Pattern-A relevance: group_knockout + 127 would fail HERE (max=64),
        not at the safety gate (≥128 + unconfirmed). Always use 'league'
        for safety-gate isolation tests.
        """
        ok, msg = GROUP_KNOCK.validate_player_count(65)
        assert ok is False
        assert "maximum 64" in msg

        # Confirm 127 is caught by max, not safety-gate
        ok127, msg127 = GROUP_KNOCK.validate_player_count(127)
        assert ok127 is False
        assert "maximum 64" in msg127


# ---------------------------------------------------------------------------
# TCM-12–14  Swiss
# ---------------------------------------------------------------------------

class TestSwissConstraints:
    """Swiss System — min=4, max=64, requires_power_of_two=False.

    Prior coverage: zero unit tests. These establish the baseline.
    """

    def test_tcm12_valid_minimum(self):
        """TCM-12: 4 players (min boundary) is valid."""
        ok, msg = SWISS.validate_player_count(4)
        assert ok is True
        assert msg == ""

    def test_tcm13_valid_maximum(self):
        """TCM-13: 64 players (max boundary) is valid."""
        ok, msg = SWISS.validate_player_count(64)
        assert ok is True
        assert msg == ""

    def test_tcm14_invalid_boundaries(self):
        """TCM-14: 3 (below min) and 65 (above max) are both invalid."""
        ok_low, msg_low = SWISS.validate_player_count(3)
        assert ok_low is False
        assert "at least 4" in msg_low

        ok_high, msg_high = SWISS.validate_player_count(65)
        assert ok_high is False
        assert "maximum 64" in msg_high


# ---------------------------------------------------------------------------
# TCM-15–17  Safety-Gate / Pattern-A Isolation
# ---------------------------------------------------------------------------

class TestSafetyGateConstraintIsolation:
    """Formal Pattern-A assertions.

    The API-level safety gate fires when:
        player_count >= 128  AND  confirmed=False → HTTP 422

    For tests targeting this branch, the tournament type MUST NOT fire
    validate_player_count() for player counts in [2, 127].
    League is the only production type that satisfies this:
        - min=2, max=1024, pow2=False  → no model-level rejection in [2, 127]
    """

    def test_tcm15_league_does_not_reject_127(self):
        """TCM-15: league.validate_player_count(127) is valid.

        League is the correct neutral type for safety-gate-at-127 tests.
        Any rejection of 127 by the tournament type would mask the test.
        """
        ok, msg = LEAGUE.validate_player_count(127)
        assert ok is True, f"league must accept 127 (safety-gate isolation): {msg}"

    def test_tcm16_league_does_not_reject_128(self):
        """TCM-16: league.validate_player_count(128) is valid.

        The safety gate at 128 is the first thing that fires when
        confirmed=False. The type must not reject 128 before the gate check.
        """
        ok, msg = LEAGUE.validate_player_count(128)
        assert ok is True, f"league must accept 128 (safety-gate isolation): {msg}"

    def test_tcm17_knockout_rejects_127_for_wrong_reason(self):
        """TCM-17: knockout.validate_player_count(127) fails for pow2, NOT safety-gate.

        This formally documents WHY knockout is WRONG for safety-gate-at-127 tests.
        The safety gate checks player_count >= 128 AND confirmed=False at the API
        layer — but knockout's validate_player_count(127) already returns False
        (pow2 violation), so the session generator fires 422 citing pow2 instead
        of the safety gate, making the test assertion meaningless.

        Root cause catalogued as Pattern A in TESTING.md (Sprint 59).
        Fix applied in test_full_boundary_matrix.py:
            tournament_type_code = "league"  # was "knockout" — see Pattern A
        """
        ok, msg = KNOCKOUT.validate_player_count(127)
        assert ok is False
        assert "power-of-2" in msg, (
            "knockout must reject 127 for power-of-2 reason "
            "(confirms Pattern A: this type MASKS the safety-gate test)"
        )
        # Confirm this is NOT the max_players guard
        assert "maximum" not in msg
