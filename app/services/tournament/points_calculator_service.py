"""
Tournament Points Calculator Service

Calculates points for tournament sessions based on ranking mode and tier.

Supports:
1. ALL_PARTICIPANTS mode (League): Standard ranking points
2. GROUP_ISOLATED mode (Group Stage): Group-specific ranking points
3. TIERED mode (Knockout): Tier-based point multipliers
4. QUALIFIED_ONLY mode (Knockout Stage): Knockout progression points
5. PERFORMANCE_POD mode (Swiss): Performance-based pod points

Point Distribution Philosophy:
- Higher placement = more points
- Higher tier/round = higher point multipliers
- Consistent across tournament types
- Configurable per tournament type
"""
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.models.tournament_type import TournamentType
from app.models.semester import Semester


class PointsCalculatorService:
    """
    Calculates tournament points based on session metadata and player rankings.

    This service provides a unified interface for point calculation across
    all tournament types, respecting the ranking_mode and tier information.
    """

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Default Point Schemes
    # ========================================================================

    # Standard ranking points (1st=3pts, 2nd=2pts, 3rd=1pt, rest=0pts)
    DEFAULT_RANKING_POINTS = {
        1: 3,
        2: 2,
        3: 1
    }

    # Tier multipliers for Knockout tournaments
    # Higher rounds = higher multipliers
    TIER_MULTIPLIERS = {
        1: 1.0,   # Round of 16 / Quarter-finals
        2: 1.5,   # Semi-finals
        3: 2.0,   # Finals
        4: 2.5,   # Special rounds (3rd place playoff, etc.)
    }

    # Performance pod modifiers for Swiss System
    POD_MODIFIERS = {
        1: 1.2,   # Top pod (top performers)
        2: 1.0,   # Middle pod
        3: 0.8,   # Bottom pod
    }

    # ========================================================================
    # Main Point Calculation Method
    # ========================================================================

    def calculate_points(
        self,
        session_id: int,
        user_id: int,
        rank: int,
        tournament_type_config: Optional[Dict] = None
    ) -> float:
        """
        Calculate points for a user based on their rank in a session.

        Args:
            session_id: Session ID
            user_id: User ID
            rank: Player's rank in this session (1=1st place, 2=2nd place, etc.)
            tournament_type_config: Optional tournament type config (overrides defaults)

        Returns:
            float: Points earned (can be fractional with multipliers)
        """
        session = self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            return 0.0

        # Get base points from rank
        base_points = self._get_base_points(rank, tournament_type_config)

        # Apply modifiers based on ranking_mode
        ranking_mode = session.ranking_mode or 'ALL_PARTICIPANTS'

        if ranking_mode == 'ALL_PARTICIPANTS':
            # League mode: standard points, no multipliers
            return float(base_points)

        elif ranking_mode == 'GROUP_ISOLATED':
            # Group stage: standard points (group isolation already handled by filtering)
            return float(base_points)

        elif ranking_mode == 'TIERED':
            # Knockout mode: apply tier multiplier
            return self._apply_tier_multiplier(base_points, session)

        elif ranking_mode == 'QUALIFIED_ONLY':
            # Knockout stage (qualified players): apply tier multiplier
            return self._apply_tier_multiplier(base_points, session)

        elif ranking_mode == 'PERFORMANCE_POD':
            # Swiss System: apply pod modifier
            return self._apply_pod_modifier(base_points, session)

        else:
            # Default: standard points
            return float(base_points)

    def calculate_points_batch(
        self,
        session_id: int,
        rankings: List[Tuple[int, int]],
        tournament_type_config: Optional[Dict] = None
    ) -> Dict[int, float]:
        """
        Calculate points for multiple users in a session (batch processing).

        Args:
            session_id: Session ID
            rankings: List of (user_id, rank) tuples
            tournament_type_config: Optional tournament type config

        Returns:
            Dict[user_id -> points]
        """
        points_map = {}

        for user_id, rank in rankings:
            points = self.calculate_points(
                session_id=session_id,
                user_id=user_id,
                rank=rank,
                tournament_type_config=tournament_type_config
            )
            points_map[user_id] = points

        return points_map

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_base_points(
        self,
        rank: int,
        tournament_type_config: Optional[Dict] = None
    ) -> int:
        """
        Get base points for a given rank.

        Args:
            rank: Player's rank (1=1st, 2=2nd, etc.)
            tournament_type_config: Optional config with custom point scheme

        Returns:
            int: Base points
        """
        # Check if tournament type has custom point scheme
        if tournament_type_config and 'point_scheme' in tournament_type_config:
            point_scheme = tournament_type_config['point_scheme']
            # Convert string keys to integers if needed (from JSON)
            if point_scheme and isinstance(next(iter(point_scheme.keys())), str):
                point_scheme = {int(k): v for k, v in point_scheme.items()}
        else:
            point_scheme = self.DEFAULT_RANKING_POINTS

        # Return points for this rank (default to 0 if not in scheme)
        return point_scheme.get(rank, 0)

    def _apply_tier_multiplier(
        self,
        base_points: int,
        session: SessionModel
    ) -> float:
        """
        Apply tier-based multiplier for Knockout tournaments.

        Higher rounds (finals, semi-finals) have higher multipliers.

        Args:
            base_points: Base points from rank
            session: Session model with pod_tier

        Returns:
            float: Points with multiplier applied
        """
        tier = session.pod_tier or session.tournament_round or 1

        # Get multiplier (default to 1.0 if tier not in map)
        multiplier = self.TIER_MULTIPLIERS.get(tier, 1.0)

        return float(base_points) * multiplier

    def _apply_pod_modifier(
        self,
        base_points: int,
        session: SessionModel
    ) -> float:
        """
        Apply pod-based modifier for Swiss System tournaments.

        Top performers get slight bonus, bottom performers get slight penalty.

        Args:
            base_points: Base points from rank
            session: Session model with pod_tier

        Returns:
            float: Points with modifier applied
        """
        pod_tier = session.pod_tier or 1

        # Get modifier (default to 1.0 if pod not in map)
        modifier = self.POD_MODIFIERS.get(pod_tier, 1.0)

        return float(base_points) * modifier

    # ========================================================================
    # Tournament Type Config Loading
    # ========================================================================

    def get_tournament_type_config(self, tournament_id: int) -> Optional[Dict]:
        """
        Get tournament type configuration for a tournament.

        Args:
            tournament_id: Tournament (Semester) ID

        Returns:
            Optional[Dict]: Tournament type config or None
        """
        tournament = self.db.query(Semester).filter(
            Semester.id == tournament_id
        ).first()

        if not tournament or not tournament.tournament_type_id:
            return None

        tournament_type = self.db.query(TournamentType).filter(
            TournamentType.id == tournament.tournament_type_id
        ).first()

        if not tournament_type:
            return None

        return tournament_type.config

    # ========================================================================
    # Point Validation and Summary
    # ========================================================================

    def validate_ranking(
        self,
        session_id: int,
        rankings: List[Tuple[int, int]]
    ) -> Tuple[bool, str]:
        """
        Validate that rankings are valid (no duplicate ranks, ranks start from 1).

        Args:
            session_id: Session ID
            rankings: List of (user_id, rank) tuples

        Returns:
            (is_valid, error_message)
        """
        if not rankings:
            return False, "Rankings list is empty"

        # Check for duplicate ranks
        ranks = [rank for _, rank in rankings]
        if len(ranks) != len(set(ranks)):
            return False, "Duplicate ranks detected"

        # Check that ranks are sequential starting from 1
        sorted_ranks = sorted(ranks)
        if sorted_ranks[0] != 1:
            return False, "Ranks must start from 1"

        # Check for gaps in ranking (optional - depending on requirements)
        # For now, we allow gaps (e.g., 1, 2, 4 is valid if player 3 didn't participate)

        return True, "Valid ranking"

    def get_points_summary(
        self,
        session_id: int,
        rankings: List[Tuple[int, int]]
    ) -> Dict:
        """
        Get a summary of points for a session (for display/verification).

        Args:
            session_id: Session ID
            rankings: List of (user_id, rank) tuples

        Returns:
            Dict with summary information
        """
        session = self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not session:
            return {"error": "Session not found"}

        tournament_config = self.get_tournament_type_config(session.semester_id)
        points_map = self.calculate_points_batch(
            session_id=session_id,
            rankings=rankings,
            tournament_type_config=tournament_config
        )

        return {
            "session_id": session_id,
            "session_title": session.title,
            "ranking_mode": session.ranking_mode,
            "tournament_phase": session.tournament_phase,
            "tournament_round": session.tournament_round,
            "tier": session.pod_tier or session.tournament_round,
            "points_distribution": [
                {
                    "user_id": user_id,
                    "rank": rank,
                    "points": points_map[user_id]
                }
                for user_id, rank in rankings
            ],
            "total_points_awarded": sum(points_map.values())
        }


# ============================================================================
# Tournament Type Point Scheme Examples
# ============================================================================

# Example custom point schemes that can be configured per tournament type:

POINT_SCHEME_STANDARD = {
    1: 3,
    2: 2,
    3: 1
}

POINT_SCHEME_TOP_HEAVY = {
    1: 5,
    2: 3,
    3: 2,
    4: 1
}

POINT_SCHEME_BALANCED = {
    1: 4,
    2: 3,
    3: 2,
    4: 1,
    5: 0.5
}

POINT_SCHEME_PARTICIPATION = {
    # Everyone who participates gets at least 1 point
    1: 5,
    2: 4,
    3: 3,
    4: 2,
    5: 1,
    # Default for any rank: 1 point
}
