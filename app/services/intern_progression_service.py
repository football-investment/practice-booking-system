"""
💼 Internship Progression Service
Handles XP and level tracking for Internship specialization
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from ..models.license import UserLicense
from ..models.user import User


class InternProgressionService:
    """Service for managing internship XP and level progression"""

    # XP thresholds for each level (5 levels total)
    LEVEL_THRESHOLDS = {
        'JUNIOR': 0,
        'MID_LEVEL': 1000,
        'SENIOR': 2500,
        'LEAD': 5000,
        'PRINCIPAL': 10000
    }

    LEVEL_ORDER = ['JUNIOR', 'MID_LEVEL', 'SENIOR', 'LEAD', 'PRINCIPAL']

    def __init__(self, db: Session):
        self.db = db

    def get_current_level(self, user_license_id: int) -> str:
        """Get current intern level from user license"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.current_level:
            return 'JUNIOR'  # Default starting level

        return license.current_level.upper()

    def get_current_xp(self, user_license_id: int) -> int:
        """Get current XP from user license"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            return 0

        return license.total_xp or 0

    def get_next_level(self, current_level: str) -> Optional[str]:
        """Get the next level in progression"""
        try:
            current_index = self.LEVEL_ORDER.index(current_level.upper())
            if current_index < len(self.LEVEL_ORDER) - 1:
                return self.LEVEL_ORDER[current_index + 1]
            return None  # Already at highest level
        except ValueError:
            return None

    def get_xp_progress(self, user_license_id: int) -> Dict:
        """
        Get XP progress information

        Returns:
            Dict with current_level, current_xp, next_level, next_threshold, progress_percentage
        """
        current_level = self.get_current_level(user_license_id)
        current_xp = self.get_current_xp(user_license_id)
        next_level = self.get_next_level(current_level)

        result = {
            'current_level': current_level,
            'current_xp': current_xp,
            'current_threshold': self.LEVEL_THRESHOLDS.get(current_level, 0),
            'next_level': next_level,
            'next_threshold': None,
            'xp_needed': None,
            'progress_percentage': 100.0
        }

        if next_level:
            next_threshold = self.LEVEL_THRESHOLDS.get(next_level, 0)
            current_threshold = self.LEVEL_THRESHOLDS.get(current_level, 0)
            xp_needed = next_threshold - current_xp

            # Calculate progress percentage
            if next_threshold > current_threshold:
                xp_in_range = current_xp - current_threshold
                range_size = next_threshold - current_threshold
                progress_percentage = min(100.0, (xp_in_range / range_size) * 100)
            else:
                progress_percentage = 100.0

            result.update({
                'next_threshold': next_threshold,
                'xp_needed': max(0, xp_needed),
                'progress_percentage': progress_percentage
            })

        return result

    def check_level_up(self, user_license_id: int) -> Optional[str]:
        """
        Check if intern should level up based on current XP

        Returns:
            New level if leveled up, None otherwise
        """
        current_level = self.get_current_level(user_license_id)
        current_xp = self.get_current_xp(user_license_id)
        next_level = self.get_next_level(current_level)

        if not next_level:
            return None

        next_threshold = self.LEVEL_THRESHOLDS.get(next_level, float('inf'))

        if current_xp >= next_threshold:
            # Update license level
            license = self.db.query(UserLicense).filter(
                UserLicense.id == user_license_id
            ).first()

            if license:
                license.current_level = next_level
                self.db.flush()

            return next_level

        return None
