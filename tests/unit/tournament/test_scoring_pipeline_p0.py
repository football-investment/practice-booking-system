"""
P0 Scoring Pipeline Tests — Pre-Refactor Baseline
===================================================

Scope: RankingService + all strategies + SessionFinalizer IR pathway.

Three categories of tests:

  [GREEN]  Correct-behavior baseline tests — must always pass.
           Document what the strategies currently DO correctly.

  [RED]    Bug-reproduction tests marked xfail(strict=True).
           Each reproduces a specific bug from SCORING_PIPELINE_AUDIT_2026-02-18.md.
           xfail(strict=True) means:
             - Test FAILS today   → shown as `x`  (expected — bug present)
             - Test PASSES after fix → shown as `X` (CI fails — update the test)

  [GREEN]  IR pathway documentation test — verifies SessionFinalizer does NOT
           auto-trigger reward distribution (current design intent).

Referenced bugs:
  BUG-01  ranking_direction read in SessionFinalizer but not forwarded to RankingService
  BUG-02  PLACEMENT scoring_type maps to ScoreBasedStrategy (DESC/SUM) — should be ASC

All tests are DB-free (SimpleNamespace / MagicMock).
"""
import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from app.services.tournament.ranking.ranking_service import RankingService
from app.services.tournament.ranking.strategies.base import RankGroup
from app.services.tournament.ranking.strategies.time_based import TimeBasedStrategy
from app.services.tournament.ranking.strategies.score_based import ScoreBasedStrategy
from app.services.tournament.ranking.strategies.rounds_based import RoundsBasedStrategy
from app.services.tournament.ranking.strategies.placement import PlacementStrategy
from app.services.tournament.ranking.strategies.factory import RankingStrategyFactory


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _round_results_single(*player_value_pairs):
    """Build single-round round_results dict from (user_id, value_str) pairs."""
    return {"1": {str(uid): val for uid, val in player_value_pairs}}


def _round_results_multi(rounds):
    """Build multi-round round_results from list of dicts: [{"uid": "val", ...}, ...]"""
    return {str(i + 1): {str(uid): val for uid, val in r.items()}
            for i, r in enumerate(rounds)}


def _participants(*user_ids):
    return [{"user_id": uid} for uid in user_ids]


def _rank_map(rank_groups):
    """Return {user_id: rank} dict from List[RankGroup]."""
    result = {}
    for rg in rank_groups:
        for uid in rg.participants:
            result[uid] = rg.rank
    return result


def _winner(rank_groups):
    """Return the user_id(s) with rank=1."""
    return rank_groups[0].participants


# ─────────────────────────────────────────────────────────────────────────────
# 1. TimeBasedStrategy — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeBasedStrategy:
    """TIME_BASED: MIN aggregation, ASC sort (fastest wins)."""

    def setup_method(self):
        self.strategy = TimeBasedStrategy()

    # TB-01
    def test_aggregate_value_returns_minimum(self):
        assert self.strategy.aggregate_value([12.5, 10.8, 11.0]) == 10.8

    # TB-02
    def test_sort_direction_is_asc(self):
        assert self.strategy.get_sort_direction() == "ASC"

    # TB-03
    def test_fastest_player_is_rank_1(self):
        """Player with minimum best time wins."""
        # A=10.5s (best), B=11.2s, C=12.0s
        rr = _round_results_single((1, "10.5s"), (2, "11.2s"), (3, "12.0s"))
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2, 3))
        assert _winner(groups) == [1]

    # TB-04
    def test_multi_round_takes_minimum_per_player(self):
        """Each player's best (minimum) time across rounds is used."""
        rr = _round_results_multi([
            {1: "11.0s", 2: "10.0s"},   # round 1: B=10.0 best
            {1: "10.2s", 2: "10.8s"},   # round 2: A=10.2 best
        ])
        # A best=10.2, B best=10.0 → B wins (lower = better)
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2))
        assert _winner(groups) == [2], f"B (10.0s) should beat A (10.2s), got {_winner(groups)}"

    # TB-05
    def test_tie_gives_same_rank_and_next_rank_skips(self):
        """Two players with identical best times share rank 1; next rank is 3."""
        rr = _round_results_single((1, "10.5s"), (2, "10.5s"), (3, "11.0s"))
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2, 3))
        ranks = _rank_map(groups)
        assert ranks[1] == ranks[2] == 1, "Tied players must share rank 1"
        assert ranks[3] == 3, "After 2-way tie at rank 1, next rank is 3 (not 2)"

    # TB-06
    def test_aggregate_value_single_value(self):
        assert self.strategy.aggregate_value([9.9]) == 9.9

    # TB-07
    def test_string_parsing_with_units(self):
        """Values like '10.5s', '10.5 seconds', '10.5' all parse to 10.5."""
        for val_str in ["10.5s", "10.5 seconds", "10.5"]:
            rr = _round_results_single((1, val_str), (2, "11.0s"))
            groups = self.strategy.calculate_rankings(rr, _participants(1, 2))
            assert _winner(groups) == [1], f"Failed to parse '{val_str}'"


