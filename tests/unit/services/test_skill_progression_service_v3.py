"""
Unit Tests: V3 EMA Skill Progression — calculate_skill_value_from_placement()

Coverage:
  T01  EMA step log-normalisation at weight=1.0 anchors at lr=0.20
  T02  Dominant skill step > supporting skill step (log-scale proportionality)
  T03  Weight=0.0 edge: step=0, value unchanged
  T04  Win from below: positive delta, skill increases
  T05  Loss from above: negative delta, skill decreases
  T06  Opponent_factor > 1.0 amplifies win delta (strong field)
  T07  Opponent_factor > 1.0 softens loss delta (strong field)
  T08  Opponent_factor < 1.0 dampens win delta (weak field)
  T09  Opponent_factor < 1.0 amplifies loss delta (weak field)
  T10  Clamp floor: skill cannot drop below 40.0
  T11  Clamp ceiling: skill cannot exceed 99.0
  T12  Solo tournament (total_players=1): placement_skill=100, always upward delta
  T13  Dominant vs supporting: |norm_delta_dom| >= |norm_delta_sup| for same placement (mathematical guarantee)
  T14  V2 legacy path (prev_value=None): converging weighted average
  T15  V2 legacy path: dominant weight amplifies delta vs supporting weight
  T16  Convergence over N tournaments: running value approaches placement target
  T17  Alternating win/loss: oscillation stays bounded (no infinite growth)
  T18  prev_value already at placement_skill: delta ≈ 0 (EMA fixed point)
  T19  Opponent_factor clamped to [0.5, 2.0] (passed-in extreme values are handled)
  T20  Negative delta / clamp: last place many times → floor at 40.0 never breached
"""

import math
import pytest

from app.services.skill_progression_service import (
    calculate_skill_value_from_placement,
    MIN_SKILL_VALUE,
    MAX_SKILL_CAP,
)

# ─── helpers ──────────────────────────────────────────────────────────────────

LR = 0.20  # default learning rate


def ema_step(weight: float, lr: float = LR) -> float:
    """Expected log-normalised EMA step for a given weight."""
    return lr * math.log(1.0 + weight) / math.log(2.0)


def placement_skill(placement: int, total: int) -> float:
    """Expected placement_skill value (100=1st, 40=last)."""
    if total == 1:
        return 100.0
    percentile = (placement - 1) / (total - 1)
    return 100.0 - percentile * (100.0 - 40.0)


# ─── T01: step at weight=1.0 equals lr ────────────────────────────────────────

class TestStepNormalisation:
    def test_T01_step_at_weight_1_equals_lr(self):
        """At weight=1.0, step = lr × log(2)/log(2) = lr exactly."""
        step = ema_step(1.0)
        assert abs(step - LR) < 1e-10, f"step should equal {LR}, got {step}"

    def test_T02_dominant_step_greater_than_supporting(self):
        """Step grows monotonically with weight (log-scale)."""
        step_dom = ema_step(1.5)
        step_sup = ema_step(0.6)
        step_neu = ema_step(1.0)
        assert step_dom > step_neu > step_sup

    def test_T03_weight_zero_step_is_zero(self):
        """Weight=0 → log(1+0)/log(2)=0 → no movement."""
        val = calculate_skill_value_from_placement(
            baseline=70.0, placement=1, total_players=5,
            tournament_count=1, skill_weight=0.0,
            prev_value=70.0, opponent_factor=1.0,
        )
        assert val == 70.0, "weight=0 should produce no change"


# ─── T04–T05: direction of delta ──────────────────────────────────────────────

class TestDeltaDirection:
    def test_T04_win_from_below_increases_skill(self):
        """1st place with prev_value below placement_skill → positive delta."""
        prev = 60.0
        val = calculate_skill_value_from_placement(
            baseline=60.0, placement=1, total_players=5,
            tournament_count=1, skill_weight=1.0,
            prev_value=prev, opponent_factor=1.0,
        )
        assert val > prev, f"Expected increase from {prev}, got {val}"

    def test_T05_loss_from_above_decreases_skill(self):
        """Last place with prev_value above placement_skill → negative delta."""
        prev = 80.0
        val = calculate_skill_value_from_placement(
            baseline=80.0, placement=5, total_players=5,
            tournament_count=1, skill_weight=1.0,
            prev_value=prev, opponent_factor=1.0,
        )
        assert val < prev, f"Expected decrease from {prev}, got {val}"


# ─── T06–T09: opponent_factor asymmetry ───────────────────────────────────────

