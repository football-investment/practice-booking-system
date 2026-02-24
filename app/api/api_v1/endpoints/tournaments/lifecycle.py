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

                # Reset flags (write to config object — Semester properties are read-only)
                if tournament.tournament_config_obj:
                    tournament.tournament_config_obj.sessions_generated = False
                    tournament.tournament_config_obj.sessions_generated_at = None
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
            if tournament.reward_config_obj:
                tournament.reward_config_obj.reward_policy_snapshot = tournament.reward_config
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
            # Write to config object — Semester properties are read-only proxies
            if tournament.tournament_config_obj:
                tournament.tournament_config_obj.sessions_generated = False
                tournament.tournament_config_obj.sessions_generated_at = None
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
            # Write to config object — Semester.enrollment_snapshot is a read-only proxy property
            if tournament.tournament_config_obj:
                tournament.tournament_config_obj.enrollment_snapshot = enrollment_snapshot
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
            tsh.created_at,
            tsh.reason,
            tsh.extra_metadata
        FROM tournament_status_history tsh
        JOIN users u ON tsh.changed_by = u.id
        WHERE tsh.tournament_id = :tournament_id
        ORDER BY tsh.created_at DESC
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
            changed_at=row.created_at.isoformat(),
            reason=row.reason,
            metadata=row.extra_metadata
        )
        for row in history_rows
    ]

    return StatusHistoryResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        current_status=tournament.tournament_status,
        history=history
    )
