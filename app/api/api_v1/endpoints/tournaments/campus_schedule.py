"""
Campus Schedule Configuration API

Manages per-campus schedule overrides for multi-venue tournaments.

Each campus running a tournament can independently configure:
  - match_duration_minutes
  - break_duration_minutes
  - parallel_fields
  - venue_label

Precedence in session generation:
  campus_schedule_configs row  >  TournamentConfiguration global  >  request params  >  type defaults
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.semester import Semester
from app.models.campus import Campus
from app.models.campus_schedule_config import CampusScheduleConfig

router = APIRouter()


# ── Pydantic schemas ────────────────────────────────────────────────────────

class CampusScheduleUpsertRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Create or update a per-campus schedule config for a tournament."""
    campus_id: int = Field(..., description="Campus ID to configure")
    match_duration_minutes: Optional[int] = Field(
        default=None, ge=1, le=480,
        description="Match duration in minutes. NULL = use global tournament default."
    )
    break_duration_minutes: Optional[int] = Field(
        default=None, ge=0, le=120,
        description="Break between matches. NULL = use global tournament default."
    )
    parallel_fields: Optional[int] = Field(
        default=None, ge=1, le=20,
        description="Parallel pitches/courts at this campus. NULL = use global default."
    )
    venue_label: Optional[str] = Field(
        default=None, max_length=100,
        description="Human-readable label (e.g. 'North Pitch'). Optional."
    )
    is_active: bool = Field(default=True, description="Whether this campus is active for session generation")


class CampusScheduleResponse(BaseModel):
    id: int
    tournament_id: int
    campus_id: int
    campus_name: Optional[str]
    match_duration_minutes: Optional[int]
    break_duration_minutes: Optional[int]
    parallel_fields: Optional[int]
    # Resolved values (after applying global defaults)
    resolved_match_duration: int
    resolved_break_duration: int
    resolved_parallel_fields: int
    venue_label: Optional[str]
    is_active: bool


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_tournament_or_404(tournament_id: int, db: Session) -> Semester:
    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return t


def _build_response(cfg: CampusScheduleConfig, tournament: Semester) -> Dict[str, Any]:
    global_match = tournament.match_duration_minutes or 90
    global_break = tournament.break_duration_minutes or 15
    global_fields = tournament.parallel_fields or 1
    return {
        "id": cfg.id,
        "tournament_id": cfg.tournament_id,
        "campus_id": cfg.campus_id,
        "campus_name": cfg.campus.name if cfg.campus else None,
        "match_duration_minutes": cfg.match_duration_minutes,
        "break_duration_minutes": cfg.break_duration_minutes,
        "parallel_fields": cfg.parallel_fields,
        "resolved_match_duration": cfg.resolved_match_duration(global_match),
        "resolved_break_duration": cfg.resolved_break_duration(global_break),
        "resolved_parallel_fields": cfg.resolved_parallel_fields(global_fields),
        "venue_label": cfg.venue_label,
        "is_active": cfg.is_active,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{tournament_id}/campus-schedules", response_model=List[Dict[str, Any]])
def list_campus_schedules(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    List all per-campus schedule configs for a tournament.

    **Authorization:** Admin only
    """
    tournament = _get_tournament_or_404(tournament_id, db)
    configs = (
        db.query(CampusScheduleConfig)
        .filter(CampusScheduleConfig.tournament_id == tournament_id)
        .all()
    )
    return [_build_response(c, tournament) for c in configs]


@router.put("/{tournament_id}/campus-schedules", response_model=Dict[str, Any])
def upsert_campus_schedule(
    tournament_id: int,
    request: CampusScheduleUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Create or update a per-campus schedule config for a tournament.

    Idempotent: if a config for (tournament_id, campus_id) already exists, it is updated.

    **Authorization:** Admin only
    """
    tournament = _get_tournament_or_404(tournament_id, db)

    # Verify campus exists
    campus = db.query(Campus).filter(Campus.id == request.campus_id).first()
    if not campus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Campus {request.campus_id} not found")

    # Upsert
    cfg = db.query(CampusScheduleConfig).filter(
        CampusScheduleConfig.tournament_id == tournament_id,
        CampusScheduleConfig.campus_id == request.campus_id,
    ).first()

    if cfg is None:
        cfg = CampusScheduleConfig(
            tournament_id=tournament_id,
            campus_id=request.campus_id,
        )
        db.add(cfg)

    cfg.match_duration_minutes = request.match_duration_minutes
    cfg.break_duration_minutes = request.break_duration_minutes
    cfg.parallel_fields = request.parallel_fields
    cfg.venue_label = request.venue_label
    cfg.is_active = request.is_active

    db.commit()
    db.refresh(cfg)
    # Eager-load campus for response
    db.refresh(cfg, ["campus"])

    return _build_response(cfg, tournament)


@router.delete("/{tournament_id}/campus-schedules/{campus_id}", response_model=Dict[str, Any])
def delete_campus_schedule(
    tournament_id: int,
    campus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Delete a per-campus schedule config (reverts to global tournament defaults).

    **Authorization:** Admin only
    """
    _get_tournament_or_404(tournament_id, db)
    cfg = db.query(CampusScheduleConfig).filter(
        CampusScheduleConfig.tournament_id == tournament_id,
        CampusScheduleConfig.campus_id == campus_id,
    ).first()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No campus schedule config for campus {campus_id} in tournament {tournament_id}"
        )
    db.delete(cfg)
    db.commit()
    return {"success": True, "deleted_campus_id": campus_id, "tournament_id": tournament_id}
