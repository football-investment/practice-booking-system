"""
Tournament Session Generation Utilities

Helper functions for session generation.
"""
from typing import Optional
from app.models.semester import Semester


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
