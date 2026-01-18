"""
Helper functions for web routes
"""
from sqlalchemy.orm import Session
from datetime import date


def update_specialization_xp(
    db: Session,
    student_id: int,
    specialization_id: str,
    xp_earned: int,
    session_id: int,
    is_update: bool = False
):
    """
    Update or create specialization_progress record with XP

    Args:
        db: Database session
        student_id: Student user ID
        specialization_id: Specialization type (e.g., 'INTERNSHIP')
        xp_earned: XP amount to award
        session_id: Session ID for tracking
        is_update: If True, recalculate XP (don't add); if False, add new XP
    """
def get_lfa_age_category(date_of_birth):
    """
    Determine LFA Player age category based on date of birth.

    Returns tuple: (category_code, category_name, age_range, description)

    Categories:
    - PRE (5-13 years): Foundation Years - Monthly semesters
    - YOUTH (14-18 years): Technical Development - Quarterly semesters
    - AMATEUR (14+ years): Competitive Play - Bi-annual semesters (instructor assigned)
    - PRO (14+ years): Professional Track - Annual semesters (instructor assigned)
    """
    if not date_of_birth:
        return None, None, None, "Date of birth not set"

    today = date.today()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    if 5 <= age <= 13:
        return "PRE", "PRE (Foundation Years)", "5-13 years", f"Age {age} - Monthly training blocks"
    elif 14 <= age <= 18:
        return "YOUTH", "YOUTH (Technical Development)", "14-18 years", f"Age {age} - Quarterly programs"
    elif age > 18:
        # For 18+ students, category must be assigned by instructor (AMATEUR or PRO)
        return None, None, None, f"Age {age} - Category assigned by instructor (AMATEUR or PRO)"
    else:
        return None, None, None, f"Age {age} - Below minimum age requirement (5 years)"
