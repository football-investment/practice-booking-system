"""
Lifecycle Helpers for Test Fixtures

SCOPE: Minimal, domain-clean state transition utilities.
DO NOT expand this file without architectural review.

These helpers ensure tests respect domain lifecycle rules.
NO validation bypasses. NO force-setting state. NO enum/string mixing.
"""
from typing import Dict
from sqlalchemy.orm import Session
from app.models.semester import Semester, SemesterStatus
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus
from app.models.user import User


def transition_tournament_to_seeking_instructor(
    tournament_id: int,
    db: Session
) -> Semester:
    """
    Transition tournament from DRAFT to SEEKING_INSTRUCTOR.

    Valid transition: DRAFT → SEEKING_INSTRUCTOR
    Business rule: Tournament must be in DRAFT status.

    Args:
        tournament_id: Tournament (semester) ID
        db: Database session

    Returns:
        Updated tournament instance

    Raises:
        ValueError: If tournament not in DRAFT status
        LookupError: If tournament not found
    """
    # 1. Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise LookupError(f"Tournament {tournament_id} not found")

    # 2. Validate current status (MUST be DRAFT)
    if tournament.status != SemesterStatus.DRAFT:
        raise ValueError(
            f"Cannot transition to SEEKING_INSTRUCTOR from {tournament.status}. "
            f"Tournament must be in DRAFT status."
        )

    # 3. Apply transition (enum-native)
    tournament.status = SemesterStatus.SEEKING_INSTRUCTOR

    # 4. Sync legacy string field (dual-status architecture)
    tournament.tournament_status = "SEEKING_INSTRUCTOR"

    # 5. Commit
    db.commit()
    db.refresh(tournament)

    return tournament


def create_instructor_application(
    tournament_id: int,
    instructor_id: int,
    db: Session
) -> InstructorAssignmentRequest:
    """
    Create instructor assignment request for tournament.

    Prerequisites:
    - Tournament status = SEEKING_INSTRUCTOR
    - No existing request from this instructor for this tournament

    Args:
        tournament_id: Tournament (semester) ID
        instructor_id: Instructor user ID
        db: Database session

    Returns:
        Created assignment request instance

    Raises:
        ValueError: If prerequisites not met
        LookupError: If tournament or instructor not found
    """
    # 1. Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise LookupError(f"Tournament {tournament_id} not found")

    # 2. Fetch instructor
    instructor = db.query(User).filter(User.id == instructor_id).first()
    if not instructor:
        raise LookupError(f"Instructor {instructor_id} not found")

    # 3. Validate tournament status (MUST be SEEKING_INSTRUCTOR)
    if tournament.status != SemesterStatus.SEEKING_INSTRUCTOR:
        raise ValueError(
            f"Cannot create assignment request for tournament in {tournament.status} status. "
            f"Tournament must be SEEKING_INSTRUCTOR."
        )

    # 4. Check for duplicate request
    existing = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id == tournament_id,
        InstructorAssignmentRequest.instructor_id == instructor_id
    ).first()

    if existing:
        raise ValueError(
            f"Instructor {instructor_id} already has an assignment request for tournament {tournament_id}"
        )

    # 5. Create assignment request (enum-native status)
    request = InstructorAssignmentRequest(
        semester_id=tournament_id,
        instructor_id=instructor_id,
        status=AssignmentRequestStatus.PENDING,
        request_message="Test assignment request created via lifecycle helper"
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request
