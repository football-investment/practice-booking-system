"""Specialization progress tracking"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.specialization import SpecializationType

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
"""
🎓 Specialization API Endpoints
Handles specialization selection and information for the LFA education platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

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


@router.get("/progress/me")
async def get_my_specialization_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's progress for all specializations (alias for /progress)"""

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