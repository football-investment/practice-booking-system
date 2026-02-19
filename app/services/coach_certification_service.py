"""
👨‍🏫 Coach Certification Service
Handles certification tracking for LFA Coach specialization
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional

from ..models.license import UserLicense


class CoachCertificationService:
    """Service for managing coach certifications"""

    # Valid certification levels in order
    CERTIFICATION_LEVELS = [
        'PRE_ASSISTANT',
        'PRE_HEAD',
        'YOUTH_ASSISTANT',
        'YOUTH_HEAD',
        'AMATEUR_ASSISTANT',
        'AMATEUR_HEAD',
        'PRO_ASSISTANT',
        'PRO_HEAD'
    ]

    # Teaching hours required for each certification
    TEACHING_HOURS_REQUIRED = {
        'PRE_ASSISTANT': 0,
        'PRE_HEAD': 100,
        'YOUTH_ASSISTANT': 200,
        'YOUTH_HEAD': 400,
        'AMATEUR_ASSISTANT': 600,
        'AMATEUR_HEAD': 1000,
        'PRO_ASSISTANT': 1500,
        'PRO_HEAD': 2500
    }

    def __init__(self, db: Session):
        self.db = db

    def get_current_certification(self, user_license_id: int) -> str:
        """Get current certification level from user license"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.current_certification:
            return 'PRE_ASSISTANT'  # Default starting certification

        return license.current_certification.upper()

    def get_teaching_hours(self, user_license_id: int) -> int:
        """Get total teaching hours from user license"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            return 0

        return license.teaching_hours or 0

    def get_next_certification(self, current_cert: str) -> Optional[str]:
        """Get the next certification in progression"""
        try:
            current_index = self.CERTIFICATION_LEVELS.index(current_cert.upper())
            if current_index < len(self.CERTIFICATION_LEVELS) - 1:
                return self.CERTIFICATION_LEVELS[current_index + 1]
            return None  # Already at highest certification
        except ValueError:
            return None

    def get_certification_progress(self, user_license_id: int) -> Dict:
        """
        Get certification progress information

        Returns:
            Dict with current_certification, teaching_hours, next_certification, hours_needed, progress_percentage
        """
        current_cert = self.get_current_certification(user_license_id)
        teaching_hours = self.get_teaching_hours(user_license_id)
        next_cert = self.get_next_certification(current_cert)

        result = {
            'current_certification': current_cert,
            'teaching_hours': teaching_hours,
            'current_required_hours': self.TEACHING_HOURS_REQUIRED.get(current_cert, 0),
            'next_certification': next_cert,
            'next_required_hours': None,
            'hours_needed': None,
            'progress_percentage': 100.0
        }

        if next_cert:
            next_required = self.TEACHING_HOURS_REQUIRED.get(next_cert, 0)
            current_required = self.TEACHING_HOURS_REQUIRED.get(current_cert, 0)
            hours_needed = next_required - teaching_hours

            # Calculate progress percentage
            if next_required > current_required:
                hours_in_range = teaching_hours - current_required
                range_size = next_required - current_required
                progress_percentage = min(100.0, (hours_in_range / range_size) * 100)
            else:
                progress_percentage = 100.0

            result.update({
                'next_required_hours': next_required,
                'hours_needed': max(0, hours_needed),
                'progress_percentage': progress_percentage
            })

        return result

    def check_certification_upgrade(self, user_license_id: int) -> Optional[str]:
        """
        Check if coach should be upgraded based on teaching hours

        Returns:
            New certification if upgraded, None otherwise
        """
        current_cert = self.get_current_certification(user_license_id)
        teaching_hours = self.get_teaching_hours(user_license_id)
        next_cert = self.get_next_certification(current_cert)

        if not next_cert:
            return None

        next_required = self.TEACHING_HOURS_REQUIRED.get(next_cert, float('inf'))

        if teaching_hours >= next_required:
            # Update license certification
            license = self.db.query(UserLicense).filter(
                UserLicense.id == user_license_id
            ).first()

            if license:
                license.current_certification = next_cert
                self.db.flush()

            return next_cert

        return None

    def add_teaching_hours(self, user_license_id: int, hours: float) -> int:
        """
        Add teaching hours to a coach's record

        Args:
            user_license_id: UserLicense ID
            hours: Hours to add

        Returns:
            New total teaching hours
        """
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            return 0

        current_hours = license.teaching_hours or 0
        new_hours = current_hours + hours

        license.teaching_hours = new_hours
        self.db.flush()

        # Check if this triggers a certification upgrade
        self.check_certification_upgrade(user_license_id)

        return int(new_hours)
