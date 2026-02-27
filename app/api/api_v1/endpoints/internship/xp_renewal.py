"""
Internship XP and license renewal endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....services.specs.semester_based.lfa_internship_service import LFAInternshipService

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



@router.post("/xp", response_model=XPResponse)
def add_xp(
    request: AddXPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add XP to the current user's Internship license.

    - **xp_amount**: XP points to add (must be > 0)
    - **reason**: Optional reason for XP award

    Automatically triggers level-up if XP thresholds are crossed.
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

        result = service.add_xp(
            license_id=license_data['id'],
            xp_amount=request.xp_amount,
            reason=request.reason
        )

        return XPResponse(
            license_id=result['license_id'],
            xp_added=result['xp_added'],
            new_xp_total=result['new_xp_total'],
            old_level=result['old_level'],
            new_level=result['new_level'],
            level_changed=result['level_changed'],
            max_level_reached=result['max_level_reached']
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


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
    service = LFAInternshipService(db)

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
def renew_license(
    license_id: int,
    request: RenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Renew/extend the license expiry date.

    - **license_id**: ID of the license to renew
    - **extension_months**: Months to extend (1-24, default: 15)

    Checks that the user owns the license before renewing.
    Returns 403 if not authorized.
    """
    service = LFAInternshipService(db)

    try:
        # Verify ownership
        license_data = service.get_license_by_user(current_user.id)
        if not license_data or license_data['id'] != license_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to modify this license"
            )

        result = service.renew_license(
            license_id=license_id,
            extension_months=request.extension_months
        )

        return RenewResponse(
            license_id=result['license_id'],
            old_expiry=result['old_expiry'].isoformat() if result['old_expiry'] else None,
            new_expiry=result['new_expiry'].isoformat() if result['new_expiry'] else None,
            is_expired=result['is_expired'],
            renewed_at=result['renewed_at'].isoformat() if result['renewed_at'] else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


