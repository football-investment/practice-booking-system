"""
Quick Actions Handlers
======================

Functions for handling quick actions in the matrix:
- Generate missing periods
- Edit existing periods
- Delete periods

Handles API calls, error handling, and success messages.
"""

from api_helpers_semesters import (
    generate_lfa_player_pre_season,
    generate_lfa_player_youth_season,
    generate_lfa_player_amateur_season,
    generate_lfa_player_pro_season,
    update_semester,
    delete_semester
)


def generate_missing_periods(token: str, age_group: str, year: int, location_id: int, missing_codes: list):
    """
    Generate all missing periods for a given age group and year

    Args:
        token: Auth token
        age_group: "PRE", "YOUTH", "AMATEUR", or "PRO"
        year: Year to generate for
        location_id: Location ID
        missing_codes: List of missing codes to generate

    Returns:
        Tuple of (success_count, failed_list)
        where failed_list contains tuples of (code, error_message)
    """
    success_count = 0
    failed = []

    for code in missing_codes:
        success = False
        error = None

        if age_group == "PRE":
            # Extract month from "M09" -> 9
            month = int(code[1:])
            success, error, _ = generate_lfa_player_pre_season(token, year, month, location_id)

        elif age_group == "YOUTH":
            # Extract quarter from "Q3" -> 3
            quarter = int(code[1])
            success, error, _ = generate_lfa_player_youth_season(token, year, quarter, location_id)

        elif age_group == "AMATEUR":
            success, error, _ = generate_lfa_player_amateur_season(token, year, location_id)

        elif age_group == "PRO":
            success, error, _ = generate_lfa_player_pro_season(token, year, location_id)

        if success:
            success_count += 1
        else:
            failed.append((code, error))

    return success_count, failed


def edit_semester_action(token: str, semester_id: int, updates: dict):
    """
    Edit an existing semester

    Args:
        token: Auth token
        semester_id: ID of semester to edit
        updates: Dict of fields to update

    Returns:
        Tuple of (success: bool, error: str or None, data: dict or None)
    """
    return update_semester(token, semester_id, updates)


def delete_semester_action(token: str, semester_id: int):
    """
    Delete a semester

    Args:
        token: Auth token
        semester_id: ID of semester to delete

    Returns:
        Tuple of (success: bool, error: str or None)
    """
    return delete_semester(token, semester_id)
