"""
Coach license renewal, promotion and stats endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User

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
from .....services.specs.semester_based.lfa_coach_service import LFACoachService
Coach License Management API Endpoints

Provides REST API endpoints for Coach certification system.
Handles license creation, theory/practice hours tracking, level progression,
expiry management, and statistics.

Level System: 1-8 certification levels
- Theory hours requirement per level
- Practice hours requirement per level
- Expiry: 2 years from creation/renewal
"""


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LicenseCreate(BaseModel):
    """Request body for creating a new Coach license"""
    starting_level: int = Field(default=1, ge=1, le=8, description="Starting certification level (1-8)")
    duration_years: int = Field(default=2, ge=1, le=5, description="License duration in years (1-5)")

    class Config:
        json_schema_extra = {
            "example": {
                "starting_level": 1,
                "duration_years": 2
            }
        }


class LicenseResponse(BaseModel):
    """Response model for Coach license data"""
    id: int
    user_id: int
    current_level: int
    max_level_reached: int
    theory_hours: int
    practice_hours: int
    expires_at: str
    is_expired: bool
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 2,
                "current_level": 3,
                "max_level_reached": 4,
                "theory_hours": 50,
                "practice_hours": 120,
                "expires_at": "2027-12-08T20:00:00Z",
                "is_expired": False,
                "is_active": True,
                "created_at": "2025-12-08T20:00:00Z",
                "updated_at": None
            }
        }


class AddTheoryHoursRequest(BaseModel):
    """Request body for adding theory hours"""
    hours: int = Field(..., gt=0, description="Theory hours to add (must be positive)")
    course_name: Optional[str] = Field(None, max_length=200, description="Name of theory course")
    description: Optional[str] = Field(None, max_length=500, description="Description of theory work")

    class Config:
        json_schema_extra = {
            "example": {
                "hours": 10,
                "course_name": "Advanced Coaching Methodology",
                "description": "Completed module on tactical analysis"
            }
        }


class AddPracticeHoursRequest(BaseModel):
    """Request body for adding practice hours"""
    hours: int = Field(..., gt=0, description="Practice hours to add (must be positive)")
    session_type: Optional[str] = Field(None, max_length=100, description="Type of practice session")
    description: Optional[str] = Field(None, max_length=500, description="Description of practice work")

    class Config:
        json_schema_extra = {
            "example": {
                "hours": 5,
                "session_type": "Team Training Session",
                "description": "Led U15 team training focusing on possession drills"
            }
        }


class HoursResponse(BaseModel):
    """Response model for hours addition"""
    license_id: int
    hours_added: int
    new_total_hours: int
    hours_type: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "hours_added": 10,
                "new_total_hours": 60,
                "hours_type": "theory"
            }
        }


class ExpiryResponse(BaseModel):
    """Response model for expiry check"""
    license_id: int
    expires_at: str
    is_expired: bool
    days_remaining: Optional[int]

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "expires_at": "2027-12-08T20:00:00Z",
                "is_expired": False,
                "days_remaining": 730
            }
        }


class RenewRequest(BaseModel):
    """Request body for renewing certification"""
    extension_years: int = Field(default=2, ge=1, le=5, description="Years to extend (1-5)")

    class Config:
        json_schema_extra = {
            "example": {
                "extension_years": 2
            }
        }


class RenewResponse(BaseModel):
    """Response model for certification renewal"""
    license_id: int
    old_expiry: str
    new_expiry: str
    is_expired: bool
    renewed_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "old_expiry": "2027-12-08T20:00:00Z",
                "new_expiry": "2029-12-08T20:00:00Z",
                "is_expired": False,
                "renewed_at": "2025-12-08T20:00:00Z"
            }
        }


