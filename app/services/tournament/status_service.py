"""
Tournament Status Service

Centralized service for managing tournament status transitions and validation.
Handles status changes, history tracking, and workflow enforcement.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from ...models.semester import Semester
from ...models.user import User


# ============================================================================
# TOURNAMENT STATUS CONSTANTS
# ============================================================================

# Valid tournament statuses
VALID_STATUSES = [
    "SEEKING_INSTRUCTOR",
    "PENDING_INSTRUCTOR_ACCEPTANCE",
    "INSTRUCTOR_CONFIRMED",
    "READY_FOR_ENROLLMENT",
    "OPEN_FOR_ENROLLMENT",
    "IN_PROGRESS",
    "CLOSED",
    "COMPLETED",
    "CANCELLED"
]

# Valid status transitions (from_status -> list of valid next statuses)
VALID_TRANSITIONS = {
    "SEEKING_INSTRUCTOR": ["PENDING_INSTRUCTOR_ACCEPTANCE", "INSTRUCTOR_CONFIRMED", "CANCELLED"],
    "PENDING_INSTRUCTOR_ACCEPTANCE": ["INSTRUCTOR_CONFIRMED", "SEEKING_INSTRUCTOR", "CANCELLED"],
    "INSTRUCTOR_CONFIRMED": ["READY_FOR_ENROLLMENT", "SEEKING_INSTRUCTOR", "CANCELLED"],
    "READY_FOR_ENROLLMENT": ["OPEN_FOR_ENROLLMENT", "IN_PROGRESS", "CANCELLED"],
    "OPEN_FOR_ENROLLMENT": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["CLOSED", "COMPLETED", "CANCELLED"],
    "CLOSED": ["COMPLETED"],
    "COMPLETED": [],  # Terminal state
    "CANCELLED": []   # Terminal state
}


# ============================================================================
# STATUS VALIDATION
# ============================================================================

def is_valid_status(status: str) -> bool:
    """
    Check if a status is valid.

    Args:
        status: Status string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return status in VALID_STATUSES


def can_transition(from_status: str, to_status: str) -> bool:
    """
    Check if a status transition is valid.

    Args:
        from_status: Current status
        to_status: Desired new status

    Returns:
        bool: True if transition is allowed, False otherwise
    """
    if from_status not in VALID_TRANSITIONS:
        return False

    return to_status in VALID_TRANSITIONS[from_status]


def get_valid_next_statuses(current_status: str) -> list[str]:
    """
    Get list of valid next statuses for a given current status.

    Args:
        current_status: Current tournament status

    Returns:
        List of valid next status strings
    """
    return VALID_TRANSITIONS.get(current_status, [])


# ============================================================================
# STATUS CHANGE OPERATIONS
# ============================================================================

def record_status_change(
    db: Session,
    tournament_id: int,
    old_status: Optional[str],
    new_status: str,
    changed_by: int,
    reason: Optional[str] = None,
    metadata: Optional[dict] = None
) -> None:
    """
    Record a status change in tournament_status_history table.

    Args:
        db: Database session
        tournament_id: Tournament ID
        old_status: Previous status (None for creation)
        new_status: New status
        changed_by: User ID who made the change
        reason: Optional reason for change
        metadata: Optional metadata dict

    Note:
        Does NOT commit - caller must manage transaction
    """
    # Convert metadata dict to JSON string if provided
    metadata_json = json.dumps(metadata) if metadata is not None else None

    db.execute(
        text("""
        INSERT INTO tournament_status_history
        (tournament_id, old_status, new_status, changed_by, reason, metadata)
        VALUES (:tournament_id, :old_status, :new_status, :changed_by, :reason, :metadata)
        """),
        {
            "tournament_id": tournament_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "reason": reason,
            "metadata": metadata_json
        }
    )


