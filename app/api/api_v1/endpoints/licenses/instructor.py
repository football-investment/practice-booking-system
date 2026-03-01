"""
Instructor license operations
"""
from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....services.license_service import LicenseService

router = APIRouter()


# Pydantic schemas (BATCH 9)
class InstructorAdvanceLicenseRequest(BaseModel):
    """Request schema for instructor license advancement"""
    model_config = ConfigDict(extra='forbid')

    user_id: int = Field(..., description="ID of user to advance")
    specialization: str = Field(..., description="COACH, PLAYER, or INTERNSHIP")
    target_level: int = Field(..., ge=1, description="Desired level number")
    reason: str | None = Field(None, description="Reason for advancement")
    requirements_met: str | None = Field(None, description="Description of requirements satisfied")

@router.post("/instructor/advance", response_model=Dict[str, Any])
async def instructor_advance_license(
    data: InstructorAdvanceLicenseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Instructor/Admin-approved license advancement (BATCH 9: Schema validation + admin access)

    Request body:
    - **user_id**: ID of user to advance
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **target_level**: Desired level number
    - **reason**: Reason for advancement (optional)
    - **requirements_met**: Description of requirements satisfied (optional)
    """
    # Check instructor/admin permissions (BATCH 9: Admin also allowed)
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can approve license advancements"
        )

    license_service = LicenseService(db)
    result = license_service.advance_license(
        user_id=data.user_id,
        specialization=data.specialization,
        target_level=data.target_level,
        advanced_by=current_user.id,
        reason=data.reason or 'Instructor approved advancement',
        requirements_met=data.requirements_met or 'Requirements verified by instructor'
    )

    return result


@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_licenses(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license information for a specific user
    - Users can view their own licenses
    - Instructors/Admins can view any user's licenses
    """
    # Users can only view their own, instructors/admins can view anyone's
    if current_user.id != user_id and current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own licenses"
        )

    license_service = LicenseService(db)
    return license_service.get_user_licenses(user_id)


@router.get("/instructor/users/{user_id}/licenses", response_model=List[Dict[str, Any]])
async def get_user_licenses_by_instructor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license information for a specific user (instructor only) - DEPRECATED, use /user/{user_id}
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view other users' licenses"
        )

    license_service = LicenseService(db)
    return license_service.get_user_licenses(user_id)


@router.get("/instructor/dashboard/{user_id}", response_model=Dict[str, Any])
async def get_user_license_dashboard_by_instructor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license dashboard for a specific user (instructor only)
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view other users' license dashboards"
        )

    license_service = LicenseService(db)
    return license_service.get_user_license_dashboard(user_id)


@router.get("/instructor/{instructor_id}/teachable-specializations", response_model=List[str])
async def get_instructor_teachable_specializations(
    instructor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of semester specialization types that an instructor can teach based on their licenses

    Returns list of specialization types like:
    - LFA_PLAYER_PRE, LFA_PLAYER_YOUTH (if has COACH license)
    - INTERNSHIP (if has INTERNSHIP license)
    - GANCUJU_PLAYER (if has PLAYER license with GANCUJU specialization)
    """
    # Authorization: instructors can only view their own, admins can view anyone's
    if current_user.role != UserRole.ADMIN and current_user.id != instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own teachable specializations"
        )

    # Get instructor's active licenses
    from .....models.license import UserLicense
    licenses = db.query(UserLicense).filter(
        UserLicense.user_id == instructor_id,
        UserLicense.is_active == True
    ).all()

    if not licenses:
        return []

    # Map licenses to semester specialization types they can teach
    teachable_specs = set()

    for license in licenses:
        if license.specialization_type == "COACH":
            # COACH license → can teach all LFA_PLAYER_* semesters
            teachable_specs.add("LFA_PLAYER_PRE")
            teachable_specs.add("LFA_PLAYER_YOUTH")
            teachable_specs.add("LFA_PLAYER_AMATEUR")
            teachable_specs.add("LFA_PLAYER_PRO")

        elif license.specialization_type == "INTERNSHIP":
            # INTERNSHIP license → can teach INTERNSHIP semesters
            teachable_specs.add("INTERNSHIP")

        elif license.specialization_type == "PLAYER":
            # PLAYER license → can teach GANCUJU_PLAYER semesters (?)
            # Note: Need to clarify this mapping
            teachable_specs.add("GANCUJU_PLAYER")

    return sorted(list(teachable_specs))


# 🔄 P0 CRITICAL: Progress-License Synchronization Endpoints
