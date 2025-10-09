"""
🎓 Specialization API Endpoints
Handles specialization selection and information for the LFA education platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ....database import get_db
from ....models.user import User
from ....models.specialization import SpecializationType
from ....dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class SpecializationResponse(BaseModel):
    code: str
    name: str
    description: str
    features: List[str]
    icon: str

class SpecializationSetRequest(BaseModel):
    specialization: str

@router.get("/", response_model=List[SpecializationResponse])
async def list_specializations():
    """
    Get available specializations with descriptions
    🎓 PUBLIC ENDPOINT - no authentication required for onboarding
    """
    specializations = []
    
    for spec in SpecializationType:
        specializations.append(SpecializationResponse(
            code=spec.value,
            name=SpecializationType.get_display_name(spec),
            description=SpecializationType.get_description(spec),
            features=SpecializationType.get_features(spec),
            icon=SpecializationType.get_icon(spec)
        ))
    
    return specializations

@router.post("/me")
async def set_user_specialization(
    specialization_data: SpecializationSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Set current user's specialization
    🎓 CRITICAL: This is used during onboarding and profile updates
    """
    try:
        specialization = SpecializationType(specialization_data.specialization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization. Must be one of: {[s.value for s in SpecializationType]}"
        )
    
    # Update user's specialization
    current_user.specialization = specialization
    db.commit()
    db.refresh(current_user)
    
    # 📝 Log for testing/debugging
    print(f"🎓 Specialization updated: {current_user.name} → {specialization.value}")
    
    return {
        "message": "Specialization updated successfully",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "specialization": {
                "code": current_user.specialization.value,
                "name": SpecializationType.get_display_name(current_user.specialization),
                "icon": SpecializationType.get_icon(current_user.specialization)
            }
        }
    }

@router.get("/me")
async def get_user_specialization(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user's specialization"""
    return {
        "user_id": current_user.id,
        "has_specialization": current_user.has_specialization,
        "specialization": {
            "code": current_user.specialization.value if current_user.specialization else None,
            "name": current_user.specialization_display,
            "icon": current_user.specialization_icon
        } if current_user.specialization else None
    }

@router.delete("/me")
async def clear_user_specialization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear user's specialization (set to NULL)"""
    current_user.specialization = None
    db.commit()
    
    print(f"🎓 Specialization cleared for: {current_user.name}")
    
    return {
        "message": "Specialization cleared successfully",
        "user_id": current_user.id
    }

@router.get("/info/{specialization_code}")
async def get_specialization_info(specialization_code: str) -> Dict[str, Any]:
    """Get detailed information about a specific specialization"""
    try:
        specialization = SpecializationType(specialization_code.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specialization '{specialization_code}' not found"
        )

    return {
        "code": specialization.value,
        "name": SpecializationType.get_display_name(specialization),
        "description": SpecializationType.get_description(specialization),
        "features": SpecializationType.get_features(specialization),
        "icon": SpecializationType.get_icon(specialization),
        "session_access": SpecializationType.get_session_access_info(specialization),
        "project_access": SpecializationType.get_project_access_info(specialization)
    }


# ========================================
# NEW: SPECIALIZATION PROGRESS & LEVELS
# ========================================

@router.get("/levels/all")
async def get_all_specializations_with_levels(
    db: Session = Depends(get_db)
):
    """Get all specializations with their level systems"""
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        specializations = service.get_all_specializations()

        # Add levels to each specialization
        for spec in specializations:
            spec['levels'] = service.get_all_levels(spec['id'])

        return {
            'success': True,
            'data': specializations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch specializations: {str(e)}")


@router.get("/levels/{specialization_id}")
async def get_specialization_levels(
    specialization_id: str,
    db: Session = Depends(get_db)
):
    """Get all levels for a specific specialization"""
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        levels = service.get_all_levels(specialization_id)

        if not levels:
            raise HTTPException(status_code=404, detail=f"Specialization '{specialization_id}' not found")

        return {
            'success': True,
            'data': levels,
            'count': len(levels)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch levels: {str(e)}")


@router.get("/progress/{specialization_id}")
async def get_my_progress(
    specialization_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's progress for a specific specialization"""
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        progress = service.get_student_progress(current_user.id, specialization_id)

        return {
            'success': True,
            'data': progress
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch progress: {str(e)}")


@router.get("/progress")
async def get_all_my_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's progress for all specializations they have"""
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        progress_data = {}

        # Get progress for user's current specialization
        if current_user.specialization:
            spec_id = current_user.specialization.value
            progress_data[spec_id] = service.get_student_progress(current_user.id, spec_id)

        return {
            'success': True,
            'data': progress_data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch progress: {str(e)}")


@router.post("/update-progress/{specialization_id}")
async def update_progress(
    specialization_id: str,
    xp_gained: int = 0,
    sessions_completed: int = 0,
    projects_completed: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update student progress (internal use by gamification system)

    Args:
        specialization_id: PLAYER, COACH, or INTERNSHIP
        xp_gained: XP to add
        sessions_completed: Number of sessions to add
        projects_completed: Number of projects to add
    """
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        result = service.update_progress(
            student_id=current_user.id,
            specialization_id=specialization_id,
            xp_gained=xp_gained,
            sessions_completed=sessions_completed,
            projects_completed=projects_completed
        )

        return {
            'success': True,
            'data': result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update progress: {str(e)}")


@router.get("/level-info/{specialization_id}/{level}")
async def get_level_info(
    specialization_id: str,
    level: int,
    db: Session = Depends(get_db)
):
    """Get requirements for a specific level"""
    from ....services.specialization_service import SpecializationService

    service = SpecializationService(db)

    try:
        level_info = service.get_level_requirements(specialization_id, level)

        if not level_info:
            raise HTTPException(
                status_code=404,
                detail=f"Level {level} not found for specialization '{specialization_id}'"
            )

        return {
            'success': True,
            'data': level_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch level info: {str(e)}")