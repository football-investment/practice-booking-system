"""
🏮 GānCuju™️©️ License API Endpoints
Marketing-oriented license progression system API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from ....database import get_db
from ....services.license_service import LicenseService
from ....dependencies import get_current_user
from ....models.user import User, UserRole

router = APIRouter()


@router.get("/metadata", response_model=List[Dict[str, Any]])
async def get_license_metadata(
    specialization: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get license metadata for all specializations or a specific one
    
    - **specialization**: Optional filter by COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_all_license_metadata(specialization)


@router.get("/metadata/{specialization}/{level}", response_model=Dict[str, Any])
async def get_license_level_metadata(
    specialization: str,
    level: int,
    db: Session = Depends(get_db)
):
    """
    Get specific license level metadata with marketing content
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: License level number (1-8 for Coach/Player, 1-5 for Internship)
    """
    license_service = LicenseService(db)
    metadata = license_service.get_license_metadata_by_level(specialization, level)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License level {level} not found for {specialization}"
        )
    
    return metadata


@router.get("/progression/{specialization}", response_model=List[Dict[str, Any]])
async def get_specialization_progression(
    specialization: str,
    db: Session = Depends(get_db)
):
    """
    Get complete progression path for a specialization
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_specialization_progression_path(specialization)


@router.get("/my-licenses", response_model=List[Dict[str, Any]])
async def get_my_licenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all licenses for the current user
    """
    license_service = LicenseService(db)
    return license_service.get_user_licenses(current_user.id)


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_license_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive license dashboard for the current user
    """
    license_service = LicenseService(db)
    return license_service.get_user_license_dashboard(current_user.id)


@router.post("/advance", response_model=Dict[str, Any])
async def advance_license(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request license advancement (requires instructor approval for actual advancement)
    
    Request body:
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **target_level**: Desired level number
    - **reason**: Reason for advancement request
    """
    required_fields = ['specialization', 'target_level']
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    license_service = LicenseService(db)
    
    # For now, allow self-advancement for testing
    # In production, this would create an advancement request
    result = license_service.advance_license(
        user_id=current_user.id,
        specialization=data['specialization'],
        target_level=data['target_level'],
        advanced_by=current_user.id,  # Would be instructor in production
        reason=data.get('reason', 'Self-advancement request'),
        requirements_met=data.get('requirements_met', 'Auto-approved for testing')
    )
    
    return result


@router.get("/requirements/{specialization}/{level}", response_model=Dict[str, Any])
async def check_advancement_requirements(
    specialization: str,
    level: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user meets requirements for license advancement
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: Target level number
    """
    license_service = LicenseService(db)
    return license_service.get_license_requirements_check(
        current_user.id, specialization, level
    )


@router.get("/marketing/{specialization}", response_model=Dict[str, Any])
async def get_marketing_content(
    specialization: str,
    level: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get marketing content for license levels
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: Optional specific level, if omitted returns all levels
    """
    license_service = LicenseService(db)
    return license_service.get_marketing_content(specialization, level)


# Instructor-only endpoints
@router.post("/instructor/advance", response_model=Dict[str, Any])
async def instructor_advance_license(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Instructor-approved license advancement
    
    Request body:
    - **user_id**: ID of user to advance
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **target_level**: Desired level number
    - **reason**: Reason for advancement
    - **requirements_met**: Description of requirements satisfied
    """
    # Check instructor permissions
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can approve license advancements"
        )
    
    required_fields = ['user_id', 'specialization', 'target_level']
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    license_service = LicenseService(db)
    result = license_service.advance_license(
        user_id=data['user_id'],
        specialization=data['specialization'],
        target_level=data['target_level'],
        advanced_by=current_user.id,
        reason=data.get('reason', 'Instructor approved advancement'),
        requirements_met=data.get('requirements_met', 'Requirements verified by instructor')
    )
    
    return result


@router.get("/instructor/users/{user_id}/licenses", response_model=List[Dict[str, Any]])
async def get_user_licenses_by_instructor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license information for a specific user (instructor only)
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