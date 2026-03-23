"""
Pitch Instructor Assignment Endpoints

Manages instructor assignment to specific pitches within a campus.

Endpoints:
  POST /pitches/{pitch_id}/assign-instructor        — admin/sport director/campus master assigns an instructor
  POST /pitch-assignments/{id}/accept               — instructor accepts a PENDING assignment
  POST /pitch-assignments/{id}/decline              — instructor declines a PENDING assignment
  GET  /pitches/{pitch_id}/eligible-instructors     — list eligible instructors for a pitch
  GET  /pitches/{pitch_id}/assignments              — list all assignments for a pitch
  GET  /campuses/{campus_id}/pitches                — list pitches for a campus
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ....dependencies import (
    get_db,
    get_current_user,
    get_current_pitch_manager_user,
)
from ....models.user import User, UserRole
from ....models.pitch import Pitch
from ....models.pitch_instructor_assignment import (
    PitchInstructorAssignment,
    PitchAssignmentStatus,
    PitchAssignmentType,
)
from ....services.tournament.pitch_instructor_service import (
    assign_instructor_to_pitch_direct,
    accept_pitch_assignment,
    decline_pitch_assignment,
    get_eligible_instructors_for_pitch,
    get_pitch_assignments,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class AssignInstructorRequest(BaseModel):
    instructor_id: int
    semester_id: Optional[int] = None
    is_master: bool = False
    required_license_type: Optional[str] = None
    required_age_group: Optional[str] = None
    notes: Optional[str] = None


class DeclineRequest(BaseModel):
    reason: Optional[str] = None


class PitchAssignmentResponse(BaseModel):
    id: int
    pitch_id: int
    instructor_id: int
    semester_id: Optional[int]
    is_master: bool
    assignment_type: str
    status: str
    required_license_type: Optional[str]
    required_age_group: Optional[str]
    assigned_by: Optional[int]
    created_at: datetime
    activated_at: Optional[datetime]
    ended_at: Optional[datetime]
    notes: Optional[str]
    sessions_updated: Optional[int] = None

    class Config:
        from_attributes = True


class EligibleInstructorResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class PitchResponse(BaseModel):
    id: int
    campus_id: int
    pitch_number: int
    name: str
    capacity: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/pitches/{pitch_id}/assign-instructor", response_model=PitchAssignmentResponse)
def assign_instructor(
    pitch_id: int,
    body: AssignInstructorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pitch_manager_user),
):
    """
    DIRECT mode: admin, sport director, or campus master invites an instructor to a pitch.

    Creates a PENDING assignment. The instructor then accepts or declines.

    - is_master=True requires: no other ACTIVE master on this pitch/semester
    - required_license_type: if set, instructor must have active InstructorSpecialization
    """
    assignment = assign_instructor_to_pitch_direct(
        db=db,
        pitch_id=pitch_id,
        instructor_id=body.instructor_id,
        assigned_by_id=current_user.id,
        semester_id=body.semester_id,
        is_master=body.is_master,
        required_license_type=body.required_license_type,
        required_age_group=body.required_age_group,
        notes=body.notes,
    )
    return assignment


@router.post("/pitch-assignments/{assignment_id}/accept", response_model=PitchAssignmentResponse)
def accept_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Instructor accepts a PENDING pitch assignment.

    Side effect when is_master=True: all sessions on that pitch (and semester)
    get session.instructor_id updated to this instructor.
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="Only instructors can accept assignments")

    assignment = accept_pitch_assignment(
        db=db,
        assignment_id=assignment_id,
        instructor_id=current_user.id,
    )

    response = PitchAssignmentResponse.model_validate(assignment)
    # Attach sessions_updated if available (set as transient attribute by service)
    sessions_updated = getattr(assignment, "_sessions_updated", None)
    if sessions_updated is not None:
        response.sessions_updated = sessions_updated
    return response


@router.post("/pitch-assignments/{assignment_id}/decline", response_model=PitchAssignmentResponse)
def decline_assignment(
    assignment_id: int,
    body: DeclineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Instructor declines a PENDING pitch assignment."""
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="Only instructors can decline assignments")

    assignment = decline_pitch_assignment(
        db=db,
        assignment_id=assignment_id,
        instructor_id=current_user.id,
        reason=body.reason,
    )
    return assignment


@router.get("/pitches/{pitch_id}/eligible-instructors", response_model=List[EligibleInstructorResponse])
def eligible_instructors(
    pitch_id: int,
    semester_id: Optional[int] = Query(default=None),
    license_type: Optional[str] = Query(default=None),
    age_group: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pitch_manager_user),
):
    """
    List instructors eligible to be assigned to this pitch.

    Filters:
    - role=INSTRUCTOR, is_active=True
    - If license_type: must have active InstructorSpecialization
    - Excludes instructors already ACTIVE on this pitch for the same semester
    """
    instructors = get_eligible_instructors_for_pitch(
        db=db,
        pitch_id=pitch_id,
        semester_id=semester_id,
        required_license_type=license_type,
        required_age_group=age_group,
    )
    return instructors


@router.get("/pitches/{pitch_id}/assignments", response_model=List[PitchAssignmentResponse])
def list_pitch_assignments(
    pitch_id: int,
    semester_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pitch_manager_user),
):
    """List all assignments for a pitch, optionally filtered by semester and status."""
    return get_pitch_assignments(
        db=db,
        pitch_id=pitch_id,
        semester_id=semester_id,
        status=status,
    )


@router.get("/campuses/{campus_id}/pitches", response_model=List[PitchResponse])
def list_campus_pitches(
    campus_id: int,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pitch_manager_user),
):
    """List all pitches for a campus."""
    q = db.query(Pitch).filter(Pitch.campus_id == campus_id)
    if not include_inactive:
        q = q.filter(Pitch.is_active == True)
    return q.order_by(Pitch.pitch_number).all()
