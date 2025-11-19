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
from ....services.audit_service import AuditService
from ....models.audit_log import AuditAction
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
async def list_specializations(db: Session = Depends(get_db)):
    """
    Get available specializations with descriptions (HYBRID: DB + JSON)
    🎓 PUBLIC ENDPOINT - no authentication required for onboarding

    Process:
    1. Load active specializations from DB
    2. Load full content from JSON configs
    3. Return merged data
    """
    from app.services.specialization_service import SpecializationService

    service = SpecializationService(db)
    all_specs = service.get_all_specializations()

    specializations = []
    for spec_data in all_specs:
        specializations.append(SpecializationResponse(
            code=spec_data['id'],
            name=spec_data['name'],
            description=spec_data['description'],
            features=spec_data.get('features', []),  # Will be added in next iteration
            icon=spec_data['icon']
        ))

    return specializations

@router.post("/me")
async def set_user_specialization(
    specialization_data: SpecializationSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Set current user's specialization (HYBRID: with age/consent validation)
    🎓 CRITICAL: This is used during onboarding and profile updates

    Process:
    1. Validate specialization enum
    2. Check DB existence + is_active
    3. Validate age requirements (JSON)
    4. Validate parental consent (for LFA_COACH under 18)
    5. Update user specialization
    """
    from app.services.specialization_service import SpecializationService

    # STEP 1: Validate enum
    try:
        specialization = SpecializationType(specialization_data.specialization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization. Must be one of: {[s.value for s in SpecializationType]}"
        )

    # STEP 2-4: Use service to validate and enroll
    service = SpecializationService(db)

    try:
        result = service.enroll_user(current_user.id, specialization.value)

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # STEP 5: Update user's specialization
    old_specialization = current_user.specialization.value if current_user.specialization else None
    current_user.specialization = specialization
    db.commit()
    db.refresh(current_user)

    # 🔍 AUDIT: Log specialization change
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SPECIALIZATION_SELECTED,
        user_id=current_user.id,
        resource_type="specialization",
        resource_id=None,
        details={
            "old_specialization": old_specialization,
            "new_specialization": specialization.value,
            "age": current_user.calculate_age() if current_user.date_of_birth else None,
            "has_parental_consent": current_user.parental_consent
        }
    )

    # 📝 Log for testing/debugging
    print(f"🎓 Specialization updated: {current_user.name} → {specialization.value}")

    # Get display info from JSON (HYBRID)
    from app.services.specialization_config_loader import SpecializationConfigLoader
    loader = SpecializationConfigLoader()
    display_info = loader.get_display_info(specialization)

    return {
        "message": "Specialization updated successfully",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "specialization": {
                "code": current_user.specialization.value,
                "name": display_info.get('name', specialization.value),
                "icon": display_info.get('icon', '🎯')
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
async def get_specialization_info(
    specialization_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed information about a specific specialization (HYBRID: DB + JSON)"""
    from app.services.specialization_service import SpecializationService
    from app.services.specialization_config_loader import SpecializationConfigLoader

    # STEP 1: Validate enum
    try:
        specialization = SpecializationType(specialization_code.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specialization '{specialization_code}' not found"
        )

    # STEP 2: Check DB existence + is_active (HYBRID)
    service = SpecializationService(db)
    if not service.validate_specialization_exists(specialization.value):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specialization '{specialization_code}' is not active"
        )

    # STEP 3: Load full info from JSON (Source of Truth)
    loader = SpecializationConfigLoader()
    display_info = loader.get_display_info(specialization)

    return {
        "code": specialization.value,
        "name": display_info.get('name', specialization.value),
        "description": display_info.get('description', ''),
        "features": display_info.get('features', []),  # TODO: Add to JSON configs
        "icon": display_info.get('icon', '🎯'),
        "min_age": display_info.get('min_age', 0),
        "color_theme": display_info.get('color_theme', '#000000')
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


@router.get("/progress/me")
async def get_my_specialization_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's progress for all specializations (alias for /progress)"""
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
        # Return empty data instead of 400 error
        return {
            'success': True,
            'data': {}
        }


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


# ========================================
# COACH-SPECIFIC: Theory/Practice Hours Tracking
# ========================================

class UpdateHoursRequest(BaseModel):
    theory_hours_increment: int = 0
    practice_hours_increment: int = 0

@router.post("/update-hours")
async def update_coach_hours(
    request: UpdateHoursRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update theory/practice hours for COACH specialization

    Args:
        theory_hours_increment: Hours to add to theory_hours_completed
        practice_hours_increment: Hours to add to practice_hours_completed

    Returns:
        Updated progress data
    """
    from ....models.user_progress import SpecializationProgress
    from ....services.specialization_service import SpecializationService
    from sqlalchemy import and_
    from datetime import datetime

    try:
        # Find COACH progress
        progress = db.query(SpecializationProgress).filter(
            and_(
                SpecializationProgress.student_id == current_user.id,
                SpecializationProgress.specialization_id == 'COACH'
            )
        ).first()

        if not progress:
            raise HTTPException(
                status_code=404,
                detail="COACH progress not found. Please complete onboarding first."
            )

        # Update hours
        progress.theory_hours_completed += request.theory_hours_increment
        progress.practice_hours_completed += request.practice_hours_increment
        progress.last_activity = datetime.utcnow()
        progress.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(progress)

        # Get updated progress with level requirements
        service = SpecializationService(db)
        updated_progress = service.get_student_progress(current_user.id, 'COACH')

        return {
            'success': True,
            'message': 'Hours updated successfully',
            'data': updated_progress
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update hours: {str(e)}")