"""
Tournament Round Management Endpoints

Handles round status queries for INDIVIDUAL_RANKING tournaments.
Refactored from match_results.py as part of P2 decomposition.

Endpoints:
- GET /{tournament_id}/sessions/{session_id}/rounds: Get rounds status
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.models.user import User
from app.models.session import Session as SessionModel
from app.dependencies import get_current_user

# Import shared services
from app.repositories.tournament_repository import TournamentRepository

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

@router.get("/{tournament_id}/sessions/{session_id}/rounds")
def get_rounds_status(
    tournament_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get rounds status for an INDIVIDUAL_RANKING session.

    Returns:
    - total_rounds: Total number of rounds configured
    - completed_rounds: Number of rounds with results recorded
    - round_results: All recorded results by round
    - pending_rounds: List of round numbers without results
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
            detail=f"Round status only available for INDIVIDUAL_RANKING tournaments (session format: {session.match_format})"
        )

    # Get rounds_data
    rounds_data = session.rounds_data or {}
    total_rounds = rounds_data.get('total_rounds', 1)
    completed_rounds = rounds_data.get('completed_rounds', 0)
    round_results = rounds_data.get('round_results', {})

    # Calculate pending rounds
    completed_round_numbers = set(int(r) for r in round_results.keys())
    all_rounds = set(range(1, total_rounds + 1))
    pending_rounds = sorted(list(all_rounds - completed_round_numbers))

    return {
        "session_id": session_id,
        "tournament_id": tournament_id,
        "match_format": session.match_format,
        "total_rounds": total_rounds,
        "completed_rounds": completed_rounds,
        "pending_rounds": pending_rounds,
        "round_results": round_results,
        "is_complete": completed_rounds == total_rounds
    }


# Export router
__all__ = ["router"]
