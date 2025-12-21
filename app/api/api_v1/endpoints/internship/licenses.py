"""
Internship license management endpoints
"""
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

"""
Internship License Management API Endpoints

Provides REST API endpoints for Internship XP-based progression system.
Handles license creation, XP tracking, level progression, expiry management,
and credit system for session enrollments.

Level System: XP-based progression with automatic level-up
- Levels: 1-8 (based on cumulative XP)
- Expiry: 15 months from creation/renewal
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import sys
import os

# Add service layer to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../implementation/02_backend_services'))

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from .....services.specs.semester_based.lfa_internship_service import LFAInternshipService

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



@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all Internship licenses (Admin only)"""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        from sqlalchemy import text
        query = text("SELECT * FROM internship_licenses WHERE is_active = TRUE ORDER BY id DESC")
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
    Create a new Internship license for the current user.

    **Cost:** 100 credits (deducted from user's credit_balance)

    - **initial_credits**: Starting credit balance (default: 0)
    - **duration_months**: License validity in months (default: 15)

    Returns the created license with all fields including expiry date.
    """
    service = LFAInternshipService(db)

    try:
        # 🔒 CRITICAL: Validate user has enough credits (100 required)
        # Refresh user from database to get latest credit_balance
        from sqlalchemy import text
        db.refresh(current_user)

        REQUIRED_CREDITS = 100
        if current_user.credit_balance < REQUIRED_CREDITS:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {current_user.credit_balance} credits, but need {REQUIRED_CREDITS} credits to unlock this specialization."
            )

        # 🔒 ATOMIC TRANSACTION: Create license AND deduct credits in ONE transaction
        # If ANY step fails, BOTH operations roll back automatically

        # Step 1: Create internship_licenses record (no commit inside service method)
        license_data = service.create_license(
            user_id=current_user.id,
            initial_credits=request.initial_credits,
            duration_months=request.duration_months
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
            {"user_id": current_user.id, "spec_type": "INTERNSHIP"}
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
            max_level_reached=license_data.get('max_achieved_level', license_data['current_level']),  # Field mapping fix
            current_xp=license_data.get('total_xp', 0),  # Field mapping: total_xp -> current_xp
            credit_balance=license_data.get('credit_balance', 0),
            expires_at=license_data['expires_at'].isoformat() if license_data.get('expires_at') else None,
            is_expired=license_data.get('is_expired', False),
            is_active=license_data.get('is_active', True),
            created_at=license_data['created_at'].isoformat() if license_data.get('created_at') else None,
            updated_at=license_data['updated_at'].isoformat() if license_data.get('updated_at') else None
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
    Get the current user's active Internship license.

    Returns 404 if no active license is found.
    """
    service = LFAInternshipService(db)

    try:
        license_data = service.get_license_by_user(current_user.id)

        if not license_data:
            raise HTTPException(
                status_code=404,
                detail="No active Internship license found for this user"
            )

        return LicenseResponse(
            id=license_data['id'],
            user_id=license_data['user_id'],
            current_level=license_data['current_level'],
            max_level_reached=license_data.get('max_achieved_level', license_data['current_level']),  # Field mapping fix
            current_xp=license_data.get('total_xp', 0),  # Field mapping: total_xp -> current_xp
            credit_balance=license_data.get('credit_balance', 0),
            expires_at=license_data['expires_at'].isoformat() if license_data.get('expires_at') else None,
            is_expired=license_data.get('is_expired', False),
            is_active=license_data.get('is_active', True),
            created_at=license_data['created_at'].isoformat() if license_data.get('created_at') else None,
            updated_at=license_data['updated_at'].isoformat() if license_data.get('updated_at') else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


