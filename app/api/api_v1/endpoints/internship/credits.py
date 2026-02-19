"""
Internship credit management endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.credit_transaction import CreditTransaction

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
from .....services.specs.semester_based.lfa_internship_service import LFAInternshipService
Internship License Management API Endpoints

Provides REST API endpoints for Internship XP-based progression system.
Handles license creation, XP tracking, level progression, expiry management,
and credit system for session enrollments.

Level System: XP-based progression with automatic level-up
- Levels: 1-8 (based on cumulative XP)
- Expiry: 15 months from creation/renewal
"""


router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LicenseCreate(BaseModel):
    """Request body for creating a new Internship license"""
    initial_credits: int = Field(default=0, ge=0, description="Starting credit balance")
    duration_months: int = Field(default=15, ge=1, le=24, description="License duration in months (1-24)")

    class Config:
        json_schema_extra = {
            "example": {
                "initial_credits": 100,
                "duration_months": 15
            }
        }


class LicenseResponse(BaseModel):
    """Response model for Internship license data"""
    id: int
    user_id: int
    current_level: int
    max_level_reached: int
    current_xp: int
    credit_balance: int
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
                "current_xp": 2500,
                "credit_balance": 150,
                "expires_at": "2026-03-08T20:00:00Z",
                "is_expired": False,
                "is_active": True,
                "created_at": "2025-12-08T20:00:00Z",
                "updated_at": None
            }
        }


class AddXPRequest(BaseModel):
    """Request body for adding XP"""
    xp_amount: int = Field(..., gt=0, description="Amount of XP to add (must be positive)")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for XP award")

    class Config:
        json_schema_extra = {
            "example": {
                "xp_amount": 500,
                "reason": "Completed module 3 with excellent performance"
            }
        }


class XPResponse(BaseModel):
    """Response model for XP addition"""
    license_id: int
    xp_added: int
    new_xp_total: int
    old_level: int
    new_level: int
    level_changed: bool
    max_level_reached: int

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "xp_added": 500,
                "new_xp_total": 3000,
                "old_level": 3,
                "new_level": 4,
                "level_changed": True,
                "max_level_reached": 4
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
                "expires_at": "2026-03-08T20:00:00Z",
                "is_expired": False,
                "days_remaining": 90
            }
        }


class RenewRequest(BaseModel):
    """Request body for renewing license"""
    extension_months: int = Field(default=15, ge=1, le=24, description="Months to extend (1-24)")

    class Config:
        json_schema_extra = {
            "example": {
                "extension_months": 12
            }
        }


class RenewResponse(BaseModel):
    """Response model for license renewal"""
    license_id: int
    old_expiry: str
    new_expiry: str
    is_expired: bool
    renewed_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "license_id": 1,
                "old_expiry": "2026-03-08T20:00:00Z",
                "new_expiry": "2027-06-08T20:00:00Z",
                "is_expired": False,
                "renewed_at": "2025-12-08T20:00:00Z"
            }
        }


class CreditPurchase(BaseModel):
    """Request body for purchasing credits"""
    amount: int = Field(..., gt=0, description="Amount of credits to purchase")
    payment_verified: bool = Field(default=False, description="Whether payment has been verified")
    payment_proof_url: Optional[str] = Field(None, max_length=500, description="URL to payment proof")
    payment_reference_code: Optional[str] = Field(None, max_length=100, description="Payment reference code")
    description: Optional[str] = Field(None, max_length=500, description="Purchase description")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 50,
                "payment_verified": True,
                "payment_reference_code": "INV-2025-001",
                "description": "Monthly credit package"
            }
        }


class CreditSpend(BaseModel):
    """Request body for spending credits"""
    enrollment_id: int = Field(..., description="Enrollment ID for the expense")
    amount: int = Field(..., gt=0, description="Amount of credits to spend")
    description: Optional[str] = Field(None, max_length=500, description="Spending description")

    class Config:
        json_schema_extra = {
            "example": {
                "enrollment_id": 123,
                "amount": 25,
                "description": "Session enrollment fee"
            }
        }


