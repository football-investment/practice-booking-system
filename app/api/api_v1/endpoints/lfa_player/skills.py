"""
LFA Player skill assessment

Provides REST API for LFA Player skill management:
- Skill tracking and updates
- Skill averages
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....services.specs.session_based.lfa_player_service import LFAPlayerService

router = APIRouter()


# ==================== Pydantic Schemas ====================

class SkillAverages(BaseModel):
    """Skill averages for LFA Player (7 skills)"""
    heading_avg: Optional[float] = Field(None, ge=0, le=100)
    shooting_avg: Optional[float] = Field(None, ge=0, le=100)
    crossing_avg: Optional[float] = Field(None, ge=0, le=100)
    passing_avg: Optional[float] = Field(None, ge=0, le=100)
    dribbling_avg: Optional[float] = Field(None, ge=0, le=100)
    ball_control_avg: Optional[float] = Field(None, ge=0, le=100)
    defending_avg: Optional[float] = Field(None, ge=0, le=100)


class LicenseCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to create LFA Player license"""
    age_group: str = Field(..., description="Age group: PRE, YOUTH, AMATEUR, PRO")
    initial_credits: int = Field(0, ge=0)
    initial_skills: Optional[SkillAverages] = None


class LicenseResponse(BaseModel):
    """LFA Player license response"""
    id: int
    user_id: int
    age_group: str
    credit_balance: int
    overall_avg: float
    skills: SkillAverages
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None


class SkillUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to update a skill"""
    skill_name: str = Field(..., description="heading, shooting, crossing, passing, dribbling, ball_control, defending")
    new_avg: float = Field(..., ge=0, le=100)


class SkillUpdateResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Response after skill update"""
    skill_name: str
    new_avg: float
    overall_avg: float


class CreditPurchase(BaseModel):
    """Request to purchase credits"""
    model_config = ConfigDict(extra='forbid')

    amount: int = Field(..., gt=0)
    payment_verified: bool = False
    payment_proof_url: Optional[str] = None
    payment_reference_code: Optional[str] = None
    description: Optional[str] = None


class CreditSpend(BaseModel):
    """Request to spend credits"""
    model_config = ConfigDict(extra='forbid')

    enrollment_id: int
    amount: int = Field(..., gt=0)
    description: Optional[str] = None


class CreditTransaction(BaseModel):
    """Credit transaction response"""
    transaction_id: int
    amount: int
    created_at: str
    payment_verified: Optional[bool] = None


class CreditResponse(BaseModel):
    """Response after credit operation"""
    transaction: CreditTransaction
    new_balance: int


class TransactionHistoryItem(BaseModel):
    """Transaction history item"""
    id: int
    transaction_type: str
    amount: int
    enrollment_id: Optional[int] = None
    payment_verified: Optional[bool] = None
    payment_reference_code: Optional[str] = None
    description: Optional[str] = None
    created_at: str


# ==================== Endpoints ====================


@router.put("/licenses/{license_id}/skills", response_model=SkillUpdateResponse)
def update_skill(
    license_id: int,
    data: SkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a skill average for a license

    **Valid skill names:**
    - heading
    - shooting
    - crossing
    - passing
    - dribbling
    - ball_control
    - defending

    **Note:** overall_avg is auto-computed from all 7 skill averages

    **Permissions:**
    - Students can update their own license
    - Instructors can update assigned students' licenses
    - Admins can update any license
    """
    try:
        service = LFAPlayerService(db)

        # RBAC: Validate ownership (students can only update own, instructors/admins can update others)
        validate_license_ownership(db, current_user, license_id, 'lfa_player_licenses')

        result = service.update_skill_avg(
            license_id=license_id,
            skill_name=data.skill_name,
            new_avg=data.new_avg
        )

        return SkillUpdateResponse(
            skill_name=result['skill_name'],
            new_avg=result['new_avg'],
            overall_avg=result['overall_avg']
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


