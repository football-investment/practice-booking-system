"""
Tournament Match Results Submission Endpoints

Handles submission of match results in various formats.
Refactored from match_results.py as part of P2 decomposition.

Endpoints:
- POST /{tournament_id}/sessions/{session_id}/submit-results: Submit structured match results
- PATCH /{tournament_id}/sessions/{session_id}/results: Record match results (legacy)
- POST /{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results: Submit round results
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.dependencies import get_current_user

# Import shared services
from app.repositories.tournament_repository import TournamentRepository
from app.services.shared.auth_validator import require_admin_or_instructor
from app.services.tournament.result_processor import ResultProcessor
from app.services.tournament.results.validators import ResultValidator

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class MatchResultEntry(BaseModel):
    """Single player result entry"""
    user_id: int
    rank: int  # 1st, 2nd, 3rd, etc.
    score: Optional[float] = None  # Optional score/points
    notes: Optional[str] = None


class RecordMatchResultsRequest(BaseModel):
    """Request schema for recording match results"""
    results: list[MatchResultEntry]
    match_notes: Optional[str] = None


class SubmitMatchResultsRequest(BaseModel):
    """
    Structured match results submission

    Format depends on match_format:
    - INDIVIDUAL_RANKING: [{"user_id": 1, "placement": 1}, ...]
    - HEAD_TO_HEAD (WIN_LOSS): [{"user_id": 1, "result": "WIN"}, {"user_id": 2, "result": "LOSS"}]
    - HEAD_TO_HEAD (SCORE): [{"user_id": 1, "score": 3}, {"user_id": 2, "score": 1}]
    - TEAM_MATCH: [{"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3}, ...]
    - TIME_BASED: [{"user_id": 1, "time_seconds": 12.45}, ...]
    - SKILL_RATING: [{"user_id": 1, "rating": 8.5, "criteria_scores": {...}}, ...]
    """
    results: list[Dict[str, Any]]
    notes: Optional[str] = None


class SubmitRoundResultsRequest(BaseModel):
    """
    Round-based results submission for INDIVIDUAL_RANKING tournaments.

    This endpoint is idempotent - submitting the same round multiple times will overwrite previous results.

    Example for TIME_BASED:
    {
        "round_number": 1,
        "results": {"123": "12.5s", "456": "13.2s"}
    }
    """
    round_number: int
    results: Dict[str, str]  # user_id -> measured_value (e.g., "12.5s", "95 points")
    notes: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_session_or_404(
    db: Session,
    tournament_id: int,
    session_id: int
) -> SessionModel:
    """
    Get session or raise 404.

    Args:
        db: Database session
        tournament_id: Tournament ID
        session_id: Session ID

    Returns:
        Session instance

    Raises:
        HTTPException: If session not found or not a tournament match
    """
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    if not session.is_tournament_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not a tournament match"
        )

    return session


def check_instructor_access(
    current_user: User,
    tournament: Semester
) -> None:
    """
    Check if instructor has access to tournament.

    Args:
        current_user: Current user
        tournament: Tournament instance

    Raises:
        HTTPException: If instructor doesn't have access
    """
    if current_user.role == UserRole.ADMIN:
        return  # Admin can access any tournament

    if current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can record match results"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/sessions/{session_id}/submit-results")
def submit_structured_match_results(
    tournament_id: int,
    session_id: int,
    request: SubmitMatchResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit structured match results (supports all match formats).

    This endpoint processes match results and:
    1. Validates raw results based on match_format
    2. Derives rankings using format-specific processor
    3. Stores both raw_results and derived_rankings in session.game_results
    4. Returns success message with derived rankings

    Match Format Support:
    - INDIVIDUAL_RANKING: Placement-based (1st, 2nd, 3rd, ...)
    - HEAD_TO_HEAD: 1v1 with WIN_LOSS or SCORE_BASED
    - TEAM_MATCH: Team assignments with scoring
    - TIME_BASED: Time trial competitions
    - SKILL_RATING: Skill evaluation (extension point)

    Authorization: INSTRUCTOR (assigned to tournament) or ADMIN
    """
    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Check authorization
    check_instructor_access(current_user, tournament)

    # Get session
    session = get_session_or_404(db, tournament_id, session_id)

    # Process results using result processor
    processor = ResultProcessor(db)

    try:
        result = processor.process_match_results(
            db=db,
            session=session,
            tournament=tournament,
            raw_results=request.results,
            match_notes=request.notes,
            recorded_by_user_id=current_user.id,
            recorded_by_name=current_user.name or current_user.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": f"Results recorded successfully for {len(result['derived_rankings'])} participants",
        "session_id": session.id,
        "tournament_id": tournament_id,
        "match_format": session.match_format,
        "rankings": result["derived_rankings"],
        "recorded_at": result["recorded_at"],
        "recorded_by": current_user.name or current_user.email
    }


@router.patch("/{tournament_id}/sessions/{session_id}/results")
async def record_match_results(
    tournament_id: int,
    session_id: int,
    result_data: RecordMatchResultsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Record results for a tournament match (session).

    - Stores results in session.game_results JSONB field
    - Updates tournament_rankings table with points
    - Auto-calculates standings based on points system

    Points System (default):
    - 1st place: 3 points
    - 2nd place: 2 points
    - 3rd place: 1 point
    - Participation: 0 points

    Authorization: INSTRUCTOR (must be assigned to tournament) or ADMIN

    LEGACY ENDPOINT: Consider using POST /submit-results instead
    """
    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Check authorization
    check_instructor_access(current_user, tournament)

    # Get session
    session = get_session_or_404(db, tournament_id, session_id)

    if session.game_results is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results have already been recorded for this match"
        )

    # Validate results using validator
    validator = ResultValidator(db)
    user_ids = [r.user_id for r in result_data.results]
    ranks = [r.rank for r in result_data.results]

    is_valid, error_message = validator.validate_match_results(
        tournament_id, user_ids, ranks
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Store results in session
    results_dict = {
        "recorded_at": datetime.utcnow().isoformat(),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name,
        "match_notes": result_data.match_notes,
        "results": [
            {
                "user_id": r.user_id,
                "rank": r.rank,
                "score": r.score,
                "notes": r.notes
            }
            for r in result_data.results
        ]
    }

    # Convert dict to JSON string (game_results is Text type, not JSONB)
    session.game_results = json.dumps(results_dict)
    db.flush()

    # Update ranks (for reward distribution)
    db.execute(
        text("""
        UPDATE tournament_rankings tr
        SET rank = ranked.row_num
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (ORDER BY COALESCE(points, 0) DESC, updated_at ASC) as row_num
            FROM tournament_rankings
            WHERE tournament_id = :tournament_id
        ) ranked
        WHERE tr.id = ranked.id
        """),
        {"tournament_id": tournament_id}
    )

    db.commit()
    db.refresh(session)

    return {
        "message": "Match results recorded successfully",
        "session_id": session.id,
        "match_name": session.title,
        "tournament_id": tournament_id,
        "results": results_dict["results"],
        "recorded_at": results_dict["recorded_at"],
        "recorded_by": current_user.name
    }


@router.post("/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results")
def submit_round_results(
    tournament_id: int,
    session_id: int,
    round_number: int,
    request: SubmitRoundResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit results for a specific round in an INDIVIDUAL_RANKING tournament.

    This endpoint is **idempotent** - submitting the same round multiple times will overwrite previous results.

    Authorization:
    - INSTRUCTOR assigned to tournament
    - ADMIN

    Workflow:
    1. Validate session exists and belongs to tournament
    2. Validate session is INDIVIDUAL_RANKING format
    3. Validate round_number is within range (1 to total_rounds)
    4. Update rounds_data.round_results[round_number] with new results
    5. Update rounds_data.completed_rounds count
    6. Return updated rounds_data
    """
    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Get session
    session = get_session_or_404(db, tournament_id, session_id)

    # Verify session is INDIVIDUAL_RANKING
    if session.match_format != "INDIVIDUAL_RANKING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round-based results only supported for INDIVIDUAL_RANKING tournaments (session format: {session.match_format})"
        )

    # Authorization check
    require_admin_or_instructor(current_user)

    # Verify instructor is assigned to this tournament or session
    if current_user.role == UserRole.INSTRUCTOR:
        if session.instructor_id != current_user.id and tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned instructor for this session"
            )

    # Get current rounds_data
    rounds_data = session.rounds_data or {}
    total_rounds = rounds_data.get('total_rounds', 1)

    # Validate round_number
    if round_number < 1 or round_number > total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid round_number {round_number}. Must be between 1 and {total_rounds}"
        )

    # Ensure rounds_data structure exists
    if 'round_results' not in rounds_data:
        rounds_data['round_results'] = {}

    # Update round results (idempotent - overwrites if exists)
    rounds_data['round_results'][str(round_number)] = request.results

    # Update completed_rounds count (count of unique round keys)
    rounds_data['completed_rounds'] = len(rounds_data['round_results'])

    # Save updated rounds_data
    session.rounds_data = rounds_data

    # Tell SQLAlchemy that JSONB field was modified (required for dict mutations)
    flag_modified(session, 'rounds_data')

    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": f"Round {round_number} results saved successfully",
        "session_id": session_id,
        "round_number": round_number,
        "rounds_data": session.rounds_data,
        "notes": request.notes
    }


# Export router
__all__ = ["router"]
