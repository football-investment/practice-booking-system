"""
Specialization Service
Modular specialization system with validation and spec-specific logic

Provides both generic functions and spec-specific imports
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Validation & Common
from .validation import (
    specialization_id_to_enum,
    handle_legacy_specialization,
    validate_specialization_exists,
    get_all_specializations,
    DEPRECATED_MAPPINGS,
    DEPRECATION_DEADLINE,
    DEPRECATION_WARNING
)

from .common import (
    get_level_requirements,
    get_student_progress,
    can_level_up,
    update_progress,
    get_all_levels,
    enroll_user
)

# LFA_PLAYER (GanCuju)
from .lfa_player import (
    enroll_lfa_player,
    get_lfa_player_level_requirements,
    get_lfa_player_progress,
    update_lfa_player_progress,
    get_all_lfa_player_levels
)

# LFA_COACH
from .lfa_coach import (
    enroll_lfa_coach,
    get_lfa_coach_level_requirements,
    get_lfa_coach_progress,
    update_lfa_coach_progress,
    get_all_lfa_coach_levels
)

# GANCUJU_PLAYER (alias)
from .gancuju import (
    enroll_gancuju_player,
    get_gancuju_player_level_requirements,
    get_gancuju_player_progress,
    update_gancuju_player_progress,
    get_all_gancuju_player_levels
)

# INTERNSHIP
from .internship import (
    enroll_internship,
    get_internship_level_requirements,
    get_internship_progress,
    update_internship_progress,
    get_all_internship_levels
)


__all__ = [
    # Validation
    'specialization_id_to_enum',
    'handle_legacy_specialization',
    'validate_specialization_exists',
    'get_all_specializations',
    'DEPRECATED_MAPPINGS',
    'DEPRECATION_DEADLINE',
    'DEPRECATION_WARNING',

    # Common
    'get_level_requirements',
    'get_student_progress',
    'can_level_up',
    'update_progress',
    'get_all_levels',
    'enroll_user',

    # LFA_PLAYER
    'enroll_lfa_player',
    'get_lfa_player_level_requirements',
    'get_lfa_player_progress',
    'update_lfa_player_progress',
    'get_all_lfa_player_levels',

    # LFA_COACH
    'enroll_lfa_coach',
    'get_lfa_coach_level_requirements',
    'get_lfa_coach_progress',
    'update_lfa_coach_progress',
    'get_all_lfa_coach_levels',

    # GANCUJU_PLAYER
    'enroll_gancuju_player',
    'get_gancuju_player_level_requirements',
    'get_gancuju_player_progress',
    'update_gancuju_player_progress',
    'get_all_gancuju_player_levels',

    # INTERNSHIP
    'enroll_internship',
    'get_internship_level_requirements',
    'get_internship_progress',
    'update_internship_progress',
    'get_all_internship_levels',

    # Backward compatibility
    'SpecializationService'
]


# Backward Compatibility Wrapper
class SpecializationService:
    """
    Backward compatibility wrapper for the modular specialization service.

    This class maintains the original API while delegating to the new modular functions.
    All existing code using SpecializationService(db) will continue to work.

    Usage:
        # Old way (still works)
        service = SpecializationService(db)
        result = service.enroll_user(user_id, "GANCUJU_PLAYER")

        # New way (recommended)
        from app.services.specialization import enroll_lfa_player
        result = enroll_lfa_player(db, user_id)
    """

    def __init__(self, db: Session):
        """
        Initialize the service with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _specialization_id_to_enum(self, specialization_id: str):
        """Convert specialization ID to enum (backward compatibility)"""
        return specialization_id_to_enum(specialization_id)

    def _handle_legacy_specialization(self, spec_id: str) -> str:
        """Handle legacy specialization IDs (backward compatibility)"""
        return handle_legacy_specialization(spec_id)

    def validate_specialization_exists(self, specialization_id: str) -> bool:
        """
        Check if specialization exists and is active.

        Args:
            specialization_id: Specialization ID to check

        Returns:
            True if specialization exists and is active
        """
        return validate_specialization_exists(self.db, specialization_id)

    def enroll_user(self, user_id: int, specialization_id: str) -> Dict[str, Any]:
        """
        Enroll user in a specialization.

        Args:
            user_id: User ID to enroll
            specialization_id: Specialization to enroll in

        Returns:
            Enrollment result dictionary
        """
        return enroll_user(self.db, user_id, specialization_id)

    def get_level_requirements(self, specialization_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Get requirements for a specific level.

        Args:
            specialization_id: Specialization ID
            level: Level number

        Returns:
            Level requirements dictionary
        """
        return get_level_requirements(self.db, specialization_id, level)

    def get_student_progress(self, student_id: int, specialization_id: str) -> Dict[str, Any]:
        """
        Get student progress in a specialization.

        Args:
            student_id: Student ID
            specialization_id: Specialization ID

        Returns:
            Progress dictionary
        """
        return get_student_progress(self.db, student_id, specialization_id)

    def can_level_up(self, progress) -> bool:
        """
        Check if student can level up.

        Args:
            progress: SpecializationProgress instance

        Returns:
            True if can level up
        """
        return can_level_up(self.db, progress)

    def update_progress(
        self,
        student_id: int,
        specialization_id: str,
        xp_gained: int = 0,
        sessions_completed: int = 0,
        projects_completed: int = 0
    ) -> Dict[str, Any]:
        """
        Update student progress and check for level up.

        Args:
            student_id: Student ID
            specialization_id: Specialization ID
            xp_gained: XP to add
            sessions_completed: Number of sessions completed
            projects_completed: Number of projects completed

        Returns:
            Update result dictionary
        """
        return update_progress(
            self.db,
            student_id,
            specialization_id,
            xp_gained,
            sessions_completed,
            projects_completed
        )

    def get_all_specializations(self) -> List[Dict[str, Any]]:
        """
        Get all active specializations.

        Returns:
            List of specialization dictionaries
        """
        return get_all_specializations(self.db)

    def get_all_levels(self, specialization_id: str) -> List[Dict[str, Any]]:
        """
        Get all levels for a specialization.

        Args:
            specialization_id: Specialization ID

        Returns:
            List of level dictionaries
        """
        return get_all_levels(self.db, specialization_id)
