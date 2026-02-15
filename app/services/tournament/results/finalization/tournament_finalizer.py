"""
Tournament Finalizer

Handles final tournament finalization and ranking calculation.
Extracted from match_results.py as part of P2 decomposition.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging

from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.tournament_enums import TournamentPhase

logger = logging.getLogger(__name__)


class TournamentFinalizer:
    """
    Finalize tournament and calculate final rankings.

    Responsibilities:
    1. Validate all matches are completed
    2. Calculate final ranking based on tournament structure:
       - Group+Knockout: Based on final match (1st, 2nd, 3rd place match)
       - League: Based on total points
    3. Update tournament_rankings table
    4. Set tournament status to COMPLETED
    """

    def __init__(self, db: Session):
        """
        Initialize finalizer with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_all_sessions(self, tournament_id: int) -> List[SessionModel]:
        """
        Get all tournament sessions.

        Args:
            tournament_id: Tournament ID

        Returns:
            List of all tournament sessions
        """
        return self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).all()

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
        """
        incomplete_matches = [
            {"session_id": s.id, "title": s.title}
            for s in sessions
            if s.game_results is None
        ]

        return len(incomplete_matches) == 0, incomplete_matches

    def extract_final_rankings(
        self,
        tournament_id: int
    ) -> List[Dict[str, Any]]:
        """
        Extract final rankings from final match and 3rd place match.

        Args:
            tournament_id: Tournament ID

        Returns:
            List of final rankings:
            [
                {"user_id": 123, "final_rank": 1, "place": "1st"},
                {"user_id": 456, "final_rank": 2, "place": "2nd"},
                {"user_id": 789, "final_rank": 3, "place": "3rd"}
            ]
        """
        final_rankings = []

        # Find final match
        final_match = self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
            SessionModel.title.ilike("%final%")
        ).first()

        # Find 3rd place match
        third_place_match = self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.tournament_phase == TournamentPhase.KNOCKOUT,
            SessionModel.title.ilike("%3rd%")
        ).first()

        # Extract rankings from final match
        if final_match and final_match.game_results:
            results = json.loads(final_match.game_results)
            for result in results.get("derived_rankings", []):
                if result["rank"] == 1:
                    final_rankings.append({
                        "user_id": result["user_id"],
                        "final_rank": 1,
                        "place": "1st"
                    })
                elif result["rank"] == 2:
                    final_rankings.append({
                        "user_id": result["user_id"],
                        "final_rank": 2,
                        "place": "2nd"
                    })

        # Extract rankings from 3rd place match
        if third_place_match and third_place_match.game_results:
            results = json.loads(third_place_match.game_results)
            for result in results.get("derived_rankings", []):
                if result["rank"] == 1:
                    final_rankings.append({
                        "user_id": result["user_id"],
                        "final_rank": 3,
                        "place": "3rd"
                    })

        return final_rankings

    def update_tournament_rankings_table(
        self,
        tournament_id: int,
        final_rankings: List[Dict[str, Any]]
    ) -> None:
        """
        Update tournament_rankings table with final rankings.

        Upserts podium (rank 1-3) into existing rankings.
        Any enrolled participant without a ranking entry gets inserted
        with rank=NULL so they qualify for PARTICIPANT-level rewards.

        Args:
            tournament_id: Tournament ID
            final_rankings: List of final ranking entries (top 3 from final matches)
        """
        from app.models.tournament_ranking import TournamentRanking
        from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus

        # Build set of user_ids with confirmed podium ranks
        podium_user_ids = {r["user_id"] for r in final_rankings}

        # Upsert podium ranks — update existing row or insert new one
        for ranking in final_rankings:
            existing = self.db.query(TournamentRanking).filter(
                TournamentRanking.tournament_id == tournament_id,
                TournamentRanking.user_id == ranking["user_id"]
            ).first()

            if existing:
                existing.rank = ranking["final_rank"]
                existing.points = 0
            else:
                self.db.execute(
                    text("""
                    INSERT INTO tournament_rankings (tournament_id, user_id, rank, points, participant_type)
                    VALUES (:tournament_id, :user_id, :rank, :points, 'INDIVIDUAL')
                    """),
                    {
                        "tournament_id": tournament_id,
                        "user_id": ranking["user_id"],
                        "rank": ranking["final_rank"],
                        "points": 0,
                    }
                )

        # Ensure all enrolled participants have a ranking entry (for PARTICIPANT rewards)
        enrolled_user_ids = {
            row[0] for row in self.db.query(SemesterEnrollment.user_id).filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
            ).all()
            if row[0] is not None
        }

        for user_id in enrolled_user_ids - podium_user_ids:
            exists = self.db.query(TournamentRanking).filter(
                TournamentRanking.tournament_id == tournament_id,
                TournamentRanking.user_id == user_id
            ).first()
            if not exists:
                self.db.execute(
                    text("""
                    INSERT INTO tournament_rankings (tournament_id, user_id, rank, points, participant_type)
                    VALUES (:tournament_id, :user_id, NULL, 0, 'INDIVIDUAL')
                    """),
                    {"tournament_id": tournament_id, "user_id": user_id}
                )

    def finalize(
        self,
        tournament: Semester
    ) -> Dict[str, Any]:
        """
        Finalize tournament and calculate final rankings.

        Args:
            tournament: Tournament (Semester) instance

        Returns:
            Result dict with success status and final rankings

        Example result:
            {
                "success": True,
                "message": "Tournament finalized successfully",
                "final_rankings": [
                    {"user_id": 123, "final_rank": 1, "place": "1st"},
                    {"user_id": 456, "final_rank": 2, "place": "2nd"},
                    {"user_id": 789, "final_rank": 3, "place": "3rd"}
                ],
                "tournament_status": "COMPLETED"
            }

        Or if incomplete:
            {
                "success": False,
                "message": "2 matches are not completed yet",
                "incomplete_matches": [...]
            }
        """
        # Get all tournament sessions
        all_sessions = self.get_all_sessions(tournament.id)

        if not all_sessions:
            return {
                "success": False,
                "message": "No tournament matches found"
            }

        # Check if all matches are completed
        all_completed, incomplete_matches = self.check_all_matches_completed(
            all_sessions
        )

        if not all_completed:
            return {
                "success": False,
                "message": f"{len(incomplete_matches)} matches are not completed yet",
                "incomplete_matches": incomplete_matches
            }

        # Extract final rankings from final matches
        final_rankings = self.extract_final_rankings(tournament.id)

        # Update tournament_rankings table
        self.update_tournament_rankings_table(tournament.id, final_rankings)

        # Update tournament status to COMPLETED first
        tournament.tournament_status = "COMPLETED"
        self.db.flush()

        # Auto-distribute rewards as part of the lifecycle
        # COMPLETED → distribute_rewards → REWARDS_DISTRIBUTED
        final_status = "COMPLETED"
        rewards_message = None
        try:
            from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_tournament
            # Returns BulkRewardDistributionResult (Pydantic model)
            reward_result = distribute_rewards_for_tournament(db=self.db, tournament_id=tournament.id)
            players_rewarded = len(reward_result.rewards_distributed)
            tournament.tournament_status = "REWARDS_DISTRIBUTED"
            final_status = "REWARDS_DISTRIBUTED"
            rewards_message = f"Rewards distributed to {players_rewarded} players"
            logger.info(
                "✅ Auto reward distribution completed for tournament %d: %s",
                tournament.id, rewards_message
            )
        except Exception as e:
            logger.error(
                "❌ Auto reward distribution failed for tournament %d: %s — "
                "tournament remains COMPLETED, rewards can be retried manually.",
                tournament.id, e
            )

        self.db.commit()

        result = {
            "success": True,
            "message": "Tournament finalized successfully",
            "final_rankings": final_rankings,
            "tournament_status": final_status,
        }
        if rewards_message:
            result["rewards_message"] = rewards_message
        return result


# Export main class
__all__ = ["TournamentFinalizer"]