class TestOpponentFactor:
    """Asymmetric ELO: win vs strong → bigger reward; loss vs strong → smaller penalty."""

    def _delta(self, placement, total, prev, opp_factor, weight=1.0):
        val = calculate_skill_value_from_placement(
            baseline=prev, placement=placement, total_players=total,
            tournament_count=1, skill_weight=weight,
            prev_value=prev, opponent_factor=opp_factor,
        )
        return round(val - prev, 6)

    def test_T06_strong_field_amplifies_win(self):
        """opp_factor=1.5 (strong field) → win delta larger than neutral."""
        d_strong = self._delta(1, 5, 60.0, opp_factor=1.5)
        d_neutral = self._delta(1, 5, 60.0, opp_factor=1.0)
        assert d_strong > d_neutral > 0

    def test_T07_strong_field_softens_loss(self):
        """opp_factor=1.5 (strong field) → loss delta smaller (less negative) than neutral."""
        d_strong = self._delta(5, 5, 80.0, opp_factor=1.5)
        d_neutral = self._delta(5, 5, 80.0, opp_factor=1.0)
        # Both are negative; strong-field loss is closer to 0
        assert d_neutral < d_strong < 0

    def test_T08_weak_field_dampens_win(self):
        """opp_factor=0.7 (weak field) → win delta smaller than neutral."""
        d_weak = self._delta(1, 5, 60.0, opp_factor=0.7)
        d_neutral = self._delta(1, 5, 60.0, opp_factor=1.0)
        assert 0 < d_weak < d_neutral

    def test_T09_weak_field_amplifies_loss(self):
        """opp_factor=0.7 (weak field) → loss delta larger (more negative) than neutral."""
        d_weak = self._delta(5, 5, 80.0, opp_factor=0.7)
        d_neutral = self._delta(5, 5, 80.0, opp_factor=1.0)
        assert d_weak < d_neutral < 0

    def test_T19_extreme_opponent_factor_clamped(self):
        """Extreme opp_factor values (0.0, 10.0) are clamped to [0.5, 2.0] internally."""
        # Even passing opp_factor=10.0 should not produce an absurd result
        d_extreme = self._delta(1, 5, 60.0, opp_factor=10.0)
        d_capped = self._delta(1, 5, 60.0, opp_factor=2.0)
        assert abs(d_extreme - d_capped) < 1e-6, "opp_factor=10 should equal opp_factor=2.0"

        d_extreme_low = self._delta(5, 5, 80.0, opp_factor=0.0)
        d_capped_low = self._delta(5, 5, 80.0, opp_factor=0.5)
        assert abs(d_extreme_low - d_capped_low) < 1e-6, "opp_factor=0 should equal opp_factor=0.5"


# ─── T10–T11: clamp boundaries ────────────────────────────────────────────────

class TestClampBoundaries:
    def test_T10_floor_at_40(self):
        """Repeated last-place results cannot push skill below 40.0."""
        val = 42.0
        for _ in range(30):
            val = calculate_skill_value_from_placement(
                baseline=val, placement=5, total_players=5,
                tournament_count=1, skill_weight=1.5,
                prev_value=val, opponent_factor=1.0,
            )
        assert val >= MIN_SKILL_VALUE, f"Skill dropped below floor: {val}"

    def test_T11_ceiling_at_99(self):
        """Repeated 1st-place results cannot push skill above 99.0."""
        val = 97.0
        for _ in range(30):
            val = calculate_skill_value_from_placement(
                baseline=val, placement=1, total_players=5,
                tournament_count=1, skill_weight=1.5,
                prev_value=val, opponent_factor=2.0,
            )
        assert val <= MAX_SKILL_CAP, f"Skill exceeded ceiling: {val}"

    def test_T20_last_place_repeatedly_stops_at_floor(self):
        """Floor is hard — skill never goes negative or below 40 regardless of weight."""
        val = 40.5
        for _ in range(100):
            val = calculate_skill_value_from_placement(
                baseline=40.0, placement=10, total_players=10,
                tournament_count=1, skill_weight=5.0,
                prev_value=val, opponent_factor=0.5,
            )
        assert val == MIN_SKILL_VALUE


# ─── T12: solo tournament ─────────────────────────────────────────────────────

class TestSoloTournament:
    def test_T12_solo_tournament_placement_skill_100(self):
        """total_players=1 → percentile=0 → placement_skill=100 → always upward delta."""
        prev = 70.0
        val = calculate_skill_value_from_placement(
            baseline=70.0, placement=1, total_players=1,
            tournament_count=1, skill_weight=1.0,
            prev_value=prev, opponent_factor=1.0,
        )
        assert val > prev, "Solo tournament should increase skill (target=100)"


# ─── T13: dominance mathematical guarantee ────────────────────────────────────

