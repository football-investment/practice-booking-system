"""
Specialization Validation Helper

This module provides helper functions for validating specialization-specific
rules using the new spec services architecture.

Used by API endpoints to enforce specialization-specific business logic:
- Session booking eligibility
- Age validation
- Enrollment requirements
- Progression status
"""

from typing import Tuple, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.session import Session as SessionModel
from app.models.license import UserLicense
from app.services.specs import get_spec_service


def validate_can_book_session(
    user: User,
    session: SessionModel,
    db: Session
) -> Tuple[bool, str]:
    """
    Validate if user can book a session using spec-specific rules.

    This function delegates to the appropriate specialization service
    based on the session's specialization type.

    Args:
        user: User attempting to book
        session: Session to book
        db: Database session

    Returns:
        Tuple of (can_book: bool, reason: str)

    Raises:
        HTTPException: If validation fails with appropriate error code
    """
    # If session is accessible to all specializations, allow booking
    if session.is_accessible_to_all:
        return True, "Session is accessible to all specializations"

    # Get appropriate spec service for target specialization
    try:
        spec_service = get_spec_service(session.target_specialization.value, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown specialization type: {session.target_specialization.value}"
        )

    # Use spec service to validate booking
    can_book, reason = spec_service.can_book_session(user, session, db)

    if not can_book:
        # Return validation result (caller decides whether to raise exception)
        return False, reason

    return True, reason


def validate_user_age_for_specialization(
    user: User,
    specialization_type: str,
    target_group: str = None,
    db: Session = None
) -> Tuple[bool, str]:
    """
    Validate if user's age meets requirements for a specialization.

    Args:
        user: User to validate
        specialization_type: Specialization type (e.g., "LFA_PLAYER_PRE")
        target_group: Optional target group/level within specialization
        db: Database session

    Returns:
        Tuple of (is_eligible: bool, reason: str)

    Raises:
        HTTPException: If specialization type is unknown
    """
    # Get appropriate spec service
    try:
        spec_service = get_spec_service(specialization_type, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialization type: {specialization_type}"
        )

    # Validate age eligibility
    is_eligible, reason = spec_service.validate_age_eligibility(user, target_group, db)

    return is_eligible, reason


def get_user_enrollment_requirements(
    user: User,
    specialization_type: str,
    db: Session
) -> Dict:
    """
    Get enrollment requirements for user in a specialization.

    Returns what the user needs to complete/provide to participate
    in the specialization (license, enrollment, payment, etc.)

    Args:
        user: User to check
        specialization_type: Specialization type
        db: Database session

    Returns:
        Dictionary with structure:
        {
            "can_participate": bool,
            "missing_requirements": List[str],
            "current_status": Dict
        }

    Raises:
        HTTPException: If specialization type is unknown
    """
    # Get appropriate spec service
    try:
        spec_service = get_spec_service(specialization_type, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialization type: {specialization_type}"
        )

    # Get enrollment requirements
    requirements = spec_service.get_enrollment_requirements(user, db)

    return requirements


def get_user_progression_status(
    user_license: UserLicense,
    db: Session
) -> Dict:
    """
    Get progression status for a user license.

    Returns current level, progress, next level, achievements, etc.
    based on the specialization type.

    Args:
        user_license: UserLicense to check
        db: Database session

    Returns:
        Dictionary with progression information (structure varies by spec)

    Raises:
        HTTPException: If specialization type is unknown
    """
    if not user_license.specialization_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License has no specialization type defined"
        )

    # Get appropriate spec service
    try:
        spec_service = get_spec_service(user_license.specialization_type, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown specialization type: {user_license.specialization_type}"
        )

    # Get progression status
    progression = spec_service.get_progression_status(user_license, db)

    return progression


def check_specialization_type(specialization_type: str) -> Tuple[bool, str]:
    """
    Check if a specialization type is valid and which service it uses.

    Args:
        specialization_type: Specialization type string

    Returns:
        Tuple of (is_valid: bool, service_type: str)
        service_type will be "session_based", "semester_based", or "unknown"
    """
    try:
        spec_service = get_spec_service(specialization_type)
        if spec_service.is_session_based():
            return True, "session_based"
        elif spec_service.is_semester_based():
            return True, "semester_based"
        else:
            return True, "unknown"
    except ValueError:
        return False, "unknown"
