"""
Ranking Strategy Pattern

This module implements the Strategy Pattern for tournament ranking calculations.

Architecture:
- Each scoring type (TIME_BASED, SCORE_BASED, ROUNDS_BASED) has its own strategy
- Strategies are responsible for:
  1. Aggregating multi-round results
  2. Calculating final values
  3. Handling tied ranks correctly
  4. Sorting participants

Output Format:
- Each strategy returns a list of RankGroup objects
- RankGroup contains: rank (int), participants (list of user_ids with same rank), final_value (float)
- This ensures tied ranks are explicitly represented

Example Output:
[
    RankGroup(rank=1, participants=[13], final_value=11.0),      # 1st place: Mbappé
    RankGroup(rank=2, participants=[7, 14], final_value=10.0),   # 2nd place TIE: Tibor & Yamal
    RankGroup(rank=4, participants=[5], final_value=9.0),        # 4th place (skip 3rd)
]

Separation of Concerns:
- Ranking strategies ONLY handle ranking logic
- Reward distribution consumes normalized rank groups
- No business logic mixing
"""

from .base import RankingStrategy, RankGroup
from .time_based import TimeBasedStrategy
from .score_based import ScoreBasedStrategy
from .rounds_based import RoundsBasedStrategy
from .factory import RankingStrategyFactory

__all__ = [
    "RankingStrategy",
    "RankGroup",
    "TimeBasedStrategy",
    "ScoreBasedStrategy",
    "RoundsBasedStrategy",
    "RankingStrategyFactory",
]