# ─────────────────────────────────────────────────────────────────────────────
# 2. ScoreBasedStrategy — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreBasedStrategy:
    """SCORE_BASED: SUM aggregation, DESC sort (highest total wins)."""

    def setup_method(self):
        self.strategy = ScoreBasedStrategy()

    # SB-01
    def test_aggregate_value_returns_sum(self):
        assert self.strategy.aggregate_value([10.0, 15.0, 20.0]) == 45.0

    # SB-02
    def test_sort_direction_is_desc(self):
        assert self.strategy.get_sort_direction() == "DESC"

    # SB-03
    def test_highest_total_score_is_rank_1(self):
        """Player with maximum SUM wins."""
        # A=15+18+16=49, B=12+20+18=50 → B wins
        rr = _round_results_multi([
            {1: "15pts", 2: "12pts"},
            {1: "18pts", 2: "20pts"},
            {1: "16pts", 2: "18pts"},
        ])
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2))
        assert _winner(groups) == [2], "B (50 total) should beat A (49 total)"

    # SB-04
    def test_single_round_scores_summed(self):
        rr = _round_results_single((1, "100pts"), (2, "80pts"), (3, "90pts"))
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2, 3))
        ranks = _rank_map(groups)
        assert ranks[1] == 1   # 100
        assert ranks[3] == 2   # 90
        assert ranks[2] == 3   # 80

    # SB-05
    def test_tie_shares_rank_and_next_skips(self):
        """Two players with identical SUM share rank 2; rank 3 is skipped."""
        rr = _round_results_single((1, "50pts"), (2, "40pts"), (3, "40pts"))
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2, 3))
        ranks = _rank_map(groups)
        assert ranks[1] == 1
        assert ranks[2] == ranks[3] == 2
        # Next rank after 2-way tie at 2 is 4 (not 3)
        assert all(rg.rank != 3 for rg in groups), "Rank 3 should be skipped after 2-way tie"

    # SB-06
    def test_multi_round_accumulates_correctly(self):
        """SUM across all rounds, not just best round."""
        rr = _round_results_multi([
            {1: "10", 2: "1"},   # round 1: A=10, B=1
            {1: "10", 2: "1"},   # round 2: A=10, B=1
            {1: "10", 2: "1"},   # round 3: A=10, B=1
        ])
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2))
        winner_rg = groups[0]
        assert winner_rg.participants == [1]
        assert winner_rg.final_value == 30.0, "SUM of 3×10 = 30"


