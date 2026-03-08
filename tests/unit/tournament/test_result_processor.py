"""
Unit tests for ResultProcessor — Round 1: Pure Methods Only

No DB. No mocks. No integration.
All tests call pure methods that perform in-memory computation only.

Invariants documented:
  - Round-robin: win=3pts, draw=1pt each, loss=0pts
  - Rankings are monotonically non-decreasing (lowest rank number = best)
  - HEAD_TO_HEAD tie → both rank 1 (business rule)
  - TIME_BASED tie → sequential ranks, NOT shared (behavioral documentation)
  - Dispatch: invalid match_format string → ValueError before any processing

Behavioral documentation test:
  test_tie_in_time_produces_sequential_ranks_not_shared explicitly documents
  the current TIME_BASED tie behavior. Do not "fix" this test.
"""
import pytest
from unittest.mock import MagicMock

from app.services.tournament.result_processor import (
    ResultProcessor,
    NotImplementedSkillRatingProcessor,
)


def _processor() -> ResultProcessor:
    """Return a fresh ResultProcessor. DB is never touched by pure methods."""
    return ResultProcessor(db=MagicMock())


# ============================================================================
# TestNotImplementedSkillRatingProcessor
# ============================================================================

class TestNotImplementedSkillRatingProcessor:
    """Stub raises NotImplementedError with a descriptive message."""

    def test_derive_rankings_raises_not_implemented(self):
        stub = NotImplementedSkillRatingProcessor()
        with pytest.raises(NotImplementedError, match="SKILL_RATING processor not yet implemented"):
            stub.derive_rankings([{"user_id": 1, "rating": 9.0}])

    def test_derive_rankings_raises_even_with_empty_results(self):
        stub = NotImplementedSkillRatingProcessor()
        with pytest.raises(NotImplementedError):
            stub.derive_rankings([])


# ============================================================================
# TestProcessIndividualRanking
# ============================================================================

class TestProcessIndividualRanking:
    """
    _process_individual_ranking: placement-based input + round-robin delegation.

    Placement-based format: [{"user_id": N, "placement": N}, ...]
    Round-robin detection: if results[0] has "player_a_id" → delegates to
      _process_round_robin_scores (tested separately).
    """

    def _call(self, results):
        return _processor()._process_individual_ranking(results)

    # --- placement-based ---

    def test_single_participant_returns_rank_1(self):
        result = self._call([{"user_id": 1, "placement": 1}])
        assert result == [(1, 1)]

    def test_sorted_by_placement_ascending_regardless_of_input_order(self):
        result = self._call([
            {"user_id": 3, "placement": 3},
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2},
        ])
        assert result == [(1, 1), (2, 2), (3, 3)]

    def test_placement_preserves_user_ids_correctly(self):
        result = self._call([
            {"user_id": 42, "placement": 1},
            {"user_id": 99, "placement": 2},
        ])
        assert result[0] == (42, 1)
        assert result[1] == (99, 2)

    def test_missing_user_id_raises_value_error(self):
        with pytest.raises(ValueError):
            self._call([{"placement": 1}])

    def test_missing_placement_raises_value_error(self):
        with pytest.raises(ValueError):
            self._call([{"user_id": 1}])

    def test_round_robin_format_detected_by_player_a_id_key(self):
        """Results containing 'player_a_id' are delegated to _process_round_robin_scores."""
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0},
            {"player_a_id": 1, "player_b_id": 3, "score_a": 2, "score_b": 1},
            {"player_a_id": 2, "player_b_id": 3, "score_a": 1, "score_b": 0},
        ])
        # player 1: 3+3=6pts (both wins), player 2: 3pts (1 win), player 3: 0pts
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] < by_user[2] < by_user[3]

    def test_invariant_ranking_is_monotonically_non_decreasing(self):
        result = self._call([
            {"user_id": 1, "placement": 2},
            {"user_id": 2, "placement": 1},
            {"user_id": 3, "placement": 3},
        ])
        ranks = [rank for _, rank in result]
        assert ranks == sorted(ranks)


