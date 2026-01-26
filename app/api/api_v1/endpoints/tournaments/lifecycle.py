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
    get_next_allowed_statuses
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

    # ============================================================================
    # AUTO-DELETE SESSIONS when transitioning from IN_PROGRESS to ENROLLMENT_CLOSED
    # ============================================================================
    if old_status == "IN_PROGRESS" and request.new_status == "ENROLLMENT_CLOSED":
        if tournament.sessions_generated:
            from app.models.session import Session as SessionModel
            from app.models.attendance import Attendance

            # Get session IDs to delete
            session_ids = [s.id for s in db.query(SessionModel).filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.auto_generated == True
            ).all()]

            if session_ids:
                # Delete attendance records first
                db.query(Attendance).filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)

                # Delete sessions
                deleted_count = db.query(SessionModel).filter(
                    SessionModel.semester_id == tournament_id,
                    SessionModel.auto_generated == True
                ).delete(synchronize_session=False)

                # Reset flags
                tournament.sessions_generated = False
                tournament.sessions_generated_at = None
                db.flush()

                print(f"🗑️ Auto-deleted {deleted_count} sessions when tournament reverted to ENROLLMENT_CLOSED")

    # ============================================================================
    # AUTO-GENERATE SESSIONS when transitioning to IN_PROGRESS
    # ============================================================================
    if request.new_status == "IN_PROGRESS":
        # 📸 SAVE REWARD POLICY SNAPSHOT FIRST (lock reward_config for this tournament)
        # This MUST happen BEFORE session generation and ALWAYS when entering IN_PROGRESS
        # This prevents admin from changing reward config after tournament starts
        if tournament.reward_config and not tournament.reward_policy_snapshot:
            tournament.reward_policy_snapshot = tournament.reward_config
            db.flush()
            print(f"📸 REWARD POLICY SNAPSHOT saved for tournament {tournament_id}:")
            print(f"   Skills: {len(tournament.reward_config.get('skill_mappings', []))}")
            print(f"   Template: {tournament.reward_config.get('template_name', 'Custom')}")

        # Check if we need to regenerate sessions
        from app.models.session import Session as SessionModel

        current_session_count = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.auto_generated == True
        ).count()

        # 🔄 NEW: INDIVIDUAL_RANKING always expects 1 session (rounds stored in rounds_data)
        # HEAD_TO_HEAD expects N sessions based on tournament type
        if tournament.format == "INDIVIDUAL_RANKING":
            expected_session_count = 1
        else:
            # HEAD_TO_HEAD: session count depends on tournament type (calculated by generator)
            expected_session_count = None  # Can't predict without running generator

        # Regenerate if: (1) not generated yet, OR (2) session count doesn't match expected (for INDIVIDUAL_RANKING)
        if tournament.format == "INDIVIDUAL_RANKING":
            needs_regeneration = (not tournament.sessions_generated) or (current_session_count != expected_session_count)
        else:
            # HEAD_TO_HEAD: just check if not generated yet
            needs_regeneration = not tournament.sessions_generated

        if needs_regeneration and current_session_count > 0:
            # Reset flags FIRST (before deletion) so can_generate_sessions() sees the correct state
            tournament.sessions_generated = False
            tournament.sessions_generated_at = None
            db.flush()

            # Delete existing sessions
            from app.models.attendance import Attendance

            session_ids = [s.id for s in db.query(SessionModel).filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.auto_generated == True
            ).all()]

            if session_ids:
                db.query(Attendance).filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
                deleted_count = db.query(SessionModel).filter(
                    SessionModel.semester_id == tournament_id,
                    SessionModel.auto_generated == True
                ).delete(synchronize_session=False)
                db.flush()
                print(f"🗑️ Deleted {deleted_count} old sessions (mismatch: had {current_session_count}, need {expected_session_count})")

        if needs_regeneration:
            # 📸 SNAPSHOT: Save enrollment state BEFORE session generation
            # This allows regeneration if something goes wrong
            from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus

            enrolled_players = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
            ).all()

            enrollment_snapshot = {
                "timestamp": datetime.now().isoformat(),
                "total_enrolled": len(enrolled_players),
                "player_ids": [e.user_id for e in enrolled_players],
                "player_details": [
                    {
                        "user_id": e.user_id,
                        "enrollment_id": e.id,
                        "payment_verified": e.payment_verified,
                        "enrolled_at": e.created_at.isoformat() if e.created_at else None
                    }
                    for e in enrolled_players
                ],
                "schedule_config": {
                    "match_duration_minutes": tournament.match_duration_minutes,
                    "break_duration_minutes": tournament.break_duration_minutes,
                    "parallel_fields": tournament.parallel_fields,
                    "tournament_type_id": tournament.tournament_type_id
                }
            }

            # 💾 SAVE ENROLLMENT SNAPSHOT to database
            tournament.enrollment_snapshot = enrollment_snapshot
            db.flush()  # Save snapshot immediately before session generation

            print(f"📸 ENROLLMENT SNAPSHOT saved for tournament {tournament_id}:")
            print(f"   Players: {len(enrolled_players)}")
            print(f"   Config: {enrollment_snapshot['schedule_config']}")

            # Auto-generate tournament sessions using default parameters
            from app.services.tournament_session_generator import TournamentSessionGenerator

            generator = TournamentSessionGenerator(db)

            # Check if can generate
            can_generate, reason = generator.can_generate_sessions(tournament_id)

            if can_generate:
                # Use semester's saved schedule configuration if available, otherwise use defaults
                # Admin sets these via schedule editor BEFORE generating sessions
                session_duration = tournament.match_duration_minutes if tournament.match_duration_minutes else 90
                break_duration = tournament.break_duration_minutes if tournament.break_duration_minutes else 15
                parallel_fields = tournament.parallel_fields if tournament.parallel_fields else 1
                number_of_rounds = tournament.number_of_rounds if tournament.number_of_rounds else 1

                # Generate sessions (durations and parallel fields from semester config or defaults)
                success, message, sessions_created = generator.generate_sessions(
                    tournament_id=tournament_id,
                    parallel_fields=parallel_fields,
                    session_duration_minutes=session_duration,
                    break_minutes=break_duration,
                    number_of_rounds=number_of_rounds
                )

                if success:
                    print(f"✅ Auto-generated {len(sessions_created)} sessions for tournament {tournament_id}")
                else:
                    print(f"⚠️ Failed to auto-generate sessions: {message}")
            else:
                print(f"⚠️ Cannot auto-generate sessions: {reason}")

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


