"""
Individual Ranking Session Finalizer

Handles finalization of INDIVIDUAL_RANKING sessions with multiple rounds.
Extracted from match_results.py as part of P2 decomposition.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
import json

from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.services.tournament.results.calculators import RankingAggregator  # DEPRECATED: Use RankingService instead
from app.services.tournament.ranking.ranking_service import RankingService
from app.services.tournament.leaderboard_service import (
    get_or_create_ranking,
    calculate_ranks
)


class SessionFinalizer:
    """
    Finalize INDIVIDUAL_RANKING session and calculate final rankings.

    Responsibilities:
    1. Validate all rounds are completed
    2. Aggregate results across all rounds
    3. Calculate final rankings (performance-based and wins-based)
    4. Save final rankings to session.game_results
    5. Update TournamentRanking table
    """

    def __init__(self, db: Session):
        """
        Initialize finalizer with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.ranking_aggregator = RankingAggregator()  # DEPRECATED: Kept for backward compatibility
        self.ranking_service = RankingService()  # ✅ NEW: Modern strategy-based ranking

    def validate_all_rounds_completed(
        self,
        rounds_data: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate that all rounds are completed.

        Args:
            rounds_data: Session rounds_data JSONB field

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if all rounds completed
            - error_message: Error message if not valid, empty string otherwise
        """
        total_rounds = rounds_data.get('total_rounds', 1)
        completed_rounds = rounds_data.get('completed_rounds', 0)

        if completed_rounds < total_rounds:
            remaining = total_rounds - completed_rounds
            return False, f"Cannot finalize: {remaining} rounds remaining. All rounds must be completed first."

        return True, ""

    def update_tournament_rankings(
        self,
        tournament_id: int,
        derived_rankings: List[Dict[str, Any]]
    ) -> None:
        """
        Update TournamentRanking table with final results.

        Args:
            tournament_id: Tournament ID
            derived_rankings: List of ranking entries with user_id and final_value
        """
        for ranking_entry in derived_rankings:
            user_id = ranking_entry["user_id"]
            final_value = ranking_entry["final_value"]

            # Get or create ranking entry
            ranking = get_or_create_ranking(
                db=self.db,
                tournament_id=tournament_id,
                user_id=user_id,
                participant_type="INDIVIDUAL"
            )

            # Store final aggregate value in points field
            ranking.points = Decimal(str(final_value))

        self.db.flush()

        # Recalculate ranks across entire tournament
        calculate_ranks(self.db, tournament_id)

    def check_all_sessions_finalized(
        self,
        tournament_id: int,
        current_session_id: int
    ) -> tuple[bool, int]:
        """
        Check if all tournament sessions are finalized.

        Args:
            tournament_id: Tournament ID
            current_session_id: Current session ID (to exclude from count)

        Returns:
            Tuple of (all_finalized, unfinalized_count)
        """
        all_sessions = self.db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).all()

        unfinalized_sessions = [
            s for s in all_sessions
            if not s.game_results
        ]

        return len(unfinalized_sessions) == 0, len(unfinalized_sessions)

    def finalize(
        self,
        tournament: Semester,
        session: SessionModel,
        recorded_by_id: int,
        recorded_by_name: str
    ) -> Dict[str, Any]:
        """
        Finalize INDIVIDUAL_RANKING session and calculate final rankings.

        Args:
            tournament: Tournament (Semester) instance
            session: Session instance to finalize
            recorded_by_id: User ID of person finalizing
            recorded_by_name: Name of person finalizing

        Returns:
            Result dict with success status and rankings

        Raises:
            ValueError: If validation fails or already finalized

        Example result:
            {
                "success": True,
                "message": "Session finalized successfully",
                "session_id": 123,
                "tournament_id": 456,
                "final_rankings": [...],
                "performance_rankings": [...],
                "wins_rankings": [...],
                "tournament_status": "IN_PROGRESS",
                "all_sessions_finalized": False,
                "remaining_sessions": 2
            }
        """
        # ========================================
        # ✅ IDEMPOTENCY GUARD #1: Prevent duplicate finalization (session-level)
        # ========================================
        if session.game_results:
            # Session already finalized - log and reject
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"🔒 IDEMPOTENCY VIOLATION (Session Level): Attempted to re-finalize session {session.id} "
                f"in tournament {tournament.id}. "
                f"Session already finalized at {json.loads(session.game_results).get('recorded_at', 'unknown')}. "
                f"Rejecting duplicate finalization request by user {recorded_by_id}."
            )
            raise ValueError(
                f"Session {session.id} is already finalized. "
                f"Cannot finalize the same session multiple times. "
                f"Use rollback endpoint if you need to reset."
            )

        # ========================================
        # ✅ IDEMPOTENCY GUARD #2: Prevent duplicate finalization (tournament_rankings-level)
        # ========================================
        # Check if tournament_rankings already exist for this tournament
        # This prevents DUAL FINALIZATION PATH bug where both sandbox and production
        # write to tournament_rankings table.
        from app.models.tournament_ranking import TournamentRanking

        existing_rankings = self.db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament.id
        ).count()

        if existing_rankings > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"🔒 IDEMPOTENCY VIOLATION (TournamentRanking Level): Attempted to finalize session {session.id} "
                f"but {existing_rankings} tournament_rankings already exist for tournament {tournament.id}. "
                f"Rejecting duplicate finalization. Existing rankings indicate tournament was already finalized."
            )
            raise ValueError(
                f"Tournament {tournament.id} already has {existing_rankings} ranking(s). "
                f"Cannot finalize session - tournament rankings already exist. "
                f"This prevents duplicate finalization from multiple code paths."
            )

        # Validate session type
        if session.match_format != "INDIVIDUAL_RANKING":
            raise ValueError(
                f"Finalization only supported for INDIVIDUAL_RANKING sessions "
                f"(current format: {session.match_format})"
            )

        if tournament.format != "INDIVIDUAL_RANKING":
            raise ValueError(
                f"Finalization only supported for INDIVIDUAL_RANKING tournaments "
                f"(current format: {tournament.format})"
            )

        # Get rounds data
        rounds_data = session.rounds_data or {}
        total_rounds = rounds_data.get('total_rounds', 1)
        round_results = rounds_data.get('round_results', {})

        # Validate all rounds completed
        is_valid, error_message = self.validate_all_rounds_completed(rounds_data)
        if not is_valid:
            raise ValueError(error_message)

        # Get tournament configuration
        ranking_direction = tournament.ranking_direction or "ASC"
        scoring_type = tournament.scoring_type or "TIME_BASED"
        measurement_unit = tournament.measurement_unit or "units"

        # ========================================
        # ✅ AUDIT LOG: Record finalization details
        # ========================================
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"🏁 FINALIZATION STARTED: "
            f"session_id={session.id}, "
            f"tournament_id={tournament.id}, "
            f"scoring_type={scoring_type}, "
            f"ranking_direction={ranking_direction}, "
            f"measurement_unit={measurement_unit}, "
            f"initiated_by_user_id={recorded_by_id}, "
            f"initiated_by_name={recorded_by_name}, "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

        # ✅ NEW: Use Strategy Pattern for ranking calculation
        # Build participants list from round_results
        unique_user_ids = set()
        for round_num, results_dict in round_results.items():
            for user_id_str in results_dict.keys():
                unique_user_ids.add(int(user_id_str))

        participants = [{"user_id": user_id} for user_id in unique_user_ids]

        # Calculate rankings using appropriate strategy
        rank_groups = self.ranking_service.calculate_rankings(
            scoring_type=scoring_type,
            round_results=round_results,
            participants=participants
        )

        # Convert to legacy format for backward compatibility
        performance_rankings, wins_rankings = self.ranking_service.convert_to_legacy_format(
            rank_groups=rank_groups,
            measurement_unit=measurement_unit
        )

        # Use performance ranking as primary
        derived_rankings = performance_rankings

        # Save to session.game_results
        recorded_at = datetime.utcnow().isoformat()
        game_results = {
            "recorded_at": recorded_at,
            "recorded_by": recorded_by_id,
            "recorded_by_name": recorded_by_name,
            "tournament_format": "INDIVIDUAL_RANKING",
            "scoring_type": scoring_type,
            "measurement_unit": measurement_unit,
            "ranking_direction": ranking_direction,
            "total_rounds": total_rounds,
            "aggregation_method": "BEST_VALUE",
            "rounds_data": rounds_data,
            # Dual ranking system
            "derived_rankings": derived_rankings,
            "performance_rankings": performance_rankings,
            "wins_rankings": wins_rankings
        }

        session.game_results = json.dumps(game_results)

        # Update tournament rankings
        self.update_tournament_rankings(tournament.id, derived_rankings)

        self.db.commit()
        self.db.refresh(session)

        # ✅ AUDIT LOG: Record successful finalization
        logger.info(
            f"✅ FINALIZATION COMPLETED: "
            f"session_id={session.id}, "
            f"tournament_id={tournament.id}, "
            f"players_ranked={len(derived_rankings)}, "
            f"scoring_type={scoring_type}, "
            f"completed_at={datetime.utcnow().isoformat()}"
        )

        # Check if all sessions finalized
        all_finalized, unfinalized_count = self.check_all_sessions_finalized(
            tournament.id, session.id
        )

        if all_finalized:
            return {
                "success": True,
                "message": "Session finalized! All sessions completed. Awaiting admin closure.",
                "session_id": session.id,
                "tournament_id": tournament.id,
                "final_rankings": derived_rankings,
                "performance_rankings": performance_rankings,
                "wins_rankings": wins_rankings,
                "tournament_status": tournament.tournament_status,
                "all_sessions_finalized": True
            }

        return {
            "success": True,
            "message": f"Session finalized successfully! {unfinalized_count} sessions remaining.",
            "session_id": session.id,
            "tournament_id": tournament.id,
            "final_rankings": derived_rankings,
            "performance_rankings": performance_rankings,
            "wins_rankings": wins_rankings,
            "tournament_status": tournament.tournament_status,
            "all_sessions_finalized": False,
            "remaining_sessions": unfinalized_count
        }


# Export main class
__all__ = ["SessionFinalizer"]
