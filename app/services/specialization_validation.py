"""
Specialization Validation Service

Validates user eligibility for specializations based on:
- Age requirements
- Parental consent (for minors in LFA_COACH)
- Age group matching (for LFA_FOOTBALL_PLAYER and LFA_COACH)
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.specialization import SpecializationType
from app.services.specialization_config_loader import get_config_loader


class SpecializationValidationError(Exception):
    """Raised when specialization validation fails"""
    pass


class SpecializationValidator:
    """
    Validates user eligibility for specializations.

    Key validations:
    1. Minimum age requirement
    2. Age group matching (for LFA_FOOTBALL_PLAYER, LFA_COACH)
    3. Parental consent (for LFA_COACH users under 18)
    """

    def __init__(self, db: Session):
        self.db = db
        self.config_loader = get_config_loader()

    def validate_user_for_specialization(
        self,
        user: User,
        specialization: SpecializationType,
        raise_exception: bool = True
    ) -> Dict[str, Any]:
        """
        Validate if user meets requirements for a specialization.

        Args:
            user: User instance
            specialization: SpecializationType enum
            raise_exception: If True, raise SpecializationValidationError on failure.
                           If False, return validation result dict.

        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'requirements': Dict[str, Any]
            }

        Raises:
            SpecializationValidationError: If validation fails and raise_exception=True
        """
        errors = []
        warnings = []

        # Load specialization config
        try:
            config = self.config_loader.load_config(specialization)
        except Exception as e:
            errors.append(f"Failed to load specialization config: {e}")
            return self._format_result(False, errors, warnings, {})

        # 1. Check minimum age requirement
        min_age = config.get('min_age', 0)
        age_valid, age_error = self._validate_min_age(user, min_age)
        if not age_valid:
            errors.append(age_error)

        # 2. Check LFA_COACH specific requirements
        if specialization == SpecializationType.LFA_COACH:
            # LFA_COACH has 14+ entry age requirement
            if user.age is not None and user.age < 14:
                errors.append(f"LFA_COACH requires minimum age of 14 years. User is {user.age} years old.")

            # Check parental consent for minors (under 18)
            if user.is_minor:
                if not user.parental_consent:
                    errors.append(
                        "LFA_COACH requires parental consent for users under 18 years old. "
                        "Parent/guardian must provide written consent."
                    )
                else:
                    warnings.append(f"Parental consent provided by: {user.parental_consent_by}")

        # 3. Check age group matching (for age-group based specializations)
        age_groups = config.get('age_groups', [])
        if age_groups:
            age_group_valid, age_group_error = self._validate_age_group(user, age_groups)
            if not age_group_valid:
                errors.append(age_group_error)

        # 4. Check date of birth is set
        if user.date_of_birth is None:
            warnings.append("User date of birth not set. Age validation skipped.")

        # Compile requirements
        requirements = {
            'min_age': min_age,
            'specialization_name': config.get('name'),
            'has_age_groups': len(age_groups) > 0,
            'age_groups': age_groups if age_groups else None,
        }

        if specialization == SpecializationType.LFA_COACH:
            requirements['requires_parental_consent_under_18'] = True
            requirements['min_age_override'] = 14  # LFA_COACH specific

        # Determine if valid
        is_valid = len(errors) == 0

        result = self._format_result(is_valid, errors, warnings, requirements)

        # Raise exception if requested and invalid
        if not is_valid and raise_exception:
            error_msg = "; ".join(errors)
            raise SpecializationValidationError(error_msg)

        return result

    def _validate_min_age(self, user: User, min_age: int) -> tuple[bool, Optional[str]]:
        """
        Validate user meets minimum age requirement.

        Args:
            user: User instance
            min_age: Minimum required age

        Returns:
            Tuple of (is_valid, error_message)
        """
        if user.date_of_birth is None:
            # Cannot validate without DOB, but don't fail
            return True, None

        user_age = user.age
        if user_age is None:
            return True, None

        if user_age < min_age:
            return False, f"User must be at least {min_age} years old. Current age: {user_age}"

        return True, None

    def _validate_age_group(self, user: User, age_groups: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """
        Validate user falls into one of the allowed age groups.

        Args:
            user: User instance
            age_groups: List of age group definitions from config

        Returns:
            Tuple of (is_valid, error_message)
        """
        if user.date_of_birth is None or user.age is None:
            # Cannot validate without age
            return True, None

        user_age = user.age

        # Check if user fits into any age group
        for age_group in age_groups:
            min_age = age_group.get('min_age', 0)
            max_age = age_group.get('max_age')  # None means no upper limit

            if max_age is None:
                # No upper limit
                if user_age >= min_age:
                    return True, None
            else:
                # Has upper limit
                if min_age <= user_age <= max_age:
                    return True, None

        # User doesn't fit any age group
        age_ranges = []
        for ag in age_groups:
            min_a = ag.get('min_age', 0)
            max_a = ag.get('max_age')
            if max_a is None:
                age_ranges.append(f"{min_a}+")
            else:
                age_ranges.append(f"{min_a}-{max_a}")

        return False, f"User age {user_age} does not match any age group: {', '.join(age_ranges)}"

    def _format_result(
        self,
        valid: bool,
        errors: List[str],
        warnings: List[str],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format validation result."""
        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings,
            'requirements': requirements
        }

    def get_eligible_specializations(self, user: User) -> List[Dict[str, Any]]:
        """
        Get list of specializations user is eligible for.

        Args:
            user: User instance

        Returns:
            List of dicts with specialization info and eligibility:
            [
                {
                    'specialization': SpecializationType,
                    'name': str,
                    'eligible': bool,
                    'errors': List[str],
                    'warnings': List[str]
                },
                ...
            ]
        """
        results = []

        for spec_enum in SpecializationType:
            validation = self.validate_user_for_specialization(
                user,
                spec_enum,
                raise_exception=False
            )

            try:
                display_info = self.config_loader.get_display_info(spec_enum)
                name = display_info['name']
            except:
                name = spec_enum.value

            results.append({
                'specialization': spec_enum,
                'specialization_id': spec_enum.value,
                'name': name,
                'eligible': validation['valid'],
                'errors': validation['errors'],
                'warnings': validation['warnings'],
                'requirements': validation['requirements']
            })

        return results

    def get_matching_age_group(
        self,
        user: User,
        specialization: SpecializationType
    ) -> Optional[Dict[str, Any]]:
        """
        Get the age group that matches the user's age.

        Args:
            user: User instance
            specialization: SpecializationType enum

        Returns:
            Age group dict or None if no match
        """
        if user.age is None:
            return None

        config = self.config_loader.load_config(specialization)
        age_groups = config.get('age_groups', [])

        for age_group in age_groups:
            min_age = age_group.get('min_age', 0)
            max_age = age_group.get('max_age')

            if max_age is None:
                if user.age >= min_age:
                    return age_group
            else:
                if min_age <= user.age <= max_age:
                    return age_group

        return None


def validate_user_specialization(
    db: Session,
    user: User,
    specialization: SpecializationType
) -> Dict[str, Any]:
    """
    Convenience function to validate user for specialization.

    Args:
        db: Database session
        user: User instance
        specialization: SpecializationType enum

    Returns:
        Validation result dict

    Raises:
        SpecializationValidationError: If validation fails
    """
    validator = SpecializationValidator(db)
    return validator.validate_user_for_specialization(user, specialization, raise_exception=True)
