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

from typing import Dict
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
    "cycle_type": "quarterly",  # 4 semesters per year (Q1-Q4)
    "themes": [
        {"code": "Q1", "start_month": 7, "end_month": 9, "theme": "Q1 Semester", "focus": "Jul-Sep: Foundation building, technical development"},
        {"code": "Q2", "start_month": 10, "end_month": 12, "theme": "Q2 Semester", "focus": "Oct-Dec: Tactical training, teamwork"},
        {"code": "Q3", "start_month": 1, "end_month": 3, "theme": "Q3 Semester", "focus": "Jan-Mar: Competition series, performance assessment"},
        {"code": "Q4", "start_month": 4, "end_month": 6, "theme": "Q4 Semester", "focus": "Apr-Jun: Advanced techniques, year-end evaluation"},
    ],
    "cost_credits": 2000,  # Quarterly mini season cost
    "enrollment_lock": False,  # Mini Season, no lock - flexible enrollment
    "requires_center": False  # Can be created at PARTNER and CENTER locations
}

LFA_PLAYER_PRO_TEMPLATE = {
    "specialization": "LFA_PLAYER",
    "age_group": "PRO",
    "cycle_type": "quarterly",  # 4 semesters per year (Q1-Q4)
    "themes": [
        {"code": "Q1", "start_month": 7, "end_month": 9, "theme": "Q1 Semester", "focus": "Jul-Sep: High-intensity training, elite development"},
        {"code": "Q2", "start_month": 10, "end_month": 12, "theme": "Q2 Semester", "focus": "Oct-Dec: Professional tactics, competitive mindset"},
        {"code": "Q3", "start_month": 1, "end_month": 3, "theme": "Q3 Semester", "focus": "Jan-Mar: Peak performance, advanced competition"},
        {"code": "Q4", "start_month": 4, "end_month": 6, "theme": "Q4 Semester", "focus": "Apr-Jun: Professional preparation, career development"},
    ],
    "cost_credits": 2500,  # Quarterly mini season cost (higher than AMATEUR)
    "enrollment_lock": False,  # Mini Season, no lock - flexible enrollment
    "requires_center": False  # Can be created at PARTNER and CENTER locations
}

# ============================================================================
# ACADEMY SEASON TEMPLATES (NEW - Full year commitment Jul 1 - Jun 30)
# ============================================================================

LFA_PLAYER_PRE_ACADEMY_TEMPLATE = {
    "specialization": "LFA_PLAYER_PRE_ACADEMY",
    "age_group": "PRE",
    "cycle_type": "academy_annual",  # Full year academy (Jul 1 - Jun 30)
    "themes": [
        {
            "code": "ACAD",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "PRE Academy Season",
            "focus": "Jul-Jun: Full year PRE Academy (5-13 years) - Structured development program with fixed enrollment"
        },
    ],
    "cost_credits": 5000,  # High fixed annual cost
    "enrollment_lock": True,  # Age category locked at July 1
    "requires_center": True  # Can only be created at CENTER locations
}

LFA_PLAYER_YOUTH_ACADEMY_TEMPLATE = {
    "specialization": "LFA_PLAYER_YOUTH_ACADEMY",
    "age_group": "YOUTH",
    "cycle_type": "academy_annual",  # Full year academy (Jul 1 - Jun 30)
    "themes": [
        {
            "code": "ACAD",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "YOUTH Academy Season",
            "focus": "Jul-Jun: Full year YOUTH Academy (14-18 years) - Intensive development with competitive focus"
        },
    ],
    "cost_credits": 7000,  # Higher cost for YOUTH academy
    "enrollment_lock": True,  # Age category locked at July 1
    "requires_center": True  # Can only be created at CENTER locations
}

LFA_PLAYER_AMATEUR_ACADEMY_TEMPLATE = {
    "specialization": "LFA_PLAYER_AMATEUR_ACADEMY",
    "age_group": "AMATEUR",
    "cycle_type": "academy_annual",  # Full year academy (Jul 1 - Jun 30)
    "themes": [
        {
            "code": "ACAD",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "AMATEUR Academy Season",
            "focus": "Jul-Jun: Full year AMATEUR Academy (14+ years) - Professional development pathway"
        },
    ],
    "cost_credits": 8000,  # Higher than YOUTH (7000) - professional level
    "enrollment_lock": True,  # Age category locked at July 1
    "requires_center": True  # Can only be created at CENTER locations
}

LFA_PLAYER_PRO_ACADEMY_TEMPLATE = {
    "specialization": "LFA_PLAYER_PRO_ACADEMY",
    "age_group": "PRO",
    "cycle_type": "academy_annual",  # Full year academy (Jul 1 - Jun 30)
    "themes": [
        {
            "code": "ACAD",
            "start_month": 7,
            "start_day": 1,
            "end_month": 6,
            "end_day": 30,
            "theme": "PRO Academy Season",
            "focus": "Jul-Jun: Full year PRO Academy (14+ years) - Elite performance training"
        },
    ],
    "cost_credits": 10000,  # Highest academy cost - elite professional level
    "enrollment_lock": True,  # Age category locked at July 1
    "requires_center": True  # Can only be created at CENTER locations
}


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

SEMESTER_TEMPLATES = {
    # Mini Seasons (quarterly/monthly - PARTNER and CENTER locations)
    ("LFA_PLAYER", "PRE"): LFA_PLAYER_PRE_TEMPLATE,
    ("LFA_PLAYER", "YOUTH"): LFA_PLAYER_YOUTH_TEMPLATE,
    ("LFA_PLAYER", "AMATEUR"): LFA_PLAYER_AMATEUR_TEMPLATE,
    ("LFA_PLAYER", "PRO"): LFA_PLAYER_PRO_TEMPLATE,

    # Academy Seasons (full year Jul-Jun - CENTER locations only)
    ("LFA_PLAYER_PRE_ACADEMY", "PRE"): LFA_PLAYER_PRE_ACADEMY_TEMPLATE,
    ("LFA_PLAYER_YOUTH_ACADEMY", "YOUTH"): LFA_PLAYER_YOUTH_ACADEMY_TEMPLATE,
    ("LFA_PLAYER_AMATEUR_ACADEMY", "AMATEUR"): LFA_PLAYER_AMATEUR_ACADEMY_TEMPLATE,
    ("LFA_PLAYER_PRO_ACADEMY", "PRO"): LFA_PLAYER_PRO_ACADEMY_TEMPLATE,

    # TODO: Add GANCUJU, COACH, INTERNSHIP templates later
}


def get_template(specialization: str, age_group: str) -> Dict:
    """Get semester template for a given specialization and age group"""
    key = (specialization, age_group)
    if key not in SEMESTER_TEMPLATES:
        raise ValueError(f"No template found for {specialization} / {age_group}")
    return SEMESTER_TEMPLATES[key]