# ============================================================================
# TestProcessRoundRobinScores
# ============================================================================

class TestProcessRoundRobinScores:
    """
    _process_round_robin_scores: win=3pts, draw=1pt each, loss=0pts.

    Rank assignment: lower points → higher rank number (worse placement).
    Tied points → same rank (shared rank, not sequential).
    """

    def _call(self, match_results):
        return _processor()._process_round_robin_scores(match_results)

    def test_winner_ranked_above_loser(self):
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] < by_user[2]

    def test_draw_gives_both_players_same_rank(self):
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 1, "score_b": 1},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == by_user[2]

    def test_three_player_cycle_all_same_points_all_same_rank(self):
        """Cycle: 1 beats 2, 2 beats 3, 3 beats 1 → each 3pts → all rank 1."""
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 1, "score_b": 0},
            {"player_a_id": 2, "player_b_id": 3, "score_a": 1, "score_b": 0},
            {"player_a_id": 3, "player_b_id": 1, "score_a": 1, "score_b": 0},
        ])
        ranks = [rank for _, rank in result]
        assert len(set(ranks)) == 1  # all tied → identical rank

    def test_points_produce_correct_ordering_three_players(self):
        """
        Known scenario: 3 matches, clear hierarchy.
        player1: 3+1=4pts (beats player2, draws player3)
        player2: 3pts    (beats player3, loses to player1)
        player3: 1pt     (draws player1, loses to player2)
        """
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 2, "score_b": 0},  # p1 wins (+3)
            {"player_a_id": 2, "player_b_id": 3, "score_a": 1, "score_b": 0},  # p2 wins (+3)
            {"player_a_id": 1, "player_b_id": 3, "score_a": 1, "score_b": 1},  # draw (+1 each)
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] < by_user[2] < by_user[3]

    def test_missing_player_a_id_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid round-robin result"):
            self._call([{"player_b_id": 2, "score_a": 1, "score_b": 0}])

    def test_missing_player_b_id_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid round-robin result"):
            self._call([{"player_a_id": 1, "score_a": 1, "score_b": 0}])

    def test_missing_scores_default_to_zero_treated_as_draw(self):
        """score_a and score_b default to 0 when absent → 0==0 → draw → same rank."""
        result = self._call([{"player_a_id": 1, "player_b_id": 2}])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == by_user[2]

    def test_all_players_appear_in_result(self):
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 1, "score_b": 0},
            {"player_a_id": 3, "player_b_id": 4, "score_a": 2, "score_b": 2},
        ])
        assert {uid for uid, _ in result} == {1, 2, 3, 4}

    def test_invariant_ranking_monotonically_non_decreasing(self):
        result = self._call([
            {"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0},
            {"player_a_id": 1, "player_b_id": 3, "score_a": 2, "score_b": 1},
            {"player_a_id": 2, "player_b_id": 3, "score_a": 1, "score_b": 0},
        ])
        ranks = [rank for _, rank in result]
        assert ranks == sorted(ranks)


# ============================================================================
# TestProcessHeadToHead
# ============================================================================

class TestProcessHeadToHead:
    """
    _process_head_to_head: exactly 2 results, WIN_LOSS or SCORE_BASED.

    Tie (SCORE_BASED, equal scores) → both rank 1 (business rule).
    """

    def _call(self, results):
        return _processor()._process_head_to_head(results)

    # --- count precondition ---

    def test_one_result_raises_value_error(self):
        with pytest.raises(ValueError, match="exactly 2 results"):
            self._call([{"user_id": 1, "result": "WIN"}])

    def test_three_results_raises_value_error(self):
        with pytest.raises(ValueError, match="exactly 2 results"):
            self._call([
                {"user_id": 1, "result": "WIN"},
                {"user_id": 2, "result": "LOSS"},
                {"user_id": 3, "result": "LOSS"},
            ])

    # --- WIN_LOSS ---

    def test_win_loss_winner_gets_rank_1_loser_rank_2(self):
        result = self._call([
            {"user_id": 1, "result": "WIN"},
            {"user_id": 2, "result": "LOSS"},
        ])
        assert result == [(1, 1), (2, 2)]

    def test_win_loss_order_independent_loser_first(self):
        """LOSS entry first in list → result unchanged."""
        result = self._call([
            {"user_id": 2, "result": "LOSS"},
            {"user_id": 1, "result": "WIN"},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 2

    def test_win_loss_two_losers_raises_value_error(self):
        with pytest.raises(ValueError, match="one WIN and one LOSS"):
            self._call([
                {"user_id": 1, "result": "LOSS"},
                {"user_id": 2, "result": "LOSS"},
            ])

    def test_win_loss_two_winners_raises_value_error(self):
        with pytest.raises(ValueError, match="one WIN and one LOSS"):
            self._call([
                {"user_id": 1, "result": "WIN"},
                {"user_id": 2, "result": "WIN"},
            ])

    # --- SCORE_BASED ---

    def test_score_based_higher_score_gets_rank_1(self):
        result = self._call([
            {"user_id": 1, "score": 3},
            {"user_id": 2, "score": 1},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 2

    def test_score_based_second_entry_wins(self):
        result = self._call([
            {"user_id": 1, "score": 0},
            {"user_id": 2, "score": 5},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[2] == 1
        assert by_user[1] == 2

    def test_score_based_tie_both_get_rank_1(self):
        """Business rule: equal scores → both players rank 1."""
        result = self._call([
            {"user_id": 1, "score": 2},
            {"user_id": 2, "score": 2},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 1

    def test_score_based_zero_zero_tie_both_rank_1(self):
        result = self._call([
            {"user_id": 1, "score": 0},
            {"user_id": 2, "score": 0},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1 and by_user[2] == 1

    # --- missing fields ---

    def test_missing_result_and_score_raises_value_error(self):
        with pytest.raises(ValueError):
            self._call([{"user_id": 1}, {"user_id": 2}])


# ============================================================================
# TestProcessTeamMatch
# ============================================================================

class TestProcessTeamMatch:
    """
    _process_team_match: team-level scores determine member ranks.

    Winning team members → rank 1. Losing team members → rank 2.
    Tie → all members rank 1.
    user_id=None or team=None entries are silently skipped (not an error).
    """

    def _call(self, results, structure_config=None):
        return _processor()._process_team_match(results, structure_config)

    def test_empty_results_returns_empty_list(self):
        assert self._call([]) == []

    def test_winning_team_members_get_rank_1(self):
        result = self._call([
            {"user_id": 1, "team": "A", "team_score": 5},
            {"user_id": 2, "team": "A", "team_score": 5},
            {"user_id": 3, "team": "B", "team_score": 2},
            {"user_id": 4, "team": "B", "team_score": 2},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 1
        assert by_user[3] == 2
        assert by_user[4] == 2

    def test_losing_team_members_get_rank_2(self):
        result = self._call([
            {"user_id": 10, "team": "A", "team_score": 1},
            {"user_id": 20, "team": "B", "team_score": 3},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[20] == 1  # B wins
        assert by_user[10] == 2  # A loses

    def test_tie_all_participants_get_rank_1(self):
        result = self._call([
            {"user_id": 1, "team": "A", "team_score": 3},
            {"user_id": 2, "team": "B", "team_score": 3},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 1

    def test_no_team_scores_raises_value_error(self):
        with pytest.raises(ValueError, match="missing team scores"):
            self._call([
                {"user_id": 1, "team": "A"},
                {"user_id": 2, "team": "B"},
            ])

    def test_result_missing_user_id_is_silently_skipped(self):
        result = self._call([
            {"team": "A", "team_score": 5},       # no user_id → skipped
            {"user_id": 2, "team": "B", "team_score": 2},
        ])
        user_ids = [uid for uid, _ in result]
        assert 2 in user_ids
        assert len(user_ids) == 1  # only user 2 appears

    def test_result_missing_team_is_silently_skipped(self):
        result = self._call([
            {"user_id": 1, "team_score": 5},       # no team → skipped
            {"user_id": 2, "team": "B", "team_score": 2},
        ])
        user_ids = [uid for uid, _ in result]
        assert 1 not in user_ids

    def test_invariant_all_valid_users_appear_in_output(self):
        result = self._call([
            {"user_id": 1, "team": "A", "team_score": 5},
            {"user_id": 2, "team": "A", "team_score": 5},
            {"user_id": 3, "team": "B", "team_score": 1},
        ])
        assert {uid for uid, _ in result} == {1, 2, 3}


# ============================================================================
# TestProcessTimeBased
# ============================================================================

class TestProcessTimeBased:
    """
    _process_time_based: fastest time = rank 1, slowest = last.

    ⚠️  BEHAVIORAL DOCUMENTATION — TIME TIE BEHAVIOR:
    Two players with identical time receive SEQUENTIAL ranks (1 and 2),
    NOT shared rank (not both rank 1). This is current implementation behavior.
    The test below documents this explicitly. Do not "fix" it to expect [1, 1].
    A future change to shared-rank tie-breaking would require updating this test.
    """

    def _call(self, results):
        return _processor()._process_time_based(results)

    def test_single_participant_gets_rank_1(self):
        result = self._call([{"user_id": 1, "time_seconds": 10.5}])
        assert result == [(1, 1)]

    def test_fastest_time_gets_rank_1(self):
        result = self._call([
            {"user_id": 1, "time_seconds": 11.0},
            {"user_id": 2, "time_seconds": 10.5},  # faster
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[2] == 1
        assert by_user[1] == 2

    def test_three_participants_ranked_ascending_by_time(self):
        result = self._call([
            {"user_id": 3, "time_seconds": 13.0},
            {"user_id": 1, "time_seconds": 11.0},
            {"user_id": 2, "time_seconds": 12.0},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 2
        assert by_user[3] == 3

    def test_tie_in_time_produces_sequential_ranks_not_shared(self):
        """
        BEHAVIORAL DOCUMENTATION: equal times → ranks [1, 2] (sequential),
        NOT [1, 1] (shared). Current implementation uses enumerate() which
        assigns strictly increasing ranks regardless of tied values.

        If future business requirements change this to shared-rank tie-breaking,
        update this test to assert ranks == [1, 1].
        """
        result = self._call([
            {"user_id": 1, "time_seconds": 10.0},
            {"user_id": 2, "time_seconds": 10.0},
        ])
        ranks = sorted(rank for _, rank in result)
        assert ranks == [1, 2], (
            "TIME_BASED: equal times receive sequential ranks (1, 2), not shared rank. "
            "This is current behavior — update this test if tie-breaking logic changes."
        )

    def test_missing_user_id_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid TIME_BASED result"):
            self._call([{"time_seconds": 10.0}])

    def test_missing_time_seconds_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid TIME_BASED result"):
            self._call([{"user_id": 1}])

    def test_invariant_ranks_are_1_indexed_and_sequential(self):
        result = self._call([
            {"user_id": 1, "time_seconds": 12.0},
            {"user_id": 2, "time_seconds": 11.0},
            {"user_id": 3, "time_seconds": 13.0},
        ])
        ranks = sorted(rank for _, rank in result)
        assert ranks == [1, 2, 3]

    def test_invariant_all_users_appear_in_output(self):
        result = self._call([
            {"user_id": 10, "time_seconds": 9.9},
            {"user_id": 20, "time_seconds": 10.1},
        ])
        assert {uid for uid, _ in result} == {10, 20}


# ============================================================================
# TestValidateResults
# ============================================================================

class TestValidateResults:
    """
    validate_results: returns (bool, str) — format-level validation only.
    No DB, no processing — pure structural check on the results list.
    """

    def _call(self, match_format, results, expected_participants=None):
        return _processor().validate_results(match_format, results, expected_participants)

    def _assert_valid(self, match_format, results, expected_participants=None):
        is_valid, msg = self._call(match_format, results, expected_participants)
        assert is_valid, f"Expected valid but got: {msg!r}"

    def _assert_invalid(self, match_format, results, expected_participants=None):
        is_valid, msg = self._call(match_format, results, expected_participants)
        assert not is_valid, "Expected invalid but returned valid"
        return msg

    # --- empty list and unknown format ---

    def test_empty_results_returns_false_with_empty_message(self):
        is_valid, msg = self._call("INDIVIDUAL_RANKING", [])
        assert not is_valid
        assert "empty" in msg.lower()

    def test_invalid_format_string_returns_false(self):
        msg = self._assert_invalid("ROCKET_LEAGUE", [{"user_id": 1}])
        assert "ROCKET_LEAGUE" in msg or "Invalid" in msg

    # --- INDIVIDUAL_RANKING: placement-based ---

    def test_individual_ranking_valid_placement_passes(self):
        self._assert_valid("INDIVIDUAL_RANKING", [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2},
        ])

    def test_individual_ranking_missing_user_id_returns_false(self):
        msg = self._assert_invalid("INDIVIDUAL_RANKING", [{"placement": 1}])
        assert "user_id" in msg or "placement" in msg

    def test_individual_ranking_missing_placement_returns_false(self):
        msg = self._assert_invalid("INDIVIDUAL_RANKING", [{"user_id": 1}])
        assert "placement" in msg

    def test_individual_ranking_duplicate_placements_returns_false(self):
        msg = self._assert_invalid("INDIVIDUAL_RANKING", [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 1},  # duplicate
        ])
        assert "uplicate" in msg  # "Duplicate" case-insensitive

    def test_individual_ranking_placements_not_starting_from_1_returns_false(self):
        msg = self._assert_invalid("INDIVIDUAL_RANKING", [
            {"user_id": 1, "placement": 2},
            {"user_id": 2, "placement": 3},
        ])
        assert "start from 1" in msg or "must start" in msg

    # --- INDIVIDUAL_RANKING: round-robin (score-based) ---

    def test_individual_ranking_round_robin_valid_passes(self):
        self._assert_valid("INDIVIDUAL_RANKING", [
            {"player_a_id": 1, "player_b_id": 2, "score_a": 3, "score_b": 0},
        ])

    def test_individual_ranking_round_robin_missing_score_returns_false(self):
        msg = self._assert_invalid("INDIVIDUAL_RANKING", [
            {"player_a_id": 1, "player_b_id": 2},  # score_a/score_b absent
        ])
        assert "score" in msg.lower()

    # --- HEAD_TO_HEAD ---

    def test_head_to_head_valid_two_results_passes(self):
        self._assert_valid("HEAD_TO_HEAD", [{"user_id": 1}, {"user_id": 2}])

    def test_head_to_head_one_result_returns_false(self):
        msg = self._assert_invalid("HEAD_TO_HEAD", [{"user_id": 1}])
        assert "2" in msg

    def test_head_to_head_three_results_returns_false(self):
        msg = self._assert_invalid("HEAD_TO_HEAD", [
            {"user_id": 1}, {"user_id": 2}, {"user_id": 3},
        ])
        assert "2" in msg

    # --- TIME_BASED ---

    def test_time_based_valid_passes(self):
        self._assert_valid("TIME_BASED", [
            {"user_id": 1, "time_seconds": 10.5},
            {"user_id": 2, "time_seconds": 11.0},
        ])

    def test_time_based_missing_time_seconds_returns_false(self):
        msg = self._assert_invalid("TIME_BASED", [{"user_id": 1}])
        assert "time_seconds" in msg

    def test_time_based_missing_user_id_returns_false(self):
        msg = self._assert_invalid("TIME_BASED", [{"time_seconds": 10.5}])
        assert "user_id" in msg

    # --- TEAM_MATCH ---

    def test_team_match_valid_passes(self):
        self._assert_valid("TEAM_MATCH", [
            {"user_id": 1, "team": "A"},
            {"user_id": 2, "team": "B"},
        ])

    def test_team_match_missing_user_id_returns_false(self):
        msg = self._assert_invalid("TEAM_MATCH", [{"team": "A"}])
        assert "user_id" in msg

    def test_team_match_missing_team_returns_false(self):
        msg = self._assert_invalid("TEAM_MATCH", [{"user_id": 1}])
        assert "team" in msg

    # --- SKILL_RATING ---

    def test_skill_rating_valid_passes(self):
        self._assert_valid("SKILL_RATING", [{"user_id": 1, "rating": 9.5}])

    def test_skill_rating_missing_user_id_returns_false(self):
        msg = self._assert_invalid("SKILL_RATING", [{"rating": 9.5}])
        assert "user_id" in msg

    # --- expected_participants ---

    def test_expected_participants_mismatch_returns_false(self):
        msg = self._assert_invalid(
            "HEAD_TO_HEAD",
            [{"user_id": 1}, {"user_id": 2}],
            expected_participants=3,
        )
        assert "Expected 3" in msg or "participants" in msg

    def test_expected_participants_match_passes(self):
        self._assert_valid(
            "HEAD_TO_HEAD",
            [{"user_id": 1}, {"user_id": 2}],
            expected_participants=2,
        )


# ============================================================================
# TestProcessResultsDispatch
# ============================================================================

class TestProcessResultsDispatch:
    """
    process_results: enum parsing + format dispatch.

    Verifies each format string routes to the correct processor
    and that the default SKILL_RATING stub raises NotImplementedError.
    """

    def _call(self, match_format, results, structure_config=None):
        return _processor().process_results(
            session_id=1,
            match_format=match_format,
            results=results,
            structure_config=structure_config,
        )

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid match_format"):
            self._call("INVALID_FORMAT", [])

    def test_individual_ranking_dispatches_and_returns_tuples(self):
        result = self._call("INDIVIDUAL_RANKING", [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2},
        ])
        assert result == [(1, 1), (2, 2)]

    def test_head_to_head_dispatches_correctly(self):
        result = self._call("HEAD_TO_HEAD", [
            {"user_id": 1, "result": "WIN"},
            {"user_id": 2, "result": "LOSS"},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 2

    def test_time_based_dispatches_correctly(self):
        result = self._call("TIME_BASED", [
            {"user_id": 1, "time_seconds": 10.0},
            {"user_id": 2, "time_seconds": 11.0},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1

    def test_team_match_dispatches_correctly(self):
        result = self._call("TEAM_MATCH", [
            {"user_id": 1, "team": "A", "team_score": 3},
            {"user_id": 2, "team": "B", "team_score": 1},
        ])
        by_user = {uid: rank for uid, rank in result}
        assert by_user[1] == 1
        assert by_user[2] == 2

    def test_skill_rating_raises_not_implemented_with_default_processor(self):
        """Default processor is NotImplementedSkillRatingProcessor — must raise."""
        with pytest.raises(NotImplementedError, match="SKILL_RATING processor not yet implemented"):
            self._call("SKILL_RATING", [{"user_id": 1, "rating": 9.0}])

    def test_skill_rating_works_after_custom_processor_injected(self):
        """set_skill_rating_processor() replaces the stub for the injected instance."""
        proc = _processor()
        custom = MagicMock()
        custom.derive_rankings.return_value = [(1, 1)]
        proc.set_skill_rating_processor(custom)

        result = proc.process_results(
            session_id=1,
            match_format="SKILL_RATING",
            results=[{"user_id": 1, "rating": 9.0}],
        )
        assert result == [(1, 1)]
        custom.derive_rankings.assert_called_once()
