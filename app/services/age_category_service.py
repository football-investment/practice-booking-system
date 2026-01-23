"""
Age Category Calculation Service
Handles automatic age-category assignment based on season start date

Business Rules:
- 5-13 years → PRE (automatic, cannot override)
- 14-18 years → YOUTH (automatic default, instructor can override to AMATEUR/PRO)
- 14+ years → Instructor can manually assign AMATEUR or PRO
- Season lock: Category determined at July 1 and stays fixed until June 30
"""
from datetime import date
from typing import Optional


def calculate_age_at_season_start(date_of_birth: date, season_year: int) -> int:
    """
    Calculate age at season start (July 1 of season_year).

    Season lock rule: Age groups are determined at season start (July 1)
    and remain fixed for the entire season (July 1 - June 30).

    This follows international football practice where age groups are
    determined at season start and do not change mid-season.

    Args:
        date_of_birth: User's birth date
        season_year: Year when season starts (e.g., 2025 for 2025/26 season)

    Returns:
        Age in years at July 1 of season_year

    Example:
        >>> calculate_age_at_season_start(date(2007, 12, 6), 2025)
        17  # Born Dec 6, 2007 → 17 years old on July 1, 2025
    """
    season_start = date(season_year, 7, 1)
    age = season_start.year - date_of_birth.year

    # Adjust if birthday hasn't occurred yet by July 1
    if (season_start.month, season_start.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1

    return age


def get_automatic_age_category(age_at_season_start: int) -> Optional[str]:
    """
    Determine automatic age category based on age at season start.

    AUTOMATIC ASSIGNMENT RULES:
    - 5-13 years → PRE (cannot be overridden)
    - 14-18 years → YOUTH (default, can be overridden to AMATEUR/PRO by instructor)
    - Age > 18 → None (instructor MUST manually assign AMATEUR or PRO)

    Args:
        age_at_season_start: Age in years at July 1

    Returns:
        "PRE", "YOUTH", or None

    Examples:
        >>> get_automatic_age_category(10)
        'PRE'
        >>> get_automatic_age_category(14)
        'YOUTH'
        >>> get_automatic_age_category(17)
        'YOUTH'
        >>> get_automatic_age_category(21)
        None  # Instructor must assign
    """
    if 5 <= age_at_season_start <= 13:
        return "PRE"
    elif 14 <= age_at_season_start <= 18:
        return "YOUTH"
    else:
        # Age < 5 or > 18: No automatic assignment
        # Instructor must choose AMATEUR or PRO for players older than 18
        return None


def get_current_season_year() -> int:
    """
    Get the current season year based on today's date.
    Season runs July 1 - June 30.

    Returns:
        Season start year (e.g., 2025 for 2025/26 season)

    Examples:
        If today is 2025-12-28 → returns 2025 (season 2025/26)
        If today is 2026-05-15 → returns 2025 (still in season 2025/26)
        If today is 2026-07-10 → returns 2026 (new season 2026/27)
    """
    today = date.today()

    if today.month >= 7:  # July-December → current year is season start
        return today.year
    else:  # January-June → previous year is season start
        return today.year - 1


def can_override_age_category(age_at_season_start: int) -> bool:
    """
    Check if instructor can override age category for this player.

    Rules:
    - 5-13 years (PRE) → CANNOT override (must stay in PRE)
    - 14-18 years (YOUTH) → CAN override to AMATEUR or PRO
    - > 18 years → CAN assign AMATEUR or PRO (no default)

    Args:
        age_at_season_start: Age in years at July 1

    Returns:
        True if instructor can override, False otherwise

    Examples:
        >>> can_override_age_category(10)
        False  # PRE players cannot be moved
        >>> can_override_age_category(14)
        True  # YOUTH players can be moved to AMATEUR/PRO
        >>> can_override_age_category(17)
        True
        >>> can_override_age_category(21)
        True
    """
    return age_at_season_start >= 14


def validate_age_category_override(
    age_at_season_start: int,
    new_category: str
) -> tuple[bool, Optional[str]]:
    """
    Validate if a requested age category override is allowed.

    Args:
        age_at_season_start: Player's age at July 1
        new_category: Requested category ("PRE", "YOUTH", "AMATEUR", "PRO")

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if override is allowed
        - (False, error_message) if override is not allowed

    Examples:
        >>> validate_age_category_override(10, "PRO")
        (False, "Students aged 10 (under 14) must remain in PRE category")

        >>> validate_age_category_override(14, "PRO")
        (True, None)

        >>> validate_age_category_override(17, "AMATEUR")
        (True, None)
    """
    valid_categories = ["PRE", "YOUTH", "AMATEUR", "PRO"]

    # Validate category name
    if new_category not in valid_categories:
        return False, f"Invalid category '{new_category}'. Must be one of: {', '.join(valid_categories)}"

    # Cannot move players under 14 out of PRE
    if age_at_season_start < 14 and new_category != "PRE":
        return False, f"Students aged {age_at_season_start} (under 14) must remain in PRE category"

    # All other cases are valid
    return True, None
