"""
LFA Player credit system

Credit management (purchase, spend, balance)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
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


@router.post("/credits/purchase", response_model=CreditResponse)
def purchase_credits(
    data: CreditPurchase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Purchase credits for your LFA Player license"""
    try:
        service = LFAPlayerService(db)

        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LFA Player license found"
            )

        tx, new_balance = service.purchase_credits(
            license_id=license_data['id'],
            amount=data.amount,
            payment_verified=data.payment_verified,
            payment_proof_url=data.payment_proof_url,
            payment_reference_code=data.payment_reference_code,
            description=data.description
        )

        return CreditResponse(
            transaction=CreditTransaction(
                transaction_id=tx['transaction_id'],
                amount=tx['amount'],
                created_at=str(tx['created_at']),
                payment_verified=tx['payment_verified']
            ),
            new_balance=new_balance
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.post("/credits/spend", response_model=CreditResponse)
def spend_credits(
    data: CreditSpend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spend credits from your LFA Player license"""
    try:
        service = LFAPlayerService(db)

        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LFA Player license found"
            )

        tx, new_balance = service.spend_credits(
            license_id=license_data['id'],
            enrollment_id=data.enrollment_id,
            amount=data.amount,
            description=data.description
        )

        return CreditResponse(
            transaction=CreditTransaction(
                transaction_id=tx['transaction_id'],
                amount=tx['amount'],
                created_at=str(tx['created_at']),
                payment_verified=None
            ),
            new_balance=new_balance
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.get("/credits/balance", response_model=int)
def get_credit_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current credit balance"""
    try:
        service = LFAPlayerService(db)

        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LFA Player license found"
            )

        balance = service.get_credit_balance(license_data['id'])
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.get("/credits/transactions", response_model=List[TransactionHistoryItem])
def get_transaction_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get credit transaction history (newest first)"""
    try:
        service = LFAPlayerService(db)

        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LFA Player license found"
            )

        history = service.get_transaction_history(license_data['id'], limit=limit)

        return [
            TransactionHistoryItem(
                id=tx['id'],
                transaction_type=tx['transaction_type'],
                amount=tx['amount'],
                enrollment_id=tx.get('enrollment_id'),
                payment_verified=tx.get('payment_verified'),
                payment_reference_code=tx.get('payment_reference_code'),
                description=tx.get('description'),
                created_at=str(tx['created_at'])
            )
            for tx in history
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")
