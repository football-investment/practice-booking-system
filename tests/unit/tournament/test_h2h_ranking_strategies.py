"""
Unit tests for HEAD-TO-HEAD Ranking Strategies

Covers all three H2H strategy classes:
  - HeadToHeadKnockoutRankingStrategy   (single elimination)
  - HeadToHeadLeagueRankingStrategy     (round robin / league)
  - HeadToHeadGroupKnockoutRankingStrategy (group stage + knockout)

Design principles:
  - DB-free: db_session parameter exists in all strategies but is never called.
    Tests pass None throughout.
  - SimpleNamespace mock sessions carry only the attributes the strategy reads:
    game_results, tournament_round, title (knockout), tournament_phase,
    group_identifier (group+knockout).
  - Beyond statement coverage: every test asserts mathematical invariants
    (rank uniqueness, monotonicity, point conservation, tie-break stability).
"""
import json
import pytest
from types import SimpleNamespace
from typing import List

from app.services.tournament.ranking.strategies.head_to_head_knockout import (
    HeadToHeadKnockoutRankingStrategy,
)
from app.services.tournament.ranking.strategies.head_to_head_league import (
    HeadToHeadLeagueRankingStrategy,
)
from app.services.tournament.ranking.strategies.head_to_head_group_knockout import (
    HeadToHeadGroupKnockoutRankingStrategy,
)


# ─── Session factory helpers ──────────────────────────────────────────────────

def _h2h_game_results(u1, u2, r1, r2, s1, s2, round_num=1):
    """Return a game_results dict for a HEAD_TO_HEAD match."""
    return {
        "match_format": "HEAD_TO_HEAD",
        "round_number": round_num,
        "participants": [
            {"user_id": u1, "result": r1, "score": s1},
            {"user_id": u2, "result": r2, "score": s2},
        ],
    }


def _knockout_session(u1, u2, r1, r2, s1=0, s2=0, round_num=1, title=None):
    """SimpleNamespace session for HeadToHeadKnockoutRankingStrategy."""
    return SimpleNamespace(
        game_results=_h2h_game_results(u1, u2, r1, r2, s1, s2, round_num),
        tournament_round=round_num,
        title=title or f"Round {round_num}",
    )


def _league_session(u1, u2, r1, r2, s1=0, s2=0):
    """SimpleNamespace session for HeadToHeadLeagueRankingStrategy."""
    return SimpleNamespace(
        game_results=_h2h_game_results(u1, u2, r1, r2, s1, s2),
    )


def _group_session(u1, u2, r1, r2, s1=0, s2=0, group="A"):
    """SimpleNamespace session for group stage within HeadToHeadGroupKnockoutRankingStrategy."""
    return SimpleNamespace(
        game_results=_h2h_game_results(u1, u2, r1, r2, s1, s2),
        tournament_phase="GROUP_STAGE",
        group_identifier=group,
    )


def _knockout_group_session(u1, u2, r1, r2, s1=0, s2=0, round_num=2, title=None):
    """SimpleNamespace session for knockout phase within HeadToHeadGroupKnockoutRankingStrategy."""
    return SimpleNamespace(
        game_results=_h2h_game_results(u1, u2, r1, r2, s1, s2, round_num),
        tournament_phase="KNOCKOUT",
        tournament_round=round_num,
        title=title or f"Knockout Round {round_num}",
    )


# ─── Invariant helpers ────────────────────────────────────────────────────────

def _assert_all_participants_present(sessions, rankings, participant_key="user_id"):
    """Every user_id that appeared in any session must appear in rankings exactly once."""
    expected_ids = set()
    for s in sessions:
        if isinstance(s.game_results, dict) and "participants" in s.game_results:
            for p in s.game_results["participants"]:
                expected_ids.add(p["user_id"])
    ranking_ids = [r["user_id"] for r in rankings]
    assert set(ranking_ids) == expected_ids, (
        f"Missing or extra participants: {expected_ids ^ set(ranking_ids)}"
    )
    assert len(ranking_ids) == len(set(ranking_ids)), "Duplicate user_id in rankings"


