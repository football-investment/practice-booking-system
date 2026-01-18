"""
Coach license management endpoints
"""
import logging
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user
from .....models.user import User, UserRole
from .....models.license import UserLicense
from .....models.specialization import SpecializationType

logger = logging.getLogger(__name__)

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

    from app.models.user import UserRole
        from sqlalchemy import text
Coach License Management API Endpoints

Provides REST API endpoints for Coach certification system.
Handles license creation, theory/practice hours tracking, level progression,
expiry management, and statistics.

Level System: 1-8 certification levels
- Theory hours requirement per level
- Practice hours requirement per level
- Expiry: 2 years from creation/renewal
"""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../implementation/02_backend_services'))

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



@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all Coach licenses (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        query = text("SELECT * FROM coach_licenses WHERE is_active = TRUE ORDER BY id DESC")
        result = db.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
    except Exception as e:
        logger.error(f"Error fetching coach licenses: {e}")
        return []

@router.post("/licenses", response_model=LicenseResponse, status_code=201)
def create_license(
    request: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Coach license for the current user.

    **Cost:** 100 credits (deducted from user's credit_balance)

    - **starting_level**: Initial certification level (1-8), defaults to 1
    - **duration_years**: License validity in years (default: 2)

    Returns the created license with all fields including expiry date.
    """
    service = LFACoachService(db)

    try:
        # 🔒 CRITICAL: Validate user has enough credits (100 required)
        # Refresh user from database to get latest credit_balance
        db.refresh(current_user)

        REQUIRED_CREDITS = 100
        if current_user.credit_balance < REQUIRED_CREDITS:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {current_user.credit_balance} credits, but need {REQUIRED_CREDITS} credits to unlock this specialization."
            )

        # 🔒 ATOMIC TRANSACTION: Create license AND deduct credits in ONE transaction
        # If ANY step fails, BOTH operations roll back automatically

        # Step 1: Create coach_licenses record (no commit inside service method)
        license_data = service.create_license(
            user_id=current_user.id,
            starting_level=request.starting_level,
            duration_years=request.duration_years
        )

        # Step 2: Create user_licenses record (CRITICAL for motivation assessment!)
        db.execute(
            text("""
                INSERT INTO user_licenses (
                    user_id,
                    specialization_type,
                    current_level,
                    max_achieved_level,
                    started_at
                )
                VALUES (:user_id, :spec_type, 1, 1, NOW())
            """),
            {"user_id": current_user.id, "spec_type": "LFA_COACH"}
        )

        # Step 3: Deduct 100 credits from user's balance
        db.execute(
            text("UPDATE users SET credit_balance = credit_balance - :amount WHERE id = :user_id"),
            {"amount": REQUIRED_CREDITS, "user_id": current_user.id}
        )

        # Step 4: COMMIT EVERYTHING at the end (one atomic transaction)
        # If we reach here, all steps succeeded - commit the entire transaction
        db.commit()

        return LicenseResponse(
            id=license_data['id'],
            user_id=license_data['user_id'],
            current_level=license_data['current_level'],
            max_level_reached=license_data['max_achieved_level'],
            theory_hours=license_data['theory_hours'],
            practice_hours=license_data['practice_hours'],
            expires_at=license_data['expires_at'].isoformat() if license_data['expires_at'] else None,
            is_expired=license_data.get('is_expired', False),
            is_active=license_data['is_active'],
            created_at=license_data['created_at'].isoformat() if license_data['created_at'] else None,
            updated_at=license_data.get('updated_at').isoformat() if license_data.get('updated_at') else None
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 402 Payment Required) without wrapping
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/licenses/me", response_model=LicenseResponse)
def get_my_license(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's active Coach license.

    Returns 404 if no active license is found.
    """
    service = LFACoachService(db)

    try:
        license_data = service.get_license_by_user(current_user.id)

        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active Coach license found for this user"
            )

        return LicenseResponse(
            id=license_data['id'],
            user_id=license_data['user_id'],
            current_level=license_data['current_level'],
            max_level_reached=license_data['max_achieved_level'],
            theory_hours=license_data['theory_hours'],
            practice_hours=license_data['practice_hours'],
            expires_at=license_data['expires_at'].isoformat() if license_data['expires_at'] else None,
            is_expired=license_data.get('is_expired', False),
            is_active=license_data['is_active'],
            created_at=license_data['created_at'].isoformat() if license_data['created_at'] else None,
            updated_at=license_data.get('updated_at').isoformat() if license_data.get('updated_at') else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


