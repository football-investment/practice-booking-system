"""
Instructor Assignment Lifecycle — Cycle 2
Extracted from lifecycle.py as part of file-size refactoring (lifecycle.py was 1133 lines).
Boundary: lifecycle.py lines 95–114 (schemas) and 576–811 (endpoints).

Cycle 2 = admin-driven direct assignment flow:
  POST /{id}/assign-instructor  — admin picks instructor
  POST /{id}/instructor/accept  — instructor confirms
  POST /{id}/instructor/decline — instructor declines, back to SEEKING_INSTRUCTOR

See also: instructor_assignment.py (application-based flow, different URL paths).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.api.api_v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class AssignInstructorRequest(BaseModel):
    """Request to assign an instructor to a tournament"""
    instructor_id: int = Field(..., description="ID of the instructor to assign")
    message: Optional[str] = Field(None, description="Optional message to instructor")


class InstructorActionRequest(BaseModel):
    """Request from instructor to accept/decline assignment"""
    message: Optional[str] = Field(None, description="Optional message/reason")


class InstructorAssignmentResponse(BaseModel):
    """Response from instructor assignment/action"""
    tournament_id: int
    tournament_name: str
    instructor_id: int
    instructor_name: str
    status: str
    action: str  # "assigned", "accepted", "declined"
    message: Optional[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/assign-instructor", response_model=InstructorAssignmentResponse)
def assign_instructor_to_tournament(
    tournament_id: int,
    request: AssignInstructorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin assigns an instructor to a tournament (Cycle 2)

    Business rules:
    - Only admins can assign instructors
    - Tournament must be in SEEKING_INSTRUCTOR status
    - Instructor must have GRANDMASTER role
    - Auto-transition to PENDING_INSTRUCTOR_ACCEPTANCE
    """

    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign instructors"
        )

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Validate current status
    if tournament.tournament_status != "SEEKING_INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign instructor: Tournament is in {tournament.tournament_status} status (must be SEEKING_INSTRUCTOR)"
        )

    # Fetch instructor
    instructor = db.query(User).filter(User.id == request.instructor_id).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instructor {request.instructor_id} not found"
        )

    # Validate instructor role
    if instructor.role != UserRole.GRANDMASTER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {instructor.email} is not an instructor (GRANDMASTER role required)"
        )

    # Assign instructor
    old_status = tournament.tournament_status
    tournament.master_instructor_id = instructor.id
    tournament.tournament_status = "PENDING_INSTRUCTOR_ACCEPTANCE"

    db.flush()

    # Record status history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="PENDING_INSTRUCTOR_ACCEPTANCE",
        changed_by=current_user.id,
        reason=f"Instructor {instructor.name} assigned by admin",
        metadata={
            "instructor_id": instructor.id,
            "instructor_email": instructor.email,
            "admin_message": request.message
        }
    )

    db.commit()
    db.refresh(tournament)

    return InstructorAssignmentResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        instructor_id=instructor.id,
        instructor_name=instructor.name,
        status=tournament.tournament_status,
        action="assigned",
        message=request.message
    )


@router.post("/{tournament_id}/instructor/accept", response_model=InstructorAssignmentResponse)
def instructor_accept_assignment(
    tournament_id: int,
    request: InstructorActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor accepts their tournament assignment (Cycle 2)

    Business rules:
    - Only assigned instructor can accept
    - Tournament must be in PENDING_INSTRUCTOR_ACCEPTANCE status
    - Auto-transition to INSTRUCTOR_CONFIRMED (awaiting admin to open enrollment)
    """

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Validate current status
    if tournament.tournament_status != "PENDING_INSTRUCTOR_ACCEPTANCE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept: Tournament is in {tournament.tournament_status} status"
        )

    # Validate instructor authorization
    if tournament.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned instructor for this tournament"
        )

    # Accept assignment - transition to INSTRUCTOR_CONFIRMED (awaiting admin to open enrollment)
    old_status = tournament.tournament_status
    tournament.tournament_status = "INSTRUCTOR_CONFIRMED"

    db.flush()

    # Record status history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="INSTRUCTOR_CONFIRMED",
        changed_by=current_user.id,
        reason=f"Instructor {current_user.name} accepted assignment - awaiting admin to open enrollment",
        metadata={
            "instructor_message": request.message,
            "instructor_accepted": True
        }
    )

    db.commit()
    db.refresh(tournament)

    return InstructorAssignmentResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        instructor_id=current_user.id,
        instructor_name=current_user.name,
        status=tournament.tournament_status,
        action="accepted",
        message=request.message
    )


@router.post("/{tournament_id}/instructor/decline", response_model=InstructorAssignmentResponse)
def instructor_decline_assignment(
    tournament_id: int,
    request: InstructorActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor declines their tournament assignment (Cycle 2)

    Business rules:
    - Only assigned instructor can decline
    - Tournament must be in PENDING_INSTRUCTOR_ACCEPTANCE status
    - Auto-transition back to SEEKING_INSTRUCTOR
    - Instructor assignment is cleared
    """

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Validate current status
    if tournament.tournament_status != "PENDING_INSTRUCTOR_ACCEPTANCE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decline: Tournament is in {tournament.tournament_status} status"
        )

    # Validate instructor authorization
    if tournament.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned instructor for this tournament"
        )

    # Decline assignment
    old_status = tournament.tournament_status
    declined_instructor_name = current_user.name
    tournament.master_instructor_id = None  # Clear assignment
    tournament.tournament_status = "SEEKING_INSTRUCTOR"  # Back to seeking

    db.flush()

    # Record status history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="SEEKING_INSTRUCTOR",
        changed_by=current_user.id,
        reason=f"Instructor {declined_instructor_name} declined assignment: {request.message or 'No reason provided'}",
        metadata={
            "declined_by": current_user.id,
            "declined_by_email": current_user.email,
            "decline_reason": request.message
        }
    )

    db.commit()
    db.refresh(tournament)

    return InstructorAssignmentResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        instructor_id=current_user.id,
        instructor_name=declined_instructor_name,
        status=tournament.tournament_status,
        action="declined",
        message=request.message
    )
