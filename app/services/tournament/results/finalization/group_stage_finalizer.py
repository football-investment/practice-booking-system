"""
Group Stage Finalizer

Handles finalization of group stage and transition to knockout stage.
Extracted from match_results.py as part of P2 decomposition.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.services.tournament.results.calculators import (
    StandingsCalculator,
    AdvancementCalculator
)


class GroupStageFinalizer:
    """
    Finalize group stage and calculate standings.

    Responsibilities:
    1. Validate all group stage matches are completed
    2. Calculate group standings
    3. Determine qualified participants for knockout stage
    4. Update knockout session participants with seeding
    5. Save snapshot of group stage standings
    """

    def __init__(self, db: Session):
        """
        Initialize finalizer with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.standings_calculator = StandingsCalculator(db)
        self.advancement_calculator = AdvancementCalculator(db)

    def get_group_sessions(self, tournament_id: int) -> List[SessionModel]:
        """
        Get all group stage sessions for tournament.

        Args:
            tournament_id: Tournament ID

        Returns:
            List of group stage sessions
        """
        return self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.tournament_phase == "Group Stage"
        ).all()

    def get_knockout_sessions(self, tournament_id: int) -> List[SessionModel]:
        """
        Get all knockout stage sessions for tournament.

        Args:
            tournament_id: Tournament ID

        Returns:
            List of knockout stage sessions sorted by round and ID
        """
        return self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.tournament_phase == "Knockout Stage"
        ).order_by(SessionModel.tournament_round, SessionModel.id).all()

    def check_all_matches_completed(
        self,
        sessions: List[SessionModel]
    ) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Check if all matches are completed.

        Args:
            sessions: List of sessions to check

        Returns:
            Tuple of (all_completed, incomplete_matches)
            - all_completed: True if all matches have results
            - incomplete_matches: List of dicts with session_id and title
        """
        incomplete_matches = [
            {"session_id": s.id, "title": s.title}
            for s in sessions
            if s.game_results is None
        ]

        return len(incomplete_matches) == 0, incomplete_matches

    def create_snapshot(
        self,
        group_standings: Dict[str, List[Dict[str, Any]]],
        qualified_participants: List[int]
    ) -> Dict[str, Any]:
        """
        Create snapshot of group stage standings.

        Args:
            group_standings: Dict mapping group_id to standings list
            qualified_participants: List of qualified user_ids

        Returns:
            Snapshot data dict
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "phase": "group_stage_complete",
            "group_standings": group_standings,
            "qualified_participants": qualified_participants,
            "total_groups": len(group_standings),
            "total_qualified": len(qualified_participants),
            "qualification_rule": "top_2_per_group"
        }

    def finalize(
        self,
        tournament: Semester
    ) -> Dict[str, Any]:
        """
        Finalize group stage and calculate standings.

        Args:
            tournament: Tournament (Semester) instance

        Returns:
            Result dict with success status and standings data

        Example result:
            {
                "success": True,
                "message": "Group stage finalized successfully",
                "group_standings": {...},
                "qualified_participants": [1, 2, 3, 4],
                "knockout_sessions_updated": 2,
                "snapshot_saved": True
            }

        Or if incomplete:
            {
                "success": False,
                "message": "2 group stage matches are not completed yet",
                "incomplete_matches": [...]
            }
        """
        # Get all group stage sessions
        group_sessions = self.get_group_sessions(tournament.id)

        if not group_sessions:
            return {
                "success": False,
                "message": "No group stage matches found"
            }

        # Check if all group matches are completed
        all_completed, incomplete_matches = self.check_all_matches_completed(
            group_sessions
        )

        if not all_completed:
            return {
                "success": False,
                "message": f"{len(incomplete_matches)} group stage matches are not completed yet",
                "incomplete_matches": incomplete_matches
            }

        # Calculate group standings
        group_standings = self.standings_calculator.calculate_group_standings(
            group_sessions
        )

        # Get knockout sessions
        knockout_sessions = self.get_knockout_sessions(tournament.id)

        # Calculate advancement and apply seeding
        qualified_participants, sessions_updated = (
            self.advancement_calculator.calculate_advancement(
                group_standings,
                knockout_sessions,
                top_n_per_group=2
            )
        )

        # Create and save snapshot
        snapshot_data = self.create_snapshot(group_standings, qualified_participants)
        tournament.enrollment_snapshot = snapshot_data

        self.db.commit()

        return {
            "success": True,
            "message": "Group stage finalized successfully! Snapshot saved.",
            "group_standings": group_standings,
            "qualified_participants": qualified_participants,
            "knockout_sessions_updated": sessions_updated,
            "snapshot_saved": True
        }


# Export main class
__all__ = ["GroupStageFinalizer"]
