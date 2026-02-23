"""
Tournament Detail Query Endpoint

Returns tournament metadata for enrollment workflow.
Performance target: p95 < 100ms
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.semester import Semester

router = APIRouter()


class TournamentDetailResponse(BaseModel):
    """Tournament detail response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    start_date: datetime
    end_date: datetime
    age_group: str
    enrollment_cost: int
    max_players: int
    tournament_status: str
    master_instructor_id: Optional[int]
    semester_id: int  # Same as id (Semester table serves as Tournament)


@router.get("/{tournament_id}", response_model=TournamentDetailResponse)
def get_tournament_detail(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tournament details by ID.

    **Authorization:** All authenticated users
    **Use Case:** Student enrollment workflow (extract semester_id)
    **Performance Target:** p95 < 100ms

    **Returns:**
    - Tournament metadata including semester_id (needed for enrollment)
    - Enrollment cost, max players, age group
    - Tournament status (DRAFT, ENROLLMENT_OPEN, IN_PROGRESS, etc.)
    - Master instructor ID (if assigned)

    **Raises:**
    - 404: Tournament not found or inactive
    """
    tournament = db.query(Semester).filter(
        Semester.id == tournament_id,
        Semester.is_active == True
    ).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    return TournamentDetailResponse(
        id=tournament.id,
        code=tournament.code,
        name=tournament.name,
        start_date=tournament.start_date,
        end_date=tournament.end_date,
        age_group=tournament.age_group or "PRO",
        enrollment_cost=tournament.enrollment_cost or 500,
        max_players=tournament.max_players or 16,
        tournament_status=tournament.tournament_status or "DRAFT",
        master_instructor_id=tournament.master_instructor_id,
        semester_id=tournament.id  # Semester.id = Tournament.id (same entity)
    )
