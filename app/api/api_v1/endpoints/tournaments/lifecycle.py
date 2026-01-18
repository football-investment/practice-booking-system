"""
Tournament Lifecycle API
Handles tournament creation, status transitions, and status history
"""
from datetime import datetime
from typing import Optional, List
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.api_v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.specialization import SpecializationType
from app.services.tournament.status_validator import (
    validate_status_transition,
    get_next_allowed_statuses,
    StatusValidationError
)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class TournamentCreateRequest(BaseModel):
    """Request to create a new tournament in DRAFT status"""
    name: str = Field(..., description="Tournament name")
    specialization_type: SpecializationType = Field(..., description="Specialization type")
    age_group: Optional[str] = Field(None, description="Age group (e.g., PRE, YOUTH)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    location_id: Optional[int] = Field(None, description="Location ID")
    campus_id: Optional[int] = Field(None, description="Campus ID")
    description: Optional[str] = Field(None, description="Tournament description")


class TournamentCreateResponse(BaseModel):
    """Response from tournament creation"""
    tournament_id: int
    name: str
    status: str
    specialization_type: str
    start_date: str
    end_date: str
    created_at: str


class StatusTransitionRequest(BaseModel):
    """Request to change tournament status"""
    new_status: str = Field(..., description="New status to transition to")
    reason: Optional[str] = Field(None, description="Reason for status change")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class StatusTransitionResponse(BaseModel):
    """Response from status transition"""
    tournament_id: int
    old_status: Optional[str]
    new_status: str
    changed_by: int
    changed_at: str
    reason: Optional[str]
    allowed_next_statuses: List[str]


class StatusHistoryEntry(BaseModel):
    """Single status history entry"""
    id: int
    old_status: Optional[str]
    new_status: str
    changed_by: int
    changed_by_name: str
    changed_at: str
    reason: Optional[str]
    metadata: Optional[dict]


class StatusHistoryResponse(BaseModel):
    """Response with full status history"""
    tournament_id: int
    tournament_name: str
    current_status: Optional[str]
    history: List[StatusHistoryEntry]


# ============================================================================
# CYCLE 2 SCHEMAS: Instructor Assignment
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
# HELPER FUNCTIONS
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
    Record a status change in tournament_status_history table

    Args:
        db: Database session
        tournament_id: Tournament ID
        old_status: Previous status (None for creation)
        new_status: New status
        changed_by: User ID who made the change
        reason: Optional reason for change
        metadata: Optional metadata dict
    """
    # Convert metadata dict to JSON string if provided
    metadata_json = json.dumps(metadata) if metadata is not None else None

    db.execute(
        text("""
        INSERT INTO tournament_status_history
        (tournament_id, old_status, new_status, changed_by, reason, extra_metadata)
        VALUES (:tournament_id, :old_status, :new_status, :changed_by, :reason, :extra_metadata)
        """),
        {
            "tournament_id": tournament_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "reason": reason,
            "extra_metadata": metadata_json
        }
    )
    # Note: No commit here - let the calling code handle transaction management


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/", response_model=TournamentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    request: TournamentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new tournament in DRAFT status (Admin only)

    Business rules:
    - Only admins can create tournaments
    - Tournaments are created in DRAFT status
    - Status history is automatically recorded
    """

    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create tournaments"
        )

    # Validate dates
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    # Generate unique tournament code
    tournament_code = f"TOURN-{start_date.strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"

    # Create tournament (Semester) record with DRAFT status
    # Only include optional FK fields if they have values
    tournament_data = {
        "code": tournament_code,
        "name": request.name,
        "specialization_type": request.specialization_type.value,  # Convert enum to string
        "age_group": request.age_group,
        "start_date": start_date,
        "end_date": end_date,
        "focus_description": request.description,
        "tournament_status": "DRAFT",
        "is_active": True
    }

    # Only add FK fields if they have values (avoid NULL FK violations)
    if request.location_id is not None:
        tournament_data["location_id"] = request.location_id
    if request.campus_id is not None:
        tournament_data["campus_id"] = request.campus_id

    tournament = Semester(**tournament_data)

    db.add(tournament)
    db.flush()  # Get tournament ID before commit

    # Record status history (NULL → DRAFT)
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=None,
        new_status="DRAFT",
        changed_by=current_user.id,
        reason="Tournament created",
        metadata={"created_by": current_user.email}
    )

    db.commit()
    db.refresh(tournament)

    return TournamentCreateResponse(
        tournament_id=tournament.id,
        name=tournament.name,
        status=tournament.tournament_status,
        specialization_type=tournament.specialization_type,  # Already a string from DB
        start_date=tournament.start_date.isoformat(),
        end_date=tournament.end_date.isoformat(),
        created_at=datetime.now().isoformat()
    )


@router.patch("/{tournament_id}/status", response_model=StatusTransitionResponse)
def transition_tournament_status(
    tournament_id: int,
    request: StatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition tournament to a new status with validation

    Business rules:
    - Only admins and instructors can change tournament status
    - Transitions must follow the valid status graph
    - Prerequisites for each status must be met
    - All changes are audited in status history
    """

    # Authorization: Admin or Instructor only
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can change tournament status"
        )

    # Fetch tournament with enrollments for validation
    from sqlalchemy.orm import joinedload
    tournament = db.query(Semester).options(
        joinedload(Semester.enrollments)
    ).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Validate status transition
    is_valid, error_message = validate_status_transition(
        current_status=tournament.tournament_status,
        new_status=request.new_status,
        tournament=tournament
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Record old status for response and history
    old_status = tournament.tournament_status

    # Update tournament status
    tournament.tournament_status = request.new_status
    db.flush()

    # Record status history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status=request.new_status,
        changed_by=current_user.id,
        reason=request.reason,
        metadata=request.metadata
    )

    db.commit()
    db.refresh(tournament)

    # Get allowed next statuses for response
    allowed_next = get_next_allowed_statuses(tournament.tournament_status)

    return StatusTransitionResponse(
        tournament_id=tournament.id,
        old_status=old_status,
        new_status=tournament.tournament_status,
        changed_by=current_user.id,
        changed_at=datetime.now().isoformat(),
        reason=request.reason,
        allowed_next_statuses=allowed_next
    )


@router.get("/{tournament_id}/status-history", response_model=StatusHistoryResponse)
def get_tournament_status_history(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full status history for a tournament (audit trail)

    Returns all status transitions with user info, timestamps, and reasons
    """

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Fetch status history with user info
    history_rows = db.execute(
        text("""
        SELECT
            tsh.id,
            tsh.old_status,
            tsh.new_status,
            tsh.changed_by,
            u.name as changed_by_name,
            tsh.changed_at,
            tsh.reason,
            tsh.metadata
        FROM tournament_status_history tsh
        JOIN users u ON tsh.changed_by = u.id
        WHERE tsh.tournament_id = :tournament_id
        ORDER BY tsh.changed_at DESC
        """),
        {"tournament_id": tournament_id}
    ).fetchall()

    history = [
        StatusHistoryEntry(
            id=row.id,
            old_status=row.old_status,
            new_status=row.new_status,
            changed_by=row.changed_by,
            changed_by_name=row.changed_by_name,
            changed_at=row.changed_at.isoformat(),
            reason=row.reason,
            metadata=row.metadata
        )
        for row in history_rows
    ]

    return StatusHistoryResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        current_status=tournament.tournament_status,
        history=history
    )


# ============================================================================
# CYCLE 2 ENDPOINTS: Instructor Assignment
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
