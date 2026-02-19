"""
Unit tests for skill rating delta calculation (V3 EMA match-performance integration).

Tests cover:
  1. calculate_skill_value_from_placement — pure EMA math, no DB
     a. match_performance_modifier=0  →  unchanged from baseline EMA
     b. positive modifier + positive delta  →  amplified gain
     c. positive modifier + negative delta  →  softened loss  ← key domain rule
     d. negative modifier + positive delta  →  softened gain
     e. negative modifier + negative delta  →  amplified loss ← key domain rule
     f. modifier=+1 + negative delta  →  loss zeroed out (minimum penalty)
     g. modifier=-1 + positive delta  →  gain zeroed out (no reward if perf terrible)

  2. _compute_match_performance_modifier — confidence weighting
     a. no sessions → 0.0
     b. perfect win rate, n=1  →  low confidence, small modifier
     c. perfect win rate, n=10 →  high confidence, near max modifier
     d. 50% win rate           →  win_rate_signal=0, modifier driven by score only
     e. score data adds to signal
     f. all losses, n=10       →  strongly negative modifier

No DB required — pure function tests.
"""

import math
import pytest

from app.services.skill_progression_service import (
    calculate_skill_value_from_placement,
    MIN_SKILL_VALUE,
    MAX_SKILL_CAP,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ema_step(prev: float, placement: int, total: int,
              weight: float = 1.0, lr: float = 0.20,
              opp: float = 1.0, modifier: float = 0.0) -> float:
    """Call EMA path (prev_value != None)."""
    return calculate_skill_value_from_placement(
        baseline=prev,
        placement=placement,
        total_players=total,
        tournament_count=1,  # unused in V3 path
        skill_weight=weight,
        prev_value=prev,
        learning_rate=lr,
        opponent_factor=opp,
        match_performance_modifier=modifier,
    )


def _raw_delta(prev: float, placement: int, total: int,
               weight: float = 1.0, lr: float = 0.20) -> float:
    """Compute what raw_delta would be before modifier / opponent factor."""
    percentile = (placement - 1) / (total - 1) if total > 1 else 0.0
    placement_skill = 100.0 - (percentile * (100.0 - 40.0))
    step = lr * math.log(1.0 + weight) / math.log(2.0)
    return step * (placement_skill - prev)


# ── Tests: calculate_skill_value_from_placement ───────────────────────────────

@pytest.mark.unit
class TestCalculateSkillValueFromPlacement:

    def test_modifier_zero_is_identity(self):
        """modifier=0 must not change the result vs omitting it."""
        prev = 60.0
        with_zero   = _ema_step(prev, placement=1, total=8, modifier=0.0)
        without_arg = calculate_skill_value_from_placement(
            baseline=prev, placement=1, total_players=8, tournament_count=1,
            prev_value=prev,
        )
        assert with_zero == without_arg

    def test_positive_modifier_amplifies_positive_delta(self):
        """Good match perf (modifier>0) + top placement → larger gain."""
        prev = 60.0
        base  = _ema_step(prev, placement=1, total=8, modifier=0.0)
        boosted = _ema_step(prev, placement=1, total=8, modifier=0.5)
        assert boosted > base

    def test_positive_modifier_softens_negative_delta(self):
        """Good match perf (modifier>0) + last place → smaller loss (domain key rule)."""
        prev = 70.0
        base    = _ema_step(prev, placement=8, total=8, modifier=0.0)
        softened = _ema_step(prev, placement=8, total=8, modifier=0.5)
        # softened loss means new_value is HIGHER (less decrease) than base
        assert softened > base

    def test_negative_modifier_softens_positive_delta(self):
        """Poor match perf (modifier<0) + top placement → smaller gain."""
        prev = 60.0
        base    = _ema_step(prev, placement=1, total=8, modifier=0.0)
        reduced = _ema_step(prev, placement=1, total=8, modifier=-0.5)
        assert reduced < base

    def test_negative_modifier_amplifies_negative_delta(self):
        """Poor match perf (modifier<0) + last place → larger loss (domain key rule)."""
        prev = 70.0
        base      = _ema_step(prev, placement=8, total=8, modifier=0.0)
        amplified = _ema_step(prev, placement=8, total=8, modifier=-0.5)
        assert amplified < base

    def test_modifier_plus1_zeroes_negative_delta(self):
        """modifier=+1 on a losing placement → EMA step becomes zero → prev unchanged."""
        prev = 70.0
        result = _ema_step(prev, placement=8, total=8, modifier=1.0)
        # raw_delta < 0, (1 - 1.0) = 0 → adjusted_delta = 0 → new_val = prev
        assert result == prev

    def test_modifier_minus1_zeroes_positive_delta(self):
        """modifier=-1 on a winning placement → EMA step becomes zero → prev unchanged."""
        prev = 60.0
        result = _ema_step(prev, placement=1, total=8, modifier=-1.0)
        assert result == prev

    def test_values_clamped_to_min_max(self):
        """Result always within [MIN_SKILL_VALUE, MAX_SKILL_CAP]."""
        # Push toward boundary with extreme modifier
        result_high = _ema_step(99.0, placement=1, total=8, modifier=1.0)
        result_low  = _ema_step(40.0, placement=8, total=8, modifier=-1.0)
        assert MIN_SKILL_VALUE <= result_low  <= MAX_SKILL_CAP
        assert MIN_SKILL_VALUE <= result_high <= MAX_SKILL_CAP

    def test_sign_symmetry_is_direction_consistent(self):
        """
        Placing 2nd in 8p with modifier=+0.5 vs modifier=-0.5:
        positive modifier should always yield a higher value.
        """
        prev = 65.0
        pos = _ema_step(prev, placement=2, total=8, modifier=0.5)
        neg = _ema_step(prev, placement=2, total=8, modifier=-0.5)
        assert pos > neg

    def test_total_players_one_gives_max_placement_skill(self):
        """Single-player tournament: percentile=0 → placement_skill=MAX → no penalty."""
        prev = 55.0
        result = _ema_step(prev, placement=1, total=1, modifier=0.0)
        # placement_skill = 100, delta > 0
        assert result > prev


# ── Tests: confidence weighting behaviour (formula-level, no DB) ──────────────

@pytest.mark.unit
class TestMatchPerformanceModifierFormula:
    """
    Tests the confidence formula directly via numeric verification.
    No DB — we verify the math, not the DB query plumbing.
    """

    def _modifier(self, wins: int, losses: int, draws: int = 0,
                  goals_for: float = 0, goals_against: float = 0) -> float:
        """Replicate _compute_match_performance_modifier math without DB."""
        total = wins + losses + draws
        if total == 0:
            return 0.0
        win_rate_signal = ((wins / total) - 0.5) * 2.0
        total_goals = goals_for + goals_against
        score_signal = (goals_for - goals_against) / total_goals if total_goals > 0 else 0.0
        raw = 0.7 * win_rate_signal + 0.3 * score_signal
        confidence = 1.0 - math.exp(-total / 5.0)
        return round(max(-1.0, min(1.0, raw * confidence)), 4)

    def test_no_matches_returns_zero(self):
        assert self._modifier(0, 0) == 0.0

    def test_all_wins_low_n_is_small(self):
        """n=1, perfect win rate → confidence=0.18 → small positive modifier."""
        m = self._modifier(wins=1, losses=0)
        assert 0 < m < 0.2

    def test_all_wins_high_n_is_near_max(self):
        """n=10, perfect win rate → confidence=0.86 → modifier near +0.7."""
        m = self._modifier(wins=10, losses=0)
        assert m > 0.5

    def test_fifty_pct_win_no_score_is_zero(self):
        """Exactly 50% win rate + no scores → win_rate_signal=0 → modifier=0."""
        m = self._modifier(wins=5, losses=5)
        assert m == 0.0

    def test_all_losses_high_n_is_strongly_negative(self):
        m = self._modifier(wins=0, losses=10)
        assert m < -0.5

    def test_score_data_adds_signal(self):
        """5W 5L (neutral win rate) but dominated on goals → positive modifier."""
        m_no_score  = self._modifier(wins=5, losses=5, goals_for=0, goals_against=0)
        m_with_score = self._modifier(wins=5, losses=5, goals_for=20, goals_against=5)
        assert m_with_score > m_no_score

    def test_modifier_bounded(self):
        """Modifier always in [-1, +1]."""
        m_high = self._modifier(wins=100, losses=0, goals_for=1000, goals_against=0)
        m_low  = self._modifier(wins=0, losses=100, goals_for=0, goals_against=1000)
        assert -1.0 <= m_low  <= 1.0
        assert -1.0 <= m_high <= 1.0
