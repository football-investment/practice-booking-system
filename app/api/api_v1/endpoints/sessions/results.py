"""
Session/Game Results Management
Allows master instructor to submit game results for tournament sessions

Phase 2.1: Uses TournamentPhase enum for type safety
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import json

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel, EventCategory
from app.models.tournament_enums import TournamentPhase  # Phase 2.1: Import enum
from app.core.redis_pubsub import publish_tournament_update

router = APIRouter()

import logging as _logging
_logger = _logging.getLogger(__name__)


def _maybe_trigger_auto_ranking(db, tournament_id: int) -> None:
    """
    Trigger ranking calculation when ALL MATCH sessions in the tournament are completed.
    Non-breaking: any failure is logged as WARNING, the result submission is not affected.
    """
    try:
        remaining = (
            db.query(SessionModel)
            .filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.event_category == EventCategory.MATCH,
                SessionModel.session_status != "completed",
            )
            .count()
        )
        if remaining > 0:
            return  # other sessions still pending
        _logger.info(
            f"[auto-ranking] All sessions completed for tournament {tournament_id}. "
            f"Triggering ranking calculation."
        )
        from app.services.tournament.ranking.ranking_service import calculate_and_store_rankings
        result = calculate_and_store_rankings(db, tournament_id)
        _logger.info(
            f"[auto-ranking] Rankings calculated for tournament {tournament_id}: "
            f"{result['rankings_count']} rows."
        )
    except Exception as e:
        _logger.warning(
            f"[auto-ranking] Failed for tournament {tournament_id}: {e}",
            exc_info=True,
        )


def _publish_session_result(db, session: SessionModel) -> None:
    """
    Publish a session_result event to Redis after db.commit().

    Payload conforms to TournamentUpdateEvent (see app.core.redis_pubsub).
    Failures are swallowed — live monitoring must never break the HTTP flow.
    """
    import datetime
    try:
        tournament_id = session.semester_id
        if tournament_id is None:
            return
        completed = (
            db.query(SessionModel)
            .filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.session_status == "completed",
            )
            .count()
        )
        total = (
            db.query(SessionModel)
            .filter(SessionModel.semester_id == tournament_id)
            .count()
        )
        progress = round(completed / total, 4) if total > 0 else 0.0
        publish_tournament_update(
            tournament_id,
            {
                "type": "session_result",
                "session_id": session.id,
                "campus_id": getattr(session, "campus_id", None),
                "pitch_id": getattr(session, "pitch_id", None),
                "round_number": getattr(session, "tournament_round", None),
                "status": "completed",
                "completed_count": completed,
                "total_count": total,
                "progress_pct": progress,
                "completed_at": datetime.datetime.utcnow().isoformat() + "Z",
            },
        )
    except Exception:
        pass  # live monitoring is best-effort


class GameResultEntry(BaseModel):
    """Single participant's game result (INDIVIDUAL tournaments)"""
    user_id: int
    score: float = Field(..., ge=0, description="Score (0-100 or custom scale)")
    rank: int = Field(..., ge=1, description="Final rank/position")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class SubmitGameResultsRequest(BaseModel):
    """Request to submit game results (INDIVIDUAL tournaments)"""
    results: List[GameResultEntry] = Field(..., min_items=1, description="List of participant results")


# ============================================================================
# HEAD_TO_HEAD Match Result Schemas
# ============================================================================

class HeadToHeadParticipantResult(BaseModel):
    """Single participant's result in a HEAD_TO_HEAD match"""
    user_id: int = Field(..., description="Participant user ID")
    score: int = Field(..., ge=0, le=99, description="Match score (0-99)")


