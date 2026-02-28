"""
GānCuju™© competition and teaching hours endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....services.specs.semester_based.gancuju_player_service import GanCujuPlayerService

"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import sys
import os

# Add service layer to path
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.utils.rbac import validate_license_ownership
from .....services.specs.semester_based.gancuju_player_service import GanCujuPlayerService
GānCuju™️©️ License Management API Endpoints

Provides REST API endpoints for GānCuju belt/level progression system.
Handles license creation, level promotion/demotion, competition tracking,
and teaching hour recording.

Level System: 1-8 (numeric levels, not belt names)
- Level 1: Beginner
- Level 8: Master
"""


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LicenseCreate(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "starting_level": 1
            }
        }
    )

    """Request body for creating a new GānCuju license"""
    starting_level: int = Field(default=1, ge=1, le=8, description="Starting level (1-8)")


class LicenseResponse(BaseModel):
    """Response model for GānCuju license data"""
    id: int
    user_id: int
    current_level: int
    max_level_reached: int
    competitions_entered: int
    competitions_won: int
    win_rate: Optional[float]
    teaching_hours: int
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 2,
                "current_level": 3,
                "max_level_reached": 5,
                "competitions_entered": 10,
                "competitions_won": 7,
                "win_rate": 70.0,
                "teaching_hours": 25,
                "is_active": True,
                "created_at": "2025-12-08T20:00:00Z",
                "updated_at": None
            }
        }


class PromoteRequest(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "reason": "Passed promotion exam with excellent performance"
            }
        }
    )

    """Request body for promoting a level"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for promotion")


class DemoteRequest(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "reason": "Failed to maintain required standards"
            }
        }
    )

    """Request body for demoting a level"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for demotion")


class LevelChangeResponse(BaseModel):
    """Response model for level promotion/demotion"""
    license_id: int
    old_level: int
    new_level: int
    max_level_reached: int
    reason: Optional[str]
    changed_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "old_level": 2,
                "new_level": 3,
                "max_level_reached": 3,
                "reason": "Passed belt exam",
                "changed_at": "2025-12-08T20:00:00Z"
            }
        }


class CompetitionRecord(BaseModel):
    """Request body for recording a competition result"""
    won: bool = Field(..., description="Whether the competition was won")
    competition_name: Optional[str] = Field(None, max_length=200, description="Name of competition")
    opponent: Optional[str] = Field(None, max_length=200, description="Opponent name")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "won": True,
                "competition_name": "Budapest GānCuju Championship",
                "opponent": "Team Alpha",
                "notes": "Final score: 3-1"
            }
        }


class CompetitionResponse(BaseModel):
    """Response model for competition record"""
    license_id: int
    competitions_entered: int
    competitions_won: int
    win_rate: Optional[float]
    latest_result: str
    recorded_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "competitions_entered": 11,
                "competitions_won": 8,
                "win_rate": 72.73,
                "latest_result": "WON",
                "recorded_at": "2025-12-08T20:00:00Z"
            }
        }


class TeachingHoursRecord(BaseModel):
    """Request body for recording teaching hours"""
    hours: int = Field(..., gt=0, description="Number of teaching hours to add")
    session_description: Optional[str] = Field(None, max_length=500, description="Description of teaching session")

    class Config:
        json_schema_extra = {
            "example": {
                "hours": 3,
                "session_description": "Taught beginner class on basic GānCuju techniques"
            }
        }


class TeachingHoursResponse(BaseModel):
    """Response model for teaching hours update"""
    license_id: int
    total_teaching_hours: int
    hours_added: int
    recorded_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "total_teaching_hours": 28,
                "hours_added": 3,
                "recorded_at": "2025-12-08T20:00:00Z"
            }
        }


class LicenseStats(BaseModel):
    """Response model for detailed license statistics"""
    license_id: int
    user_id: int
    current_level: int
    max_level_reached: int
    competitions_entered: int
    competitions_won: int
    win_rate: Optional[float]
    teaching_hours: int
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "user_id": 2,
                "current_level": 4,
                "max_level_reached": 5,
                "competitions_entered": 15,
                "competitions_won": 11,
                "win_rate": 73.33,
                "teaching_hours": 40,
                "is_active": True,
                "created_at": "2025-12-08T20:00:00Z",
                "updated_at": "2025-12-08T21:00:00Z"
            }
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================



@router.post("/competitions", response_model=CompetitionResponse)
def record_competition(
    request: CompetitionRecord,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a competition result for the current user's license.

    - **won**: Whether the competition was won (true/false)
    - **competition_name**: Optional name of competition
    - **opponent**: Optional opponent name
    - **notes**: Optional additional notes

    Automatically updates competitions_entered, competitions_won, and win_rate.
    """
    service = GanCujuPlayerService(db)

    try:
        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active GānCuju license found for this user"
            )

        result = service.record_competition(
            license_id=license_data['id'],
            won=request.won,
            competition_name=request.competition_name,
            opponent=request.opponent,
            notes=request.notes
        )

        return CompetitionResponse(
            license_id=result['license_id'],
            competitions_entered=result['competitions_entered'],
            competitions_won=result['competitions_won'],
            win_rate=result['win_rate'],
            latest_result="WON" if request.won else "LOST",
            recorded_at=result['recorded_at'].isoformat() if result['recorded_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/teaching-hours", response_model=TeachingHoursResponse)
def record_teaching_hours(
    request: TeachingHoursRecord,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record teaching hours for the current user's license.

    - **hours**: Number of hours to add (must be > 0)
    - **session_description**: Optional description of teaching session

    Accumulates to total teaching_hours in the license.
    """
    service = GanCujuPlayerService(db)

    try:
        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active GānCuju license found for this user"
            )

        result = service.record_teaching_hours(
            license_id=license_data['id'],
            hours=request.hours,
            session_description=request.session_description
        )

        return TeachingHoursResponse(
            license_id=result['license_id'],
            total_teaching_hours=result['total_teaching_hours'],
            hours_added=request.hours,
            recorded_at=result['recorded_at'].isoformat() if result['recorded_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/licenses/{license_id}/stats", response_model=LicenseStats)
def get_license_stats(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed statistics for a specific license.

    - **license_id**: ID of the license to retrieve

    Checks that the user owns the license before returning stats.
    Returns 403 if not authorized.
    """
    service = GanCujuPlayerService(db)

    try:
        # Verify ownership
        license_data = service.get_license_by_user(current_user.id)
        if not license_data or license_data['id'] != license_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this license"
            )

        stats = service.get_license_stats(license_id)

        return LicenseStats(
            license_id=stats['id'],
            user_id=stats['user_id'],
            current_level=stats['current_level'],
            max_level_reached=stats['max_level_reached'],
            competitions_entered=stats['competitions_entered'],
            competitions_won=stats['competitions_won'],
            win_rate=stats['win_rate'],
            teaching_hours=stats['teaching_hours'],
            is_active=stats['is_active'],
            created_at=stats['created_at'].isoformat() if stats['created_at'] else None,
            updated_at=stats['updated_at'].isoformat() if stats['updated_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