# ─────────────────────────────────────────────────────────────────────────────
# 3. RoundsBasedStrategy — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestRoundsBasedStrategy:
    """ROUNDS_BASED: MAX aggregation, DESC sort (best single-round result wins)."""

    def setup_method(self):
        self.strategy = RoundsBasedStrategy()

    # RB-01
    def test_aggregate_value_returns_maximum(self):
        assert self.strategy.aggregate_value([6.0, 11.0, 10.0]) == 11.0

    # RB-02
    def test_sort_direction_is_desc(self):
        assert self.strategy.get_sort_direction() == "DESC"

    # RB-03
    def test_best_single_round_determines_winner(self):
        """
        Tournament 222 example from rounds_based.py docstring.
        Mbappé(13): 11, 10, 11 → best=11
        Tibor(7):   6,  7,  10 → best=10
        Yamal(14):  8,  10, 10 → best=10
        → Mbappé ranks 1st; Tibor & Yamal tie at 2nd; next rank = 4th.
        """
        rr = _round_results_multi([
            {13: "11 pts", 7: "6 pts", 14: "8 pts"},
            {13: "10 pts", 7: "7 pts", 14: "10 pts"},
            {13: "11 pts", 7: "10 pts", 14: "10 pts"},
        ])
        groups = self.strategy.calculate_rankings(rr, _participants(13, 7, 14))
        assert _winner(groups) == [13], "Mbappé (best=11) should be rank 1"
        ranks = _rank_map(groups)
        assert ranks[7] == ranks[14] == 2, "Tibor & Yamal both have best=10, should tie at rank 2"
        assert ranks[7] != 3, "Rank 3 should be skipped after 2-way tie at 2"

    # RB-04
    def test_max_not_sum_used_for_aggregation(self):
        """ROUNDS_BASED picks MAX, not SUM — distinguish from SCORE_BASED."""
        rr = _round_results_multi([
            {1: "1 pts", 2: "5 pts"},   # round 1
            {1: "1 pts", 2: "5 pts"},   # round 2
        ])
        # B: SUM=10, MAX=5; A: SUM=2, MAX=1
        # Both strategies would rank B first here — use a different scenario:
        rr2 = _round_results_multi([
            {1: "3 pts", 2: "1 pts"},   # A=3, B=1  (A higher this round)
            {1: "3 pts", 2: "10 pts"},  # A=3, B=10 (B has one big round)
        ])
        # SUM: A=6, B=11 → B wins;  MAX: A=3, B=10 → B still wins here
        # More distinct test:
        rr3 = _round_results_multi([
            {1: "10 pts", 2: "3 pts"},  # A=10, B=3
            {1: "1 pts",  2: "9 pts"},  # A=1, B=9
        ])
        # MAX: A=10, B=9 → A wins
        # SUM: A=11, B=12 → B wins (SCORE_BASED would pick B)
        groups = self.strategy.calculate_rankings(rr3, _participants(1, 2))
        assert _winner(groups) == [1], (
            "ROUNDS_BASED uses MAX: A best=10 > B best=9 → A wins. "
            "SUM would give B (11<12) — verify we use MAX not SUM."
        )

    # RB-05
    def test_single_round_tournament_uses_that_round(self):
        rr = _round_results_single((1, "7 pts"), (2, "9 pts"))
        groups = self.strategy.calculate_rankings(rr, _participants(1, 2))
        assert _winner(groups) == [2], "Single-round: player with 9 pts wins"


# ─────────────────────────────────────────────────────────────────────────────
# 4. RankingStrategyFactory dispatch — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestRankingStrategyFactory:
    """Factory correctly dispatches each scoring_type to the right strategy class."""

    # F-01
    def test_time_based_creates_time_based_strategy(self):
        s = RankingStrategyFactory.create("TIME_BASED")
        assert isinstance(s, TimeBasedStrategy)

    # F-02
    def test_score_based_creates_score_based_strategy(self):
        s = RankingStrategyFactory.create("SCORE_BASED")
        assert isinstance(s, ScoreBasedStrategy)

    # F-03
    def test_rounds_based_creates_rounds_based_strategy(self):
        s = RankingStrategyFactory.create("ROUNDS_BASED")
        assert isinstance(s, RoundsBasedStrategy)

    # F-04
    def test_distance_based_creates_score_based_strategy(self):
        """DISTANCE_BASED is currently mapped to ScoreBasedStrategy."""
        s = RankingStrategyFactory.create("DISTANCE_BASED")
        assert isinstance(s, ScoreBasedStrategy)

    # F-05
    def test_placement_creates_placement_strategy(self):
        """PLACEMENT now maps to PlacementStrategy (BUG-02 fixed)."""
        s = RankingStrategyFactory.create("PLACEMENT")
        assert isinstance(s, PlacementStrategy)
        assert not isinstance(s, ScoreBasedStrategy)

    # F-06
    def test_unknown_scoring_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown scoring_type"):
            RankingStrategyFactory.create("UNKNOWN_TYPE")

    # F-07
    def test_head_to_head_swiss_raises_value_error(self):
        """BUG-05 documented: Swiss is not registered in the factory."""
        with pytest.raises(ValueError):
            RankingStrategyFactory.create(
                tournament_format="HEAD_TO_HEAD",
                tournament_type_code="swiss"
            )

    # F-08
    def test_strategy_aggregate_values_match_documented_behaviour(self):
        """Verify hardcoded aggregation per strategy — used as baseline for BUG-01 tests."""
        time_s = RankingStrategyFactory.create("TIME_BASED")
        score_s = RankingStrategyFactory.create("SCORE_BASED")
        rounds_s = RankingStrategyFactory.create("ROUNDS_BASED")

        values = [3.0, 7.0, 5.0]
        assert time_s.aggregate_value(values)   == 3.0   # MIN
        assert score_s.aggregate_value(values)  == 15.0  # SUM
        assert rounds_s.aggregate_value(values) == 7.0   # MAX

    # F-09
    def test_strategy_sort_directions_are_hardcoded(self):
        """
        Each strategy has a hardcoded sort direction — no runtime override.
        This is the precondition for BUG-01: ranking_direction cannot be injected.
        """
        assert RankingStrategyFactory.create("TIME_BASED").get_sort_direction()   == "ASC"
        assert RankingStrategyFactory.create("SCORE_BASED").get_sort_direction()  == "DESC"
        assert RankingStrategyFactory.create("ROUNDS_BASED").get_sort_direction() == "DESC"