class SubmitHeadToHeadMatchRequest(BaseModel):
    """Request to submit HEAD_TO_HEAD match result"""
    results: List[HeadToHeadParticipantResult] = Field(
        ...,
        min_items=2,
        max_items=2,
        description="Exactly 2 participants (Team A vs Team B)"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Optional match notes")


@router.patch("/{session_id}/results", status_code=status.HTTP_200_OK)
def submit_game_results(
    session_id: int,
    request: SubmitGameResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit game results for a tournament session

    Authorization: Master Instructor only (or Admin)
    """
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if tournament game
    if session.event_category != EventCategory.MATCH:
        raise HTTPException(status_code=400, detail="This is not a tournament game session")

    # Authorization: Only master instructor of the tournament or admin
    semester = session.semester
    if current_user.role != UserRole.ADMIN and semester.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the tournament's master instructor can submit results"
        )

    # ✅ Store results in rounds_data for finalization compatibility
    # Convert game results (score+rank) to round_results format (round 1)
    round_results = {}
    for entry in request.results:
        # Store score as string (finalization expects string values)
        round_results[str(entry.user_id)] = str(entry.score)

    # Update rounds_data (create new dict to trigger SQLAlchemy change detection)
    session.rounds_data = {
        "total_rounds": 1,
        "completed_rounds": 1,
        "round_results": {
            "1": round_results  # Round 1 results
        }
    }

    # ⚠️ DO NOT write to session.game_results here
    # The finalization process will write the final format to game_results
    # Writing here would conflict with finalization's idempotency check

    # Mark JSONB field as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "rounds_data")

    session.session_status = "completed"

    db.commit()
    db.refresh(session)
    _publish_session_result(db, session)
    _maybe_trigger_auto_ranking(db, session.semester_id)

    return {
        "session_id": session_id,
        "game_type": session.game_type,
        "results_count": len(request.results),
        "message": "Game results submitted successfully"
    }


@router.get("/{session_id}/results", status_code=status.HTTP_200_OK)
def get_game_results(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get game results for a tournament session

    Returns empty list if no results submitted yet
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if tournament game
    if session.event_category != EventCategory.MATCH:
        raise HTTPException(status_code=400, detail="This is not a tournament game session")

    # Parse results from rounds_data (submitted results) or game_results (finalized)
    results = []

    # Check if results are in rounds_data (submitted but not finalized)
    if session.rounds_data and "round_results" in session.rounds_data:
        round_1_results = session.rounds_data.get("round_results", {}).get("1", {})
        results = [
            {
                "user_id": int(user_id),
                "score": float(score) if score else 0.0,
                "rank": idx + 1  # Approximation - actual rank would need sorting
            }
            for idx, (user_id, score) in enumerate(round_1_results.items())
        ]

    # Check if finalized (game_results contains full finalization data)
    elif session.game_results:
        try:
            finalized_data = json.loads(session.game_results)
            # Extract derived_rankings from finalized data
            if isinstance(finalized_data, dict) and "derived_rankings" in finalized_data:
                results = finalized_data["derived_rankings"]
            else:
                results = []
        except json.JSONDecodeError:
            results = []

    return {
        "session_id": session_id,
        "game_type": session.game_type,
        "results": results,
        "finalized": bool(session.game_results)
    }


# ============================================================================
# HEAD_TO_HEAD Match Result Submission Endpoint
# ============================================================================

@router.patch("/{session_id}/head-to-head-results", status_code=status.HTTP_200_OK)
def submit_head_to_head_match_result(
    session_id: int,
    request: SubmitHeadToHeadMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit HEAD_TO_HEAD match result for a tournament session (League/Knockout)

    Validates:
    - Exactly 2 participants
    - Both participants present (attendance)
    - Scores are non-negative integers
    - Session is HEAD_TO_HEAD format

    Stores result in session.game_results as JSONB

    Authorization: Master Instructor only (or Admin)
    """
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if tournament game
    if session.event_category != EventCategory.MATCH:
        raise HTTPException(status_code=400, detail="This is not a tournament game session")

    # Validate HEAD_TO_HEAD format
    semester = session.semester
    if semester.format != "HEAD_TO_HEAD":
        raise HTTPException(
            status_code=400,
            detail=f"This endpoint is for HEAD_TO_HEAD tournaments only. Tournament format: {semester.format}"
        )

    # Validate INDIVIDUAL participant type — TEAM tournaments must use /team-results
    cfg = semester.tournament_config_obj
    if cfg and cfg.participant_type == "TEAM":
        raise HTTPException(
            status_code=400,
            detail=(
                "HEAD_TO_HEAD result submission is only supported for INDIVIDUAL tournaments. "
                "TEAM tournaments must use PATCH /sessions/{id}/team-results instead."
            ),
        )

    # Authorization: Only master instructor of the tournament or admin
    if current_user.role != UserRole.ADMIN and semester.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the tournament's master instructor can submit results"
        )

    # Validate exactly 2 participants
    if len(request.results) != 2:
        raise HTTPException(
            status_code=400,
            detail="HEAD_TO_HEAD matches require exactly 2 participants"
        )

    # Get participant IDs
    participant_ids = [r.user_id for r in request.results]

    # Validate participants are enrolled in the tournament
    from app.models.semester_enrollment import SemesterEnrollment
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == semester.id,
        SemesterEnrollment.user_id.in_(participant_ids),
        SemesterEnrollment.is_active == True
    ).all()

    if len(enrollments) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Both participants must be enrolled in tournament {semester.id}. Found {len(enrollments)} enrollments."
        )

    # Determine winner
    result_a = request.results[0]
    result_b = request.results[1]

    if result_a.score > result_b.score:
        winner_id = result_a.user_id
        result_a_status = "win"
        result_b_status = "loss"
    elif result_b.score > result_a.score:
        winner_id = result_b.user_id
        result_a_status = "loss"
        result_b_status = "win"
    else:
        # Tie
        winner_id = None
        result_a_status = "tie"
        result_b_status = "tie"

    # Get tournament type info
    tournament_type_code = None
    if semester.tournament_config_obj and semester.tournament_config_obj.tournament_type:
        tournament_type_code = semester.tournament_config_obj.tournament_type.code

    # Build game_results JSONB structure
    import datetime
    game_results_data = {
        "match_format": "HEAD_TO_HEAD",
        "tournament_type": tournament_type_code,  # "league" or "knockout"
        "participants": [
            {
                "user_id": result_a.user_id,
                "score": result_a.score,
                "result": result_a_status
            },
            {
                "user_id": result_b.user_id,
                "score": result_b.score,
                "result": result_b_status
            }
        ],
        "winner_user_id": winner_id,
        "match_status": "completed",
        "submitted_at": datetime.datetime.utcnow().isoformat(),
        "submitted_by": current_user.id,
        "notes": request.notes
    }

    # Store in session.game_results
    session.game_results = json.dumps(game_results_data)
    session.session_status = "completed"

    # Mark field as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "game_results")

    db.commit()
    db.refresh(session)
    _publish_session_result(db, session)
    _maybe_trigger_auto_ranking(db, session.semester_id)

    # Phase 2.1: Use TournamentPhase enum for type-safe comparison
    progression_result = None
    if session.tournament_phase == TournamentPhase.KNOCKOUT:
        try:
            from app.services.tournament.knockout_progression_service import KnockoutProgressionService
            progression_service = KnockoutProgressionService(db)

            # ✅ FIX: Use process_knockout_progression() which handles all rounds dynamically
            progression_result = progression_service.process_knockout_progression(
                session=session,
                tournament=semester,
                game_results=game_results_data
            )

            # Phase 2.1: Production-ready progression logging
            if progression_result and "updated_sessions" in progression_result:
                # Successfully updated next-round matches
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Knockout progression: {progression_result['message']}",
                           extra={"session_id": session_id, "updated_sessions": progression_result['updated_sessions']})
        except Exception as e:
            # Log error but don't fail the result submission
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Knockout progression error: {e}",
                        extra={"session_id": session_id}, exc_info=True)

    return {
        "session_id": session_id,
        "match_format": "HEAD_TO_HEAD",
        "tournament_type": tournament_type_code,
        "winner_user_id": winner_id,
        "result": "tie" if winner_id is None else "win/loss",
        "message": "HEAD_TO_HEAD match result submitted successfully",
        "knockout_progression": progression_result  # Include progression info
    }