def change_tournament_status(
    db: Session,
    tournament: Semester,
    new_status: str,
    changed_by: int,
    reason: Optional[str] = None,
    metadata: Optional[dict] = None,
    validate_transition: bool = True
) -> bool:
    """
    Change tournament status with validation and history tracking.

    Args:
        db: Database session
        tournament: Tournament (Semester) object
        new_status: New status to set
        changed_by: User ID making the change
        reason: Optional reason for change
        metadata: Optional metadata dict
        validate_transition: If True, validate transition is allowed (default: True)

    Returns:
        bool: True if status changed successfully, False if transition invalid

    Raises:
        ValueError: If new_status is invalid or transition not allowed

    Note:
        Does NOT commit - caller must manage transaction
    """
    # Validate new status
    if not is_valid_status(new_status):
        raise ValueError(f"Invalid status: {new_status}")

    # Validate transition if requested
    if validate_transition:
        current_status = tournament.tournament_status
        if not can_transition(current_status, new_status):
            raise ValueError(
                f"Invalid status transition: {current_status} -> {new_status}. "
                f"Valid next statuses: {get_valid_next_statuses(current_status)}"
            )

    # Record old status
    old_status = tournament.tournament_status

    # Update tournament status
    tournament.tournament_status = new_status
    tournament.updated_at = datetime.now(timezone.utc)

    # Record in history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        reason=reason,
        metadata=metadata
    )

    return True


# ============================================================================
# STATUS QUERY FUNCTIONS
# ============================================================================

def get_status_history(
    db: Session,
    tournament_id: int,
    limit: int = 50
) -> list[Dict[str, Any]]:
    """
    Get status change history for a tournament.

    Args:
        db: Database session
        tournament_id: Tournament ID
        limit: Maximum number of history entries to return (default: 50)

    Returns:
        List of status history dicts with keys:
        - old_status
        - new_status
        - changed_by
        - changed_at
        - reason
        - metadata
    """
    result = db.execute(
        text("""
        SELECT
            tsh.old_status,
            tsh.new_status,
            tsh.changed_by,
            tsh.changed_at,
            tsh.reason,
            tsh.metadata,
            u.name as changed_by_name,
            u.email as changed_by_email
        FROM tournament_status_history tsh
        LEFT JOIN users u ON tsh.changed_by = u.id
        WHERE tsh.tournament_id = :tournament_id
        ORDER BY tsh.changed_at DESC
        LIMIT :limit
        """),
        {"tournament_id": tournament_id, "limit": limit}
    )

    history = []
    for row in result:
        history.append({
            "old_status": row.old_status,
            "new_status": row.new_status,
            "changed_by": row.changed_by,
            "changed_by_name": row.changed_by_name,
            "changed_by_email": row.changed_by_email,
            "changed_at": row.changed_at,
            "reason": row.reason,
            "metadata": json.loads(row.metadata) if row.metadata else None
        })

    return history


def get_tournaments_by_status(
    db: Session,
    status: str,
    limit: int = 100
) -> list[Semester]:
    """
    Get all tournaments with a specific status.

    Args:
        db: Database session
        status: Tournament status to filter by
        limit: Maximum number of tournaments to return (default: 100)

    Returns:
        List of Tournament (Semester) objects
    """
    return db.query(Semester).filter(
        Semester.tournament_status == status,
        Semester.specialization_type == 'LFA_FOOTBALL_PLAYER'
    ).order_by(Semester.start_date).limit(limit).all()


# ============================================================================
# WORKFLOW HELPER FUNCTIONS
# ============================================================================

def can_open_enrollment(tournament: Semester) -> tuple[bool, Optional[str]]:
    """
    Check if a tournament can open enrollment.

    Args:
        tournament: Tournament (Semester) object

    Returns:
        Tuple of (can_open: bool, reason: Optional[str])
        If can_open is False, reason explains why
    """
    # Must have instructor confirmed
    if tournament.tournament_status != "INSTRUCTOR_CONFIRMED":
        return False, f"Tournament status must be INSTRUCTOR_CONFIRMED, currently {tournament.tournament_status}"

    # Must have assigned instructor
    if not tournament.master_instructor_id:
        return False, "Tournament must have an assigned instructor"

    return True, None


def can_start_tournament(tournament: Semester) -> tuple[bool, Optional[str]]:
    """
    Check if a tournament can be started.

    Args:
        tournament: Tournament (Semester) object

    Returns:
        Tuple of (can_start: bool, reason: Optional[str])
        If can_start is False, reason explains why
    """
    # Must be ready for enrollment or enrollment open
    if tournament.tournament_status not in ["READY_FOR_ENROLLMENT", "OPEN_FOR_ENROLLMENT"]:
        return False, f"Tournament status must be READY_FOR_ENROLLMENT or OPEN_FOR_ENROLLMENT, currently {tournament.tournament_status}"

    # Must have assigned instructor
    if not tournament.master_instructor_id:
        return False, "Tournament must have an assigned instructor"

    # TODO: Check if minimum participants enrolled (implement when enrollment system is ready)

    return True, None