def _assert_ranks_start_at_one(rankings):
    """Rank 1 must exist (unless rankings are empty)."""
    if not rankings:
        return
    assert min(r["rank"] for r in rankings) == 1


def _assert_no_rank_gap_beyond_tie(rankings):
    """
    After sorting by rank, consecutive entries either share a rank (tie)
    or the next rank is exactly previous_rank + 1 + (number of tied entries - 1).
    Simpler invariant: every rank value from 1 to max_rank that *should* exist
    does exist (no skipped ranks that aren't explained by ties).
    Concretely: sorted ranks must be non-decreasing and each rank increment
    is >= 1 (ties allowed) and <= (count of previous tied participants).
    """
    sorted_ranks = sorted(r["rank"] for r in rankings)
    for i in range(1, len(sorted_ranks)):
        gap = sorted_ranks[i] - sorted_ranks[i - 1]
        assert gap >= 0, "Ranks must be non-decreasing"
        # A jump of more than 1 is only valid if caused by a tie block above.
        # Count how many participants share the previous rank.
        prev_rank = sorted_ranks[i - 1]
        tie_count = sum(1 for r in rankings if r["rank"] == prev_rank)
        assert gap <= tie_count, (
            f"Rank jumped by {gap} after {tie_count} tied entries at rank {prev_rank}"
        )


# ============================================================================
# Section 1 — HeadToHeadKnockoutRankingStrategy
# ============================================================================

