"""
INTERNSHIP Specialization Service
Handles internship program progression (3 levels)
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

from .common import (
    get_level_requirements,
    get_student_progress,
    update_progress,
    get_all_levels,
    enroll_user
)

logger = logging.getLogger(__name__)

SPECIALIZATION_ID = "INTERNSHIP"


def enroll_internship(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Enroll user in INTERNSHIP program

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Enrollment result dictionary
    """
    return enroll_user(db, user_id, SPECIALIZATION_ID)


def get_internship_level_requirements(db: Session, level: int) -> Optional[Dict[str, Any]]:
    """
    Get level requirements for INTERNSHIP

    Args:
        db: Database session
        level: Level number (1-3 for internship)

    Returns:
        Level requirements dict
    """
    return get_level_requirements(db, SPECIALIZATION_ID, level)


def get_internship_progress(db: Session, student_id: int) -> Dict[str, Any]:
    """
    Get student progress in INTERNSHIP

    Args:
        db: Database session
        student_id: Student ID

    Returns:
        Progress dictionary
    """
    return get_student_progress(db, student_id, SPECIALIZATION_ID)


def update_internship_progress(
    db: Session,
    student_id: int,
    xp_gained: int = 0,
    sessions_completed: int = 0,
    projects_completed: int = 0
) -> Dict[str, Any]:
    """
    Update student progress in INTERNSHIP

    Args:
        db: Database session
        student_id: Student ID
        xp_gained: XP to add
        sessions_completed: Number of sessions completed
        projects_completed: Number of projects completed

    Returns:
        Update result dictionary
    """
    return update_progress(
        db,
        student_id,
        SPECIALIZATION_ID,
        xp_gained,
        sessions_completed,
        projects_completed
    )


def get_all_internship_levels(db: Session) -> List[Dict[str, Any]]:
    """
    Get all INTERNSHIP levels (3 levels only)

    Args:
        db: Database session

    Returns:
        List of level configurations
    """
    return get_all_levels(db, SPECIALIZATION_ID)