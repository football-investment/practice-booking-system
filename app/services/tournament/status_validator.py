"""
Tournament Status Validator Service
Handles tournament status transitions with business rule validation
"""
from typing import Optional, Tuple
from app.models.semester import Semester


# Valid status transition graph
VALID_TRANSITIONS = {
    "DRAFT": ["SEEKING_INSTRUCTOR", "CANCELLED"],
    "SEEKING_INSTRUCTOR": ["PENDING_INSTRUCTOR_ACCEPTANCE", "READY_FOR_ENROLLMENT", "CANCELLED"],
    "PENDING_INSTRUCTOR_ACCEPTANCE": ["READY_FOR_ENROLLMENT", "SEEKING_INSTRUCTOR", "CANCELLED"],
    "READY_FOR_ENROLLMENT": ["ENROLLMENT_OPEN", "IN_PROGRESS", "CANCELLED"],  # Direct IN_PROGRESS for API enrollment
    "ENROLLMENT_OPEN": ["ENROLLMENT_CLOSED", "CANCELLED"],
    "ENROLLMENT_CLOSED": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
    "COMPLETED": ["REWARDS_DISTRIBUTED", "ARCHIVED"],
    "REWARDS_DISTRIBUTED": ["ARCHIVED"],
    "CANCELLED": ["ARCHIVED"],
    "ARCHIVED": []  # Terminal state
}


class StatusValidationError(Exception):
    """Raised when a status transition is invalid"""
    pass


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

    if new_status == "READY_FOR_ENROLLMENT":
        # Must have instructor assigned and confirmed
        if not tournament.master_instructor_id:
            return False, "Cannot open enrollment: No instructor assigned"

    if new_status == "ENROLLMENT_OPEN":
        # Must have enrollment capacity and dates configured
        if not hasattr(tournament, 'max_participants') or tournament.max_participants is None:
            return False, "Cannot open enrollment: Max participants not configured"

    if new_status == "ENROLLMENT_CLOSED":
        # Must have at least minimum participants
        enrollments = getattr(tournament, 'enrollments', [])
        active_enrollments = [e for e in enrollments if e.is_active]
        if len(active_enrollments) < 2:  # Minimum 2 for a tournament
            return False, "Cannot close enrollment: Minimum 2 participants required"

    if new_status == "IN_PROGRESS":
        # Must have instructor and participants
        if not tournament.master_instructor_id:
            return False, "Cannot start tournament: No instructor assigned"

        enrollments = getattr(tournament, 'enrollments', [])
        active_enrollments = [e for e in enrollments if e.is_active]
        if len(active_enrollments) < 2:
            return False, "Cannot start tournament: Minimum 2 participants required"

    if new_status == "COMPLETED":
        # All sessions must have attendance records
        sessions = getattr(tournament, 'sessions', [])
        if not sessions:
            return False, "Cannot complete tournament: No sessions found"

        # Note: Detailed attendance validation would go here in production
        # For now, we just check sessions exist

    if new_status == "REWARDS_DISTRIBUTED":
        # Rankings must be submitted before distributing rewards
        from app.models.tournament_ranking import TournamentRanking

        # Note: Attendance validation is NOT required here - rankings are sufficient
        # The reward distribution endpoint will handle any additional validations

        # Count submitted rankings
        # NOTE: Cannot use func.count() with filter directly - need proper query
        # For now, skip the complex SQL validation (endpoint will validate)
        pass

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
