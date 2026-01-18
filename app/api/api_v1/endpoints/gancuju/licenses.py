"""
GānCuju™© license management endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user
from .....models.user import User, UserRole
from .....models.license import UserLicense
from .....models.specialization import SpecializationType

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

    from app.models.user import UserRole
        from sqlalchemy import text
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



@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all GānCuju licenses (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        query = text("SELECT * FROM gancuju_licenses WHERE is_active = TRUE ORDER BY id DESC")
        result = db.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
    except:
        return []

@router.post("/licenses", response_model=LicenseResponse, status_code=201)
def create_license(
    request: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new GānCuju license for the current user.

    **Cost:** 100 credits (deducted from user's credit_balance)

    - **starting_level**: Initial level (1-8), defaults to 1

    Returns the created license with all fields.
    """
    service = GanCujuPlayerService(db)

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

        # Step 1: Create gancuju_licenses record (no commit inside service method)
        license_data = service.create_license(
            user_id=current_user.id,
            starting_level=request.starting_level
        )

        # Step 2: Create user_licenses record (CRITICAL for motivation assessment!)
        db.execute(
            text("""
                INSERT INTO user_licenses (
                    user_id,
                    specialization_type,
                    current_level,
                    max_achieved_level,
                    started_at,
                    created_at
                )
                VALUES (:user_id, :spec_type, 1, 1, NOW(), NOW())
            """),
            {"user_id": current_user.id, "spec_type": "GANCUJU_PLAYER"}
        )

        # Step 3: Deduct 100 credits from user's balance
        db.execute(
            text("UPDATE users SET credit_balance = credit_balance - :amount WHERE id = :user_id"),
            {"amount": REQUIRED_CREDITS, "user_id": current_user.id}
        )

        # Step 4: Get full license data
        full_license = service.get_license_by_user(current_user.id)

        if not full_license:
            raise HTTPException(status_code=500, detail="License created but could not retrieve it")

        # Step 5: COMMIT EVERYTHING at the end (one atomic transaction)
        # If we reach here, all steps succeeded - commit the entire transaction
        db.commit()

        return LicenseResponse(
            id=full_license['id'],
            user_id=full_license['user_id'],
            current_level=full_license['current_level'],
            max_level_reached=full_license.get('max_achieved_level', full_license['current_level']),
            competitions_entered=full_license['competitions_entered'],
            competitions_won=full_license['competitions_won'],
            win_rate=float(full_license['win_rate']) if full_license['win_rate'] else None,
            teaching_hours=full_license['teaching_hours'],
            is_active=full_license.get('is_active', True),
            created_at=full_license['created_at'].isoformat() if full_license.get('created_at') else None,
            updated_at=full_license['updated_at'].isoformat() if full_license.get('updated_at') else None
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
    Get the current user's active GānCuju license.

    Returns 404 if no active license is found.
    """
    service = GanCujuPlayerService(db)

    try:
        license_data = service.get_license_by_user(current_user.id)

        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active GānCuju license found for this user"
            )

        return LicenseResponse(
            id=license_data['id'],
            user_id=license_data['user_id'],
            current_level=license_data['current_level'],
            max_level_reached=license_data.get('max_achieved_level', license_data['current_level']),
            competitions_entered=license_data['competitions_entered'],
            competitions_won=license_data['competitions_won'],
            win_rate=license_data['win_rate'],
            teaching_hours=license_data['teaching_hours'],
            is_active=license_data['is_active'],
            created_at=license_data['created_at'].isoformat() if license_data['created_at'] else None,
            updated_at=license_data['updated_at'].isoformat() if license_data['updated_at'] else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


