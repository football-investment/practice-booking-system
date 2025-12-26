"""
GANCUJU_PLAYER Specialization Service (Alias for LFA_PLAYER)
Handles progression, enrollment, and level management for GanCuju players
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

from app.models.specialization import SpecializationType
from app.services.specialization_config_loader import get_config_loader
from .common import (
    get_level_requirements,
    get_student_progress,
    update_progress,
    get_all_levels,
    enroll_user
)

logger = logging.getLogger(__name__)

SPECIALIZATION_ID = "GANCUJU_PLAYER"


def enroll_gancuju_player(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Enroll user in GANCUJU_PLAYER specialization

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Enrollment result dictionary
    """
    return enroll_user(db, user_id, SPECIALIZATION_ID)


def get_gancuju_player_level_requirements(db: Session, level: int) -> Optional[Dict[str, Any]]:
    """
    Get level requirements for GANCUJU_PLAYER

    Args:
        db: Database session
        level: Level number

    Returns:
        Level requirements dict
    """
    return get_level_requirements(db, SPECIALIZATION_ID, level)


def get_gancuju_player_progress(db: Session, student_id: int) -> Dict[str, Any]:
    """
    Get student progress in GANCUJU_PLAYER specialization

    Args:
        db: Database session
        student_id: Student ID

    Returns:
        Progress dictionary
    """
    return get_student_progress(db, student_id, SPECIALIZATION_ID)


def update_gancuju_player_progress(
    db: Session,
    student_id: int,
    xp_gained: int = 0,
    sessions_completed: int = 0,
    projects_completed: int = 0
) -> Dict[str, Any]:
    """
    Update student progress in GANCUJU_PLAYER specialization

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


def get_all_gancuju_player_levels(db: Session) -> List[Dict[str, Any]]:
    """
    Get all GANCUJU_PLAYER levels

    Args:
        db: Database session

    Returns:
        List of level configurations
    """
    return get_all_levels(db, SPECIALIZATION_ID)