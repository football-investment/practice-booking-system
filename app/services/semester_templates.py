"""
Semester Template Configuration
================================
Defines semester templates for each specialization and age group.

Templates include:
- Cycle length (monthly, quarterly, semi-annual, annual)
- Theme names
- Focus descriptions
- Start/end date patterns
"""

from typing import List, Dict
from datetime import datetime, timedelta


# Helper function to get first Monday of a month
def get_first_monday(year: int, month: int) -> datetime:
    """Get the first Monday of a given month"""
    date = datetime(year, month, 1)
    # Find first Monday
    while date.weekday() != 0:  # 0 = Monday
        date += timedelta(days=1)
    return date


# Helper function to get last Sunday of a month
def get_last_sunday(year: int, month: int) -> datetime:
    """Get the last Sunday of a given month"""
    # Start from last day of month
    if month == 12:
        date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        date = datetime(year, month + 1, 1) - timedelta(days=1)

    # Find last Sunday
    while date.weekday() != 6:  # 6 = Sunday
        date -= timedelta(days=1)
    return date


# ============================================================================
# LFA FOOTBALL PLAYER TEMPLATES
# ============================================================================

LFA_PLAYER_PRE_TEMPLATE = {
    "specialization": "LFA_PLAYER",
    "age_group": "PRE",
    "cycle_type": "monthly",  # 12 semesters per year
    "themes": [
        {"month": 1, "code": "M01", "theme": "New Year Challenge", "focus": "New Year resolutions, fresh start"},
        {"month": 2, "code": "M02", "theme": "Winter Heroes", "focus": "Winter challenges, perseverance"},
        {"month": 3, "code": "M03", "theme": "Spring Awakening", "focus": "Spring renewal, new techniques"},
        {"month": 4, "code": "M04", "theme": "Easter Football Festival", "focus": "Easter competition, playful development"},
        {"month": 5, "code": "M05", "theme": "May Champions", "focus": "Champions' month, individual growth"},
        {"month": 6, "code": "M06", "theme": "Summer Kickoff Camp", "focus": "Summer kickoff, intensive training"},
        {"month": 7, "code": "M07", "theme": "Sunshine Skills", "focus": "Sunny football, outdoor experience"},
        {"month": 8, "code": "M08", "theme": "Back to Football", "focus": "Return preparation"},
        {"month": 9, "code": "M09", "theme": "Autumn Academy", "focus": "Autumn academy, new season start"},
        {"month": 10, "code": "M10", "theme": "Halloween Cup", "focus": "Halloween-themed challenges"},
        {"month": 11, "code": "M11", "theme": "Team Spirit Month", "focus": "Team spirit, collaboration"},
        {"month": 12, "code": "M12", "theme": "Christmas Champions", "focus": "Christmas finale, year-end celebration"},
    ]
}

LFA_PLAYER_YOUTH_TEMPLATE = {
    "specialization": "LFA_PLAYER",
    "age_group": "YOUTH",
    "cycle_type": "quarterly",  # 4 semesters per year
    "themes": [
        {"quarter": 1, "code": "Q1", "months": [1, 2, 3], "theme": "Q1 Semester", "focus": "Jan-Mar: Foundation building, technical development"},
        {"quarter": 2, "code": "Q2", "months": [4, 5, 6], "theme": "Q2 Semester", "focus": "Apr-Jun: Tactical training, teamwork"},
        {"quarter": 3, "code": "Q3", "months": [7, 8, 9], "theme": "Q3 Semester", "focus": "Jul-Sep: Competition series, performance assessment"},
        {"quarter": 4, "code": "Q4", "months": [10, 11, 12], "theme": "Q4 Semester", "focus": "Oct-Dec: Advanced techniques, year-end evaluation"},
    ]
}

LFA_PLAYER_AMATEUR_TEMPLATE = {
    "specialization": "LFA_PLAYER",
    "age_group": "AMATEUR",
    "cycle_type": "annual",  # 1 season per year (Jul-Jun)
    "themes": [
        {
            "code": "Season",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "Season",
            "focus": "Jul-Jun: Amateur football season"
        },
    ]
}

LFA_PLAYER_PRO_TEMPLATE = {
    "specialization": "LFA_PLAYER",
    "age_group": "PRO",
    "cycle_type": "annual",  # 1 semester per year
    "themes": [
        {
            "code": "Season",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "Season",
            "focus": "Jul-Jun: Professional football season"
        },
    ]
}


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

SEMESTER_TEMPLATES = {
    ("LFA_PLAYER", "PRE"): LFA_PLAYER_PRE_TEMPLATE,
    ("LFA_PLAYER", "YOUTH"): LFA_PLAYER_YOUTH_TEMPLATE,
    ("LFA_PLAYER", "AMATEUR"): LFA_PLAYER_AMATEUR_TEMPLATE,
    ("LFA_PLAYER", "PRO"): LFA_PLAYER_PRO_TEMPLATE,
    # TODO: Add GANCUJU, COACH, INTERNSHIP templates later
}


def get_template(specialization: str, age_group: str) -> Dict:
    """Get semester template for a given specialization and age group"""
    key = (specialization, age_group)
    if key not in SEMESTER_TEMPLATES:
        raise ValueError(f"No template found for {specialization} / {age_group}")
    return SEMESTER_TEMPLATES[key]
