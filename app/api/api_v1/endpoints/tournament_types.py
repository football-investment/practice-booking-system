"""
Tournament Types API Endpoint

Provides list of available tournament types (League, Knockout, etc.)
for admins to select when creating tournaments.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.tournament_type import TournamentType


router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
def list_tournament_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """
    List all available tournament types (Admin only)

    Returns tournament type metadata including:
    - Basic info (id, code, display_name, description)
    - Player constraints (min_players, max_players, requires_power_of_two)
    - Timing defaults (session_duration_minutes, break_between_sessions_minutes)
    - Full config (JSON with detailed rules)

    **Authorization:** Admin only

    **Response Example:**
    ```json
    [
        {
            "id": 1,
            "code": "league",
            "display_name": "League (Round Robin)",
            "description": "Every player plays against every other player once...",
            "min_players": 4,
            "max_players": 16,
            "requires_power_of_two": false,
            "session_duration_minutes": 90,
            "break_between_sessions_minutes": 15,
            "config": {...}
        }
    ]
    ```
    """
    tournament_types = db.query(TournamentType).order_by(TournamentType.id).all()

    return [
        {
            "id": tt.id,
            "code": tt.code,
            "display_name": tt.display_name,
            "description": tt.description,
            "min_players": tt.min_players,
            "max_players": tt.max_players,
            "requires_power_of_two": tt.requires_power_of_two,
            "session_duration_minutes": tt.session_duration_minutes,
            "break_between_sessions_minutes": tt.break_between_sessions_minutes,
            "config": tt.config
        }
        for tt in tournament_types
    ]


@router.get("/{tournament_type_id}", response_model=Dict[str, Any])
def get_tournament_type(
    tournament_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get details of a specific tournament type (Admin only)

    **Authorization:** Admin only
    """
    tournament_type = db.query(TournamentType).filter(
        TournamentType.id == tournament_type_id
    ).first()

    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament type with ID {tournament_type_id} not found"
        )

    return {
        "id": tournament_type.id,
        "code": tournament_type.code,
        "display_name": tournament_type.display_name,
        "description": tournament_type.description,
        "min_players": tournament_type.min_players,
        "max_players": tournament_type.max_players,
        "requires_power_of_two": tournament_type.requires_power_of_two,
        "session_duration_minutes": tournament_type.session_duration_minutes,
        "break_between_sessions_minutes": tournament_type.break_between_sessions_minutes,
        "config": tournament_type.config
    }


@router.post("/{tournament_type_id}/estimate", response_model=Dict[str, Any])
def estimate_tournament_duration(
    tournament_type_id: int,
    player_count: int,
    parallel_fields: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Estimate tournament duration based on tournament type and player count

    **Parameters:**
    - `tournament_type_id`: Tournament type ID
    - `player_count`: Number of enrolled players
    - `parallel_fields`: Number of fields available for parallel matches (default: 1)

    **Authorization:** Admin only

    **Response Example:**
    ```json
    {
        "tournament_type": "League (Round Robin)",
        "player_count": 8,
        "parallel_fields": 1,
        "total_matches": 28,
        "total_rounds": 7,
        "estimated_duration_minutes": 1260,
        "estimated_duration_days": 0.88
    }
    ```
    """
    tournament_type = db.query(TournamentType).filter(
        TournamentType.id == tournament_type_id
    ).first()

    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament type with ID {tournament_type_id} not found"
        )

    # Validate player count
    is_valid, error_msg = tournament_type.validate_player_count(player_count)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Estimate duration
    estimation = tournament_type.estimate_duration(player_count, parallel_fields)

    return {
        "tournament_type": tournament_type.display_name,
        "player_count": player_count,
        "parallel_fields": parallel_fields,
        **estimation
    }
