"""
TIME_BASED Ranking Strategy

For tournaments where participants compete against time (e.g., sprint, obstacle course).

Rules:
- Lower time is better (ASC sorting)
- Best (minimum) time across all rounds wins
- Tied times receive same rank
- Next rank skips after ties

Example:
Round 1: Player A: 10.5s, Player B: 11.2s, Player C: 10.5s
Round 2: Player A: 11.0s, Player B: 10.8s, Player C: 11.5s
Round 3: Player A: 10.2s, Player B: 11.0s, Player C: 10.5s

Final Rankings:
1st: Player A (10.2s - best time)
2nd: Player C (10.5s - best time)
3rd: Player B (10.8s - best time)
"""
from typing import List, Dict, Any
from .base import RankingStrategy, RankGroup


class TimeBasedStrategy(RankingStrategy):
    """
    TIME_BASED ranking strategy.

    Aggregation: MIN (best/fastest time)
    Sort: ASC (lower is better)
    Tied Ranks: Allowed (same time = same rank)
    """

    def aggregate_value(self, values: List[float]) -> float:
        """
        Get the best (minimum) time across all rounds.

        Args:
            values: List of times from each round

        Returns:
            Minimum time
        """
        return min(values) if values else float('inf')

    def get_sort_direction(self) -> str:
        """TIME_BASED uses ascending sort (lower is better)"""
        return 'ASC'

    def get_aggregation_label(self, ranking_direction: str = None) -> str:
        effective = ranking_direction or self.get_sort_direction()
        return "MIN_VALUE" if effective == "ASC" else "MAX_VALUE"

    def calculate_rankings(
        self,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]],
        ranking_direction: str = None
    ) -> List[RankGroup]:
        """
        Calculate TIME_BASED rankings.

        Process:
        1. Extract numeric time values from each round
        2. Find best (minimum) time for each participant
        3. Sort by best time (ASC)
        4. Group participants with same best time (tied ranks)

        Args:
            round_results: {"1": {"13": "10.5s", "14": "11.2s"}, ...}
            participants: [{"user_id": 13, ...}, {"user_id": 14, ...}]

        Returns:
            List[RankGroup] with tied ranks grouped
        """
        # Build user_id to best_time mapping
        user_best_times = {}

        for participant in participants:
            user_id = participant['user_id']
            times = []

            # Collect times from all rounds
            for round_num, round_data in round_results.items():
                user_id_str = str(user_id)
                if user_id_str in round_data:
                    time_str = round_data[user_id_str]
                    # Parse time value (remove 's', 'seconds', etc.)
                    try:
                        time_value = float(''.join(c for c in time_str if c.isdigit() or c == '.'))
                        times.append(time_value)
                    except (ValueError, TypeError):
                        continue

            # Aggregate: direction-sensitive (default ASC → MIN; override DESC → MAX)
            if times:
                effective_dir = ranking_direction or self.get_sort_direction()
                user_best_times[user_id] = self._aggregate_direction_sensitive(times, effective_dir)

        # Group by value and assign ranks (handles ties + direction override)
        return self._group_by_value(user_best_times, direction_override=ranking_direction)