class PromoteRequest(BaseModel):
    """Request body for promoting level"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for promotion")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Met all requirements for Level 3 certification"
            }
        }


class PromoteResponse(BaseModel):
    """Response model for level promotion"""
    license_id: int
    old_level: int
    new_level: int
    max_level_reached: int
    promoted_at: str
    reason: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "old_level": 2,
                "new_level": 3,
                "max_level_reached": 3,
                "promoted_at": "2025-12-08T20:00:00Z",
                "reason": "Met requirements"
            }
        }


class LicenseStats(BaseModel):
    """Response model for detailed license statistics"""
    license_id: int
    user_id: int
    current_level: int
    max_level_reached: int
    theory_hours: int
    practice_hours: int
    total_hours: int
    expires_at: str
    is_expired: bool
    days_remaining: Optional[int]
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "user_id": 2,
                "current_level": 3,
                "max_level_reached": 4,
                "theory_hours": 60,
                "practice_hours": 150,
                "total_hours": 210,
                "expires_at": "2027-12-08T20:00:00Z",
                "is_expired": False,
                "days_remaining": 730,
                "is_active": True,
                "created_at": "2025-12-08T20:00:00Z",
                "updated_at": "2025-12-08T21:00:00Z"
            }
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================



@router.get("/licenses/{license_id}/expiry", response_model=ExpiryResponse)
def check_expiry(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check expiry status of a specific license.

    - **license_id**: ID of the license to check

    Checks that the user owns the license before returning expiry info.
    Returns 403 if not authorized.
    """
    service = LFACoachService(db)

    try:
        # Verify ownership
        license_data = service.get_license_by_user(current_user.id)
        if not license_data or license_data['id'] != license_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this license"
            )

        result = service.check_expiry(license_id)

        return ExpiryResponse(
            license_id=result['license_id'],
            expires_at=result['expires_at'].isoformat() if result['expires_at'] else None,
            is_expired=result['is_expired'],
            days_remaining=result.get('days_remaining')
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/licenses/{license_id}/renew", response_model=RenewResponse)
def renew_certification(
    license_id: int,
    request: RenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Renew/extend the certification expiry date.

    - **license_id**: ID of the license to renew
    - **extension_years**: Years to extend (1-5, default: 2)

    Checks that the user owns the license before renewing.
    Returns 403 if not authorized.
    """
    service = LFACoachService(db)

    try:
        # Verify ownership
        license_data = service.get_license_by_user(current_user.id)
        if not license_data or license_data['id'] != license_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to modify this license"
            )

        result = service.renew_certification(
            license_id=license_id,
            extension_years=request.extension_years
        )

        return RenewResponse(
            license_id=result['license_id'],
            old_expiry=result['old_expires_at'].isoformat() if result['old_expires_at'] else None,
            new_expiry=result['new_expires_at'].isoformat() if result['new_expires_at'] else None,
            is_expired=False,
            renewed_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/licenses/{license_id}/promote", response_model=PromoteResponse)
def promote_level(
    license_id: int,
    request: PromoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Promote the license to the next certification level.

    - **license_id**: ID of the license to promote
    - **reason**: Optional reason for promotion

    Checks that the user owns the license before promoting.
    Returns 403 if not authorized, 400 if already at max level.
    """
    service = LFACoachService(db)

    try:
        # Verify ownership
        license_data = service.get_license_by_user(current_user.id)
        if not license_data or license_data['id'] != license_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to modify this license"
            )

        result = service.promote_level(license_id, reason=request.reason)

        return PromoteResponse(
            license_id=result['license_id'],
            old_level=result['old_level'],
            new_level=result['new_level'],
            max_level_reached=result['max_achieved_level'],
            promoted_at=result['promoted_at'].isoformat() if result['promoted_at'] else None,
            reason=result.get('reason')
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
    service = LFACoachService(db)

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
            max_level_reached=stats['max_achieved_level'],
            theory_hours=stats['theory_hours'],
            practice_hours=stats['practice_hours'],
            total_hours=stats['theory_hours'] + stats['practice_hours'],
            expires_at=stats['expires_at'].isoformat() if stats['expires_at'] else None,
            is_expired=stats.get('is_expired', False),
            days_remaining=stats.get('days_remaining'),
            is_active=stats['is_active'],
            created_at=stats['created_at'].isoformat() if stats['created_at'] else None,
            updated_at=stats.get('updated_at').isoformat() if stats.get('updated_at') else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
