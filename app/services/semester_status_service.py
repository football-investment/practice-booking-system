"""
Semester Status Transition Service
Handles automatic status changes based on instructor assignments

Business Logic:
- DRAFT → INSTRUCTOR_ASSIGNED: When master instructor ACCEPTS offer (not just when offered)
- INSTRUCTOR_ASSIGNED → READY_FOR_ENROLLMENT: When first assistant is assigned
- READY_FOR_ENROLLMENT → ONGOING: When first session starts (cron job)
- ONGOING → COMPLETED: When last session ends (cron job)

CRITICAL: Only transition semesters when master instructor offer is ACCEPTED
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models.semester import Semester, SemesterStatus
from app.models.instructor_assignment import LocationMasterInstructor, MasterOfferStatus
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def transition_to_instructor_assigned(
    db: Session,
    location_city: str,
    master_instructor_id: int
) -> int:
    """
    Transition DRAFT semesters to INSTRUCTOR_ASSIGNED when master ACCEPTS offer

    CRITICAL CHANGE (Hybrid Hiring System):
    - OLD: Triggered on master contract creation
    - NEW: Only triggered when offer_status = ACCEPTED

    This function should ONLY be called when:
    - Instructor accepts a direct hire offer (OFFERED → ACCEPTED)
    - Instructor accepts job application offer (application accepted → contract created with ACCEPTED status)
    - Legacy immediate-active contract is created (offer_status = NULL)

    Args:
        db: Database session
        location_city: City where master is assigned (e.g., 'Budapest')
        master_instructor_id: ID of the hired master instructor

    Returns:
        Number of semesters updated (0 if offer not accepted yet)
    """
    # CRITICAL: Verify master instructor has ACCEPTED offer before transitioning
    master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.instructor_id == master_instructor_id,
        LocationMasterInstructor.is_active == True
    ).first()

    if not master:
        logger.warning(
            f"Cannot transition semesters: No active master contract for instructor {master_instructor_id}"
        )
        return 0

    # Check offer status: Must be ACCEPTED or NULL (legacy)
    if master.offer_status not in [MasterOfferStatus.ACCEPTED, None]:
        logger.info(
            f"Skipping semester transition: Master instructor offer status is {master.offer_status.value}. "
            f"Semesters will only transition when offer is ACCEPTED."
        )
        return 0

    # Offer is accepted (or legacy) - proceed with transition
    updated_count = db.query(Semester).filter(
        Semester.location_city == location_city,
        Semester.status == SemesterStatus.DRAFT
    ).update({
        'master_instructor_id': master_instructor_id,
        'status': SemesterStatus.INSTRUCTOR_ASSIGNED,
        'updated_at': datetime.utcnow()
    }, synchronize_session=False)

    db.commit()

    logger.info(
        f"Transitioned {updated_count} semesters to INSTRUCTOR_ASSIGNED "
        f"for location {location_city}, master_id={master_instructor_id} "
        f"(offer_status={master.offer_status.value if master.offer_status else 'LEGACY'})"
    )

    return updated_count


def transition_to_ready_for_enrollment(
    db: Session,
    semester_id: int
) -> bool:
    """
    Transition INSTRUCTOR_ASSIGNED semester to READY_FOR_ENROLLMENT
    Called when first assistant instructor is assigned

    Args:
        db: Database session
        semester_id: ID of the semester to transition

    Returns:
        True if transition occurred, False otherwise
    """
    semester = db.query(Semester).filter(
        Semester.id == semester_id,
        Semester.status == SemesterStatus.INSTRUCTOR_ASSIGNED
    ).first()

    if semester:
        semester.status = SemesterStatus.READY_FOR_ENROLLMENT
        semester.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Semester {semester.code} (ID {semester_id}) transitioned to READY_FOR_ENROLLMENT"
        )
        return True

    logger.warning(
        f"Cannot transition semester {semester_id} to READY_FOR_ENROLLMENT "
        f"(not found or not in INSTRUCTOR_ASSIGNED status)"
    )
    return False


def check_and_transition_semester(
    db: Session,
    semester_id: int
) -> Optional[str]:
    """
    Check semester instructor coverage and transition if ready

    This function checks if a semester has:
    - Master instructor assigned
    - At least one assistant instructor assigned

    If both conditions are met and semester is in DRAFT or INSTRUCTOR_ASSIGNED,
    it transitions to READY_FOR_ENROLLMENT

    Args:
        db: Database session
        semester_id: ID of the semester to check

    Returns:
        New status after check, or None if semester not found
    """
    from app.models.instructor_assignment import InstructorAssignment

    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        logger.error(f"Semester {semester_id} not found")
        return None

    # Count assigned instructors for this semester
    instructor_count = db.query(InstructorAssignment).filter(
        InstructorAssignment.semester_id == semester_id,
        InstructorAssignment.is_active == True
    ).count()

    # If semester has master + at least 1 assistant, mark ready
    if semester.master_instructor_id and instructor_count > 0:
        if semester.status in [SemesterStatus.DRAFT, SemesterStatus.INSTRUCTOR_ASSIGNED]:
            old_status = semester.status
            semester.status = SemesterStatus.READY_FOR_ENROLLMENT
            semester.updated_at = datetime.utcnow()
            db.commit()

            logger.info(
                f"Semester {semester.code} (ID {semester_id}) auto-transitioned "
                f"from {old_status} to READY_FOR_ENROLLMENT "
                f"(master + {instructor_count} assistants)"
            )

    return semester.status.value


def get_semesters_for_status_transition(
    db: Session,
    from_status: SemesterStatus,
    to_status: SemesterStatus
) -> List[Semester]:
    """
    Get semesters eligible for status transition

    Useful for batch operations and cron jobs

    Args:
        db: Database session
        from_status: Current status to filter by
        to_status: Target status (for logging/context)

    Returns:
        List of semesters eligible for transition
    """
    semesters = db.query(Semester).filter(
        Semester.status == from_status,
        Semester.is_active == True
    ).all()

    logger.info(
        f"Found {len(semesters)} semesters eligible for transition "
        f"from {from_status} to {to_status}"
    )

    return semesters


def bulk_transition_by_date(
    db: Session,
    check_start_dates: bool = True,
    check_end_dates: bool = True
) -> dict:
    """
    Batch transition semesters based on start/end dates
    Should be run by cron job daily

    Transitions:
    - READY_FOR_ENROLLMENT → ONGOING: When start_date is reached
    - ONGOING → COMPLETED: When end_date has passed

    Args:
        db: Database session
        check_start_dates: Whether to transition based on start dates
        check_end_dates: Whether to transition based on end dates

    Returns:
        Dict with counts: {'started': X, 'completed': Y}
    """
    from datetime import date
    today = date.today()

    result = {'started': 0, 'completed': 0}

    # Transition to ONGOING
    if check_start_dates:
        started = db.query(Semester).filter(
            Semester.status == SemesterStatus.READY_FOR_ENROLLMENT,
            Semester.start_date <= today
        ).update({
            'status': SemesterStatus.ONGOING,
            'updated_at': datetime.utcnow()
        }, synchronize_session=False)

        result['started'] = started
        logger.info(f"Transitioned {started} semesters to ONGOING (start date reached)")

    # Transition to COMPLETED
    if check_end_dates:
        completed = db.query(Semester).filter(
            Semester.status == SemesterStatus.ONGOING,
            Semester.end_date < today
        ).update({
            'status': SemesterStatus.COMPLETED,
            'updated_at': datetime.utcnow()
        }, synchronize_session=False)

        result['completed'] = completed
        logger.info(f"Transitioned {completed} semesters to COMPLETED (end date passed)")

    db.commit()

    return result
