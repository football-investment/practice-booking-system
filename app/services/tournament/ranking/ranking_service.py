"""
Ranking Service

Modern replacement for RankingAggregator using Strategy Pattern.

This service:
1. Uses RankingStrategyFactory to get the correct strategy
2. Delegates ranking calculation to the strategy
3. Returns normalized RankGroup output with proper tied ranks

Replaces: app/services/tournament/results/calculators/ranking_aggregator.py
"""
from typing import Dict, List, Any, Tuple
from .strategies import RankingStrategyFactory, RankGroup


class RankingService:
    """
    Modern ranking service using Strategy Pattern.

    Usage:
        service = RankingService()
        rank_groups = service.calculate_rankings(
            scoring_type="ROUNDS_BASED",
            round_results=round_results,
            participants=participants
        )
    """

    def calculate_rankings(
        self,
        scoring_type: str,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]],
        ranking_direction: str = None
    ) -> List[RankGroup]:
        """
        Calculate rankings using the appropriate strategy.

        Args:
            scoring_type: One of 'TIME_BASED', 'SCORE_BASED', 'ROUNDS_BASED', 'PLACEMENT'
            round_results: {"1": {"13": "11 pts", ...}, "2": {...}, ...}
            participants: [{"user_id": 13, ...}, ...]
            ranking_direction: Optional override — 'ASC' (lower=better) or 'DESC' (higher=better).
                If None, each strategy uses its hardcoded default direction.
                Fixed: previously ignored (BUG-01). Now forwarded to the strategy.

        Returns:
            List[RankGroup] with proper tied ranks
        """
        # Get the appropriate strategy
        strategy = RankingStrategyFactory.create(scoring_type)

        # Calculate rankings — forward ranking_direction so strategies can override direction
        return strategy.calculate_rankings(round_results, participants, ranking_direction=ranking_direction)

    def get_aggregation_label(
        self,
        scoring_type: str,
        ranking_direction: str = None
    ) -> str:
        """
        Return the aggregation method label for a given scoring_type and direction.

        Used to populate session.game_results["aggregation_method"] accurately (fixes BUG-03).

        Args:
            scoring_type: e.g. 'TIME_BASED', 'SCORE_BASED', 'ROUNDS_BASED', 'PLACEMENT'
            ranking_direction: Optional 'ASC' or 'DESC' override

        Returns:
            Label string: 'MIN_VALUE', 'MAX_VALUE', 'SUM', 'SUM_PLACEMENT'
        """
        strategy = RankingStrategyFactory.create(scoring_type)
        return strategy.get_aggregation_label(ranking_direction=ranking_direction)

    def convert_to_legacy_format(
        self,
        rank_groups: List[RankGroup],
        measurement_unit: str = "units"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Convert RankGroup output to legacy format for backward compatibility.

        This is TEMPORARY to maintain compatibility with existing code.
        Eventually, all code should work with RankGroup directly.

        Args:
            rank_groups: List of RankGroup objects
            measurement_unit: Unit label (e.g., "seconds", "points")

        Returns:
            Tuple of (performance_rankings, wins_rankings)
            - performance_rankings: Legacy format with individual ranks
            - wins_rankings: Empty list (not used in modern flow)
        """
        performance_rankings = []

        for rank_group in rank_groups:
            for user_id in rank_group.participants:
                performance_rankings.append({
                    "user_id": user_id,
                    "rank": rank_group.rank,
                    "final_value": rank_group.final_value,
                    "measurement_unit": measurement_unit,
                    "is_tied": rank_group.is_tied()
                })

        # wins_rankings not used in modern flow
        wins_rankings = []

        return performance_rankings, wins_rankings
