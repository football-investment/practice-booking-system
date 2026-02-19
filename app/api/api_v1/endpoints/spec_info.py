"""
Specialization Information API Endpoints

Provides endpoints for querying specialization-specific information
using the new spec services architecture.

Endpoints:
- GET /spec-info/enrollment-requirements - Get enrollment requirements for current user
- GET /spec-info/progression - Get progression status for user's license
- GET /spec-info/can-book/{session_id} - Check if user can book a specific session
- GET /spec-info/age-eligibility - Check age eligibility for a specialization
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.session import Session as SessionModel
from app.models.license import UserLicense
from app.api.helpers.spec_validation import (
    validate_can_book_session,
    validate_user_age_for_specialization,
    get_user_enrollment_requirements,
    get_user_progression_status,
    check_specialization_type
)

router = APIRouter()


@router.get("/enrollment-requirements", response_model=Dict[str, Any])
def get_enrollment_requirements_for_user(
    specialization_type: str = Query(..., description="Specialization type to check"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get enrollment requirements for current user in a specialization.

    Returns what the user needs to complete/provide to participate:
    - Active license
    - Semester enrollment (for semester-based specs)
    - Payment verification
    - Age eligibility
    - Position selection (for Internship)
    - etc.

    **Example Response:**
    ```json
    {
        "can_participate": false,
        "missing_requirements": [
            "Active license required",
            "Semester enrollment required"
        ],
        "current_status": {
            "has_license": false,
            "has_semester_enrollment": false,
            "payment_verified": false
        }
    }
    ```
    """
    # Check if specialization type is valid
    is_valid, service_type = check_specialization_type(specialization_type)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialization type: {specialization_type}"
        )

    # Get requirements using spec service
    requirements = get_user_enrollment_requirements(current_user, specialization_type, db)

    return {
        "specialization_type": specialization_type,
        "service_type": service_type,
        **requirements
    }


@router.get("/progression/{license_id}", response_model=Dict[str, Any])
def get_progression_for_license(
    license_id: int = Path(..., description="User license ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get progression status for a user license.

    Returns current level/certification/belt, progress percentage,
    next level, achievements, etc. based on specialization type.

    **Response varies by specialization:**
    - **LFA Player:** Current age group, cross-group attendance rules
    - **GanCuju Player:** Current belt, next belt, belt history
    - **LFA Coach:** Current certification, teaching hours, next cert requirements
    - **LFA Internship:** Current level, XP, semester, thresholds

    **Access Control:**
    - Students can only view their own licenses
    - Instructors and admins can view any license
    """
    # Get license
    license = db.query(UserLicense).filter(UserLicense.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License {license_id} not found"
        )

    # Check access: students can only view own licenses
    if current_user.role.value == 'student' and license.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own license progression"
        )

    # Get progression status using spec service
    progression = get_user_progression_status(license, db)

    # Check service type
    _, service_type = check_specialization_type(license.specialization_type)

    return {
        "license_id": license_id,
        "user_id": license.user_id,
        "specialization_type": license.specialization_type,
        "service_type": service_type,
        **progression
    }


@router.get("/can-book/{session_id}", response_model=Dict[str, Any])
def check_can_book_session(
    session_id: int = Path(..., description="Session ID to check"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check if current user can book a specific session.

    Uses spec-specific validation rules:
    - **Session-based (LFA Player):** Direct booking, no semester enrollment needed
    - **Semester-based (GanCuju, Coach, Internship):** Requires active enrollment + payment

    **Example Response:**
    ```json
    {
        "session_id": 123,
        "can_book": false,
        "reason": "Payment not verified. Please complete payment to access sessions.",
        "session_specialization": "INTERNSHIP",
        "service_type": "semester_based"
    }
    ```
    """
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    # Check if user can book using spec service
    can_book, reason = validate_can_book_session(current_user, session, db)

    # Check service type
    _, service_type = check_specialization_type(session.specialization_type)

    return {
        "session_id": session_id,
        "session_name": session.name,
        "session_specialization": session.specialization_type,
        "service_type": service_type,
        "can_book": can_book,
        "reason": reason
    }


@router.get("/age-eligibility", response_model=Dict[str, Any])
def check_age_eligibility(
    specialization_type: str = Query(..., description="Specialization type to check"),
    target_group: Optional[str] = Query(None, description="Target group/level within specialization"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check if current user's age meets requirements for a specialization.

    **Examples:**
    - `specialization_type=LFA_PLAYER_PRE` → Check if age 6-11
    - `specialization_type=LFA_COACH&target_group=PRO_HEAD` → Check if age 23+
    - `specialization_type=INTERNSHIP` → Check if age 18+
    - `specialization_type=GANCUJU_PLAYER` → Check if age 5+

    **Example Response:**
    ```json
    {
        "specialization_type": "LFA_COACH",
        "target_group": "PRO_HEAD",
        "user_age": 25,
        "is_eligible": true,
        "reason": "Eligible for LFA Coach (age 25)"
    }
    ```
    """
    # Check if specialization type is valid
    is_valid, service_type = check_specialization_type(specialization_type)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialization type: {specialization_type}"
        )

    # Validate age eligibility
    is_eligible, reason = validate_user_age_for_specialization(
        current_user, specialization_type, target_group, db
    )

    # Calculate user's age if they have date_of_birth
    user_age = None
    if current_user.date_of_birth:
        from datetime import datetime
        today = datetime.now().date()
        age = today.year - current_user.date_of_birth.year
        if (today.month, today.day) < (current_user.date_of_birth.month, current_user.date_of_birth.day):
            age -= 1
        user_age = age

    return {
        "specialization_type": specialization_type,
        "target_group": target_group,
        "service_type": service_type,
        "user_age": user_age,
        "is_eligible": is_eligible,
        "reason": reason
    }


@router.get("/specialization-types", response_model=Dict[str, Any])
def list_specialization_types() -> Any:
    """
    List all available specialization types and their service types.

    Returns which specializations are session-based vs semester-based.

    **Example Response:**
    ```json
    {
        "specializations": {
            "LFA_PLAYER": "session_based",
            "GANCUJU_PLAYER": "semester_based",
            "LFA_COACH": "semester_based",
            "INTERNSHIP": "semester_based"
        }
    }
    ```
    """
    # Test all known specialization prefixes
    known_prefixes = [
        "LFA_PLAYER",
        "GANCUJU_PLAYER",
        "LFA_COACH",
        "INTERNSHIP"
    ]

    specializations = {}
    for prefix in known_prefixes:
        is_valid, service_type = check_specialization_type(prefix)
        if is_valid:
            specializations[prefix] = service_type

    return {
        "specializations": specializations,
        "total_count": len(specializations)
    }
