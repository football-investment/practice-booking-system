"""
LFA Player credit system

Credit management (purchase, spend, balance)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....services.specs.session_based.lfa_player_service import LFAPlayerService

router = APIRouter()


# ==================== Pydantic Schemas ====================

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
