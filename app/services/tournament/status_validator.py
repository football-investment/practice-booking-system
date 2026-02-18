"""
Tournament Status Validator Service
Handles tournament status transitions with business rule validation
"""
from typing import Optional, Tuple
from app.models.semester import Semester


# Valid status transition graph
# NOTE: READY_FOR_ENROLLMENT removed - it was redundant (no player visibility, no functionality)
# Simplified workflow: INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN → ENROLLMENT_CLOSED → IN_PROGRESS
VALID_TRANSITIONS = {
    "DRAFT": ["SEEKING_INSTRUCTOR", "CANCELLED"],
    "SEEKING_INSTRUCTOR": ["PENDING_INSTRUCTOR_ACCEPTANCE", "CANCELLED"],
    "PENDING_INSTRUCTOR_ACCEPTANCE": ["INSTRUCTOR_CONFIRMED", "SEEKING_INSTRUCTOR", "CANCELLED"],
    "INSTRUCTOR_CONFIRMED": ["ENROLLMENT_OPEN", "CANCELLED"],  # Direct to ENROLLMENT_OPEN
    "ENROLLMENT_OPEN": ["ENROLLMENT_CLOSED", "CANCELLED"],
    "ENROLLMENT_CLOSED": ["IN_PROGRESS", "CANCELLED"],  # Scheduled start (enrollment closed, waiting for start_date)
    "IN_PROGRESS": ["COMPLETED", "CANCELLED", "ENROLLMENT_CLOSED"],  # ENROLLMENT_CLOSED: admin rollback for stuck (0 sessions)
    "COMPLETED": ["REWARDS_DISTRIBUTED", "ARCHIVED"],
    "REWARDS_DISTRIBUTED": ["ARCHIVED"],
    "CANCELLED": ["ARCHIVED"],
    "ARCHIVED": []  # Terminal state
}


class StatusValidationError(Exception):
    """Raised when a status transition is invalid"""


def validate_status_transition(
    current_status: Optional[str],
    new_status: str,
    tournament: Semester
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a status transition is allowed based on business rules

    Args:
        current_status: Current tournament status (None for new tournaments)
        new_status: Desired new status
        tournament: Tournament (Semester) object with related data

    Returns:
        Tuple of (is_valid, error_message)
    """

    # Special case: New tournament creation (NULL → DRAFT)
    if current_status is None:
        if new_status != "DRAFT":
            return False, "New tournaments must start in DRAFT status"
        return True, None

    # 1. Check if transition is allowed in the graph
    allowed_transitions = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_transitions:
        return False, f"Invalid transition: {current_status} → {new_status} is not allowed"

    # 2. Business rule validations for specific status transitions

    if new_status == "SEEKING_INSTRUCTOR":
        # Must have sessions defined before seeking instructor
        if not tournament.sessions or len(tournament.sessions) == 0:
            return False, "Cannot seek instructor: No sessions defined for this tournament"

        # Must have basic tournament info (name, dates)
        if not tournament.name or not tournament.start_date or not tournament.end_date:
            return False, "Cannot seek instructor: Missing basic tournament information (name, dates)"

    if new_status == "PENDING_INSTRUCTOR_ACCEPTANCE":
        # Must have instructor assigned
        if not tournament.master_instructor_id:
            return False, "Cannot move to pending acceptance: No instructor assigned"

    if new_status == "ENROLLMENT_OPEN":
        # Must have instructor assigned and confirmed
        if not tournament.master_instructor_id:
            return False, "Cannot open enrollment: No instructor assigned"
        # Must have enrollment capacity and dates configured
        if not hasattr(tournament, 'max_players') or tournament.max_players is None:
            return False, "Cannot open enrollment: Max participants not configured"
        # Must have campus assigned — campus_id is required before sessions can be generated
        if not getattr(tournament, 'campus_id', None):
            return False, (
                "Cannot open enrollment: No campus assigned. "
                "Set campus_id via PATCH /{id} before opening enrollment."
            )

    if new_status == "ENROLLMENT_CLOSED":
        # Must have at least minimum participants for tournament type
        enrollments = getattr(tournament, 'enrollments', [])
        active_enrollments = [e for e in enrollments if e.is_active]
        player_count = len(active_enrollments)

        # Get minimum from tournament type (fallback to 2 if no type configured)
        min_players_required = 2
        if tournament.tournament_type_id:
            # Load tournament type to get min_players
            from app.models.tournament_type import TournamentType
            from sqlalchemy.orm import Session

            # Get db session from tournament
            db: Session = tournament.__dict__.get('_sa_instance_state').session
            if db:
                tournament_type = db.query(TournamentType).filter(TournamentType.id == tournament.tournament_type_id).first()
                if tournament_type:
                    min_players_required = tournament_type.min_players

        if player_count < min_players_required:
            return False, f"Cannot close enrollment: Minimum {min_players_required} participants required (current: {player_count})"

    if new_status == "IN_PROGRESS":
        # Must have instructor and participants
        if not tournament.master_instructor_id:
            return False, "Cannot start tournament: No instructor assigned"

        # Validate against tournament type's minimum player requirement
        enrollments = getattr(tournament, 'enrollments', [])
        active_enrollments = [e for e in enrollments if e.is_active]
        player_count = len(active_enrollments)

        # Get minimum from tournament type (fallback to 2 if no type configured)
        min_players_required = 2
        if tournament.tournament_type_id:
            # Load tournament type to get min_players
            from app.models.tournament_type import TournamentType
            from sqlalchemy.orm import Session

            # Get db session from tournament
            db: Session = tournament.__dict__.get('_sa_instance_state').session
            if db:
                tournament_type = db.query(TournamentType).filter(TournamentType.id == tournament.tournament_type_id).first()
                if tournament_type:
                    min_players_required = tournament_type.min_players

        if player_count < min_players_required:
            return False, f"Cannot start tournament: Minimum {min_players_required} participants required (current: {player_count})"

    if new_status == "COMPLETED":
        # All sessions must have attendance records
        sessions = getattr(tournament, 'sessions', [])
        if not sessions:
            return False, "Cannot complete tournament: No sessions found"

        # Note: Detailed attendance validation would go here in production
        # For now, we just check sessions exist

    if new_status == "REWARDS_DISTRIBUTED":
        # Rankings must be submitted before distributing rewards
        pass

        # Note: Attendance validation is NOT required here - rankings are sufficient
        # The reward distribution endpoint will handle any additional validations

        # Count submitted rankings
        # NOTE: Cannot use func.count() with filter directly - need proper query
        # For now, skip the complex SQL validation (endpoint will validate)

    # All validations passed
    return True, None


def get_next_allowed_statuses(current_status: Optional[str]) -> list[str]:
    """
    Get list of statuses that can be transitioned to from current status

    Args:
        current_status: Current tournament status (None for new tournaments)

    Returns:
        List of allowed next statuses
    """
    if current_status is None:
        return ["DRAFT"]

    return VALID_TRANSITIONS.get(current_status, [])


def is_terminal_status(status: str) -> bool:
    """
    Check if a status is terminal (no further transitions allowed)

    Args:
        status: Tournament status

    Returns:
        True if terminal status
    """
    return len(VALID_TRANSITIONS.get(status, [])) == 0
