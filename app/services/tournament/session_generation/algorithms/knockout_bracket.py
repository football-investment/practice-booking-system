"""
Knockout Bracket Algorithm

Calculates knockout bracket structure including byes and bronze matches.
"""
import math
from typing import Dict, Any


class KnockoutBracket:
    """
    Calculates knockout bracket structure
    """

    @staticmethod
    def calculate_structure(qualifiers: int) -> Dict[str, Any]:
        """
        Calculate knockout bracket structure based on number of qualifiers

        Implements the business logic decisions:
        - 4 qualifiers: No byes, no bronze
        - 6 qualifiers: 2 byes (seeds 1-2), bronze match
        - 8 qualifiers: No byes, bronze match
        - 10 qualifiers: 4 byes (seeds 1-4), bronze match
        - 12 qualifiers: 4 byes (seeds 1-4), bronze match
        - Other: Round up to next power of 2, bronze for 8+

        Returns:
            {
                'play_in_matches': int,  # Number of play-in matches
                'byes': int,             # Number of byes
                'bracket_size': int,     # Final bracket size (power of 2)
                'has_bronze': bool       # Whether to include 3rd place match
            }
        """
        if qualifiers == 4:
            return {
                'play_in_matches': 0,
                'byes': 0,
                'bracket_size': 4,
                'has_bronze': True  # ✅ FIX: Bronze match required even for 4-player knockout
            }

        elif qualifiers == 6:
            # ✅ Decision: 6 → 4 bracket with byes
            return {
                'play_in_matches': 2,  # Seeds 3-6 play (2 matches)
                'byes': 2,             # Seeds 1-2 bye to semifinals
                'bracket_size': 4,
                'has_bronze': True     # ✅ Decision: Bronze for 8+ knockouts (bracket_size=4 but qualifiers=6)
            }

        elif qualifiers == 8:
            return {
                'play_in_matches': 0,
                'byes': 0,
                'bracket_size': 8,
                'has_bronze': True
            }

        elif qualifiers == 10:
            # ✅ Decision: 10 → 8 bracket with byes
            return {
                'play_in_matches': 3,  # Seeds 5-10 play (3 matches: 5v10, 6v9, 7v8)
                'byes': 4,             # Seeds 1-4 bye to quarterfinals
                'bracket_size': 8,
                'has_bronze': True
            }

        elif qualifiers == 12:
            # ✅ Decision: 12 → 8 bracket with byes
            return {
                'play_in_matches': 4,  # Seeds 5-12 play (4 matches)
                'byes': 4,             # Seeds 1-4 bye to quarterfinals
                'bracket_size': 8,
                'has_bronze': True
            }

        else:
            # For other sizes, round up to next power of 2
            bracket_size = 2 ** math.ceil(math.log2(qualifiers))
            byes = bracket_size - qualifiers
            play_in_matches = (qualifiers - byes) // 2

            return {
                'play_in_matches': play_in_matches,
                'byes': byes,
                'bracket_size': bracket_size,
                'has_bronze': bracket_size >= 8  # ✅ Decision: Bronze only for 8+ brackets
            }