class CreditTransaction(BaseModel):
    """Credit transaction details"""
    transaction_id: int
    amount: int
    transaction_type: str
    payment_verified: bool
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": 45,
                "amount": 50,
                "transaction_type": "PURCHASE",
                "payment_verified": True,
                "created_at": "2025-12-08T20:00:00Z"
            }
        }


class CreditResponse(BaseModel):
    """Response model for credit operations"""
    transaction: CreditTransaction
    new_balance: int

    class Config:
        json_schema_extra = {
            "example": {
                "transaction": {
                    "transaction_id": 45,
                    "amount": 50,
                    "transaction_type": "PURCHASE",
                    "payment_verified": True,
                    "created_at": "2025-12-08T20:00:00Z"
                },
                "new_balance": 200
            }
        }


class TransactionHistoryItem(BaseModel):
    """Single transaction history entry"""
    id: int
    amount: int
    transaction_type: str
    enrollment_id: Optional[int]
    description: Optional[str]
    payment_verified: bool
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 45,
                "amount": 50,
                "transaction_type": "PURCHASE",
                "enrollment_id": None,
                "description": "Monthly package",
                "payment_verified": True,
                "created_at": "2025-12-08T20:00:00Z"
            }
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================



@router.post("/credits/purchase", response_model=CreditResponse)
def purchase_credits(
    request: CreditPurchase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Purchase credits for the current user's Internship license.

    - **amount**: Credits to purchase (must be > 0)
    - **payment_verified**: Whether payment is verified
    - **payment_proof_url**: Optional URL to payment proof
    - **payment_reference_code**: Optional payment reference
    - **description**: Optional purchase description

    Creates a PURCHASE transaction and updates credit balance.
    """
    service = LFAInternshipService(db)

    try:
        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active Internship license found for this user"
            )

        transaction, new_balance = service.purchase_credits(
            license_id=license_data['id'],
            amount=request.amount,
            payment_verified=request.payment_verified,
            payment_proof_url=request.payment_proof_url,
            payment_reference_code=request.payment_reference_code,
            description=request.description
        )

        return CreditResponse(
            transaction=CreditTransaction(
                transaction_id=transaction['id'],
                amount=transaction['amount'],
                transaction_type=transaction['transaction_type'],
                payment_verified=transaction['payment_verified'],
                created_at=transaction['created_at'].isoformat() if transaction['created_at'] else None
            ),
            new_balance=new_balance
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/credits/spend", response_model=CreditResponse)
def spend_credits(
    request: CreditSpend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Spend credits from the current user's Internship license.

    - **enrollment_id**: Enrollment ID for the expense
    - **amount**: Credits to spend (must be > 0)
    - **description**: Optional spending description

    Creates a SPENT transaction (negative amount) and deducts from balance.
    Returns 400 if insufficient credits.
    """
    service = LFAInternshipService(db)

    try:
        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active Internship license found for this user"
            )

        transaction, new_balance = service.spend_credits(
            license_id=license_data['id'],
            enrollment_id=request.enrollment_id,
            amount=request.amount,
            description=request.description
        )

        return CreditResponse(
            transaction=CreditTransaction(
                transaction_id=transaction['id'],
                amount=transaction['amount'],
                transaction_type=transaction['transaction_type'],
                payment_verified=transaction['payment_verified'],
                created_at=transaction['created_at'].isoformat() if transaction['created_at'] else None
            ),
            new_balance=new_balance
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/credits/balance", response_model=int)
def get_credit_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current credit balance for the user's Internship license.

    Returns the balance as an integer.
    Returns 404 if no active license is found.
    """
    service = LFAInternshipService(db)

    try:
        # Get user's license
        license_data = service.get_license_by_user(current_user.id)
        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active Internship license found for this user"
            )

        balance = service.get_credit_balance(license_data['id'])
        return balance

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
