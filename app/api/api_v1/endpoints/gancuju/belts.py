"""
GānCuju™© belt promotion/demotion endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user
from .....models.user import User
from .....models.license import UserLicense

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../implementation/02_backend_services'))

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LicenseCreate(BaseModel):
    """Request body for creating a new GānCuju license"""
    starting_level: int = Field(default=1, ge=1, le=8, description="Starting level (1-8)")

    class Config:
        json_schema_extra = {
            "example": {
                "starting_level": 1
            }
        }


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
    """Request body for promoting a level"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for promotion")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Passed promotion exam with excellent performance"
            }
        }


class DemoteRequest(BaseModel):
    """Request body for demoting a level"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for demotion")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Failed to maintain required standards"
            }
        }


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



@router.post("/licenses/{license_id}/promote", response_model=LevelChangeResponse)
def promote_level(
    license_id: int,
    request: PromoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Promote the license to the next level.

    - **license_id**: ID of the license to promote
    - **reason**: Optional reason for promotion

    **Permissions:**
    - Students can promote their own license
    - Instructors can promote any student's license
    - Admins can promote any license

    Returns 403 if not authorized, 400 if already at max level.
    """
    service = GanCujuPlayerService(db)

    try:
        # RBAC: Validate ownership (students can only promote own, instructors/admins can promote others)
        validate_license_ownership(db, current_user, license_id, 'gancuju_licenses')

        result = service.promote_level(license_id, reason=request.reason)

        return LevelChangeResponse(
            license_id=result['license_id'],
            old_level=result['old_level'],
            new_level=result['new_level'],
            max_level_reached=result['max_level_reached'],
            reason=result.get('reason'),
            changed_at=result['changed_at'].isoformat() if result['changed_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/licenses/{license_id}/demote", response_model=LevelChangeResponse)
def demote_level(
    license_id: int,
    request: DemoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Demote the license to the previous level.

    - **license_id**: ID of the license to demote
    - **reason**: Optional reason for demotion

    **Permissions:**
    - Students CANNOT demote themselves (403 forbidden)
    - Instructors can demote any student's license
    - Admins can demote any license

    Returns 403 if not authorized, 400 if already at min level.
    """
    service = GanCujuPlayerService(db)

    try:
        # RBAC: Validate ownership (only instructors/admins can demote, not students)
        validate_license_ownership(db, current_user, license_id, 'gancuju_licenses')

        result = service.demote_level(license_id, reason=request.reason)

        return LevelChangeResponse(
            license_id=result['license_id'],
            old_level=result['old_level'],
            new_level=result['new_level'],
            max_level_reached=result['max_level_reached'],
            reason=result.get('reason'),
            changed_at=result['changed_at'].isoformat() if result['changed_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