# ─────────────────────────────────────────────────────────────────────────────
# 5. RankingService.convert_to_legacy_format — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestRankingServiceLegacyConversion:

    def setup_method(self):
        self.service = RankingService()

    # LC-01
    def test_single_winner_converted_correctly(self):
        groups = [RankGroup(rank=1, participants=[42], final_value=10.5)]
        perf, wins = self.service.convert_to_legacy_format(groups, "seconds")
        assert len(perf) == 1
        assert perf[0] == {
            "user_id": 42, "rank": 1, "final_value": 10.5,
            "measurement_unit": "seconds", "is_tied": False
        }
        assert wins == [], "Modern flow returns empty wins_rankings"

    # LC-02
    def test_tied_group_expands_to_multiple_entries_with_same_rank(self):
        groups = [
            RankGroup(rank=1, participants=[1, 2], final_value=10.0),  # tie
            RankGroup(rank=3, participants=[3], final_value=8.0),
        ]
        perf, _ = self.service.convert_to_legacy_format(groups)
        ranks = {e["user_id"]: e["rank"] for e in perf}
        tied = {e["user_id"]: e["is_tied"] for e in perf}
        assert ranks[1] == ranks[2] == 1, "Tied players share rank 1"
        assert ranks[3] == 3, "Rank 3 after 2-way tie (rank 2 skipped)"
        assert tied[1] is True
        assert tied[2] is True
        assert tied[3] is False

    # LC-03
    def test_empty_rank_groups_returns_empty_list(self):
        perf, wins = self.service.convert_to_legacy_format([])
        assert perf == []
        assert wins == []


# ─────────────────────────────────────────────────────────────────────────────
# 6. RankingService end-to-end dispatch — [GREEN]
# ─────────────────────────────────────────────────────────────────────────────

