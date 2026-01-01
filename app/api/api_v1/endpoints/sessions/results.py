"""
Session/Game Results Management
Allows master instructor to submit game results for tournament sessions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import json

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel

router = APIRouter()


class GameResultEntry(BaseModel):
    """Single participant's game result"""
    user_id: int
    score: float = Field(..., ge=0, description="Score (0-100 or custom scale)")
    rank: int = Field(..., ge=1, description="Final rank/position")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class SubmitGameResultsRequest(BaseModel):
    """Request to submit game results"""
    results: List[GameResultEntry] = Field(..., min_items=1, description="List of participant results")


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
    if not session.is_tournament_game:
        raise HTTPException(status_code=400, detail="This is not a tournament game session")

    # Authorization: Only master instructor of the tournament or admin
    semester = session.semester
    if current_user.role != UserRole.ADMIN and semester.master_instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the tournament's master instructor can submit results"
        )

    # Convert results to JSON-serializable format
    results_data = [
        {
            "user_id": entry.user_id,
            "score": entry.score,
            "rank": entry.rank,
            "notes": entry.notes
        }
        for entry in request.results
    ]

    # Store as JSON string
    session.game_results = json.dumps(results_data)

    db.commit()
    db.refresh(session)

    return {
        "session_id": session_id,
        "game_type": session.game_type,
        "results_count": len(results_data),
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
    if not session.is_tournament_game:
        raise HTTPException(status_code=400, detail="This is not a tournament game session")

    # Parse results if available
    if not session.game_results:
        return {
            "session_id": session_id,
            "game_type": session.game_type,
            "results": []
        }

    # Parse JSON
    try:
        results = json.loads(session.game_results)
    except json.JSONDecodeError:
        results = []

    return {
        "session_id": session_id,
        "game_type": session.game_type,
        "results": results
    }
