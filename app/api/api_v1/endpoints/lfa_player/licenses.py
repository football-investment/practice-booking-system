"""
LFA Player license management

Provides REST API for LFA Player license management:
- License CRUD operations
- Skill tracking and updates
- Credit management (purchase, spend, balance)
- Transaction history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field

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
    """Request to update a skill"""
    skill_name: str = Field(..., description="heading, shooting, crossing, passing, dribbling, ball_control, defending")
    new_avg: float = Field(..., ge=0, le=100)


class SkillUpdateResponse(BaseModel):
    """Response after skill update"""
    skill_name: str
    new_avg: float
    overall_avg: float


class CreditPurchase(BaseModel):
    """Request to purchase credits"""
    amount: int = Field(..., gt=0)
    payment_verified: bool = False
    payment_proof_url: Optional[str] = None
    payment_reference_code: Optional[str] = None
    description: Optional[str] = None


class CreditSpend(BaseModel):
    """Request to spend credits"""
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


@router.get("/licenses", response_model=List[LicenseResponse])
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all LFA Player licenses (Admin only)

    Returns a list of all active LFA Player licenses in the system.
    """
    # Check if admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view all licenses"
        )

    try:
        service = LFAPlayerService(db)
        # Get all licenses from database
        query = "SELECT * FROM lfa_player_licenses WHERE is_active = TRUE ORDER BY id DESC"
        licenses = db.execute(query).fetchall()

        result = []
        for lic in licenses:
            license_data = service.get_license_by_user(lic.user_id)
            if license_data:
                result.append(LicenseResponse(
                    id=license_data['id'],
                    user_id=license_data['user_id'],
                    age_group=license_data['age_group'],
                    credit_balance=license_data['credit_balance'],
                    overall_avg=license_data.get('overall_avg', 0.0),
                    is_active=license_data.get('is_active', True),
                    created_at=license_data.get('created_at'),
                    updated_at=license_data.get('updated_at')
                ))

        return result
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing LFA Player licenses: {str(e)}")
        # Return empty list instead of error
        return []


@router.post("/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
def create_license(
    data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new LFA Player license for the current user

    **Cost:** 100 credits (deducted from user's credit_balance)

    **Age Groups:**
    - PRE: Pre-academy
    - YOUTH: Youth academy
    - AMATEUR: Amateur level
    - PRO: Professional level
    """
    try:
        # 🔒 CRITICAL: Validate user has enough credits (100 required)
        # Refresh user from database to get latest credit_balance
        db.refresh(current_user)

        REQUIRED_CREDITS = 100
        if current_user.credit_balance < REQUIRED_CREDITS:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. You have {current_user.credit_balance} credits, but need {REQUIRED_CREDITS} credits to unlock this specialization."
            )

        service = LFAPlayerService(db)

        # Convert Pydantic model to dict if skills provided
        initial_skills = data.initial_skills.dict(exclude_none=True) if data.initial_skills else None

        # 🔒 ATOMIC TRANSACTION: Create license AND deduct credits in ONE transaction
        # If ANY step fails, BOTH operations roll back automatically

        # Step 1: Create license (no commit inside service method)
        license_data = service.create_license(
            user_id=current_user.id,
            age_group=data.age_group,
            initial_credits=data.initial_credits,
            initial_skills=initial_skills
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
            {"user_id": current_user.id, "spec_type": "LFA_PLAYER"}
        )

        # Step 3: Deduct 100 credits from user's balance
        db.execute(
            text("UPDATE users SET credit_balance = credit_balance - :amount WHERE id = :user_id"),
            {"amount": REQUIRED_CREDITS, "user_id": current_user.id}
        )

        # Step 4: Get full license data with skills
        full_license = service.get_license_by_user(current_user.id)

        if not full_license:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="License created but could not retrieve it"
            )

        # Step 5: COMMIT EVERYTHING at the end (one atomic transaction)
        # If we reach here, all steps succeeded - commit the entire transaction
        db.commit()

        # Format response
        return LicenseResponse(
            id=full_license['id'],
            user_id=full_license['user_id'],
            age_group=full_license['age_group'],
            credit_balance=full_license['credit_balance'],
            overall_avg=full_license['overall_avg'],
            skills=SkillAverages(**full_license['skills']),
            is_active=full_license['is_active'],
            created_at=str(full_license['created_at']),
            updated_at=str(full_license['updated_at']) if full_license.get('updated_at') else None
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 402 Payment Required) without wrapping
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.get("/licenses/me", response_model=LicenseResponse)
def get_my_license(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's active LFA Player license"""
    try:
        service = LFAPlayerService(db)
        license_data = service.get_license_by_user(current_user.id)

        if not license_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LFA Player license found"
            )

        return LicenseResponse(
            id=license_data['id'],
            user_id=license_data['user_id'],
            age_group=license_data['age_group'],
            credit_balance=license_data['credit_balance'],
            overall_avg=license_data['overall_avg'],
            skills=SkillAverages(**license_data['skills']),
            is_active=license_data['is_active'],
            created_at=str(license_data['created_at']),
            updated_at=str(license_data['updated_at']) if license_data['updated_at'] else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


