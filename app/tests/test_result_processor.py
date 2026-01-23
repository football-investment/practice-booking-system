"""
Unit Tests for ResultProcessor Service

Tests the conversion of performance data to derived rankings
for different match formats.

Test Coverage:
- INDIVIDUAL_RANKING: Placement-based ranking
- HEAD_TO_HEAD: 1v1 winner/loser or score-based
- TEAM_MATCH: Team scores → individual rankings
- TIME_BASED: Performance times → ranking (fastest first)
- SKILL_RATING: Extension point (should raise NotImplementedError)
- Validation: Format-specific validation rules
"""

import pytest
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple

from app.services.tournament.result_processor import ResultProcessor
from app.models.match_structure import MatchFormat, ScoringType


class TestResultProcessor:
    """Test suite for ResultProcessor service"""

    @pytest.fixture
    def result_processor(self, db_session: Session):
        """Create ResultProcessor instance"""
        return ResultProcessor(db_session)

    # ========================================================================
    # TEST 1: INDIVIDUAL_RANKING - Placement-based ranking
    # ========================================================================

    def test_individual_ranking_basic(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING with 4 participants

        Input: Placement data
        Expected: Rankings match placements
        """
        results = [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2},
            {"user_id": 3, "placement": 3},
            {"user_id": 4, "placement": 4}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        assert rankings == [
            (1, 1),  # user_id=1, rank=1
            (2, 2),
            (3, 3),
            (4, 4)
        ]

    def test_individual_ranking_unordered_input(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING with unordered input

        Input: Results in random order
        Expected: Rankings sorted by placement
        """
        results = [
            {"user_id": 4, "placement": 4},
            {"user_id": 1, "placement": 1},
            {"user_id": 3, "placement": 3},
            {"user_id": 2, "placement": 2}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        # Rankings should be sorted by placement
        assert rankings == [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4)
        ]

    def test_individual_ranking_validation_missing_fields(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING validation - missing required fields

        Expected: Validation fails with clear error message
        """
        results = [
            {"user_id": 1},  # Missing 'placement'
            {"placement": 2}  # Missing 'user_id'
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        assert is_valid is False
        assert "requires 'user_id' and 'placement'" in error_msg

    def test_individual_ranking_validation_duplicate_placements(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING validation - duplicate placements

        Expected: Validation fails
        """
        results = [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 1},  # Duplicate placement
            {"user_id": 3, "placement": 3}
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        assert is_valid is False
        assert "Duplicate placements" in error_msg

    def test_individual_ranking_validation_placements_start_from_1(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING validation - placements must start from 1

        Expected: Validation fails if placements don't start from 1
        """
        results = [
            {"user_id": 1, "placement": 2},  # Starts from 2, not 1
            {"user_id": 2, "placement": 3},
            {"user_id": 3, "placement": 4}
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        assert is_valid is False
        assert "Placements must start from 1" in error_msg

    # ========================================================================
    # TEST 2: HEAD_TO_HEAD - Winner/Loser
    # ========================================================================

    def test_head_to_head_win_loss(self, result_processor):
        """
        TEST: HEAD_TO_HEAD with WIN_LOSS scoring

        Input: Winner and loser
        Expected: Winner rank=1, loser rank=2
        """
        results = [
            {"user_id": 1, "result": "WIN"},
            {"user_id": 2, "result": "LOSS"}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='HEAD_TO_HEAD',
            results=results
        )

        assert rankings == [
            (1, 1),  # Winner
            (2, 2)   # Loser
        ]

    def test_head_to_head_score_based(self, result_processor):
        """
        TEST: HEAD_TO_HEAD with SCORE_BASED scoring

        Input: Match scores
        Expected: Higher score wins
        """
        results = [
            {"user_id": 1, "score": 3},
            {"user_id": 2, "score": 1}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='HEAD_TO_HEAD',
            results=results
        )

        assert rankings == [
            (1, 1),  # user_id=1 scored 3
            (2, 2)   # user_id=2 scored 1
        ]

    def test_head_to_head_score_tie(self, result_processor):
        """
        TEST: HEAD_TO_HEAD with tied scores

        Input: Equal scores
        Expected: Both players rank=1 (tie)
        """
        results = [
            {"user_id": 1, "score": 2},
            {"user_id": 2, "score": 2}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='HEAD_TO_HEAD',
            results=results
        )

        assert rankings == [
            (1, 1),
            (2, 1)
        ]

    def test_head_to_head_validation_requires_two_participants(self, result_processor):
        """
        TEST: HEAD_TO_HEAD validation - must have exactly 2 participants

        Expected: Validation fails if not 2 participants
        """
        results = [
            {"user_id": 1, "result": "WIN"}
            # Missing opponent
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='HEAD_TO_HEAD',
            results=results
        )

        assert is_valid is False
        assert "requires exactly 2 results" in error_msg

    # ========================================================================
    # TEST 3: TEAM_MATCH - Team vs Team
    # ========================================================================

    def test_team_match_basic(self, result_processor):
        """
        TEST: TEAM_MATCH with Team A winning

        Input: Team scores (Team A: 5, Team B: 3)
        Expected: Team A members rank=1, Team B members rank=2
        """
        results = [
            {"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 2, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 3, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 4, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 5, "team": "B", "team_score": 3, "opponent_score": 5},
            {"user_id": 6, "team": "B", "team_score": 3, "opponent_score": 5},
            {"user_id": 7, "team": "B", "team_score": 3, "opponent_score": 5},
            {"user_id": 8, "team": "B", "team_score": 3, "opponent_score": 5}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TEAM_MATCH',
            results=results
        )

        # Winners first (rank=1), then losers (rank=2)
        assert len(rankings) == 8
        assert all(rank == 1 for uid, rank in rankings if uid in [1, 2, 3, 4])
        assert all(rank == 2 for uid, rank in rankings if uid in [5, 6, 7, 8])

    def test_team_match_tie(self, result_processor):
        """
        TEST: TEAM_MATCH with tied scores

        Input: Equal team scores
        Expected: All players rank=1
        """
        results = [
            {"user_id": 1, "team": "A", "team_score": 4, "opponent_score": 4},
            {"user_id": 2, "team": "A", "team_score": 4, "opponent_score": 4},
            {"user_id": 3, "team": "B", "team_score": 4, "opponent_score": 4},
            {"user_id": 4, "team": "B", "team_score": 4, "opponent_score": 4}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TEAM_MATCH',
            results=results
        )

        # All players get rank=1 in a tie
        assert all(rank == 1 for _, rank in rankings)

    def test_team_match_validation_requires_team_info(self, result_processor):
        """
        TEST: TEAM_MATCH validation - requires team and score info

        Expected: Validation fails without team/score data
        """
        results = [
            {"user_id": 1, "team": "A"},  # Missing team_score
            {"user_id": 2}  # Missing team
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='TEAM_MATCH',
            results=results
        )

        assert is_valid is False
        assert "requires 'user_id' and 'team'" in error_msg

    # ========================================================================
    # TEST 4: TIME_BASED - Performance times
    # ========================================================================

    def test_time_based_basic(self, result_processor):
        """
        TEST: TIME_BASED - fastest time wins

        Input: Time measurements in seconds
        Expected: Rankings ordered by time (fastest = rank 1)
        """
        results = [
            {"user_id": 1, "time_seconds": 11.23},
            {"user_id": 2, "time_seconds": 11.45},
            {"user_id": 3, "time_seconds": 11.89},
            {"user_id": 4, "time_seconds": 12.01}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TIME_BASED',
            results=results
        )

        assert rankings == [
            (1, 1),  # 11.23s - fastest
            (2, 2),  # 11.45s
            (3, 3),  # 11.89s
            (4, 4)   # 12.01s - slowest
        ]

    def test_time_based_unordered_input(self, result_processor):
        """
        TEST: TIME_BASED with unordered input

        Input: Times in random order
        Expected: Rankings sorted by time
        """
        results = [
            {"user_id": 4, "time_seconds": 12.01},
            {"user_id": 1, "time_seconds": 11.23},
            {"user_id": 3, "time_seconds": 11.89},
            {"user_id": 2, "time_seconds": 11.45}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TIME_BASED',
            results=results
        )

        # Should be sorted by time (ascending)
        assert rankings == [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4)
        ]

    def test_time_based_validation_requires_time_field(self, result_processor):
        """
        TEST: TIME_BASED validation - requires time_seconds field

        Expected: Validation fails without time data
        """
        results = [
            {"user_id": 1},  # Missing time_seconds
            {"time_seconds": 12.5}  # Missing user_id
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='TIME_BASED',
            results=results
        )

        assert is_valid is False
        assert "requires 'user_id' and 'time_seconds'" in error_msg

    # ========================================================================
    # TEST 5: SKILL_RATING - Extension Point
    # ========================================================================

    def test_skill_rating_not_implemented(self, result_processor):
        """
        TEST: SKILL_RATING raises NotImplementedError

        Expected: Clear error message about extension point
        """
        results = [
            {"user_id": 1, "rating": 9.5},
            {"user_id": 2, "rating": 8.0}
        ]

        with pytest.raises(NotImplementedError) as exc_info:
            result_processor.process_results(
                session_id=1,
                match_format='SKILL_RATING',
                results=results
            )

        error_msg = str(exc_info.value)
        assert "SKILL_RATING processor not yet implemented" in error_msg
        assert "Business logic for rating criteria" in error_msg

    def test_skill_rating_can_be_injected(self, result_processor):
        """
        TEST: SKILL_RATING processor can be injected via dependency injection

        Expected: Custom processor is used when injected
        """
        # Create mock SKILL_RATING processor
        class MockSkillRatingProcessor:
            def derive_rankings(self, results, structure_config=None):
                # Simple mock: sort by rating (descending)
                sorted_results = sorted(results, key=lambda x: x.get("rating", 0), reverse=True)
                return [(r["user_id"], idx + 1) for idx, r in enumerate(sorted_results)]

        # Inject custom processor
        result_processor.set_skill_rating_processor(MockSkillRatingProcessor())

        results = [
            {"user_id": 1, "rating": 9.5},
            {"user_id": 2, "rating": 8.0},
            {"user_id": 3, "rating": 9.0}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='SKILL_RATING',
            results=results
        )

        # Should be sorted by rating (descending)
        assert rankings == [
            (1, 1),  # rating=9.5
            (3, 2),  # rating=9.0
            (2, 3)   # rating=8.0
        ]

    # ========================================================================
    # TEST 6: General Validation
    # ========================================================================

    def test_validation_empty_results(self, result_processor):
        """
        TEST: Validation fails for empty results

        Expected: Clear error message
        """
        is_valid, error_msg = result_processor.validate_results(
            match_format='INDIVIDUAL_RANKING',
            results=[]
        )

        assert is_valid is False
        assert "Results list is empty" in error_msg

    def test_validation_invalid_match_format(self, result_processor):
        """
        TEST: Validation fails for invalid match format

        Expected: Clear error message
        """
        is_valid, error_msg = result_processor.validate_results(
            match_format='INVALID_FORMAT',
            results=[{"user_id": 1}]
        )

        assert is_valid is False
        assert "Invalid match_format" in error_msg

    def test_validation_expected_participants_count(self, result_processor):
        """
        TEST: Validation checks expected participant count

        Expected: Validation fails if count doesn't match
        """
        results = [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2}
        ]

        is_valid, error_msg = result_processor.validate_results(
            match_format='INDIVIDUAL_RANKING',
            results=results,
            expected_participants=4  # Expected 4, got 2
        )

        assert is_valid is False
        assert "Expected 4 participants, got 2" in error_msg

    def test_process_results_invalid_format_raises_error(self, result_processor):
        """
        TEST: process_results raises ValueError for invalid format

        Expected: ValueError with clear message
        """
        with pytest.raises(ValueError) as exc_info:
            result_processor.process_results(
                session_id=1,
                match_format='INVALID_FORMAT',
                results=[{"user_id": 1}]
            )

        assert "Invalid match_format" in str(exc_info.value)

    # ========================================================================
    # TEST 7: Edge Cases
    # ========================================================================

    def test_individual_ranking_with_2_participants(self, result_processor):
        """
        TEST: INDIVIDUAL_RANKING works with minimum 2 participants

        Expected: Rankings work correctly
        """
        results = [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        assert rankings == [(1, 1), (2, 2)]

    def test_team_match_with_uneven_teams(self, result_processor):
        """
        TEST: TEAM_MATCH handles uneven team sizes

        Input: Team A has 3 players, Team B has 2 players
        Expected: Rankings based on team score, regardless of team size
        """
        results = [
            {"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 2, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 3, "team": "A", "team_score": 5, "opponent_score": 3},
            {"user_id": 4, "team": "B", "team_score": 3, "opponent_score": 5},
            {"user_id": 5, "team": "B", "team_score": 3, "opponent_score": 5}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TEAM_MATCH',
            results=results
        )

        # Team A wins (3 members get rank=1)
        assert all(rank == 1 for uid, rank in rankings if uid in [1, 2, 3])
        # Team B loses (2 members get rank=2)
        assert all(rank == 2 for uid, rank in rankings if uid in [4, 5])

    def test_time_based_with_identical_times(self, result_processor):
        """
        TEST: TIME_BASED handles identical times

        Input: Two participants with same time
        Expected: Rankings still assigned (order may vary)
        """
        results = [
            {"user_id": 1, "time_seconds": 11.50},
            {"user_id": 2, "time_seconds": 11.50},
            {"user_id": 3, "time_seconds": 12.00}
        ]

        rankings = result_processor.process_results(
            session_id=1,
            match_format='TIME_BASED',
            results=results
        )

        # Should have 3 participants with sequential ranks
        assert len(rankings) == 3
        ranks = sorted([rank for _, rank in rankings])
        assert ranks == [1, 2, 3]

    # ========================================================================
    # TEST 8: Integration with MatchFormat Enum
    # ========================================================================

    def test_accepts_enum_and_string_formats(self, result_processor):
        """
        TEST: process_results accepts both enum and string match_format

        Expected: Both work correctly
        """
        results = [
            {"user_id": 1, "placement": 1},
            {"user_id": 2, "placement": 2}
        ]

        # Test with string
        rankings_string = result_processor.process_results(
            session_id=1,
            match_format='INDIVIDUAL_RANKING',
            results=results
        )

        # Test with enum
        rankings_enum = result_processor.process_results(
            session_id=1,
            match_format=MatchFormat.INDIVIDUAL_RANKING.value,
            results=results
        )

        assert rankings_string == rankings_enum
