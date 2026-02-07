"""
SCORE_BASED Ranking Strategy

For tournaments where participants accumulate points/scores (e.g., goals, repetitions, accuracy).

Rules:
- Higher score is better (DESC sorting)
- Total score across all rounds wins
- Tied scores receive same rank
- Next rank skips after ties

Example:
Round 1: Player A: 15pts, Player B: 12pts, Player C: 15pts
Round 2: Player A: 18pts, Player B: 20pts, Player C: 14pts
Round 3: Player A: 16pts, Player B: 18pts, Player C: 20pts

Final Rankings:
1st: Player A (49pts total)
2nd: Player B (50pts total) ← Whoops, B actually wins!
3rd: Player C (49pts total)

Actually:
1st: Player B (50pts)
2nd: Player A (49pts) TIE
2nd: Player C (49pts) TIE
4th: (skipped)
"""
from typing import List, Dict, Any
from .base import RankingStrategy, RankGroup


class ScoreBasedStrategy(RankingStrategy):
    """
    SCORE_BASED ranking strategy.

    Aggregation: SUM (total score across all rounds)
    Sort: DESC (higher is better)
    Tied Ranks: Allowed (same total score = same rank)
    """

    def aggregate_value(self, values: List[float]) -> float:
        """
        Get the total score across all rounds.

        Args:
            values: List of scores from each round

        Returns:
            Sum of all scores
        """
        return sum(values) if values else 0.0

    def get_sort_direction(self) -> str:
        """SCORE_BASED uses descending sort (higher is better)"""
        return 'DESC'

    def calculate_rankings(
        self,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]]
    ) -> List[RankGroup]:
        """
        Calculate SCORE_BASED rankings.

        Process:
        1. Extract numeric score values from each round
        2. Sum scores across all rounds for each participant
        3. Sort by total score (DESC)
        4. Group participants with same total score (tied ranks)

        Args:
            round_results: {"1": {"13": "15 pts", "14": "12 pts"}, ...}
            participants: [{"user_id": 13, ...}, {"user_id": 14, ...}]

        Returns:
            List[RankGroup] with tied ranks grouped
        """
        # Build user_id to total_score mapping
        user_total_scores = {}

        for participant in participants:
            user_id = participant['user_id']
            scores = []

            # Collect scores from all rounds
            for round_num, round_data in round_results.items():
                user_id_str = str(user_id)
                if user_id_str in round_data:
                    score_str = round_data[user_id_str]
                    # Parse score value (remove 'pts', 'points', etc.)
                    try:
                        score_value = float(''.join(c for c in score_str if c.isdigit() or c == '.' or c == '-'))
                        scores.append(score_value)
                    except (ValueError, TypeError):
                        continue

            # Aggregate: total (sum) score
            if scores:
                user_total_scores[user_id] = self.aggregate_value(scores)

        # Group by value and assign ranks (handles ties)
        return self._group_by_value(user_total_scores)