# ============================================================================
# TOURNAMENT UPDATE (Admin only)
# ============================================================================

class TournamentUpdateRequest(BaseModel):
    """Request to update tournament fields (Admin only)"""
    name: Optional[str] = Field(None, description="Tournament name")
    enrollment_cost: Optional[int] = Field(None, ge=0, description="Enrollment cost in credits")
    max_players: Optional[int] = Field(None, gt=0, description="Maximum players")
    age_group: Optional[str] = Field(None, description="Age group")
    description: Optional[str] = Field(None, description="Tournament description")
    # ✅ NEW: Additional editable fields for admin
    start_date: Optional[str] = Field(None, description="Tournament start date (ISO format)")
    end_date: Optional[str] = Field(None, description="Tournament end date (ISO format)")
    specialization_type: Optional[str] = Field(None, description="Specialization type")
    assignment_type: Optional[str] = Field(None, description="Assignment type (OPEN_ASSIGNMENT or APPLICATION_BASED)")
    participant_type: Optional[str] = Field(None, description="Participant type (INDIVIDUAL, TEAM, MIXED)")
    tournament_type_id: Optional[int] = Field(None, description="Tournament type ID (⚠️ WARNING: Can only change if no sessions generated)")
    tournament_status: Optional[str] = Field(None, description="Tournament status (⚠️ ADMIN OVERRIDE: Bypasses state machine validation)")
    # ✅ NEW: Tournament format and scoring configuration
    format: Optional[str] = Field(None, description="Tournament format (HEAD_TO_HEAD or INDIVIDUAL_RANKING)")
    scoring_type: Optional[str] = Field(None, description="Scoring type (TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT)")
    measurement_unit: Optional[str] = Field(None, description="Measurement unit (seconds, meters, points, etc.)")
    ranking_direction: Optional[str] = Field(None, description="Ranking direction (ASC = lowest wins, DESC = highest wins)")
    number_of_rounds: Optional[int] = Field(None, ge=1, le=10, description="Number of rounds for INDIVIDUAL_RANKING tournaments (⚠️ WARNING: Triggers session regeneration if changed)")