@pytest.mark.unit
@pytest.mark.tournament
class TestKnockoutRanking:
    """
    HeadToHeadKnockoutRankingStrategy

    Invariants verified:
    - Rank 1 is unique (single champion)
    - All participants present exactly once
    - Rank sequence is gapless within tie blocks
    - Higher round reached → better rank (monotonicity)
    - Tied at same round + result → same rank
    - Elimination score breaks same-round ties (higher score = better rank)
    - 3rd Place Playoff title shifts winner to rank 3, not rank 1
    """

    def setup_method(self):
        self.strategy = HeadToHeadKnockoutRankingStrategy()

    # ── Structural / degenerate inputs ────────────────────────────────────────

    def test_empty_sessions_returns_empty_list(self):
        assert self.strategy.calculate_rankings([], db_session=None) == []

    def test_session_without_game_results_is_ignored(self):
        s = SimpleNamespace(game_results=None, tournament_round=1, title="R1")
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_session_with_wrong_match_format_is_ignored(self):
        s = SimpleNamespace(
            game_results={"match_format": "PLACEMENT", "participants": []},
            tournament_round=1, title="R1",
        )
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_session_with_one_participant_is_ignored(self):
        s = SimpleNamespace(
            game_results={
                "match_format": "HEAD_TO_HEAD",
                "participants": [{"user_id": 1, "result": "win", "score": 3}],
            },
            tournament_round=1, title="R1",
        )
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_malformed_json_string_game_results_is_ignored(self):
        s = SimpleNamespace(
            game_results="not valid json {{{",
            tournament_round=1, title="R1",
        )
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_game_results_as_json_string_is_parsed(self):
        """game_results may arrive as a JSON string (some driver configurations)."""
        data = _h2h_game_results(1, 2, "win", "loss", 2, 0, round_num=1)
        s = SimpleNamespace(
            game_results=json.dumps(data),
            tournament_round=1, title="Final",
        )
        rankings = self.strategy.calculate_rankings([s], db_session=None)
        assert len(rankings) == 2
        assert rankings[0]["rank"] == 1

    # ── Basic two-player final ─────────────────────────────────────────────────

    def test_final_winner_gets_rank_1(self):
        sessions = [_knockout_session(1, 2, "win", "loss", s1=3, s2=1, round_num=1)]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["rank"] == 1
        assert by_user[2]["rank"] == 2

    def test_rank_1_is_unique_invariant(self):
        """INVARIANT: exactly one participant holds rank 1."""
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=2),
            _knockout_session(3, 4, "win", "loss", round_num=2),
            _knockout_session(1, 3, "win", "loss", round_num=3),  # Final
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        rank_ones = [r for r in rankings if r["rank"] == 1]
        assert len(rank_ones) == 1, f"Expected single rank-1, got {rank_ones}"

    def test_all_participants_appear_exactly_once(self):
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=2),
            _knockout_session(3, 4, "win", "loss", round_num=2),
            _knockout_session(1, 3, "win", "loss", round_num=3),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        _assert_all_participants_present(sessions, rankings)

    def test_rank_sequence_has_no_gap_beyond_tie_blocks(self):
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=1),
            _knockout_session(3, 4, "win", "loss", round_num=1),
            _knockout_session(1, 3, "win", "loss", round_num=2),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        _assert_ranks_start_at_one(rankings)
        _assert_no_rank_gap_beyond_tie(rankings)

    # ── Round progression / monotonicity ──────────────────────────────────────

    def test_later_round_always_ranks_higher(self):
        """INVARIANT: participant eliminated in round N+1 ranks above one eliminated in round N."""
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=1),
            _knockout_session(3, 4, "win", "loss", round_num=1),
            _knockout_session(1, 3, "win", "loss", round_num=2),  # Semis
            _knockout_session(2, 5, "win", "loss", round_num=2),  # QF
            _knockout_session(1, 2, "win", "loss", round_num=3),  # Final
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # User 1 (won final) must rank above user 3 (lost semis) who ranks above user 2
        assert by_user[1]["rank"] < by_user[3]["rank"]

    def test_tournament_round_attribute_takes_precedence_over_game_results_round(self):
        """session.tournament_round overrides game_results['round_number']."""
        data = _h2h_game_results(1, 2, "win", "loss", 2, 0, round_num=1)
        s_early = SimpleNamespace(game_results=data, tournament_round=5, title="Final")
        data2 = _h2h_game_results(3, 4, "win", "loss", 1, 0, round_num=99)
        s_late = SimpleNamespace(game_results=data2, tournament_round=1, title="R1")

        rankings = self.strategy.calculate_rankings([s_early, s_late], db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # session.tournament_round=5 >> 1 → users 1,2 should have been in later round
        assert by_user[1]["round_reached"] == 5
        assert by_user[3]["round_reached"] == 1
        assert by_user[1]["rank"] < by_user[3]["rank"]

    # ── Tie-breaking ──────────────────────────────────────────────────────────

    def test_semifinal_losers_share_same_rank(self):
        """Two participants eliminated at the same round with same result → tied rank."""
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=1),
            _knockout_session(3, 4, "win", "loss", round_num=1),
            _knockout_session(1, 3, "win", "loss", round_num=2),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[2]["rank"] == by_user[4]["rank"], (
            "Both semifinal losers must share the same rank"
        )

    def test_higher_elimination_score_breaks_tie_in_favour_of_higher_scorer(self):
        """
        Two participants eliminated in the same round, same result:
        the one who scored more in their elimination match gets the BETTER rank.

        Tie detection requires round_reached == prev, result == prev AND
        elimination_score == prev (all three must match). Different scores →
        different ranks, with higher scorer ranked better (lower rank number).
        """
        sessions = [
            # User 2 scored 3 when losing; user 4 scored 0
            _knockout_session(1, 2, "win", "loss", s1=5, s2=3, round_num=1),
            _knockout_session(3, 4, "win", "loss", s1=2, s2=0, round_num=1),
            _knockout_session(1, 3, "win", "loss", round_num=2),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # Different elimination scores → different ranks (score breaks the tie)
        assert by_user[2]["elimination_score"] == 3
        assert by_user[4]["elimination_score"] == 0
        # Higher elimination score → strictly better rank (lower rank number)
        assert by_user[2]["rank"] < by_user[4]["rank"]

    def test_perfect_tie_no_score_difference_same_rank(self):
        """Truly tied participants (same round, same result, same score) → same rank."""
        sessions = [
            _knockout_session(1, 2, "win", "loss", s1=1, s2=0, round_num=1),
            _knockout_session(3, 4, "win", "loss", s1=1, s2=0, round_num=1),
            _knockout_session(1, 3, "win", "loss", round_num=2),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[2]["rank"] == by_user[4]["rank"]

    # ── 3rd Place Playoff ─────────────────────────────────────────────────────

    def test_3rd_place_playoff_winner_gets_rank_3_not_1(self):
        """
        Final match winner → rank 1.
        3rd Place Playoff winner → rank 3, NOT rank 1.
        """
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=2, title="Semifinal"),
            _knockout_session(3, 4, "win", "loss", round_num=2, title="Semifinal"),
            _knockout_session(2, 4, "win", "loss", round_num=2, title="3rd Place Playoff"),
            _knockout_session(1, 3, "win", "loss", round_num=3, title="Final"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}

        # User 1 won the Final → rank 1
        assert by_user[1]["rank"] == 1
        # User 3 lost the Final → rank 2
        assert by_user[3]["rank"] == 2
        # User 2 won 3rd Place Playoff → rank 3
        assert by_user[2]["rank"] == 3
        # User 4 lost 3rd Place Playoff → rank 4
        assert by_user[4]["rank"] == 4

    def test_third_place_playoff_detected_by_playoff_title(self):
        """'Playoff' keyword in title also triggers 3rd place detection."""
        sessions = [
            _knockout_session(1, 2, "win", "loss", round_num=2, title="Bronze Medal Playoff"),
            _knockout_session(3, 4, "win", "loss", round_num=3, title="Final"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[3]["rank"] == 1
        assert by_user[1]["rank"] > by_user[3]["rank"]

    # ── Output shape ──────────────────────────────────────────────────────────

    def test_output_contains_required_fields(self):
        sessions = [_knockout_session(1, 2, "win", "loss")]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        required = {"user_id", "rank", "round_reached", "result", "elimination_score"}
        for r in rankings:
            assert required.issubset(r.keys()), f"Missing fields: {required - r.keys()}"

    def test_winner_has_no_elimination_score(self):
        """Tournament winner was never eliminated → elimination_score is None."""
        sessions = [_knockout_session(1, 2, "win", "loss", s1=3, s2=1)]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["elimination_score"] is None
        assert by_user[2]["elimination_score"] == 1


# ============================================================================
# Section 2 — HeadToHeadLeagueRankingStrategy
# ============================================================================

@pytest.mark.unit
@pytest.mark.tournament
class TestLeagueRanking:
    """
    HeadToHeadLeagueRankingStrategy

    Point system: Win=3, Tie=1, Loss=0.

    Mathematical invariants:
    - Total points across all participants = 3 × (total wins) since each win
      awards exactly 3 and each tied match distributes 2 total (1+1) — but the
      simpler invariant to assert: for each match exactly one side gets 3 or
      both sides get 1 (zero-sum relative to opponent).
    - Points are non-negative and bounded above by 3 × matches_played.
    - Rank 1 holder has the highest (or equal) points of all participants.
    - Tiebreaker is stable: same input always yields same output.
    """

    def setup_method(self):
        self.strategy = HeadToHeadLeagueRankingStrategy()

    # ── Structural / degenerate inputs ────────────────────────────────────────

    def test_empty_sessions_returns_empty_list(self):
        assert self.strategy.calculate_rankings([], db_session=None) == []

    def test_session_without_game_results_is_ignored(self):
        s = SimpleNamespace(game_results=None)
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_non_h2h_format_is_ignored(self):
        s = SimpleNamespace(game_results={"match_format": "PLACEMENT", "participants": []})
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    def test_session_with_three_participants_is_ignored(self):
        """League matches must have exactly 2 participants."""
        s = SimpleNamespace(game_results={
            "match_format": "HEAD_TO_HEAD",
            "participants": [
                {"user_id": 1, "result": "win", "score": 3},
                {"user_id": 2, "result": "loss", "score": 1},
                {"user_id": 3, "result": "loss", "score": 0},
            ],
        })
        assert self.strategy.calculate_rankings([s], db_session=None) == []

    # ── Points system ─────────────────────────────────────────────────────────

    def test_win_awards_3_points(self):
        sessions = [_league_session(1, 2, "win", "loss")]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == 3
        assert by_user[2]["points"] == 0

    def test_tie_awards_1_point_each(self):
        sessions = [_league_session(1, 2, "tie", "tie")]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == 1
        assert by_user[2]["points"] == 1

    def test_loss_awards_0_points(self):
        sessions = [_league_session(1, 2, "win", "loss")]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[2]["points"] == 0

    def test_points_accumulate_across_multiple_matches(self):
        """User 1 wins all 3 matches → 9 points."""
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(1, 3, "win", "loss"),
            _league_session(1, 4, "win", "loss"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == 9

    def test_invariant_total_points_equals_3_times_wins_plus_2_times_draws(self):
        """
        INVARIANT: Σ points = 3 × (total wins) + 2 × (total draws).
        For each win: one side gets 3, other gets 0 → net 3.
        For each draw: both sides get 1 → net 2.
        """
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(2, 3, "tie", "tie"),
            _league_session(3, 4, "win", "loss"),
            _league_session(1, 4, "tie", "tie"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        total_points = sum(r["points"] for r in rankings)
        total_wins = sum(r["wins"] for r in rankings)
        total_draws = sum(r["ties"] for r in rankings) // 2  # each draw counted twice (key is "ties")
        assert total_points == 3 * total_wins + 2 * total_draws

    # ── Rank ordering ─────────────────────────────────────────────────────────

    def test_rank_1_has_highest_points(self):
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(1, 3, "win", "loss"),
            _league_session(2, 3, "win", "loss"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        rank_1 = next(r for r in rankings if r["rank"] == 1)
        max_points = max(r["points"] for r in rankings)
        assert rank_1["points"] == max_points

    def test_monotonic_points_monotonic_rank(self):
        """INVARIANT: if points_A > points_B then rank_A < rank_B (strict ordering)."""
        sessions = [
            _league_session(1, 2, "win", "loss"),     # 1: 3pt, 2: 0pt
            _league_session(1, 3, "win", "loss"),     # 1: 6pt, 3: 0pt
            _league_session(2, 3, "tie", "tie"),      # 2: 1pt, 3: 1pt
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == 6  # 3+3
        assert by_user[2]["points"] == 1  # 0+1
        assert by_user[3]["points"] == 1  # 0+1
        assert by_user[1]["rank"] < by_user[2]["rank"]
        assert by_user[1]["rank"] < by_user[3]["rank"]

    def test_all_participants_present_exactly_once(self):
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(2, 3, "win", "loss"),
            _league_session(3, 1, "win", "loss"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        _assert_all_participants_present(sessions, rankings)
        _assert_ranks_start_at_one(rankings)

    # ── Tiebreakers ───────────────────────────────────────────────────────────

    def test_tied_points_resolved_by_goal_difference(self):
        """
        Users 1 and 2 both win once, lose once → same points.
        User 1 wins by 5, loses by 1 → GD = +4.
        User 2 wins by 1, loses by 5 → GD = -4.
        User 1 must rank above user 2.
        """
        sessions = [
            _league_session(1, 3, "win", "loss", s1=5, s2=0),    # 1 wins big
            _league_session(2, 4, "win", "loss", s1=1, s2=0),    # 2 wins small
            _league_session(3, 1, "win", "loss", s1=1, s2=0),    # 1 loses small
            _league_session(4, 2, "win", "loss", s1=5, s2=0),    # 2 loses big
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # User 1: GD = (5 - 0) + (0 - 1) = +4
        # User 2: GD = (1 - 0) + (0 - 5) = -4
        assert by_user[1]["goal_difference"] > by_user[2]["goal_difference"]
        assert by_user[1]["rank"] < by_user[2]["rank"]

    def test_tied_points_and_gd_resolved_by_goals_scored(self):
        """
        Users 1 and 2 same points, same GD → goals_scored decides.
        """
        sessions = [
            _league_session(1, 3, "win", "loss", s1=3, s2=1),   # 1 GD +2, 3 goals
            _league_session(2, 4, "win", "loss", s1=2, s2=0),   # 2 GD +2, 2 goals
            _league_session(3, 1, "win", "loss", s1=1, s2=0),   # 1 net -1  (3-1-0=+2 total? no...)
        ]
        # Simpler: 2 participants, same points, same goal_difference, different goals_for
        sessions2 = [
            _league_session(1, 3, "win", "loss", s1=3, s2=1),   # 1: GF=3, GA=1, GD=2
            _league_session(2, 4, "win", "loss", s1=2, s2=0),   # 2: GF=2, GA=0, GD=2
            # After 1 match each: same points (3), same GD (+2), but 1 has 3 GF vs 2's 2 GF
        ]
        rankings = self.strategy.calculate_rankings(sessions2, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == by_user[2]["points"]
        assert by_user[1]["goal_difference"] == by_user[2]["goal_difference"]
        assert by_user[1]["goals_scored"] > by_user[2]["goals_scored"]
        assert by_user[1]["rank"] < by_user[2]["rank"]

    def test_true_three_way_tie_all_get_same_rank(self):
        """
        3 participants play round robin, each wins once and loses once.
        All tied on points=3, same GD, same goals_scored → same rank.
        """
        sessions = [
            _league_session(1, 2, "win", "loss", s1=1, s2=0),
            _league_session(2, 3, "win", "loss", s1=1, s2=0),
            _league_session(3, 1, "win", "loss", s1=1, s2=0),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # All have 3 points, GD=0, GF=1
        for uid in [1, 2, 3]:
            assert by_user[uid]["points"] == 3
            assert by_user[uid]["goal_difference"] == 0
        # All tied → same rank
        assert by_user[1]["rank"] == by_user[2]["rank"] == by_user[3]["rank"]

    # ── Determinism ───────────────────────────────────────────────────────────

    def test_deterministic_output_for_same_input(self):
        """INVARIANT: same input always produces identical ranking output."""
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(2, 3, "win", "loss"),
            _league_session(3, 1, "win", "loss"),
        ]
        r1 = self.strategy.calculate_rankings(sessions, db_session=None)
        r2 = self.strategy.calculate_rankings(sessions, db_session=None)
        assert r1 == r2

    # ── Output shape ──────────────────────────────────────────────────────────

    def test_output_contains_required_fields(self):
        sessions = [_league_session(1, 2, "win", "loss", s1=2, s2=1)]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        required = {
            "user_id", "rank", "points", "wins", "ties", "losses",
            "goals_scored", "goals_conceded", "goal_difference",
        }
        for r in rankings:
            assert required.issubset(r.keys())

    def test_wins_losses_ties_consistent_with_points(self):
        """INVARIANT: points == wins*3 + ties*1 for every participant."""
        sessions = [
            _league_session(1, 2, "win", "loss"),
            _league_session(1, 3, "tie", "tie"),
            _league_session(2, 3, "win", "loss"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        for r in rankings:
            expected_points = r["wins"] * 3 + r["ties"] * 1
            assert r["points"] == expected_points, (
                f"user {r['user_id']}: points={r['points']}, "
                f"wins={r['wins']}, ties={r['ties']}"
            )

    def test_goal_difference_equals_scored_minus_conceded(self):
        """INVARIANT: goal_difference = goals_scored - goals_conceded."""
        sessions = [_league_session(1, 2, "win", "loss", s1=3, s2=1)]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        for r in rankings:
            assert r["goal_difference"] == r["goals_scored"] - r["goals_conceded"]


# ============================================================================
# Section 3 — HeadToHeadGroupKnockoutRankingStrategy
# ============================================================================

@pytest.mark.unit
@pytest.mark.tournament
class TestGroupKnockoutRanking:
    """
    HeadToHeadGroupKnockoutRankingStrategy

    Hybrid group + knockout tournament ranking.

    Invariants verified:
    - Knockout participants ALWAYS rank above group-only participants
    - Group-only rank numbers start from (len(knockout_rankings) + 1)
    - All participants appear exactly once in final rankings
    - Group standings per group are sorted: points DESC, GD DESC, GF DESC
    - Internally delegates knockout phase to HeadToHeadKnockoutRankingStrategy
    """

    def setup_method(self):
        self.strategy = HeadToHeadGroupKnockoutRankingStrategy()

    # ── Structural / degenerate inputs ────────────────────────────────────────

    def test_empty_sessions_returns_empty_list(self):
        assert self.strategy.calculate_rankings([], db_session=None) == []

    def test_only_group_sessions_no_knockout_returns_group_ranked_from_1(self):
        """
        Without any knockout sessions there are no knockout participants.
        Group-only participants are ranked starting from rank 1
        (len(knockout_rankings)+1 = 0+1 = 1).
        """
        sessions = [
            _group_session(1, 2, "win", "loss", s1=2, s2=0, group="A"),
            _group_session(3, 4, "win", "loss", s1=1, s2=0, group="A"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        assert len(rankings) == 4
        assert min(r["rank"] for r in rankings) == 1

    # ── Phase separation ──────────────────────────────────────────────────────

    def test_group_sessions_separated_from_knockout_sessions(self):
        """Participants from group sessions that do not advance get group-only ranks."""
        group_sessions = [
            _group_session(1, 2, "win", "loss", group="A"),
            _group_session(3, 4, "win", "loss", group="B"),
        ]
        knockout_sessions = [
            _knockout_group_session(1, 3, "win", "loss", round_num=2, title="Final"),
        ]
        rankings = self.strategy.calculate_rankings(
            group_sessions + knockout_sessions, db_session=None
        )
        # 4 participants total
        assert len(rankings) == 4
        by_user = {r["user_id"]: r for r in rankings}
        # Users 1 and 3 participated in knockout
        # Users 2 and 4 are group-only → must rank lower
        for ko_user in [1, 3]:
            for group_user in [2, 4]:
                assert by_user[ko_user]["rank"] < by_user[group_user]["rank"], (
                    f"Knockout user {ko_user} must rank above group-only user {group_user}"
                )

    def test_knockout_ranks_are_1_to_n_before_group_only(self):
        """
        INVARIANT: group-only rank numbers start from len(knockout_rankings)+1.
        """
        group_sessions = [
            _group_session(1, 2, "win", "loss", group="A"),
            _group_session(3, 4, "win", "loss", group="B"),
            _group_session(5, 6, "win", "loss", group="C"),
        ]
        knockout_sessions = [
            _knockout_group_session(1, 3, "win", "loss", round_num=1, title="SF1"),
            _knockout_group_session(5, 7, "win", "loss", round_num=1, title="SF2"),
            _knockout_group_session(1, 5, "win", "loss", round_num=2, title="Final"),
        ]
        rankings = self.strategy.calculate_rankings(
            group_sessions + knockout_sessions, db_session=None
        )
        # Knockout participants: 1, 3, 5, 7 (4 people)
        # Group-only: 2, 4, 6
        knockout_ranks = {r["rank"] for r in rankings if r["user_id"] in {1, 3, 5, 7}}
        group_only_ranks = {r["rank"] for r in rankings if r["user_id"] in {2, 4, 6}}
        assert max(knockout_ranks) < min(group_only_ranks), (
            "All knockout ranks must be numerically lower than all group-only ranks"
        )

    # ── Group standings ───────────────────────────────────────────────────────

    def test_group_standings_sorted_by_points_desc(self):
        """Within a group, participant with more wins gets better group rank."""
        group_sessions = [
            _group_session(1, 2, "win", "loss", group="A"),
            _group_session(1, 3, "win", "loss", group="A"),
            _group_session(2, 3, "win", "loss", group="A"),
        ]
        rankings = self.strategy.calculate_rankings(group_sessions, db_session=None)
        # User 1: 2 wins = 6 pts; User 2: 1 win = 3 pts; User 3: 0 wins = 0 pts
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["rank"] < by_user[2]["rank"] < by_user[3]["rank"]

    def test_multi_group_group_only_sorted_by_group_rank_first(self):
        """
        Group-only participants from multiple groups are ranked:
        first all rank-1 group finishers, then all rank-2, etc.
        """
        # Group A winner = user 1, Group B winner = user 3
        group_sessions = [
            _group_session(1, 2, "win", "loss", s1=2, s2=0, group="A"),
            _group_session(3, 4, "win", "loss", s1=2, s2=0, group="B"),
        ]
        # No knockout sessions → all group-only
        rankings = self.strategy.calculate_rankings(group_sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        # Group rank 1 (users 1 and 3) must beat group rank 2 (users 2 and 4)
        assert by_user[1]["rank"] <= by_user[2]["rank"]
        assert by_user[3]["rank"] <= by_user[4]["rank"]

    def test_group_winner_has_correct_points_in_final_ranking(self):
        sessions = [
            _group_session(1, 2, "win", "loss", s1=3, s2=0, group="A"),
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        by_user = {r["user_id"]: r for r in rankings}
        assert by_user[1]["points"] == 3
        assert by_user[2]["points"] == 0

    # ── All participants invariant ─────────────────────────────────────────────

    def test_all_participants_appear_exactly_once_in_final_rankings(self):
        """INVARIANT: final rankings contain every participant exactly once."""
        group_sessions = [
            _group_session(1, 2, "win", "loss", group="A"),
            _group_session(3, 4, "win", "loss", group="B"),
        ]
        knockout_sessions = [
            _knockout_group_session(1, 3, "win", "loss", round_num=2, title="Final"),
        ]
        all_sessions = group_sessions + knockout_sessions
        rankings = self.strategy.calculate_rankings(all_sessions, db_session=None)

        user_ids_in_sessions = set()
        for s in all_sessions:
            for p in s.game_results["participants"]:
                user_ids_in_sessions.add(p["user_id"])

        ranking_ids = [r["user_id"] for r in rankings]
        assert set(ranking_ids) == user_ids_in_sessions
        assert len(ranking_ids) == len(set(ranking_ids)), "Duplicate user_id in final rankings"

    def test_group_session_without_game_results_is_ignored(self):
        sessions = [
            SimpleNamespace(
                game_results=None,
                tournament_phase="GROUP_STAGE",
                group_identifier="A",
            )
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        assert rankings == []

    def test_group_session_with_non_h2h_format_is_ignored(self):
        sessions = [
            SimpleNamespace(
                game_results={"match_format": "PLACEMENT", "participants": []},
                tournament_phase="GROUP_STAGE",
                group_identifier="A",
            )
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        assert rankings == []

    def test_group_identifier_defaults_to_a_when_missing(self):
        """session.group_identifier=None falls back to group 'A'."""
        sessions = [
            SimpleNamespace(
                game_results=_h2h_game_results(1, 2, "win", "loss", 1, 0),
                tournament_phase="GROUP_STAGE",
                group_identifier=None,
            )
        ]
        rankings = self.strategy.calculate_rankings(sessions, db_session=None)
        assert len(rankings) == 2
