"""
PLACEMENT Ranking Strategy

For tournaments where participants submit their placement position (e.g., race finishing order).

Rules:
- Lower placement number is better (ASC sorting)
- Total placement-sum across rounds determines ranking (like golf scoring)
- Tied totals receive same rank
- Next rank skips after ties

Example:
Round 1: Player A: 1st, Player B: 2nd, Player C: 3rd
Round 2: Player A: 1st, Player B: 3rd, Player C: 2nd

Totals: A=2, B=5, C=5
Final Rankings:
1st: Player A (total=2)
2nd: Player B (total=5) TIE
2nd: Player C (total=5) TIE
4th: (skipped)

Note: BUG-02 fix — previously PLACEMENT incorrectly mapped to ScoreBasedStrategy (DESC/SUM),
which ranked placement=3 above placement=1. This strategy uses ASC sorting so placement=1 wins.
"""
from typing import List, Dict, Any, Optional
from .base import RankingStrategy, RankGroup


class PlacementStrategy(RankingStrategy):
    """
    PLACEMENT ranking strategy.

    Aggregation: SUM (total placement positions across rounds, like golf)
    Sort: ASC (lower total placement = better)
    Tied Ranks: Allowed (same total placement = same rank)
    """

    def aggregate_value(self, values: List[float]) -> float:
        """
        Sum placement positions across rounds.

        Lower sum = better (player who consistently finishes 1st has lowest sum).

        Args:
            values: List of placement positions from each round (e.g., [1.0, 2.0, 1.0])

        Returns:
            Sum of placement positions
        """
        return sum(values) if values else float('inf')

    def get_sort_direction(self) -> str:
        """PLACEMENT uses ascending sort (lower placement-sum is better)"""
        return 'ASC'

    def calculate_rankings(
        self,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]],
        ranking_direction: Optional[str] = None
    ) -> List[RankGroup]:
        """
        Calculate PLACEMENT rankings.

        Process:
        1. Extract numeric placement values from each round
        2. Sum placements across all rounds (lower sum = more consistent winner)
        3. Sort by total placement sum (ASC)
        4. Group participants with same total (tied ranks)

        Args:
            round_results: {"1": {"1": "1", "2": "2", "3": "3"}, ...}
                           Values are placement positions (integers as strings)
            participants: [{"user_id": 1, ...}, ...]
            ranking_direction: Optional override (default 'ASC' — lower placement = better)

        Returns:
            List[RankGroup] with tied ranks grouped, rank 1 = best (lowest) placement sum
        """
        user_placement_sums = {}

        for participant in participants:
            user_id = participant['user_id']
            placements = []

            for round_num, round_data in round_results.items():
                user_id_str = str(user_id)
                if user_id_str in round_data:
                    placement_str = round_data[user_id_str]
                    try:
                        placement_value = float(
                            ''.join(c for c in placement_str if c.isdigit() or c == '.' or c == '-')
                        )
                        placements.append(placement_value)
                    except (ValueError, TypeError):
                        continue

            if placements:
                user_placement_sums[user_id] = self.aggregate_value(placements)

        return self._group_by_value(user_placement_sums, direction_override=ranking_direction)
