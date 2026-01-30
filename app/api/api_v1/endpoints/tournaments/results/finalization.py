"""
Tournament Finalization Endpoints

Handles finalization of tournament stages and sessions.
Refactored from match_results.py as part of P2 decomposition.

Endpoints:
- POST /{tournament_id}/finalize-group-stage: Finalize group stage
- POST /{tournament_id}/finalize-tournament: Finalize tournament
- POST /{tournament_id}/sessions/{session_id}/finalize: Finalize individual ranking session
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel
from app.dependencies import get_current_user

# Import shared services
from app.repositories.tournament_repository import TournamentRepository
from app.services.shared.auth_validator import require_admin, require_admin_or_instructor
from app.services.tournament.results.finalization import (
    GroupStageFinalizer,
    TournamentFinalizer,
    SessionFinalizer
)

router = APIRouter()


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


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/finalize-group-stage")
def finalize_group_stage(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Finalize Group Stage and calculate group standings.

    This endpoint:
    1. Validates all group stage matches are completed
    2. Calculates group standings (points from game_results)
    3. Determines qualified participants for knockout stage
    4. Updates knockout session participant_user_ids with seeding

    Authorization: ADMIN or INSTRUCTOR
    """
    # Authorization check
    require_admin_or_instructor(
        current_user,
        detail="Only admins and instructors can finalize tournament stages"
    )

    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Use GroupStageFinalizer service
    finalizer = GroupStageFinalizer(db)
    result = finalizer.finalize(tournament)

    return result


@router.post("/{tournament_id}/finalize-tournament")
def finalize_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Finalize Tournament and calculate FINAL RANKING.

    This endpoint:
    1. Validates ALL matches are completed
    2. Calculates final ranking based on tournament structure:
       - Group+Knockout: Based on final match (1st, 2nd, 3rd place match)
       - League: Based on total points
    3. Updates tournament_rankings table
    4. Sets tournament status to COMPLETED

    Authorization: ADMIN only
    """
    # Authorization check
    require_admin(
        current_user,
        detail="Only admins can finalize tournaments"
    )

    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Use TournamentFinalizer service
    finalizer = TournamentFinalizer(db)
    result = finalizer.finalize(tournament)

    return result


@router.post("/{tournament_id}/sessions/{session_id}/finalize")
def finalize_individual_ranking_session(
    tournament_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Finalize INDIVIDUAL_RANKING session and calculate final rankings.

    This endpoint:
    1. Validates all rounds are completed
    2. Aggregates results across all rounds (e.g., sum of times, average score, best time)
    3. Calculates final rankings based on tournament.ranking_direction:
       - ASC: Lowest value wins (e.g., fastest time)
       - DESC: Highest value wins (e.g., highest score)
    4. Saves final rankings to session.game_results
    5. Updates TournamentRanking table with final results
    6. Updates tournament status if all sessions finalized

    Authorization: INSTRUCTOR (assigned) or ADMIN

    Example Use Cases:
    - Time-based (ASC): Best (lowest) time across all rounds wins
    - Score-based (DESC): Highest total score across all rounds wins
    - Distance-based (DESC): Longest total distance across all rounds wins
    """
    # Get tournament using repository
    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)

    # Get session
    session = get_session_or_404(db, tournament_id, session_id)

    # Authorization check
    require_admin_or_instructor(
        current_user,
        detail="Only instructors and admins can finalize sessions"
    )

    if current_user.role == UserRole.INSTRUCTOR:
        if session.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned instructor for this session"
            )

    # Use SessionFinalizer service
    finalizer = SessionFinalizer(db)

    try:
        result = finalizer.finalize(
            tournament=tournament,
            session=session,
            recorded_by_id=current_user.id,
            recorded_by_name=current_user.name or current_user.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return result


# Export router
__all__ = ["router"]
