"""
Individual Ranking Aggregator

Aggregates results across multiple rounds for INDIVIDUAL_RANKING tournaments.
Extracted from match_results.py as part of P2 decomposition.
"""

from decimal import Decimal
from typing import Dict, List, Any, Tuple
import re


class RankingAggregator:
    """
    Aggregate rankings across multiple rounds for INDIVIDUAL_RANKING tournaments.

    Handles:
    - Parsing measured values from strings (e.g., "12.5s", "95 points")
    - Aggregating best performance across rounds
    - Calculating both performance-based and wins-based rankings
    - Tie-breaking logic
    """

    @staticmethod
    def parse_measured_value(measured_value_str: str) -> Decimal:
        """
        Parse numeric value from measured string.

        Args:
            measured_value_str: String like "12.5s", "95 points", "15.2 meters"

        Returns:
            Decimal numeric value

        Raises:
            ValueError: If no numeric value found
        """
        numeric_match = re.search(r'[\d.]+', measured_value_str)
        if not numeric_match:
            raise ValueError(f"Cannot parse measured value '{measured_value_str}'")

        return Decimal(numeric_match.group())

    @staticmethod
    def aggregate_user_values(
        round_results: Dict[str, Dict[str, str]],
        ranking_direction: str
    ) -> Dict[int, Decimal]:
        """
        Aggregate best value for each user across all rounds.

        Args:
            round_results: Dict mapping round_number -> {user_id: measured_value}
            ranking_direction: "ASC" (lowest wins) or "DESC" (highest wins)

        Returns:
            Dict mapping user_id to their best aggregated value

        Example:
            round_results = {
                "1": {"123": "12.5s", "456": "13.2s"},
                "2": {"123": "12.0s", "456": "13.5s"}
            }
            Result: {123: Decimal("12.0"), 456: Decimal("13.2")}
        """
        # Structure: {user_id: [value1, value2, value3, ...]}
        user_round_values: Dict[int, List[Decimal]] = {}

        for round_num, results_dict in round_results.items():
            for user_id_str, measured_value_str in results_dict.items():
                user_id = int(user_id_str)

                numeric_value = RankingAggregator.parse_measured_value(measured_value_str)

                if user_id not in user_round_values:
                    user_round_values[user_id] = []
                user_round_values[user_id].append(numeric_value)

        # Calculate final aggregate value for each user
        user_final_values = {}

        for user_id, values in user_round_values.items():
            if ranking_direction == "ASC":
                # ASC: Lowest is best (e.g., fastest time) → take MIN
                final_value = min(values)
            else:
                # DESC: Highest is best (e.g., highest score) → take MAX
                final_value = max(values)

            user_final_values[user_id] = final_value

        return user_final_values

    @staticmethod
    def calculate_performance_rankings(
        user_final_values: Dict[int, Decimal],
        ranking_direction: str,
        measurement_unit: str = "units"
    ) -> List[Dict[str, Any]]:
        """
        Calculate rankings based on best individual performance.

        Args:
            user_final_values: Dict mapping user_id to their best value
            ranking_direction: "ASC" or "DESC"
            measurement_unit: Unit label (e.g., "seconds", "points")

        Returns:
            List of ranking entries sorted by performance:
            [
                {
                    "user_id": 123,
                    "rank": 1,
                    "final_value": 12.0,
                    "measurement_unit": "seconds"
                },
                ...
            ]
        """
        # Sort by final value based on ranking_direction
        if ranking_direction == "ASC":
            sorted_users = sorted(user_final_values.items(), key=lambda x: x[1])
        else:
            sorted_users = sorted(user_final_values.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks (handle ties by giving same rank)
        performance_rankings = []
        current_rank = 1
        prev_value = None

        for i, (user_id, final_value) in enumerate(sorted_users):
            if prev_value is not None and final_value != prev_value:
                current_rank = i + 1

            performance_rankings.append({
                "user_id": user_id,
                "rank": current_rank,
                "final_value": float(final_value),
                "measurement_unit": measurement_unit
            })

            prev_value = final_value

        return performance_rankings

    @staticmethod
    def calculate_wins_rankings(
        round_results: Dict[str, Dict[str, str]],
        ranking_direction: str,
        total_rounds: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate rankings based on number of round wins.

        A "win" means having the best value in that round.

        Args:
            round_results: Dict mapping round_number -> {user_id: measured_value}
            ranking_direction: "ASC" or "DESC"
            total_rounds: Total number of rounds

        Returns:
            List of ranking entries sorted by wins:
            [
                {
                    "user_id": 123,
                    "rank": 1,
                    "wins": 3,
                    "total_rounds": 3
                },
                ...
            ]
        """
        # Collect all user IDs
        all_user_ids = set()
        for results_dict in round_results.values():
            all_user_ids.update(int(uid) for uid in results_dict.keys())

        # Count how many times each user won a round
        user_round_wins = {user_id: 0 for user_id in all_user_ids}

        for round_num, results_dict in round_results.items():
            # Parse all values in this round
            round_values = {}
            for user_id_str, measured_value_str in results_dict.items():
                user_id = int(user_id_str)
                try:
                    numeric_value = RankingAggregator.parse_measured_value(measured_value_str)
                    round_values[user_id] = numeric_value
                except ValueError:
                    continue

            # Find winner(s) of this round
            if round_values:
                if ranking_direction == "ASC":
                    best_value = min(round_values.values())
                else:
                    best_value = max(round_values.values())

                # Award win to user(s) with best value (handle ties)
                for user_id, value in round_values.items():
                    if value == best_value:
                        user_round_wins[user_id] += 1

        # Sort by number of wins (descending)
        sorted_users_wins = sorted(user_round_wins.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks based on wins
        wins_rankings = []
        current_rank = 1
        prev_wins = None

        for i, (user_id, wins) in enumerate(sorted_users_wins):
            if prev_wins is not None and wins < prev_wins:
                current_rank = i + 1

            wins_rankings.append({
                "user_id": user_id,
                "rank": current_rank,
                "wins": wins,
                "total_rounds": total_rounds
            })

            prev_wins = wins

        return wins_rankings

    @staticmethod
    def aggregate_rankings(
        round_results: Dict[str, Dict[str, str]],
        ranking_direction: str,
        total_rounds: int,
        measurement_unit: str = "units"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Calculate dual ranking system: performance-based and wins-based.

        Args:
            round_results: Dict mapping round_number -> {user_id: measured_value}
            ranking_direction: "ASC" (lowest wins) or "DESC" (highest wins)
            total_rounds: Total number of rounds
            measurement_unit: Unit label (e.g., "seconds", "points")

        Returns:
            Tuple of (performance_rankings, wins_rankings)

        Example:
            performance_rankings = [
                {"user_id": 123, "rank": 1, "final_value": 12.0, "measurement_unit": "seconds"},
                {"user_id": 456, "rank": 2, "final_value": 13.2, "measurement_unit": "seconds"}
            ]
            wins_rankings = [
                {"user_id": 123, "rank": 1, "wins": 2, "total_rounds": 3},
                {"user_id": 456, "rank": 2, "wins": 1, "total_rounds": 3}
            ]
        """
        # Calculate best performance for each user
        user_final_values = RankingAggregator.aggregate_user_values(
            round_results, ranking_direction
        )

        # Calculate performance rankings
        performance_rankings = RankingAggregator.calculate_performance_rankings(
            user_final_values, ranking_direction, measurement_unit
        )

        # Calculate wins rankings
        wins_rankings = RankingAggregator.calculate_wins_rankings(
            round_results, ranking_direction, total_rounds
        )

        return performance_rankings, wins_rankings


# Export main class
__all__ = ["RankingAggregator"]
