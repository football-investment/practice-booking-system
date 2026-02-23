"""
Tournament Admin Update Endpoint
Extracted from lifecycle.py as part of file-size refactoring (lifecycle.py was 1133 lines).
Boundary: lifecycle.py lines 818–1133.

Single endpoint:
  PATCH /{tournament_id} — Admin updates 15+ tournament fields with auto-session triggers.

WARNING: tournament_status field in TournamentUpdateRequest bypasses the state machine
(admin override). Use PATCH /{id}/status for validated status transitions.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.api_v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.specialization import SpecializationType
from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

router = APIRouter()


# ============================================================================
# SCHEMA
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
    # ✅ NEW: Campus assignment (required before ENROLLMENT_OPEN status)
    campus_id: Optional[int] = Field(None, description="Campus ID where tournament will be held")


# ============================================================================
# ENDPOINT
# ============================================================================

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

    # ✅ NEW: Update campus_id (required for ENROLLMENT_OPEN status)
    if request.campus_id is not None:
        # Validate campus exists
        from app.models.campus import Campus
        campus = db.query(Campus).filter(Campus.id == request.campus_id).first()
        if not campus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campus {request.campus_id} not found"
            )
        updates["campus_id"] = {"old": tournament.campus_id, "new": request.campus_id}
        tournament.campus_id = request.campus_id

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
            if tournament.tournament_config_obj:
                tournament.tournament_config_obj.sessions_generated = False
                tournament.tournament_config_obj.sessions_generated_at = None
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
                if tournament.tournament_config_obj:
                    tournament.tournament_config_obj.sessions_generated = False
                    tournament.tournament_config_obj.sessions_generated_at = None

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