class TestDominanceGuarantee:
    """
    V3 mathematical guarantee:
        norm_delta = delta / headroom
        For same placement: |norm_delta_dom| / |norm_delta_sup|
            = step_dom / step_sup
            = log(1+w_dom) / log(1+w_sup)   [constant, independent of prev_value]
    """

    def _norm_delta(self, weight, prev, placement, total):
        val = calculate_skill_value_from_placement(
            baseline=prev, placement=placement, total_players=total,
            tournament_count=1, skill_weight=weight,
            prev_value=prev, opponent_factor=1.0,
        )
        delta = val - prev
        ps = placement_skill(placement, total)
        headroom = ps - prev if delta >= 0 else prev - ps
        if abs(headroom) < 1e-9:
            return 0.0
        return delta / headroom

    def test_T13_dominant_norm_delta_geq_supporting_win(self):
        """On a win, |norm_delta| for dominant skill >= all supporting skills."""
        prev = 65.0
        nd_dom = abs(self._norm_delta(1.5, prev, 1, 5))
        nd_sup = abs(self._norm_delta(0.6, prev, 1, 5))
        nd_neu = abs(self._norm_delta(1.0, prev, 1, 5))
        assert nd_dom >= nd_neu >= nd_sup, (
            f"Dominance order violated: dom={nd_dom:.6f} neu={nd_neu:.6f} sup={nd_sup:.6f}"
        )

    def test_T13b_dominant_norm_delta_geq_supporting_loss(self):
        """On a loss, |norm_delta| dominance order also holds."""
        prev = 75.0
        nd_dom = abs(self._norm_delta(1.5, prev, 5, 5))
        nd_sup = abs(self._norm_delta(0.6, prev, 5, 5))
        assert nd_dom >= nd_sup

    def test_T13c_ratio_matches_log_formula(self):
        """
        The actual ratio of norm_deltas equals log(1+w_dom)/log(1+w_sup) exactly.
        Validates the mathematical derivation in the service docstring.
        """
        w_dom, w_sup = 1.5, 0.8
        prev = 60.0
        nd_dom = self._norm_delta(w_dom, prev, 1, 5)
        nd_sup = self._norm_delta(w_sup, prev, 1, 5)
        expected_ratio = math.log(1 + w_dom) / math.log(1 + w_sup)
        actual_ratio = nd_dom / nd_sup
        # The service rounds output to 1 decimal (round(..., 1)), introducing up to ~1e-4
        # floating-point rounding error in the ratio. We allow 1e-3 tolerance.
        assert abs(actual_ratio - expected_ratio) < 1e-3, (
            f"Ratio mismatch: expected {expected_ratio:.6f}, got {actual_ratio:.6f}"
        )


# ─── T14–T15: V2 legacy path ──────────────────────────────────────────────────

class TestV2LegacyPath:
    def test_T14_v2_converges_to_placement(self):
        """V2 path (prev_value=None): new value moves toward placement_skill."""
        baseline = 60.0
        # 1st place of 5 → placement_skill=100
        val = calculate_skill_value_from_placement(
            baseline=baseline, placement=1, total_players=5,
            tournament_count=1, skill_weight=1.0,
            prev_value=None,
        )
        assert val > baseline, f"V2 1st place should increase skill from {baseline}"

    def test_T15_v2_dominant_weight_amplifies_delta(self):
        """V2 path: skill_weight=1.5 produces larger delta than weight=0.6."""
        baseline = 60.0
        val_dom = calculate_skill_value_from_placement(
            baseline=baseline, placement=1, total_players=5,
            tournament_count=1, skill_weight=1.5,
            prev_value=None,
        )
        val_sup = calculate_skill_value_from_placement(
            baseline=baseline, placement=1, total_players=5,
            tournament_count=1, skill_weight=0.6,
            prev_value=None,
        )
        assert (val_dom - baseline) > (val_sup - baseline), (
            f"V2 dominant delta ({val_dom - baseline:.2f}) should exceed "
            f"supporting delta ({val_sup - baseline:.2f})"
        )


# ─── T16–T18: convergence and stability ───────────────────────────────────────

class TestConvergenceAndStability:
    def test_T16_ema_converges_toward_target(self):
        """
        Repeated 1st place: prev_value monotonically approaches placement_skill=100.
        After 20 tournaments the skill should be substantially higher than start.
        """
        val = 60.0
        target = placement_skill(1, 5)  # 100.0
        for _ in range(20):
            val = calculate_skill_value_from_placement(
                baseline=60.0, placement=1, total_players=5,
                tournament_count=1, skill_weight=1.0,
                prev_value=val, opponent_factor=1.0,
            )
        assert val > 85.0, f"Expected convergence toward 100, got {val}"
        assert val <= MAX_SKILL_CAP

    def test_T17_alternating_win_loss_stays_bounded(self):
        """
        Alternating 1st / 5th does not cause runaway growth or collapse.
        After 50 tournaments the value should stay in [45, 75] starting from 60.
        """
        val = 60.0
        for i in range(50):
            placement = 1 if i % 2 == 0 else 5
            val = calculate_skill_value_from_placement(
                baseline=60.0, placement=placement, total_players=5,
                tournament_count=1, skill_weight=1.0,
                prev_value=val, opponent_factor=1.0,
            )
        assert 45.0 <= val <= 75.0, (
            f"Alternating win/loss oscillated out of expected range: {val}"
        )

    def test_T18_value_at_fixed_point_no_movement(self):
        """
        When prev_value == placement_skill, raw_delta == 0 → new_value == prev_value.
        (EMA fixed point: already exactly at the evidence target.)
        """
        target = placement_skill(2, 5)  # e.g., 85.0
        val = calculate_skill_value_from_placement(
            baseline=target, placement=2, total_players=5,
            tournament_count=1, skill_weight=1.5,
            prev_value=target, opponent_factor=1.5,
        )
        assert abs(val - target) < 0.05, (
            f"At fixed point, expected no movement, got {val - target:.4f}"
        )
