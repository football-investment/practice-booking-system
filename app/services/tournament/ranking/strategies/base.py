"""
Base Ranking Strategy

Defines the abstract interface for all ranking strategies.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class RankGroup:
    """
    Represents a group of participants with the same rank.

    This is the ONLY valid output format for ranking strategies.
    Tied ranks are explicitly represented by having multiple user_ids in participants.

    Attributes:
        rank: Integer rank (1, 2, 3, ...). If tied, next rank skips (e.g., 1, 2, 2, 4)
        participants: List of user_ids who share this rank
        final_value: The aggregated value used for ranking (e.g., best time, total score)

    Example:
        RankGroup(rank=2, participants=[7, 14], final_value=10.0)
        -> Tibor (user_id=7) and Yamal (user_id=14) are TIED at 2nd place with 10 points
    """
    rank: int
    participants: List[int]  # user_ids
    final_value: float

    def is_tied(self) -> bool:
        """Check if this rank group represents a tie"""
        return len(self.participants) > 1


class RankingStrategy(ABC):
    """
    Abstract base class for ranking strategies.

    Each scoring type (TIME_BASED, SCORE_BASED, ROUNDS_BASED) implements this interface.

    Responsibilities:
    1. Aggregate multi-round results
    2. Calculate final value for each participant
    3. Sort participants by final value
    4. Handle tied ranks correctly
    5. Return normalized RankGroup output

    Business Rule:
    - Tied ranks MUST skip subsequent ranks
    - Example: If 2 players tie for 2nd, next rank is 4th (not 3rd)
    """

    @abstractmethod
    def calculate_rankings(
        self,
        round_results: Dict[str, Dict[str, str]],
        participants: List[Dict[str, Any]]
    ) -> List[RankGroup]:
        """
        Calculate final rankings from round results.

        Args:
            round_results: {
                "1": {"user_id_13": "11.5s", "user_id_14": "12.3s"},
                "2": {"user_id_13": "10.8s", "user_id_14": "11.9s"},
                "3": {"user_id_13": "11.2s", "user_id_14": "10.5s"}
            }
            participants: List of participant dicts with user_id

        Returns:
            List[RankGroup] sorted by rank, with tied ranks grouped

        Example:
            [
                RankGroup(rank=1, participants=[13], final_value=10.8),
                RankGroup(rank=2, participants=[14, 7], final_value=11.2),
                RankGroup(rank=4, participants=[5], final_value=12.5)
            ]
        """
        pass

    @abstractmethod
    def aggregate_value(self, values: List[float]) -> float:
        """
        Aggregate multiple round values into a single final value.

        Implementation varies by strategy:
        - TIME_BASED: min(values) - best (fastest) time
        - SCORE_BASED: sum(values) - total score
        - ROUNDS_BASED: max(values) - best single round performance

        Args:
            values: List of numeric values from each round

        Returns:
            Single aggregated value
        """
        pass

    @abstractmethod
    def get_sort_direction(self) -> str:
        """
        Get sort direction for this strategy.

        Returns:
            'ASC' for ascending (lower is better, e.g., time)
            'DESC' for descending (higher is better, e.g., score)
        """
        pass

    def _aggregate_direction_sensitive(
        self,
        values: List[float],
        direction: str
    ) -> float:
        """
        Aggregate values for strategies where the aggregation method depends on direction.

        Used by TIME_BASED and ROUNDS_BASED strategies when ranking_direction is overridden:
          - ASC (lower=better): take MIN (fastest/lowest)
          - DESC (higher=better): take MAX (highest/best)

        SCORE_BASED and PLACEMENT always use SUM regardless of direction.

        Args:
            values: List of numeric values from each round
            direction: 'ASC' or 'DESC'

        Returns:
            Aggregated float value
        """
        if direction == 'ASC':
            return min(values) if values else float('inf')
        return max(values) if values else 0.0

    def _group_by_value(
        self,
        user_values: Dict[int, float],
        direction_override: str = None
    ) -> List[RankGroup]:
        """
        Helper: Group users by their final value and assign ranks.

        Handles tied ranks correctly:
        - Users with same final_value get same rank
        - Next rank skips based on number of tied users

        Args:
            user_values: {user_id: final_value}
            direction_override: Optional 'ASC' or 'DESC' to override get_sort_direction().
                Used when ranking_direction is passed to calculate_rankings().

        Returns:
            List[RankGroup] with tied ranks grouped
        """
        # Sort by value (direction_override takes precedence over hardcoded strategy direction)
        effective_direction = direction_override or self.get_sort_direction()
        reverse = effective_direction == 'DESC'
        sorted_items = sorted(user_values.items(), key=lambda x: x[1], reverse=reverse)

        rank_groups = []
        current_rank = 1
        i = 0

        while i < len(sorted_items):
            current_value = sorted_items[i][1]
            tied_users = [sorted_items[i][0]]

            # Find all users with the same value (tied)
            j = i + 1
            while j < len(sorted_items) and sorted_items[j][1] == current_value:
                tied_users.append(sorted_items[j][0])
                j += 1

            # Create rank group
            rank_groups.append(RankGroup(
                rank=current_rank,
                participants=tied_users,
                final_value=current_value
            ))

            # Next rank skips based on number of tied users
            current_rank += len(tied_users)
            i = j

        return rank_groups
