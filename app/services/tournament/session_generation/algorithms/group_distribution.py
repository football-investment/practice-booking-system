"""
Group Distribution Algorithm

Calculates optimal group distribution for group-stage tournaments.
"""
from typing import Dict, Any, List


class GroupDistribution:
    """
    Calculates optimal group sizes and distribution
    """

    @staticmethod
    def calculate_optimal_distribution(player_count: int) -> Dict[str, Any]:
        """
        Calculate optimal group distribution for any player count.

        Business Rules:
        - Minimum group size: 3 players
        - Maximum group size: 5 players
        - Prefer balanced groups (4 players ideal)
        - Top 2 from each group advance to knockout

        Examples:
        - 8 players → 2 groups of 4
        - 9 players → 3 groups of 3
        - 10 players → 2 groups of 5
        - 11 players → 2 groups of 4, 1 group of 3
        - 12 players → 3 groups of 4
        - 13 players → 2 groups of 5, 1 group of 3

        Returns:
            {
                'groups_count': int,
                'group_sizes': List[int],  # Size of each group
                'qualifiers_per_group': int,  # Always 2
                'group_rounds': int  # Matches per group
            }
        """
        if player_count < 6:
            # Special case: less than 6 players
            # Use single group or reject
            return {
                'groups_count': 1,
                'group_sizes': [player_count],
                'qualifiers_per_group': min(2, player_count - 1),
                'group_rounds': max(1, player_count - 1)
            }

        # Strategy: Try to create balanced groups
        # Prefer groups of 4, but allow 3 and 5

        # Try different group counts and find best distribution
        best_distribution = None
        best_score = float('inf')  # Lower score = more balanced

        for num_groups in range(2, player_count // 3 + 2):
            # Calculate base size and remainder
            base_size = player_count // num_groups
            remainder = player_count % num_groups

            # Check if base_size is valid (3-5)
            if base_size < 3 or base_size > 5:
                continue

            # Check if we can distribute remainder (some groups get +1)
            max_size = base_size + (1 if remainder > 0 else 0)
            if max_size > 5:
                continue

            # Create group sizes
            group_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_groups)]

            # Calculate balance score (variance in group sizes)
            # Lower variance = better balance
            avg_size = sum(group_sizes) / len(group_sizes)
            variance = sum((size - avg_size) ** 2 for size in group_sizes)

            # Prefer 4-player groups (add bonus if close to 4)
            size_4_bonus = sum(abs(size - 4) for size in group_sizes)
            score = variance + size_4_bonus * 0.1

            if score < best_score:
                best_score = score
                best_distribution = {
                    'groups_count': num_groups,
                    'group_sizes': group_sizes,
                    'qualifiers_per_group': 2,
                    'group_rounds': max(group_sizes) - 1  # Rounds = max_size - 1
                }

        return best_distribution
