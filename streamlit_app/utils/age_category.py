"""
Age Category Utility Functions
Shared utility for determining age categories across the application
"""
from datetime import date


def get_age_category_for_season(date_of_birth):
    """
    Determine age category based on age AT SEASON START (July 1).
    Season lock: Category is fixed for entire season (July 1 - June 30).

    This follows international football practice where age groups
    are determined at season start and remain fixed throughout the season.

    Args:
        date_of_birth: Date of birth (date object or ISO string)

    Returns:
        str: Age category ("PRE", "YOUTH", or None for 18+)
    """
    if not date_of_birth:
        return None

    # Handle string format (from API)
    if isinstance(date_of_birth, str):
        try:
            from datetime import datetime
            date_of_birth = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00')).date()
        except:
            return None

    today = date.today()

    # Determine current season start date (July 1)
    if today.month >= 7:  # July-December
        season_start = date(today.year, 7, 1)
    else:  # January-June
        season_start = date(today.year - 1, 7, 1)

    # Calculate age AT season start (July 1)
    age_at_season_start = season_start.year - date_of_birth.year
    if (season_start.month, season_start.day) < (date_of_birth.month, date_of_birth.day):
        age_at_season_start -= 1

    # Determine category based on age AT SEASON START
    # PRE: 5-13 years (automatic, cannot override)
    # YOUTH: 14-17 years (automatic, cannot override)
    # AMATEUR: 18+ years (automatic default - ALL adults start as Amateur)
    # PRO: 18+ years (ONLY if instructor/admin manually sets it - NOT automatic)
    if 5 <= age_at_season_start <= 13:
        return "PRE"
    elif 14 <= age_at_season_start <= 17:
        return "YOUTH"
    elif age_at_season_start >= 18:
        # Default to AMATEUR for ALL 18+ ages (18, 25, 39, etc.)
        # ONLY instructor/admin can manually upgrade to PRO category
        # IMPORTANT: Return UPPERCASE to match get_age_category_info() in dashboard
        return "AMATEUR"

    return None
