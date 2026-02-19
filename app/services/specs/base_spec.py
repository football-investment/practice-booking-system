"""
Base Specialization Service - Abstract Base Class

This module defines the abstract interface that all specialization services must implement.

Specialization Types:
- SESSION-BASED: Continuous training, no semester enrollment required
  - LFA_PLAYER: Football training with age-based categorization
  - GANCUJU_PLAYER: Traditional Chinese football with belt system

- SEMESTER-BASED: Fixed duration courses requiring semester enrollment
  - LFA_COACH: Coach training with curriculum, projects, and belt progression
  - LFA_INTERNSHIP: Work-based learning with company placements
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session


class BaseSpecializationService(ABC):
    """
    Abstract base class for all specialization services.

    Defines common interface that all specialization types must implement.
    This allows for clean separation between session-based and semester-based
    specializations while maintaining a consistent API.

    Usage:
        service = get_spec_service(user.specialization)
        can_book, reason = service.can_book_session(user, session)
    """

    # ========================================================================
    # ABSTRACT METHODS - Must be implemented by all subclasses
    # ========================================================================

    @abstractmethod
    def can_book_session(self, user, session, db: Session) -> Tuple[bool, str]:
        """
        Check if user can book a session.

        Session-based specs: Check age group compatibility, no semester enrollment needed
        Semester-based specs: Check semester enrollment and payment verification

        Args:
            user: User model instance
            session: Session model instance
            db: Database session

        Returns:
            Tuple of (can_book: bool, reason: str)
            - (True, "Success message") if booking allowed
            - (False, "Error message explaining why not") if not allowed
        """

    @abstractmethod
    def get_enrollment_requirements(self, user, db: Session) -> Dict:
        """
        Get what's needed for user to enroll/participate in this specialization.

        Session-based specs: Returns age group info, active license status
        Semester-based specs: Returns semester enrollment status, payment status

        Args:
            user: User model instance
            db: Database session

        Returns:
            Dictionary with structure:
            {
                "can_participate": bool,
                "missing_requirements": List[str],
                "current_status": Dict (spec-specific info)
            }
        """

    @abstractmethod
    def validate_age_eligibility(self, user, target_group: Optional[str] = None, db: Session = None) -> Tuple[bool, str]:
        """
        Validate age requirements for this specialization.

        Session-based specs: Check if user's age fits the age group rules
        Semester-based specs: May have minimum age requirements but not age groups

        Args:
            user: User model instance
            target_group: Optional specific age group to validate against (for session-based)
            db: Database session (optional, for complex queries)

        Returns:
            Tuple of (is_eligible: bool, reason: str)
        """

    @abstractmethod
    def get_progression_status(self, user_license, db: Session) -> Dict:
        """
        Get current progression/level status for this user's license.

        Session-based specs: Returns skill assessment progress
        Semester-based specs: Returns belt/level progression, curriculum completion

        Args:
            user_license: UserLicense model instance
            db: Database session

        Returns:
            Dictionary with structure:
            {
                "current_level": str,
                "progress_percentage": float,
                "achievements": List[Dict],
                "next_milestone": Dict (optional)
            }
        """

    # ========================================================================
    # COMMON UTILITY METHODS - Shared across all specializations
    # ========================================================================

    def calculate_age(self, date_of_birth: date) -> int:
        """
        Calculate user's age in years based on date of birth.

        Args:
            date_of_birth: User's date of birth

        Returns:
            Age in years (integer)
        """
        if not date_of_birth:
            raise ValueError("Date of birth is required to calculate age")

        today = datetime.now().date()
        age = today.year - date_of_birth.year

        # Adjust if birthday hasn't occurred yet this year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1

        return age

    def is_session_based(self) -> bool:
        """
        Check if this is a session-based specialization.

        Session-based specs don't require semester enrollment.
        Override in subclass if needed.

        Returns:
            True if session-based, False if semester-based
        """
        return False

    def is_semester_based(self) -> bool:
        """
        Check if this is a semester-based specialization.

        Semester-based specs require semester enrollment and payment.
        Override in subclass if needed.

        Returns:
            True if semester-based, False if session-based
        """
        return not self.is_session_based()

    def get_specialization_name(self) -> str:
        """
        Get human-readable name of this specialization.
        Override in subclass.

        Returns:
            Specialization name (e.g., "LFA Football Player", "LFA Coach")
        """
        return self.__class__.__name__.replace("Service", "")

    # ========================================================================
    # VALIDATION HELPERS
    # ========================================================================

    def validate_user_has_license(self, user, db: Session) -> Tuple[bool, Optional[str]]:
        """
        Check if user has an active license for this specialization.

        Args:
            user: User model instance
            db: Database session

        Returns:
            Tuple of (has_license: bool, error_message: Optional[str])
        """
        from app.models.license import UserLicense

        license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.is_active == True
        ).first()

        if not license:
            return False, f"No active license found for {self.get_specialization_name()}"

        return True, None

    def validate_date_of_birth(self, user) -> Tuple[bool, str]:
        """
        Check if user has a valid date of birth set.

        Args:
            user: User model instance

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not user.date_of_birth:
            return False, "Date of birth is required but not set"

        # Check if date of birth is in the future
        if user.date_of_birth > datetime.now().date():
            return False, "Date of birth cannot be in the future"

        return True, "Date of birth is valid"
