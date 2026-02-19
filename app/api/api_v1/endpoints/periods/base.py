"""
Base Utilities for Period Generators
====================================
Shared helper functions for all period generation endpoints.
"""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from typing import Tuple, Optional

from .....models.semester import Semester


def get_first_monday(year: int, month: int) -> date:
    """
    Get the first Monday of a given month

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Date of the first Monday in the specified month
    """
    d = datetime(year, month, 1)
    # Find first Monday
    while d.weekday() != 0:  # 0 = Monday
        d += timedelta(days=1)
    return d.date()


def get_last_sunday(year: int, month: int) -> date:
    """
    Get the last Sunday of a given month

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Date of the last Sunday in the specified month
    """
    # Start from last day of month
    if month == 12:
        d = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = datetime(year, month + 1, 1) - timedelta(days=1)

    # Find last Sunday
    while d.weekday() != 6:  # 6 = Sunday
        d -= timedelta(days=1)
    return d.date()


def check_existing_period(
    db: Session,
    specialization_type: str,
    code: str
) -> Tuple[bool, Optional[Semester]]:
    """
    Check if a period already exists

    Args:
        db: Database session
        specialization_type: Specialization type (e.g., "LFA_PLAYER_PRE")
        code: Period code (e.g., "2025/LFA_PLAYER_PRE_M03")

    Returns:
        Tuple of (exists: bool, semester: Optional[Semester])
    """
    existing = db.query(Semester).filter(
        Semester.specialization_type == specialization_type,
        Semester.code == code
    ).first()
    return (existing is not None, existing)


def get_period_label(specialization: str) -> str:
    """
    Get period label based on specialization

    Args:
        specialization: Base specialization type (e.g., "LFA_PLAYER", "INTERNSHIP")

    Returns:
        "season" for LFA_PLAYER, "semester" for others
    """
    return "season" if specialization == "LFA_PLAYER" else "semester"
