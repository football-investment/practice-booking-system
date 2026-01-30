"""
Tournament Session Generation Validator

Validates whether a tournament is ready for session generation.
"""
from typing import Tuple
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.repositories.tournament_repository import TournamentRepository


class GenerationValidator:
    """
    Validates tournament readiness for session generation
    """

    def __init__(self, db: Session):
        self.db = db
        self.tournament_repo = TournamentRepository(db)

    def can_generate_sessions(self, tournament_id: int) -> Tuple[bool, str]:
        """
        Check if tournament is ready for session generation

        Returns:
            (can_generate, reason)
        """
        tournament = self.tournament_repo.get_optional(tournament_id)
        if not tournament:
            return False, "Tournament not found"

        # Check if already generated
        if tournament.sessions_generated:
            return False, f"Sessions already generated at {tournament.sessions_generated_at}"

        # ✅ Check format-specific requirements
        if tournament.format == "HEAD_TO_HEAD":
            # HEAD_TO_HEAD requires tournament type
            if not tournament.tournament_type_id:
                return False, "HEAD_TO_HEAD tournaments require a tournament type (Swiss, League, Knockout, etc.)"
        elif tournament.format == "INDIVIDUAL_RANKING":
            # INDIVIDUAL_RANKING should NOT have tournament type
            if tournament.tournament_type_id is not None:
                return False, "INDIVIDUAL_RANKING tournaments cannot have a tournament type"
        else:
            return False, f"Invalid tournament format: {tournament.format}"

        # Check if enrollment is closed (tournament status must be IN_PROGRESS or later)
        if tournament.tournament_status not in ["IN_PROGRESS", "COMPLETED"]:
            return False, f"Tournament not ready for session generation. Current status: {tournament.tournament_status}. Sessions can only be generated when status is IN_PROGRESS."

        # Check if there are enough enrolled players
        active_enrollment_count = self.db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
        ).count()

        # Different minimum player requirements based on format
        if tournament.format == "INDIVIDUAL_RANKING":
            min_players = 2  # INDIVIDUAL_RANKING needs at least 2 players
        else:
            min_players = 4  # HEAD_TO_HEAD tournaments typically need at least 4

        if active_enrollment_count < min_players:
            return False, f"Not enough players enrolled. Need at least {min_players}, have {active_enrollment_count}"

        return True, "Ready for session generation"