# ─── TEAM RESULTS ─────────────────────────────────────────────────────────────

class TeamResultEntry(BaseModel):
    """Single team's result for a TEAM tournament session"""
    team_id: int
    score: float = Field(..., description="Score for this team in this session")
    rank: Optional[int] = Field(None, ge=1, description="Optional rank override; auto-computed if None")


class SubmitTeamResultsRequest(BaseModel):
    """Submit results for a TEAM tournament session (one or more rounds)"""
    results: List[TeamResultEntry]
    round_number: int = Field(1, ge=1, description="Round number within the session (1-based)")


@router.patch("/{session_id}/team-results", status_code=status.HTTP_200_OK)
def submit_team_results(
    session_id: int,
    request: SubmitTeamResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit results for a TEAM tournament session.

    Writes team scores into rounds_data["round_results"][str(round_number)]
    using "team_{team_id}" keys, mirroring the INDIVIDUAL format of "user_{user_id}".

    Authorization: Admin or Master Instructor of the tournament.
    Idempotent: re-submitting the same round overwrites previous results.
    """
    from sqlalchemy.orm.attributes import flag_modified
    from app.models.semester import Semester

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify this session belongs to a TEAM tournament
    tournament = db.query(Semester).filter(Semester.id == session.semester_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    cfg = tournament.tournament_config_obj
    if not cfg or cfg.participant_type != "TEAM":
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only for TEAM tournaments. "
                   "Use PATCH /sessions/{id}/results for INDIVIDUAL tournaments."
        )

    # Authorization
    if current_user.role != UserRole.ADMIN and tournament.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the tournament's master instructor or admin can submit results"
        )

    if not request.results:
        raise HTTPException(status_code=400, detail="No results provided")

    # Build round_results dict: {"team_42": "95.5", "team_43": "82.0"}
    round_results = {f"team_{e.team_id}": str(e.score) for e in request.results}

    rd = dict(session.rounds_data) if session.rounds_data else {}
    if "round_results" not in rd:
        rd["round_results"] = {}
    rd["round_results"][str(request.round_number)] = round_results
    rd["completed_rounds"] = max(rd.get("completed_rounds", 0), request.round_number)

    session.rounds_data = rd
    flag_modified(session, "rounds_data")
    db.commit()
    db.refresh(session)
    _publish_session_result(db, session)

    return {
        "session_id": session_id,
        "round_number": request.round_number,
        "teams_recorded": len(request.results),
        "round_results": round_results,
        "message": "Team results submitted successfully"
    }
