"""
ROUNDS_BASED Ranking Strategy

For tournaments where participants compete in multiple rounds, and BEST single performance counts.

Rules:
- Higher score is better (DESC sorting)
- BEST (maximum) score from any single round wins
- Tied best scores receive same rank
- Next rank skips after ties

Example (CRITICAL - This is what tournament 222 uses):
Round 1: Mbappé: 11pts, Tibor: 6pts, Yamal: 8pts
Round 2: Mbappé: 10pts, Tibor: 7pts, Yamal: 10pts
Round 3: Mbappé: 11pts, Tibor: 10pts, Yamal: 10pts

Final Rankings (BEST score from any round):
1st: Mbappé (11pts - appears in Round 1 and 3)
2nd: Tibor (10pts - appears in Round 3) TIE
2nd: Yamal (10pts - appears in Round 2 and 3) TIE
4th: (next participant)

This is DIFFERENT from SCORE_BASED:
- SCORE_BASED: SUM all rounds (Mbappé: 32pts total)
- ROUNDS_BASED: MAX single round (Mbappé: 11pts best)
"""
from typing import List, Dict, Any
from .base import RankingStrategy, RankGroup


class RoundsBasedStrategy(RankingStrategy):
    """
    ROUNDS_BASED ranking strategy.

    Aggregation: MAX (best single round performance)
    Sort: DESC (higher is better)
    Tied Ranks: Allowed (same best score = same rank)

    CRITICAL: This is the strategy tournament 222 uses!
    """

    def aggregate_value(self, values: List[float]) -> float:
        """
        Get the best (maximum) score from any single round.

        Args:
            values: List of scores from each round

        Returns:
            Maximum score
        """
        return max(values) if values else 0.0

    def get_sort_direction(self) -> str:
        """ROUNDS_BASED uses descending sort (higher is better)"""
        return 'DESC'

    def calculate_rankings(
        self,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]],
        ranking_direction: str = None
    ) -> List[RankGroup]:
        """
        Calculate ROUNDS_BASED rankings.

        Process:
        1. Extract numeric score values from each round
        2. Find best score for each participant (MAX by default; MIN if ranking_direction='ASC')
        3. Sort by best score (DESC by default; ASC if ranking_direction='ASC')
        4. Group participants with same best score (tied ranks)

        Args:
            round_results: {"1": {"13": "11 pts", "14": "8 pts"}, "2": {"13": "10 pts", "14": "10 pts"}, ...}
            participants: [{"user_id": 13, ...}, {"user_id": 14, ...}]

        Returns:
            List[RankGroup] with tied ranks grouped

        Example Output for tournament 222:
            [
                RankGroup(rank=1, participants=[13], final_value=11.0),      # Mbappé
                RankGroup(rank=2, participants=[7, 14], final_value=10.0),   # Tibor & Yamal TIE
                RankGroup(rank=4, participants=[5], final_value=9.0),        # Next player
                ...
            ]
        """
        # Build user_id to best_score mapping
        user_best_scores = {}

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

            # Aggregate: direction-sensitive (default DESC → MAX; override ASC → MIN)
            if scores:
                effective_dir = ranking_direction or self.get_sort_direction()
                user_best_scores[user_id] = self._aggregate_direction_sensitive(scores, effective_dir)

        # Group by value and assign ranks (handles ties + direction override)
        return self._group_by_value(user_best_scores, direction_override=ranking_direction)
