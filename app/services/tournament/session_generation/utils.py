"""
Tournament Session Generation Utilities

Helper functions for session generation.
"""
from typing import Optional, TYPE_CHECKING
from app.models.semester import Semester

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


def get_tournament_venue(tournament: Semester) -> str:
    """
    Get tournament venue with proper fallback chain.

    Replaces deprecated tournament.location_venue attribute.

    Fallback chain:
    1. tournament.campus.venue (most specific - facility level)
    2. tournament.campus.name (campus name if no venue)
    3. tournament.location.city (city level fallback)
    4. 'TBD' (if no location data available)

    Args:
        tournament: Tournament (Semester) instance

    Returns:
        str: Venue string or 'TBD' if not available

    Examples:
        >>> # Campus with venue
        >>> get_tournament_venue(tournament)
        'Main Field'

        >>> # Campus without venue
        >>> get_tournament_venue(tournament)
        'Buda Campus (Budapest)'

        >>> # Location only
        >>> get_tournament_venue(tournament)
        'Budapest'

        >>> # No location data
        >>> get_tournament_venue(tournament)
        'TBD'

    Note:
        Requires eager loading of tournament.campus and tournament.location
        relationships to avoid N+1 queries.
    """
    # Priority 1: Campus venue (most specific)
    if tournament.campus:
        if tournament.campus.venue:
            return tournament.campus.venue

        # Fallback: Campus name with city
        if tournament.campus.name and tournament.campus.location:
            return f"{tournament.campus.name} ({tournament.campus.location.city})"

        # Campus name only
        if tournament.campus.name:
            return tournament.campus.name

    # Priority 2: Location city (city-level fallback)
    if tournament.location:
        return tournament.location.city

    # Priority 3: Default
    return 'TBD'


def get_campus_schedule(
    db: "DBSession",
    tournament_id: int,
    campus_id: Optional[int],
    global_match_duration: int = 90,
    global_break_duration: int = 15,
    global_parallel_fields: int = 1,
) -> dict:
    """
    Resolve effective schedule parameters for a (tournament, campus) pair.

    Precedence:
      1. campus_schedule_configs row for (tournament_id, campus_id)
      2. global TournamentConfiguration values (passed as parameters)

    Returns a dict with:
      - match_duration_minutes: int
      - break_duration_minutes: int
      - parallel_fields: int
      - venue_label: str | None
    """
    if campus_id is not None:
        from app.models.campus_schedule_config import CampusScheduleConfig
        cfg = db.query(CampusScheduleConfig).filter(
            CampusScheduleConfig.tournament_id == tournament_id,
            CampusScheduleConfig.campus_id == campus_id,
            CampusScheduleConfig.is_active == True,
        ).first()
        if cfg:
            return {
                "match_duration_minutes": cfg.resolved_match_duration(global_match_duration),
                "break_duration_minutes": cfg.resolved_break_duration(global_break_duration),
                "parallel_fields": cfg.resolved_parallel_fields(global_parallel_fields),
                "venue_label": cfg.venue_label,
            }

    return {
        "match_duration_minutes": global_match_duration,
        "break_duration_minutes": global_break_duration,
        "parallel_fields": global_parallel_fields,
        "venue_label": None,
    }
