"""
Tournament Session Generation API Endpoint

CRITICAL: Sessions are generated ONLY after enrollment closes (tournament_status = IN_PROGRESS)

Provides:
1. Preview of session structure (before generation)
2. Actual session generation (creates sessions in DB)
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.services.tournament_session_generator import TournamentSessionGenerator


router = APIRouter()


class SessionGenerationRequest(BaseModel):
    """Request body for session generation"""
    parallel_fields: int = Field(default=1, ge=1, le=10, description="Number of fields available for parallel matches")
    session_duration_minutes: int = Field(default=90, ge=1, le=180, description="Duration of each session in minutes (business allows 1-5 min matches)")
    break_minutes: int = Field(default=15, ge=0, le=60, description="Break time between sessions in minutes")


class SessionPreview(BaseModel):
    """Preview of a single session"""
    title: str
    description: str
    date_start: str
    date_end: str
    game_type: str
    tournament_phase: str
    tournament_round: int
    tournament_match_number: int


class SessionGenerationResponse(BaseModel):
    """Response for session generation"""
    success: bool
    message: str
    tournament_id: int
    tournament_name: str
    sessions_generated_count: int
    sessions: Optional[List[Dict[str, Any]]] = None


@router.get("/{tournament_id}/preview-sessions", response_model=Dict[str, Any])
def preview_tournament_sessions(
    tournament_id: int,
    parallel_fields: int = 1,
    session_duration_minutes: int = 90,
    break_minutes: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Preview tournament session structure WITHOUT creating sessions in database

    **Authorization:** Admin only

    **Parameters:**
    - `tournament_id`: Tournament (Semester) ID
    - `parallel_fields`: Number of fields for parallel matches (default: 1)
    - `session_duration_minutes`: Session duration (default: 90)
    - `break_minutes`: Break between sessions (default: 15)

    **Returns:**
    - Tournament info
    - Tournament type config
    - Player count (enrolled)
    - Estimated sessions (preview)

    **Response Example:**
    ```json
    {
        "tournament_id": 121,
        "tournament_name": "🇭🇺 HU - Winter Cup - Budapest",
        "tournament_type": "League (Round Robin)",
        "player_count": 8,
        "parallel_fields": 1,
        "estimated_sessions": [
            {
                "title": "Winter Cup - Round 1 - Match 1",
                "date_start": "2026-01-20T09:00:00",
                "date_end": "2026-01-20T10:30:00",
                "game_type": "Round 1",
                "tournament_phase": "League",
                "tournament_round": 1,
                "tournament_match_number": 1
            }
        ],
        "total_matches": 28,
        "total_rounds": 7,
        "estimated_duration_minutes": 1260
    }
    ```
    """
    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    # Check if tournament has tournament_type_id
    if not tournament.tournament_type_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament does not have a tournament type configured. Cannot generate preview."
        )

    # Fetch tournament type
    tournament_type = db.query(TournamentType).filter(
        TournamentType.id == tournament.tournament_type_id
    ).first()

    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament type configuration not found"
        )

    # Get enrolled player count
    from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus

    player_count = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True,
        SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
    ).count()

    if player_count < tournament_type.min_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough players enrolled. Need at least {tournament_type.min_players}, have {player_count}"
        )

    # Validate player count
    is_valid, error_msg = tournament_type.validate_player_count(player_count)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Use semester's saved schedule configuration if available, otherwise use query parameters
    session_duration = tournament.match_duration_minutes if tournament.match_duration_minutes else session_duration_minutes
    break_duration = tournament.break_duration_minutes if tournament.break_duration_minutes else break_minutes

    # Generate preview (call generator service in DRY_RUN mode)
    generator = TournamentSessionGenerator(db)

    # Generate session structure (same logic as actual generation, but don't commit)
    if tournament_type.code == "league":
        sessions = generator._generate_league_sessions(
            tournament, tournament_type, player_count, parallel_fields,
            session_duration, break_duration
        )
    elif tournament_type.code == "knockout":
        sessions = generator._generate_knockout_sessions(
            tournament, tournament_type, player_count, parallel_fields,
            session_duration, break_duration
        )
    elif tournament_type.code == "group_knockout":
        sessions = generator._generate_group_knockout_sessions(
            tournament, tournament_type, player_count, parallel_fields,
            session_duration, break_duration
        )
    elif tournament_type.code == "swiss":
        sessions = generator._generate_swiss_sessions(
            tournament, tournament_type, player_count, parallel_fields,
            session_duration, break_duration
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tournament type: {tournament_type.code}"
        )

    # Estimate duration
    estimation = tournament_type.estimate_duration(player_count, parallel_fields)

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "tournament_type": tournament_type.display_name,
        "player_count": player_count,
        "parallel_fields": parallel_fields,
        "estimated_sessions": sessions,
        "total_matches": estimation['total_matches'],
        "total_rounds": estimation['total_rounds'],
        "estimated_duration_minutes": estimation['estimated_duration_minutes']
    }


