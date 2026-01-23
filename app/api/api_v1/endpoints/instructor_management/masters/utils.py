"""
Helper Functions - License & Age Group Validation

Utility functions for master instructor validation:
- Age group mapping and compatibility checks
- License hierarchy validation
"""


def get_semester_age_group(spec_type: str) -> str:
    """Map semester specialization to age group"""
    mapping = {
        "LFA_PLAYER_PRE": "PRE_FOOTBALL",
        "LFA_PLAYER_YOUTH": "YOUTH_FOOTBALL",
        "LFA_PLAYER_AMATEUR": "AMATEUR_FOOTBALL",
        "LFA_PLAYER_PRO": "PRO_FOOTBALL"
    }
    return mapping.get(spec_type, "UNKNOWN")


def can_teach_age_group(instructor_age_group: str, semester_age_group: str) -> bool:
    """
    Check if instructor can teach this age group based on LFA_COACH hierarchy

    LFA_COACH License Hierarchy:
    - Level 2 (PRE Head Coach) → can teach PRE only
    - Level 4 (YOUTH Head Coach) → can teach PRE + YOUTH
    - Level 6 (AMATEUR Head Coach) → can teach PRE + YOUTH + AMATEUR
    - Level 8 (PRO Head Coach) → can teach ALL (PRE + YOUTH + AMATEUR + PRO)
    """
    hierarchy = {
        "PRE_FOOTBALL": ["PRE_FOOTBALL"],
        "YOUTH_FOOTBALL": ["PRE_FOOTBALL", "YOUTH_FOOTBALL"],
        "AMATEUR_FOOTBALL": ["PRE_FOOTBALL", "YOUTH_FOOTBALL", "AMATEUR_FOOTBALL"],
        "PRO_FOOTBALL": ["PRE_FOOTBALL", "YOUTH_FOOTBALL", "AMATEUR_FOOTBALL", "PRO_FOOTBALL"]
    }

    allowed = hierarchy.get(instructor_age_group, [])
    return semester_age_group in allowed


def get_allowed_age_groups(instructor_age_group: str) -> list:
    """Get list of age groups this instructor can teach"""
    hierarchy = {
        "PRE_FOOTBALL": ["PRE"],
        "YOUTH_FOOTBALL": ["PRE", "YOUTH"],
        "AMATEUR_FOOTBALL": ["PRE", "YOUTH", "AMATEUR"],
        "PRO_FOOTBALL": ["PRE", "YOUTH", "AMATEUR", "PRO"]
    }

    return hierarchy.get(instructor_age_group, [])
