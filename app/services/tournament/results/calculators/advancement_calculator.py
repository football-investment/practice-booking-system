"""
Group Stage Advancement Calculator

Determines which participants advance to knockout stage.
Extracted from match_results.py as part of P2 decomposition.
"""

from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel


class AdvancementCalculator:
    """
    Calculate which participants advance from group stage to knockout stage.

    Handles:
    - Qualification rules (e.g., top 2 per group)
    - Seeding for knockout matches
    - Standard crossover bracket logic (A1 vs B2, B1 vs A2)
    """

    def __init__(self, db: Session):
        """
        Initialize calculator with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    @staticmethod
    def get_qualified_participants(
        group_standings: Dict[str, List[Dict[str, Any]]],
        top_n: int = 2
    ) -> List[int]:
        """
        Get list of qualified participant user_ids from group standings.

        Args:
            group_standings: Dict mapping group_id to standings list
            top_n: Number of top participants per group to qualify

        Returns:
            List of qualified user_ids

        Example:
            group_standings = {
                "Group A": [{"user_id": 1, "rank": 1}, {"user_id": 2, "rank": 2}, ...],
                "Group B": [{"user_id": 3, "rank": 1}, {"user_id": 4, "rank": 2}, ...]
            }
            Result: [1, 2, 3, 4]
        """
        qualified_participants = []

        for group_id, standings in group_standings.items():
            # Top N from each group qualify
            qualified_from_group = [p['user_id'] for p in standings[:top_n]]
            qualified_participants.extend(qualified_from_group)

        return qualified_participants

    def apply_crossover_seeding(
        self,
        group_standings: Dict[str, List[Dict[str, Any]]],
        knockout_sessions: List[SessionModel]
    ) -> int:
        """
        Apply standard crossover bracket seeding to knockout sessions.

        Standard seeding for 2 groups:
        - Semifinal 1: A1 vs B2
        - Semifinal 2: B1 vs A2

        Args:
            group_standings: Dict mapping group_id to standings list
            knockout_sessions: List of knockout stage sessions

        Returns:
            Number of sessions updated

        Side effects:
            Updates participant_user_ids for knockout sessions
        """
        # Get sorted groups (alphabetically by group_id)
        sorted_groups = sorted(group_standings.items())

        if len(sorted_groups) < 2:
            return 0  # Need at least 2 groups for crossover

        group_a_id, group_a_standings = sorted_groups[0]
        group_b_id, group_b_standings = sorted_groups[1]

        # Extract top 2 from each group
        a1 = group_a_standings[0]['user_id'] if len(group_a_standings) >= 1 else None
        a2 = group_a_standings[1]['user_id'] if len(group_a_standings) >= 2 else None
        b1 = group_b_standings[0]['user_id'] if len(group_b_standings) >= 1 else None
        b2 = group_b_standings[1]['user_id'] if len(group_b_standings) >= 2 else None

        # Get Round of 4 (Semifinal) sessions - tournament_round is Integer!
        # Round 1 = Semifinals (4 players), Round 2 = Final (2 players)
        semifinal_sessions = [s for s in knockout_sessions if s.tournament_round == 1]

        sessions_updated = 0

        if len(semifinal_sessions) >= 2 and all([a1, a2, b1, b2]):
            # Semifinal 1: A1 vs B2 (crossover bracket)
            semifinal_sessions[0].participant_user_ids = [a1, b2]
            sessions_updated += 1

            # Semifinal 2: B1 vs A2 (crossover bracket)
            semifinal_sessions[1].participant_user_ids = [b1, a2]
            sessions_updated += 1

            # Note: Final match (round 2) participant_user_ids will be set after semifinals are completed

        return sessions_updated

    def calculate_advancement(
        self,
        group_standings: Dict[str, List[Dict[str, Any]]],
        knockout_sessions: List[SessionModel],
        top_n_per_group: int = 2
    ) -> Tuple[List[int], int]:
        """
        Calculate advancement from group stage to knockout stage.

        Args:
            group_standings: Dict mapping group_id to standings list
            knockout_sessions: List of knockout stage sessions
            top_n_per_group: Number of top participants per group to qualify

        Returns:
            Tuple of (qualified_participants, sessions_updated)

        Side effects:
            Updates participant_user_ids for knockout sessions
        """
        # Get qualified participants
        qualified_participants = self.get_qualified_participants(
            group_standings, top_n_per_group
        )

        # Apply crossover seeding
        sessions_updated = self.apply_crossover_seeding(
            group_standings, knockout_sessions
        )

        return qualified_participants, sessions_updated


# Export main class
__all__ = ["AdvancementCalculator"]