@router.patch("/{tournament_id}", status_code=status.HTTP_200_OK)
def update_tournament(
    tournament_id: int,
    request: TournamentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update tournament fields (Admin only)

    **Authorization:** Admin only

    **Allowed updates:**
    - name: Tournament name
    - enrollment_cost: Credits required to enroll
    - max_players: Maximum participant capacity (cannot be reduced below current enrollment count)
    - age_group: Age group classification
    - description: Tournament description
    - start_date: Tournament start date (ISO format)
    - end_date: Tournament end date (ISO format)
    - specialization_type: Specialization type
    - assignment_type: OPEN_ASSIGNMENT or APPLICATION_BASED
    - participant_type: INDIVIDUAL, TEAM, or MIXED
    - tournament_type_id: Tournament type (⚠️ Auto-deletes sessions if changed)
    - tournament_status: Tournament status (⚠️ ADMIN OVERRIDE: Bypasses state machine validation)

    **Important Notes:**
    - max_players cannot be reduced below current enrollment count
    - tournament_type_id: Automatically deletes existing sessions if changed
    - tournament_status: Admin can set ANY status (state machine validation bypassed)
    """
    # Admin-only check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update tournaments"
        )

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Track what was updated
    updates = {}

    # Update name
    if request.name is not None:
        updates["name"] = {"old": tournament.name, "new": request.name}
        tournament.name = request.name

    # Update enrollment_cost
    if request.enrollment_cost is not None:
        updates["enrollment_cost"] = {"old": tournament.enrollment_cost, "new": request.enrollment_cost}
        tournament.enrollment_cost = request.enrollment_cost

    # Update max_players
    if request.max_players is not None:
        # Check if tournament has enrollments
        enrollments_count = db.query(Semester).filter(
            Semester.id == tournament_id
        ).join(Semester.enrollments).count() if hasattr(tournament, 'enrollments') else 0

        if enrollments_count > request.max_players:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce max_players to {request.max_players}: Tournament already has {enrollments_count} enrollments"
            )

        updates["max_players"] = {"old": tournament.max_players, "new": request.max_players}
        tournament.max_players = request.max_players

    # Update age_group
    if request.age_group is not None:
        updates["age_group"] = {"old": tournament.age_group, "new": request.age_group}
        tournament.age_group = request.age_group

    # Update description
    if request.description is not None:
        updates["focus_description"] = {"old": tournament.focus_description, "new": request.description}
        tournament.focus_description = request.description

    # ✅ NEW: Update start_date
    if request.start_date is not None:
        from datetime import datetime
        try:
            new_start_date = datetime.fromisoformat(request.start_date).date()
            updates["start_date"] = {"old": str(tournament.start_date), "new": str(new_start_date)}
            tournament.start_date = new_start_date
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {request.start_date}. Expected ISO format (YYYY-MM-DD)"
            )

    # ✅ NEW: Update end_date
    if request.end_date is not None:
        from datetime import datetime
        try:
            new_end_date = datetime.fromisoformat(request.end_date).date()
            updates["end_date"] = {"old": str(tournament.end_date), "new": str(new_end_date)}
            tournament.end_date = new_end_date
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {request.end_date}. Expected ISO format (YYYY-MM-DD)"
            )

    # ✅ NEW: Update specialization_type
    if request.specialization_type is not None:
        updates["specialization_type"] = {"old": tournament.specialization_type, "new": request.specialization_type}
        tournament.specialization_type = request.specialization_type

    # ✅ NEW: Update assignment_type
    if request.assignment_type is not None:
        # Validate assignment_type
        valid_types = ["OPEN_ASSIGNMENT", "APPLICATION_BASED"]
        if request.assignment_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid assignment_type: {request.assignment_type}. Must be one of {valid_types}"
            )
        updates["assignment_type"] = {"old": tournament.assignment_type, "new": request.assignment_type}
        tournament.assignment_type = request.assignment_type

    # ✅ NEW: Update participant_type
    if request.participant_type is not None:
        # Validate participant_type
        valid_types = ["INDIVIDUAL", "TEAM", "MIXED"]
        if request.participant_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid participant_type: {request.participant_type}. Must be one of {valid_types}"
            )
        updates["participant_type"] = {"old": tournament.participant_type, "new": request.participant_type}
        tournament.participant_type = request.participant_type

    # ⚠️ NEW: Update tournament_type_id (AUTO-REGENERATES sessions)
    if request.tournament_type_id is not None:
        # Validate tournament type exists
        from app.models.tournament_type import TournamentType
        tournament_type = db.query(TournamentType).filter(TournamentType.id == request.tournament_type_id).first()
        if not tournament_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament type {request.tournament_type_id} not found"
            )

        # ✅ AUTO-DELETE existing sessions if type changes
        if tournament.sessions_generated and tournament.tournament_type_id != request.tournament_type_id:
            from app.models.session import Session as SessionModel
            deleted_count = db.query(SessionModel).filter(SessionModel.semester_id == tournament.id).delete()
            tournament.sessions_generated = False
            tournament.sessions_generated_at = None
            updates["sessions_deleted"] = {"count": deleted_count, "reason": "tournament_type_changed"}

        updates["tournament_type_id"] = {"old": tournament.tournament_type_id, "new": request.tournament_type_id}
        tournament.tournament_type_id = request.tournament_type_id

    # ⚠️ ADMIN OVERRIDE: Update tournament_status (bypasses state machine validation)
    if request.tournament_status is not None:
        # Validate status value exists in VALID_TRANSITIONS
        from app.services.tournament.status_validator import VALID_TRANSITIONS
        if request.tournament_status not in VALID_TRANSITIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tournament_status: {request.tournament_status}. Must be one of {list(VALID_TRANSITIONS.keys())}"
            )

        # Store old status before changing
        old_tournament_status = tournament.tournament_status

        # ✅ ADMIN OVERRIDE: Allow ANY status transition (no validation)
        updates["tournament_status"] = {
            "old": old_tournament_status,
            "new": request.tournament_status,
            "admin_override": True
        }
        tournament.tournament_status = request.tournament_status
        db.flush()

        # ⚠️ TRIGGER AUTO-GENERATION if transitioning to IN_PROGRESS
        if request.tournament_status == "IN_PROGRESS" and not tournament.sessions_generated:
            from app.services.tournament_session_generator import TournamentSessionGenerator

            generator = TournamentSessionGenerator(db)
            can_generate, reason = generator.can_generate_sessions(tournament.id)

            if can_generate:
                session_duration = tournament.match_duration_minutes if tournament.match_duration_minutes else 90
                break_duration = tournament.break_duration_minutes if tournament.break_duration_minutes else 15
                parallel_fields = tournament.parallel_fields if tournament.parallel_fields else 1
                number_of_rounds = tournament.number_of_rounds if tournament.number_of_rounds else 1

                success, message, sessions_created = generator.generate_sessions(
                    tournament_id=tournament.id,
                    parallel_fields=parallel_fields,
                    session_duration_minutes=session_duration,
                    break_minutes=break_duration,
                    number_of_rounds=number_of_rounds
                )

                if success:
                    updates["sessions_auto_generated"] = {
                        "count": len(sessions_created),
                        "rounds": number_of_rounds
                    }
                else:
                    updates["session_generation_failed"] = message
            else:
                updates["session_generation_skipped"] = reason

    # ✅ NEW: Update format (INDIVIDUAL_RANKING vs HEAD_TO_HEAD)
    if request.format is not None:
        updates["format"] = {"old": tournament.format, "new": request.format}
        tournament.format = request.format

    # ✅ NEW: Update scoring_type (TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT)
    if request.scoring_type is not None:
        updates["scoring_type"] = {"old": tournament.scoring_type, "new": request.scoring_type}
        tournament.scoring_type = request.scoring_type

    # ✅ NEW: Update measurement_unit (seconds, meters, points, etc.)
    if request.measurement_unit is not None:
        updates["measurement_unit"] = {"old": tournament.measurement_unit, "new": request.measurement_unit}
        tournament.measurement_unit = request.measurement_unit

    # ✅ NEW: Update ranking_direction (ASC/DESC)
    if request.ranking_direction is not None:
        updates["ranking_direction"] = {"old": tournament.ranking_direction, "new": request.ranking_direction}
        tournament.ranking_direction = request.ranking_direction

    # ⚠️ NEW: Update number_of_rounds (AUTO-REGENERATES sessions if changed)
    if request.number_of_rounds is not None:
        old_rounds = tournament.number_of_rounds

        # ✅ AUTO-DELETE and MARK for regeneration if rounds changed and sessions exist
        if tournament.sessions_generated and old_rounds != request.number_of_rounds:
            from app.models.session import Session as SessionModel
            from app.models.attendance import Attendance

            # Get session IDs to delete
            session_ids = [s.id for s in db.query(SessionModel).filter(
                SessionModel.semester_id == tournament.id,
                SessionModel.auto_generated == True
            ).all()]

            if session_ids:
                # Delete attendance records first
                db.query(Attendance).filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)

                # Delete sessions
                deleted_count = db.query(SessionModel).filter(
                    SessionModel.semester_id == tournament.id,
                    SessionModel.auto_generated == True
                ).delete(synchronize_session=False)

                # Reset flags so lifecycle can regenerate
                tournament.sessions_generated = False
                tournament.sessions_generated_at = None

                updates["sessions_deleted"] = {
                    "count": deleted_count,
                    "reason": f"number_of_rounds changed from {old_rounds} to {request.number_of_rounds}",
                    "note": "Sessions will auto-regenerate when tournament starts (status → IN_PROGRESS)"
                }

        updates["number_of_rounds"] = {"old": old_rounds, "new": request.number_of_rounds}
        tournament.number_of_rounds = request.number_of_rounds

    # If no updates, return early
    if not updates:
        return {
            "tournament_id": tournament.id,
            "message": "No fields updated",
            "updates": {}
        }

    # Save changes
    db.commit()
    db.refresh(tournament)

    return {
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "message": "Tournament updated successfully",
        "updates": updates
    }