class TestRankingServiceDispatch:
    """Full calculate_rankings() calls through RankingService."""

    def setup_method(self):
        self.service = RankingService()

    # RS-01
    def test_time_based_dispatches_min_asc(self):
        rr = _round_results_single((1, "9.0s"), (2, "11.0s"))
        groups = self.service.calculate_rankings("TIME_BASED", rr, _participants(1, 2))
        assert _winner(groups) == [1], "TIME_BASED: lowest time wins"

    # RS-02
    def test_score_based_dispatches_sum_desc(self):
        rr = _round_results_multi([{1: "10", 2: "5"}, {1: "10", 2: "5"}])
        groups = self.service.calculate_rankings("SCORE_BASED", rr, _participants(1, 2))
        assert _winner(groups) == [1], "SCORE_BASED: highest SUM wins"

    # RS-03
    def test_rounds_based_dispatches_max_desc(self):
        # A: rounds [1, 20]; B: rounds [15, 15]  → A MAX=20, B MAX=15
        rr = _round_results_multi([{1: "1", 2: "15"}, {1: "20", 2: "15"}])
        groups = self.service.calculate_rankings("ROUNDS_BASED", rr, _participants(1, 2))
        assert _winner(groups) == [1], "ROUNDS_BASED: highest single-round value wins"

    # RS-04
    def test_calculate_rankings_signature_has_ranking_direction_param(self):
        """
        BUG-01 fixed: RankingService.calculate_rankings() now accepts ranking_direction.
        """
        import inspect
        sig = inspect.signature(self.service.calculate_rankings)
        assert "ranking_direction" in sig.parameters, (
            "BUG-01 fix was reverted: ranking_direction missing from RankingService.calculate_rankings()."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. BUG-01 reproduction — ranking_direction ignored [xfail → RED]
# ─────────────────────────────────────────────────────────────────────────────

class TestBUG01_RankingDirectionFixed:
    """
    BUG-01 FIXED: ranking_direction is now forwarded through the full chain:
      SessionFinalizer → RankingService.calculate_rankings(ranking_direction=...) → strategy

    Each strategy now respects the ranking_direction override when provided.
    These tests verify the fix is working correctly.
    """

    def setup_method(self):
        self.service = RankingService()

    # BUG01-A (was xfail, now GREEN)
    def test_bug01a_score_based_asc_direction_lower_score_wins(self):
        """
        SCORE_BASED with ranking_direction='ASC' (lower score = better, e.g. fewest errors).
        Player A: 1 error.  Player B: 5 errors.
        With ranking_direction='ASC': Player A (fewer errors) must be rank 1.
        """
        rr = _round_results_single((1, "1"), (2, "5"))
        groups = self.service.calculate_rankings(
            scoring_type="SCORE_BASED",
            round_results=rr,
            participants=_participants(1, 2),
            ranking_direction="ASC",
        )
        winner = _winner(groups)
        assert winner == [1], (
            f"Player 1 (score=1, fewer errors) must win with ranking_direction='ASC'. "
            f"Got winner={winner}."
        )

    # BUG01-B (was xfail, now GREEN)
    def test_bug01b_rounds_based_asc_direction_lower_best_wins(self):
        """
        ROUNDS_BASED with ranking_direction='ASC' (sprint: lower time = faster).
        Player A: best round = 2.0s.  Player B: best round = 9.0s.
        With ranking_direction='ASC': Player A (faster) must be rank 1.
        """
        rr = _round_results_multi([
            {1: "2.0s", 2: "9.0s"},
            {1: "5.0s", 2: "9.0s"},
        ])
        groups = self.service.calculate_rankings(
            scoring_type="ROUNDS_BASED",
            round_results=rr,
            participants=_participants(1, 2),
            ranking_direction="ASC",
        )
        winner = _winner(groups)
        assert winner == [1], (
            f"Player 1 (best round=2.0s) must win with ranking_direction='ASC'. "
            f"Got winner={winner}."
        )

    # BUG01-C (was xfail, now GREEN)
    def test_bug01c_ranking_service_api_accepts_ranking_direction(self):
        """
        RankingService.calculate_rankings() now accepts ranking_direction — BUG-01 fixed.
        """
        import inspect
        sig = inspect.signature(self.service.calculate_rankings)
        assert "ranking_direction" in sig.parameters, (
            "RankingService.calculate_rankings() must accept 'ranking_direction'. "
            "If this fails, the BUG-01 fix was reverted."
        )

    def test_bug01_default_none_preserves_original_behaviour(self):
        """
        ranking_direction=None (default) must produce same results as before the fix.
        SCORE_BASED without override → DESC (highest score wins).
        """
        rr = _round_results_single((1, "1"), (2, "5"))
        groups = self.service.calculate_rankings(
            scoring_type="SCORE_BASED",
            round_results=rr,
            participants=_participants(1, 2),
            # no ranking_direction → default DESC
        )
        winner = _winner(groups)
        assert winner == [2], (
            "Without ranking_direction override, SCORE_BASED must keep DESC (highest=5 wins). "
            f"Got winner={winner}."
        )

    def test_bug01_desc_override_matches_default_for_score_based(self):
        """Explicit DESC == no override for SCORE_BASED."""
        rr = _round_results_single((1, "1"), (2, "5"))
        g_default = self.service.calculate_rankings("SCORE_BASED", rr, _participants(1, 2))
        g_explicit = self.service.calculate_rankings("SCORE_BASED", rr, _participants(1, 2), ranking_direction="DESC")
        assert _rank_map(g_default) == _rank_map(g_explicit)

    def test_bug01_rounds_based_asc_uses_min_aggregation(self):
        """
        ROUNDS_BASED + ASC: aggregation must flip from MAX to MIN.
        A: [1, 5], B: [3, 4] → A MAX=5, B MAX=4 (B wins DESC); A MIN=1, B MIN=3 (A wins ASC).
        """
        rr = _round_results_multi([{1: "1", 2: "3"}, {1: "5", 2: "4"}])
        groups_asc = self.service.calculate_rankings("ROUNDS_BASED", rr, _participants(1, 2), ranking_direction="ASC")
        groups_desc = self.service.calculate_rankings("ROUNDS_BASED", rr, _participants(1, 2), ranking_direction="DESC")
        assert _winner(groups_asc) == [1], "ASC: A (MIN=1) beats B (MIN=3)"
        assert _winner(groups_desc) == [1], "DESC: A (MAX=5) beats B (MAX=4)"


# ─────────────────────────────────────────────────────────────────────────────
# 8. BUG-02 reproduction — PLACEMENT sort direction wrong [xfail → RED]
# ─────────────────────────────────────────────────────────────────────────────

class TestBUG02_PlacementStrategyFixed:
    """
    BUG-02 FIXED: PLACEMENT now maps to PlacementStrategy (SUM/ASC).

    PlacementStrategy:
      - Aggregation: SUM (total placement positions across rounds)
      - Sort: ASC (lower placement-sum = better, like golf scoring)

    Previously PLACEMENT mapped to ScoreBasedStrategy (DESC/SUM) which incorrectly
    ranked placement=3 above placement=1.
    """

    def setup_method(self):
        self.service = RankingService()

    # BUG02-A (was xfail, now GREEN)
    def test_bug02a_placement_winner_has_lowest_placement_number(self):
        """
        Single-round placement tournament.
        Player A: placement=1 (race winner).
        Player B: placement=2.
        Player C: placement=3.
        Expected and actual: A at rank 1.
        """
        rr = _round_results_single((1, "1"), (2, "2"), (3, "3"))
        groups = self.service.calculate_rankings(
            scoring_type="PLACEMENT",
            round_results=rr,
            participants=_participants(1, 2, 3),
        )
        winner = _winner(groups)
        assert winner == [1], (
            f"Player 1 (placement=1) must be rank 1 with PlacementStrategy (ASC). "
            f"Got winner={winner}."
        )

    # BUG02-B (was xfail, now GREEN)
    def test_bug02b_multi_round_placement_lower_sum_wins(self):
        """
        2-round placement event:
        Player A: placed 1st + 1st = sum 2 (best).
        Player B: placed 1st + 3rd = sum 4 (worse).
        PlacementStrategy (SUM/ASC): A wins.
        """
        rr = _round_results_multi([
            {1: "1", 2: "1"},   # round 1: both 1st (tie)
            {1: "1", 2: "3"},   # round 2: A=1st, B=3rd
        ])
        groups = self.service.calculate_rankings(
            scoring_type="PLACEMENT",
            round_results=rr,
            participants=_participants(1, 2),
        )
        winner = _winner(groups)
        assert winner == [1], (
            f"Player 1 (sum=2) must beat Player 2 (sum=4) with ASC sort. Got winner={winner}."
        )

    # BUG02-C — updated: PLACEMENT now produces PlacementStrategy (not ScoreBasedStrategy)
    def test_bug02c_placement_returns_placement_strategy_instance(self):
        """
        Factory now maps PLACEMENT → PlacementStrategy (BUG-02 fixed).
        """
        strategy = RankingStrategyFactory.create("PLACEMENT")
        assert isinstance(strategy, PlacementStrategy), (
            f"PLACEMENT must map to PlacementStrategy, got {type(strategy).__name__}. "
            "BUG-02 fix may have been reverted."
        )
        assert not isinstance(strategy, ScoreBasedStrategy), (
            "PLACEMENT must NOT map to ScoreBasedStrategy any more."
        )

    def test_bug02_placement_aggregate_is_sum(self):
        strategy = PlacementStrategy()
        assert strategy.aggregate_value([1.0, 3.0, 2.0]) == 6.0

    def test_bug02_placement_sort_direction_is_asc(self):
        strategy = PlacementStrategy()
        assert strategy.get_sort_direction() == "ASC"

    def test_bug02_placement_tied_placements_share_rank(self):
        """Two players with same placement-sum share rank; next rank skips."""
        rr = _round_results_single((1, "2"), (2, "2"), (3, "4"))
        groups = self.service.calculate_rankings("PLACEMENT", rr, _participants(1, 2, 3))
        ranks = _rank_map(groups)
        assert ranks[1] == ranks[2] == 1, "Both with sum=2 share rank 1"
        assert ranks[3] == 3, "After 2-way tie at 1, next rank is 3"


# ─────────────────────────────────────────────────────────────────────────────
# 9. IR pathway — reward NOT triggered [GREEN — documents current design]
# ─────────────────────────────────────────────────────────────────────────────

class TestIRPathwayRewardNotTriggered:
    """
    Integration test: SessionFinalizer.finalize() (IR pathway) must NOT call
    distribute_rewards_for_tournament().

    Reward distribution is exclusively the responsibility of TournamentFinalizer,
    which is triggered by the admin COMPLETED status transition.

    This test documents the design separation:
      SessionFinalizer  → per-session ranking only
      TournamentFinalizer → final rankings + XP distribution

    If this test starts failing, it means reward distribution was accidentally
    introduced into the IR session finalization path.
    """

    def _build_mock_db(self, existing_ranking_count=0, unfinalized_session_count=0):
        """
        Build a mock SQLAlchemy session that covers all DB interactions in
        SessionFinalizer.finalize().
        """
        mock_db = MagicMock()

        def _query_side_effect(model):
            q = MagicMock()
            inner = MagicMock()
            # .filter().count() → 0 (no existing TournamentRanking)
            inner.filter.return_value = inner
            inner.count.return_value = existing_ranking_count
            # .filter().all() → empty list (all sessions "finalized")
            inner.all.return_value = [] if unfinalized_session_count == 0 else [MagicMock()]
            q.filter.return_value = inner
            return q

        mock_db.query.side_effect = _query_side_effect
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        return mock_db

    def _build_tournament(self):
        return SimpleNamespace(
            id=999,
            format="INDIVIDUAL_RANKING",
            scoring_type="SCORE_BASED",
            ranking_direction="DESC",
            measurement_unit="pts",
            tournament_status="IN_PROGRESS",
        )

    def _build_session(self, total_rounds=1, completed_rounds=1):
        return SimpleNamespace(
            id=111,
            semester_id=999,
            match_format="INDIVIDUAL_RANKING",
            game_results=None,  # not yet finalized
            rounds_data={
                "total_rounds": total_rounds,
                "completed_rounds": completed_rounds,
                "round_results": {
                    "1": {"101": "10 pts", "102": "7 pts"}
                },
            },
            tournament_phase="INDIVIDUAL_RANKING",
        )

    @patch(
        "app.services.tournament.results.finalization.session_finalizer."
        "calculate_ranks"
    )
    @patch(
        "app.services.tournament.results.finalization.session_finalizer."
        "get_or_create_ranking"
    )
    def test_session_finalizer_does_not_call_distribute_rewards(
        self,
        mock_get_or_create,
        mock_calculate_ranks,
    ):
        """
        SessionFinalizer.finalize() must NOT call distribute_rewards_for_tournament.

        TournamentFinalizer is the sole caller of reward distribution.
        This test patches the reward orchestrator and asserts it was never called.
        """
        # Patch the reward orchestrator at its source module.
        # tournament_finalizer.py imports it lazily inside finalize(), so we patch
        # the canonical location instead of the importer.
        with patch(
            "app.services.tournament.tournament_reward_orchestrator."
            "distribute_rewards_for_tournament"
        ) as mock_distribute:
            from app.services.tournament.results.finalization.session_finalizer import (
                SessionFinalizer,
            )

            mock_ranking = MagicMock()
            mock_ranking.points = 0
            mock_get_or_create.return_value = mock_ranking

            db = self._build_mock_db(existing_ranking_count=0)
            tournament = self._build_tournament()
            session = self._build_session(total_rounds=1, completed_rounds=1)

            finalizer = SessionFinalizer(db)
            result = finalizer.finalize(
                tournament=tournament,
                session=session,
                recorded_by_id=1,
                recorded_by_name="Test Instructor",
            )

            # ── Primary assertion ──────────────────────────────────────────
            mock_distribute.assert_not_called(), (
                "distribute_rewards_for_tournament MUST NOT be called from SessionFinalizer. "
                "Only TournamentFinalizer triggers reward distribution after admin sets COMPLETED."
            )

            # ── Sanity checks on the finalization result ───────────────────
            assert result["success"] is True, f"Finalization failed: {result}"
            assert result["session_id"] == 111
            assert result["tournament_id"] == 999
            assert len(result["final_rankings"]) >= 1

            # game_results written as JSON
            assert session.game_results is not None
            stored = json.loads(session.game_results)
            assert stored["tournament_format"] == "INDIVIDUAL_RANKING"
            assert stored["scoring_type"] == "SCORE_BASED"

    # IR-02
    @patch(
        "app.services.tournament.results.finalization.session_finalizer.calculate_ranks"
    )
    @patch(
        "app.services.tournament.results.finalization.session_finalizer.get_or_create_ranking"
    )
    def test_session_finalizer_idempotency_guard_rejects_already_finalized(
        self,
        mock_get_or_create,
        mock_calculate_ranks,
    ):
        """
        IDEMPOTENCY GUARD #1: If session.game_results is already set,
        finalize() must raise ValueError, not re-finalize.
        """
        from app.services.tournament.results.finalization.session_finalizer import (
            SessionFinalizer,
        )

        db = self._build_mock_db()
        tournament = self._build_tournament()
        session = self._build_session()
        session.game_results = json.dumps({"recorded_at": "2026-01-01T00:00:00"})

        finalizer = SessionFinalizer(db)
        with pytest.raises(ValueError, match="already finalized"):
            finalizer.finalize(
                tournament=tournament,
                session=session,
                recorded_by_id=1,
                recorded_by_name="Test Instructor",
            )

    # IR-03
    @patch(
        "app.services.tournament.results.finalization.session_finalizer.calculate_ranks"
    )
    @patch(
        "app.services.tournament.results.finalization.session_finalizer.get_or_create_ranking"
    )
    def test_session_finalizer_idempotency_guard_rejects_existing_tournament_rankings(
        self,
        mock_get_or_create,
        mock_calculate_ranks,
    ):
        """
        IDEMPOTENCY GUARD #2: If TournamentRanking rows already exist,
        finalize() must raise ValueError to prevent dual finalization.
        """
        from app.services.tournament.results.finalization.session_finalizer import (
            SessionFinalizer,
        )

        db = self._build_mock_db(existing_ranking_count=3)  # 3 existing rankings
        tournament = self._build_tournament()
        session = self._build_session()

        finalizer = SessionFinalizer(db)
        with pytest.raises(ValueError, match="already has"):
            finalizer.finalize(
                tournament=tournament,
                session=session,
                recorded_by_id=1,
                recorded_by_name="Test Instructor",
            )

    # IR-04
    def test_validate_all_rounds_completed_blocks_incomplete_session(self):
        """
        Validate that incomplete rounds prevent finalization.
        """
        from app.services.tournament.results.finalization.session_finalizer import (
            SessionFinalizer,
        )

        finalizer = SessionFinalizer(MagicMock())
        rounds_data = {"total_rounds": 3, "completed_rounds": 1}
        is_valid, message = finalizer.validate_all_rounds_completed(rounds_data)
        assert is_valid is False
        assert "2 rounds remaining" in message

    # IR-05
    def test_validate_all_rounds_completed_passes_when_all_done(self):
        """All rounds complete → validation passes."""
        from app.services.tournament.results.finalization.session_finalizer import (
            SessionFinalizer,
        )
        finalizer = SessionFinalizer(MagicMock())
        rounds_data = {"total_rounds": 3, "completed_rounds": 3}
        is_valid, message = finalizer.validate_all_rounds_completed(rounds_data)
        assert is_valid is True
        assert message == ""
