"""
License payment verification
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_admin_user_web
from .....models.user import User
from .....models.license import UserLicense

    from ....models.license import UserLicense
    from datetime import datetime
router = APIRouter()

@router.post("/{license_id}/verify-payment", response_model=Dict[str, Any])
async def verify_license_payment(
    license_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user_web)
):
    """
    Mark UserLicense payment as verified (Admin only - Web cookie auth)

    This is used when admin verifies that payment was received for a license
    BEFORE student creates a SemesterEnrollment request.
    """

    license = db.query(UserLicense).filter(UserLicense.id == license_id).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    if license.payment_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already verified"
        )

    # Mark as verified
    license.payment_verified = True
    license.payment_verified_at = datetime.now()
    db.commit()

    # Log audit
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.PAYMENT_VERIFIED,
        user_id=admin_user.id,
        resource_type="user_license",
        resource_id=license_id,
        details={
            "payment_reference_code": license.payment_reference_code,
            "user_id": license.user_id,
            "specialization": license.specialization_type
        }
    )

    return {
        "success": True,
        "message": "Payment verified successfully",
        "license_id": license_id,
        "payment_verified_at": license.payment_verified_at.isoformat()
    }


@router.post("/{license_id}/unverify-payment", response_model=Dict[str, Any])
async def unverify_license_payment(
    license_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user_web)
):
    """
    Remove payment verification from UserLicense (Admin only - Web cookie auth)

    This is used when admin needs to revert a payment verification.
    """

    license = db.query(UserLicense).filter(UserLicense.id == license_id).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    if not license.payment_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is not verified"
        )

    # Remove verification
    license.payment_verified = False
    license.payment_verified_at = None
    db.commit()

    # Log audit
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.PAYMENT_UNVERIFIED,
        user_id=admin_user.id,
        resource_type="user_license",
        resource_id=license_id,
        details={
            "payment_reference_code": license.payment_reference_code,
            "user_id": license.user_id,
            "specialization": license.specialization_type
        }
    )

    return {
        "success": True,
        "message": "Payment verification removed",
        "license_id": license_id
    }


# ⚽ FOOTBALL SKILLS ENDPOINTS (LFA Player Specializations)
