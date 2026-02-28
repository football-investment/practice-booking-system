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
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, ConfigDict, Field
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
    """Single player result entry (legacy format)"""
    user_id: int = Field(..., ge=1, description="User ID (must be positive)")
    rank: int = Field(..., ge=1, description="Rank/placement (1st, 2nd, 3rd, etc.)")
    score: Optional[float] = Field(None, ge=0.0, description="Optional score/points (non-negative)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class RecordMatchResultsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request schema for recording match results (legacy endpoint)"""
    results: List[MatchResultEntry] = Field(..., min_items=1, description="List of match results (min 1 participant)")
    match_notes: Optional[str] = Field(None, max_length=1000, description="Optional match notes")


# ============================================================================
# Typed Result Models for Structured Submission (Type-safe Validation)
# ============================================================================

class IndividualRankingResult(BaseModel):
    """Result for INDIVIDUAL_RANKING tournaments"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    placement: int = Field(..., ge=1, description="Final placement (1st, 2nd, 3rd, etc.)")
    score: Optional[float] = Field(None, ge=0.0, description="Optional score")


class HeadToHeadWinLossResult(BaseModel):
    """Result for HEAD_TO_HEAD tournaments (WIN/LOSS format)"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    result: Literal["WIN", "LOSS", "TIE"] = Field(..., description="Match result (WIN/LOSS/TIE)")


class HeadToHeadScoreResult(BaseModel):
    """Result for HEAD_TO_HEAD tournaments (SCORE format)"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    score: int = Field(..., ge=0, le=999, description="Match score (0-999)")


class TeamMatchResult(BaseModel):
    """Result for TEAM_MATCH tournaments"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    team: str = Field(..., min_length=1, max_length=10, description="Team identifier (e.g., 'A', 'B', 'RED', 'BLUE')")
    team_score: int = Field(..., ge=0, le=999, description="Team score (0-999)")
    opponent_score: int = Field(..., ge=0, le=999, description="Opponent score (0-999)")


class TimeBasedResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Result for TIME_BASED tournaments (time trials)"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    time_seconds: float = Field(..., gt=0.0, le=86400.0, description="Time in seconds (must be positive, max 24 hours)")


class SkillRatingResult(BaseModel):
    """Result for SKILL_RATING tournaments"""
    user_id: int = Field(..., ge=1, description="Participant user ID")
    rating: float = Field(..., ge=0.0, le=10.0, description="Skill rating (0.0-10.0)")
    criteria_scores: Optional[Dict[str, float]] = Field(None, description="Optional detailed criteria scores")


# Union type for all result formats (enables type-safe validation)
ResultEntryUnion = Union[
    IndividualRankingResult,
    HeadToHeadWinLossResult,
    HeadToHeadScoreResult,
    TeamMatchResult,
    TimeBasedResult,
    SkillRatingResult
]


class SubmitMatchResultsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """
    Structured match results submission (Type-safe with Union validation)

    Supports all match formats:
    - INDIVIDUAL_RANKING: IndividualRankingResult (user_id, placement)
    - HEAD_TO_HEAD (WIN_LOSS): HeadToHeadWinLossResult (user_id, result: "WIN"/"LOSS"/"TIE")
    - HEAD_TO_HEAD (SCORE): HeadToHeadScoreResult (user_id, score)
    - TEAM_MATCH: TeamMatchResult (user_id, team, team_score, opponent_score)
    - TIME_BASED: TimeBasedResult (user_id, time_seconds)
    - SKILL_RATING: SkillRatingResult (user_id, rating, criteria_scores)

    Pydantic validates each result entry against all Union types until a match is found.
    """
    results: List[ResultEntryUnion] = Field(..., min_items=1, description="List of match results (min 1 participant)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional match notes")


class SubmitRoundResultsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """
    Round-based results submission for INDIVIDUAL_RANKING tournaments.

    This endpoint is idempotent - submitting the same round multiple times will overwrite previous results.

    Example for TIME_BASED:
    {
        "round_number": 1,
        "results": {"123": "12.5s", "456": "13.2s"}
    }
    """
    round_number: int = Field(..., ge=1, le=100, description="Round number (1-100)")
    results: Dict[str, str] = Field(
        ...,
        min_length=1,
        description="User results map: user_id -> measured_value (e.g., '12.5s', '95 points'). Min 1 participant."
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Optional round notes")


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

    # Convert Pydantic models to dict for business logic compatibility
    raw_results = [r.model_dump() for r in request.results]

    try:
        result = processor.process_match_results(
            db=db,
            session=session,
            tournament=tournament,
            raw_results=raw_results,
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

    all_done = rounds_data['completed_rounds'] >= int(total_rounds)
    rankings_calculated = False

    # ── Auto-calculate rankings when all rounds are complete ──────────────────
    if all_done:
        try:
            from app.models.tournament_ranking import TournamentRanking
            from app.services.tournament.results.calculators.ranking_aggregator import RankingAggregator

            # Extract combined round_results from all IR sessions
            all_sessions_for_ranking = db.query(SessionModel).filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.is_tournament_game == True,
            ).all()

            combined_round_results: Dict[str, Any] = {}
            for _s in all_sessions_for_ranking:
                _rd = _s.rounds_data or {}
                _rr = _rd.get("round_results", {})
                if isinstance(_rr, dict):
                    for _rk, _pv in _rr.items():
                        if isinstance(_pv, dict):
                            combined_round_results[_rk] = _pv

            if combined_round_results:
                # Get ranking_direction (ASC = lowest wins, DESC = highest wins)
                ranking_direction = "ASC"
                if tournament.tournament_config_obj:
                    ranking_direction = tournament.tournament_config_obj.ranking_direction or "ASC"

                user_final_values = RankingAggregator.aggregate_user_values(
                    combined_round_results, ranking_direction
                )
                performance_rankings = RankingAggregator.calculate_performance_rankings(
                    user_final_values, ranking_direction
                )

                # Overwrite existing rankings (idempotent)
                db.query(TournamentRanking).filter(
                    TournamentRanking.tournament_id == tournament_id
                ).delete()

                for entry in performance_rankings:
                    db.add(TournamentRanking(
                        tournament_id=tournament_id,
                        user_id=entry["user_id"],
                        participant_type="INDIVIDUAL",
                        rank=entry["rank"],
                        points=entry["final_value"],
                    ))

                db.commit()
                rankings_calculated = True
        except Exception as _e:
            # Ranking calculation is best-effort; don't fail the round submission
            import logging
            logging.getLogger(__name__).warning(
                "Auto-ranking after round %d failed for tournament %d: %s",
                round_number, tournament_id, _e
            )

    return {
        "success": True,
        "message": f"Round {round_number} results saved successfully",
        "session_id": session_id,
        "round_number": round_number,
        "rounds_data": session.rounds_data,
        "all_rounds_complete": all_done,
        "rankings_calculated": rankings_calculated,
        "notes": request.notes
    }


# Export router
__all__ = ["router"]