@router.post("/{tournament_id}/generate-sessions", response_model=SessionGenerationResponse)
def generate_tournament_sessions(
    tournament_id: int,
    request: SessionGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> SessionGenerationResponse:
    """
    Generate tournament sessions based on tournament type and enrolled player count

    **CRITICAL CONSTRAINT:** Sessions can ONLY be generated when tournament_status = "IN_PROGRESS"
    (i.e., AFTER enrollment closes)

    **Authorization:** Admin only

    **Validations:**
    1. Tournament exists and has tournament_type_id
    2. Tournament status is IN_PROGRESS (enrollment closed)
    3. Sessions not already generated (sessions_generated = False)
    4. Sufficient player count (>= min_players for tournament type)
    5. Player count meets tournament type constraints (e.g., power-of-2 for knockout)

    **Creates:**
    - Session records in database (auto_generated = True)
    - Sets tournament.sessions_generated = True
    - Records tournament.sessions_generated_at timestamp

    **Response Example:**
    ```json
    {
        "success": true,
        "message": "Successfully generated 28 sessions",
        "tournament_id": 121,
        "tournament_name": "Winter Cup",
        "sessions_generated_count": 28,
        "sessions": [...]
    }
    ```

    **Error Scenarios:**
    - 400: Tournament not ready (wrong status, already generated, etc.)
    - 404: Tournament or tournament type not found
    """
    generator = TournamentSessionGenerator(db)

    # Check if can generate (includes all validations)
    can_generate, reason = generator.can_generate_sessions(tournament_id)
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
        )

    # Fetch tournament to get schedule configuration
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    # Use semester's saved schedule configuration if available, otherwise use request parameters
    # Admin sets these via schedule editor BEFORE generating sessions
    session_duration = tournament.match_duration_minutes if tournament.match_duration_minutes else request.session_duration_minutes
    break_duration = tournament.break_duration_minutes if tournament.break_duration_minutes else request.break_minutes
    parallel_fields = tournament.parallel_fields if tournament.parallel_fields else request.parallel_fields

    # Generate sessions
    success, message, sessions_created = generator.generate_sessions(
        tournament_id=tournament_id,
        parallel_fields=parallel_fields,
        session_duration_minutes=session_duration,
        break_minutes=break_duration
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    # Fetch tournament for response
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    return SessionGenerationResponse(
        success=True,
        message=message,
        tournament_id=tournament_id,
        tournament_name=tournament.name,
        sessions_generated_count=len(sessions_created),
        sessions=sessions_created
    )


@router.delete("/{tournament_id}/sessions", response_model=Dict[str, Any])
def delete_generated_sessions(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Delete all auto-generated sessions for a tournament (RESET functionality)

    **Authorization:** Admin only

    **Use Case:** If admin needs to regenerate sessions with different parameters

    **CAUTION:** This will delete ALL auto-generated sessions for this tournament.
    Manual sessions (auto_generated = False) are NOT deleted.

    **Response Example:**
    ```json
    {
        "success": true,
        "message": "Deleted 28 auto-generated sessions",
        "deleted_count": 28
    }
    ```
    """
    from app.models.session import Session as SessionModel
    from app.models.attendance import Attendance

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    # Get session IDs that will be deleted
    session_ids_to_delete = [
        s.id for s in db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.auto_generated == True
        ).all()
    ]

    if not session_ids_to_delete:
        return {
            "success": True,
            "message": "No auto-generated sessions to delete",
            "deleted_count": 0
        }

    # 1. Delete attendance records first (foreign key dependency)
    attendance_deleted = db.query(Attendance).filter(
        Attendance.session_id.in_(session_ids_to_delete)
    ).delete(synchronize_session=False)

    # 2. Delete only auto-generated sessions
    deleted_count = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.auto_generated == True
    ).delete(synchronize_session=False)

    # 3. Reset generation flags
    tournament.sessions_generated = False
    tournament.sessions_generated_at = None

    db.commit()

    return {
        "success": True,
        "message": f"Deleted {deleted_count} auto-generated sessions",
        "deleted_count": deleted_count
    }
