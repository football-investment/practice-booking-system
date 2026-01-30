"""
Round Robin Pairing Algorithm

Implements circle/rotation algorithm for fair round-robin scheduling.
"""
from typing import List, Tuple


class RoundRobinPairing:
    """
    Generates round-robin pairings using circle/rotation algorithm
    """

    @staticmethod
    def get_round_pairings(player_ids: List[int], round_num: int) -> List[Tuple[int, int]]:
        """
        Generate pairings for a specific round using circle/rotation algorithm

        Args:
            player_ids: List of player IDs
            round_num: Round number (1-indexed)

        Returns:
            List of (player1_id, player2_id) tuples for this round
        """
        n = len(player_ids)
        pairings = []

        if n % 2 == 1:
            # Odd number: add dummy player for bye
            players = player_ids + [None]
            n += 1
        else:
            players = player_ids[:]

        # Circle method: fix first player, rotate others
        # Round 1: [1,2,3,4,5,6] → pairs: (1,6), (2,5), (3,4)
        # Round 2: [1,3,4,5,6,2] → pairs: (1,2), (3,6), (4,5)
        # etc.

        # Rotation offset based on round_num
        rotated = [players[0]] + players[1:][round_num - 1:] + players[1:][:round_num - 1]

        # Pair first with last, second with second-to-last, etc.
        for i in range(n // 2):
            player1 = rotated[i]
            player2 = rotated[n - 1 - i]
            pairings.append((player1, player2))

        return pairings

    @staticmethod
    def calculate_rounds(player_count: int) -> int:
        """
        Calculate number of rounds needed for round-robin tournament

        Args:
            player_count: Number of players

        Returns:
            Number of rounds (n-1 for even, n for odd)
        """
        return player_count if player_count % 2 == 1 else player_count - 1
