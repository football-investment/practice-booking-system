"""
Pitch Instructor Service

Manages instructor assignment to specific pitches (pályák) within a campus.

Two assignment modes:
  DIRECT:       Admin/campus master directly invites an instructor → PENDING
                Instructor accepts → ACTIVE → all pitch sessions get instructor_id
  JOB_POSTING:  Open position (InstructorPosition with pitch_id)
                Instructor applies → master accepts → PitchInstructorAssignment ACTIVE

Business rules enforced here:
  - Only 1 ACTIVE master per pitch per semester (DB unique constraint + service 409)
  - Instructor must have role=INSTRUCTOR
  - Optional license/age_group filtering for eligibility
  - On master accept: batch-assign session.instructor_id for all sessions on that pitch
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, UserRole
from app.models.pitch import Pitch
from app.models.pitch_instructor_assignment import (
    PitchInstructorAssignment,
    PitchAssignmentStatus,
    PitchAssignmentType,
)
from app.models.session import Session as SessionModel
from app.models.instructor_specialization import InstructorSpecialization


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_pitch_or_404(db: Session, pitch_id: int) -> Pitch:
    pitch = db.query(Pitch).filter(Pitch.id == pitch_id).first()
    if not pitch:
        raise HTTPException(status_code=404, detail=f"Pitch {pitch_id} not found")
    if not pitch.is_active:
        raise HTTPException(status_code=400, detail=f"Pitch {pitch_id} is not active")
    return pitch


def _get_instructor_or_404(db: Session, instructor_id: int) -> User:
    user = db.query(User).filter(User.id == instructor_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Instructor {instructor_id} not found")
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=422,
            detail=f"User {instructor_id} is not an instructor (role={user.role.value})"
        )
    return user


def _check_license_requirement(
    db: Session,
    instructor_id: int,
    required_license_type: Optional[str]
) -> None:
    """Raises 422 if instructor lacks the required license/specialization."""
    if not required_license_type:
        return
    match = db.query(InstructorSpecialization).filter(
        InstructorSpecialization.user_id == instructor_id,
        InstructorSpecialization.specialization == required_license_type,
        InstructorSpecialization.is_active == True,
    ).first()
    if not match:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Instructor {instructor_id} does not have required "
                f"specialization '{required_license_type}'"
            )
        )


def _check_master_uniqueness(
    db: Session,
    pitch_id: int,
    semester_id: Optional[int],
    exclude_assignment_id: Optional[int] = None
) -> None:
    """Raises 409 if there is already an active master on this pitch/semester."""
    q = db.query(PitchInstructorAssignment).filter(
        PitchInstructorAssignment.pitch_id == pitch_id,
        PitchInstructorAssignment.is_master == True,
        PitchInstructorAssignment.status == PitchAssignmentStatus.ACTIVE.value,
    )
    if semester_id is not None:
        q = q.filter(PitchInstructorAssignment.semester_id == semester_id)
    if exclude_assignment_id:
        q = q.filter(PitchInstructorAssignment.id != exclude_assignment_id)
    existing = q.first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Pitch {pitch_id} already has an active master instructor "
                f"(assignment_id={existing.id})"
            )
        )


def _batch_assign_sessions(
    db: Session,
    pitch_id: int,
    semester_id: Optional[int],
    instructor_id: int,
) -> int:
    """
    Set session.instructor_id = instructor_id for all sessions on this pitch.
    Returns the number of sessions updated.
    """
    q = db.query(SessionModel).filter(SessionModel.pitch_id == pitch_id)
    if semester_id is not None:
        q = q.filter(SessionModel.semester_id == semester_id)
    sessions = q.all()
    for s in sessions:
        s.instructor_id = instructor_id
    return len(sessions)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def assign_instructor_to_pitch_direct(
    db: Session,
    pitch_id: int,
    instructor_id: int,
    assigned_by_id: int,
    semester_id: Optional[int] = None,
    is_master: bool = False,
    required_license_type: Optional[str] = None,
    required_age_group: Optional[str] = None,
    notes: Optional[str] = None,
) -> PitchInstructorAssignment:
    """
    DIRECT mode: admin or campus master directly invites an instructor to a pitch.

    Creates a PitchInstructorAssignment with status=PENDING.
    The instructor then calls accept_pitch_assignment() to activate it.

    Raises:
        404  — pitch or instructor not found
        400  — pitch is not active
        422  — instructor lacks required license/specialization
        409  — another active master already exists (if is_master=True)
    """
    _get_pitch_or_404(db, pitch_id)
    _get_instructor_or_404(db, instructor_id)
    _check_license_requirement(db, instructor_id, required_license_type)

    if is_master:
        # Pre-check: cannot have 2 pending+active masters racing. Block if already ACTIVE.
        _check_master_uniqueness(db, pitch_id, semester_id)

    assignment = PitchInstructorAssignment(
        pitch_id=pitch_id,
        instructor_id=instructor_id,
        semester_id=semester_id,
        is_master=is_master,
        assignment_type=PitchAssignmentType.DIRECT.value,
        status=PitchAssignmentStatus.PENDING.value,
        required_license_type=required_license_type,
        required_age_group=required_age_group,
        assigned_by=assigned_by_id,
        notes=notes,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def accept_pitch_assignment(
    db: Session,
    assignment_id: int,
    instructor_id: int,
) -> PitchInstructorAssignment:
    """
    Instructor accepts a PENDING pitch assignment.

    Side effects when is_master=True:
      - All sessions on that pitch (and semester, if set) get session.instructor_id updated
      - activated_at is stamped

    Raises:
        404  — assignment not found
        403  — wrong instructor (assignment belongs to someone else)
        409  — status is not PENDING (already processed)
        409  — another active master exists (race condition guard)
    """
    assignment = db.query(PitchInstructorAssignment).filter(
        PitchInstructorAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")
    if assignment.instructor_id != instructor_id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to accept this assignment"
        )
    if assignment.status != PitchAssignmentStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Assignment status must be PENDING (got {assignment.status})"
        )

    # Master uniqueness guard (race condition: two instructors with PENDING master assignments)
    if assignment.is_master:
        _check_master_uniqueness(
            db,
            assignment.pitch_id,
            assignment.semester_id,
            exclude_assignment_id=assignment.id
        )

    # Activate
    assignment.status = PitchAssignmentStatus.ACTIVE.value
    assignment.activated_at = datetime.now(timezone.utc)

    # Batch assign sessions on this pitch
    updated_count = 0
    if assignment.is_master:
        updated_count = _batch_assign_sessions(
            db,
            assignment.pitch_id,
            assignment.semester_id,
            instructor_id
        )

    db.commit()
    db.refresh(assignment)

    # Attach update count as a transient attribute for callers
    assignment._sessions_updated = updated_count
    return assignment


def decline_pitch_assignment(
    db: Session,
    assignment_id: int,
    instructor_id: int,
    reason: Optional[str] = None,
) -> PitchInstructorAssignment:
    """
    Instructor declines a PENDING pitch assignment.

    Raises:
        404  — assignment not found
        403  — wrong instructor
        409  — assignment is not PENDING
    """
    assignment = db.query(PitchInstructorAssignment).filter(
        PitchInstructorAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")
    if assignment.instructor_id != instructor_id:
        raise HTTPException(status_code=403, detail="Not authorized to decline this assignment")
    if assignment.status != PitchAssignmentStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Assignment status must be PENDING (got {assignment.status})"
        )

    assignment.status = PitchAssignmentStatus.DECLINED.value
    if reason:
        assignment.notes = (assignment.notes or "") + f"\n[DECLINED] {reason}"
    db.commit()
    db.refresh(assignment)
    return assignment


def get_eligible_instructors_for_pitch(
    db: Session,
    pitch_id: int,
    semester_id: Optional[int] = None,
    required_license_type: Optional[str] = None,
    required_age_group: Optional[str] = None,
) -> List[User]:
    """
    Returns instructors eligible to be assigned to this pitch.

    Filters applied:
      - role = INSTRUCTOR
      - is_active = True
      - If required_license_type: must have active InstructorSpecialization for that type
      - Excludes instructors already ACTIVE on this pitch for the same semester

    Args:
        required_age_group: Advisory filter — logged but not enforced (no DB column for age group
                            on users; stored in InstructorAssignment periods for matching).
    """
    # Existing active assignments on this pitch (to exclude)
    already_active = db.query(PitchInstructorAssignment.instructor_id).filter(
        PitchInstructorAssignment.pitch_id == pitch_id,
        PitchInstructorAssignment.status == PitchAssignmentStatus.ACTIVE.value,
        *([PitchInstructorAssignment.semester_id == semester_id] if semester_id else [])
    ).subquery()

    q = db.query(User).filter(
        User.role == UserRole.INSTRUCTOR,
        User.is_active == True,
        ~User.id.in_(already_active),
    )

    if required_license_type:
        # Must have active InstructorSpecialization for required type
        q = q.join(
            InstructorSpecialization,
            (InstructorSpecialization.user_id == User.id) &
            (InstructorSpecialization.specialization == required_license_type) &
            (InstructorSpecialization.is_active == True)
        )

    return q.order_by(User.name).all()


def get_pitch_assignments(
    db: Session,
    pitch_id: int,
    semester_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[PitchInstructorAssignment]:
    """List all assignments for a pitch, optionally filtered by semester and status."""
    q = db.query(PitchInstructorAssignment).filter(
        PitchInstructorAssignment.pitch_id == pitch_id
    )
    if semester_id:
        q = q.filter(PitchInstructorAssignment.semester_id == semester_id)
    if status:
        q = q.filter(PitchInstructorAssignment.status == status)
    return q.order_by(PitchInstructorAssignment.created_at.desc()).all()
