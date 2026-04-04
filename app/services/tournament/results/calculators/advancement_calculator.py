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
    - Standard crossover bracket logic for N groups (seed[i] vs seed[total-1-i])
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
            # Support both TEAM standings (team_id key) and INDIVIDUAL (user_id key)
            id_key = "team_id" if (standings and "team_id" in standings[0]) else "user_id"
            qualified_from_group = [p[id_key] for p in standings[:top_n]]
            qualified_participants.extend(qualified_from_group)

        return qualified_participants

    def apply_crossover_seeding(
        self,
        group_standings: Dict[str, List[Dict[str, Any]]],
        knockout_sessions: List[SessionModel]
    ) -> int:
        """
        Apply standard crossover bracket seeding to knockout sessions.

        Generalised for N groups with top_n qualifiers each:
        - Seeds are ordered rank-first across groups: A1, B1, ..., N1, A2, B2, ..., N2
        - Bracket pairs: seed[i] vs seed[total-1-i]
          e.g. 2 groups, top 2 → [A1,B1,A2,B2] → SF1: A1 vs B2, SF2: B1 vs A2
          e.g. 4 groups, top 2 → [A1,B1,C1,D1,A2,B2,C2,D2]
                                 → QF1: A1 vs D2, QF2: B1 vs C2, QF3: C1 vs B2, QF4: D1 vs A2

        Args:
            group_standings: Dict mapping group_id to standings list
            knockout_sessions: List of knockout stage sessions

        Returns:
            Number of sessions updated

        Side effects:
            Updates participant_user_ids for knockout sessions
        """
        from sqlalchemy.orm.attributes import flag_modified

        sorted_groups = sorted(group_standings.items())
        num_groups = len(sorted_groups)

        if num_groups < 2:
            return 0

        # Detect TEAM mode from first standing entry
        first_standings = next(
            (s for _, s in sorted_groups if s), []
        )
        is_team = bool(first_standings and "team_id" in first_standings[0])
        id_key = "team_id" if is_team else "user_id"

        # First-round sessions (round 1 = deepest knockout round, e.g. QF or SF)
        first_round_sessions = [s for s in knockout_sessions if s.tournament_round == 1]
        num_first_round = len(first_round_sessions)

        if num_first_round == 0:
            return 0

        # Infer top_n from bracket size: total_qualifiers = num_first_round * 2
        total_qualifiers = num_first_round * 2
        top_n = total_qualifiers // num_groups

        if top_n < 1:
            return 0

        # Build seeded list rank-first across all groups:
        # rank 1 from A,B,C,D,...  then rank 2 from A,B,C,D,...
        seeded: List[int] = []
        for rank in range(top_n):
            for _group_id, standings in sorted_groups:
                if len(standings) > rank:
                    seeded.append(standings[rank][id_key])

        if len(seeded) < total_qualifiers:
            return 0  # Not enough qualified participants

        # Assign bracket pairs: seed[i] vs seed[total-1-i]
        sessions_updated = 0
        for i, session in enumerate(first_round_sessions):
            high = total_qualifiers - 1 - i
            if i < high:
                if is_team:
                    session.participant_team_ids = [seeded[i], seeded[high]]
                    flag_modified(session, "participant_team_ids")
                else:
                    session.participant_user_ids = [seeded[i], seeded[high]]
                    flag_modified(session, "participant_user_ids")
                sessions_updated += 1

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
