"""
Tournament Schedule Configuration API

First-class domain endpoint for reading and writing match duration,
break duration, and parallel field count — both globally (tournament-wide)
and per-campus.

Precedence (already implemented in session generation):
  1. CampusScheduleConfig (per campus, per tournament)
  2. TournamentConfiguration globals (this endpoint)
  3. Request-level defaults in generate-sessions
  4. TournamentType hardcoded defaults

All values are persisted to the database.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.semester import Semester
from app.models.tournament_configuration import TournamentConfiguration

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────

class MatchDurationConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """
    Global match-duration / schedule configuration for a tournament.

    These values act as defaults. Per-campus overrides (CampusScheduleConfig)
    take precedence over these globals during session generation.
    """
    match_duration_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=480,
        description=(
            "Duration of each match in minutes. "
            "Applies to all campuses unless overridden per-campus. "
            "Typical values: 90 (football), 5 (chess rapid), 1-3 (speed trials)."
        ),
    )
    break_duration_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        description="Break between consecutive matches in minutes. 0 = back-to-back.",
    )
    parallel_fields: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description=(
            "Number of pitches/courts/boards available simultaneously across the tournament. "
            "Per-campus overrides in CampusScheduleConfig take priority."
        ),
    )


class ScheduleConfigResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    tournament_id: int
    tournament_name: str
    # Global values (from TournamentConfiguration)
    match_duration_minutes: Optional[int]
    break_duration_minutes: Optional[int]
    parallel_fields: int
    # Effective values (with fallback to type defaults)
    effective_match_duration: int
    effective_break_duration: int
    effective_parallel_fields: int


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_or_404(tournament_id: int, db: Session) -> Semester:
    t = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return t


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{tournament_id}/schedule-config", response_model=Dict[str, Any])
def get_schedule_config(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Get the global schedule configuration for a tournament.

    Returns both the stored values and the effective values (with type defaults).

    **Authorization:** Admin only
    """
    tournament = _get_or_404(tournament_id, db)
    cfg = tournament.tournament_config_obj

    # Resolve type defaults if available
    type_match_default = 90
    type_break_default = 15
    if tournament.tournament_config_obj and tournament.tournament_config_obj.tournament_type:
        tt = tournament.tournament_config_obj.tournament_type
        type_match_default = getattr(tt, "session_duration_minutes", 90) or 90
        type_break_default = getattr(tt, "break_between_sessions_minutes", 15) or 15

    stored_match = cfg.match_duration_minutes if cfg else None
    stored_break = cfg.break_duration_minutes if cfg else None
    stored_parallel = cfg.parallel_fields if cfg else 1

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        # Stored values (may be None = use type default)
        "match_duration_minutes": stored_match,
        "break_duration_minutes": stored_break,
        "parallel_fields": stored_parallel,
        # Effective values (what session generation will use)
        "effective_match_duration": stored_match or type_match_default,
        "effective_break_duration": stored_break or type_break_default,
        "effective_parallel_fields": stored_parallel or 1,
        # Type defaults for reference
        "type_match_default": type_match_default,
        "type_break_default": type_break_default,
    }


@router.patch("/{tournament_id}/schedule-config", response_model=Dict[str, Any])
def update_schedule_config(
    tournament_id: int,
    request: MatchDurationConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Update the global schedule configuration for a tournament.

    Only provided fields are updated (PATCH semantics — NULL fields are ignored).
    To clear a value back to type defaults, set it to null in the request.

    **Authorization:** Admin only

    **Effect:** Values are persisted to `tournament_configurations` table
    and will be used as defaults in all subsequent session generation calls.
    Per-campus overrides (set via PUT /campus-schedules) take precedence.
    """
    tournament = _get_or_404(tournament_id, db)

    if not tournament.tournament_config_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament has no configuration record. Create the tournament properly first."
        )

    cfg: TournamentConfiguration = tournament.tournament_config_obj

    if request.match_duration_minutes is not None:
        cfg.match_duration_minutes = request.match_duration_minutes
    if request.break_duration_minutes is not None:
        cfg.break_duration_minutes = request.break_duration_minutes
    if request.parallel_fields is not None:
        cfg.parallel_fields = request.parallel_fields

    db.commit()
    db.refresh(cfg)

    return {
        "success": True,
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "match_duration_minutes": cfg.match_duration_minutes,
        "break_duration_minutes": cfg.break_duration_minutes,
        "parallel_fields": cfg.parallel_fields,
        "message": (
            f"Schedule config updated: match_duration={cfg.match_duration_minutes}min, "
            f"break={cfg.break_duration_minutes}min, parallel_fields={cfg.parallel_fields}"
        ),
    }
