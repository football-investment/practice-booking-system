"""
Payment verification workflow for semester enrollments
Handles payment verification by enrollment ID or payment code
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from .....database import get_db
from .....dependencies import get_current_admin_user, get_current_user
from .....models.user import User, UserRole
from .....models.semester_enrollment import SemesterEnrollment

router = APIRouter()


@router.post("/{enrollment_id}/verify-payment")
async def verify_enrollment_payment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Verify payment for a specific enrollment (Admin only)
    """
    enrollment = db.query(SemesterEnrollment).filter(SemesterEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.verify_payment(current_user.id)
    db.commit()

    return {
        "success": True,
        "message": "Payment verified successfully"
    }


@router.post("/{enrollment_id}/unverify-payment")
async def unverify_enrollment_payment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Unverify payment for a specific enrollment (Admin only)
    """
    enrollment = db.query(SemesterEnrollment).filter(SemesterEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.unverify_payment()
    db.commit()

    return {
        "success": True,
        "message": "Payment unverified successfully"
    }


@router.get("/{enrollment_id}/payment-info")
async def get_payment_info(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow both student and admin
):
    """
    📄 Get payment information for an enrollment (payment code, instructions, etc.)

    Returns:
    - payment_reference_code: Unique code for bank transfer
    - bank_details: Bank account information
    - amount: Payment amount
    - enrollment_details: Specialization, semester info
    """

    enrollment = (
        db.query(SemesterEnrollment)
        .options(
            joinedload(SemesterEnrollment.user),
            joinedload(SemesterEnrollment.semester),
            joinedload(SemesterEnrollment.user_license)
        )
        .filter(SemesterEnrollment.id == enrollment_id)
        .first()
    )

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    # Security: Only allow students to view their own enrollments, or admins to view any
    if current_user.role != UserRole.ADMIN and enrollment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this enrollment")

    # Generate payment code if it doesn't exist
    if not enrollment.payment_reference_code:
        enrollment.set_payment_code()
        db.commit()
        db.refresh(enrollment)

    # Get specialization display name
    spec_names = {
        'INTERNSHIP': 'Internship Program',
        'GANCUJU_PLAYER': 'GānCuju Player',
        'LFA_FOOTBALL_PLAYER': 'LFA Football Player',
        'LFA_COACH': 'LFA Coach'
    }

    response_data = {
        "payment_reference_code": enrollment.payment_reference_code,
        "enrollment_id": enrollment.id,
        "student_name": enrollment.user.name,
        "student_email": enrollment.user.email,
        "specialization": spec_names.get(enrollment.specialization_type, enrollment.specialization_type),
        "specialization_type": enrollment.specialization_type,
        "semester_name": enrollment.semester.name,
        "semester_id": enrollment.semester_id,
        "payment_verified": enrollment.payment_verified,
        "amount": 50000,  # TODO: Make this configurable per semester/specialization
        "currency": "HUF",
        "bank_details": {
            "account_holder": "LFA Education Center Kft.",
            "account_number": "12345678-12345678-12345678",
            "bank_name": "OTP Bank",
            "swift": "OTPVHUHB",
            "iban": "HU42 1177 3016 1111 1118 0000 0000"
        },
        "instructions": f"Please transfer {50000} HUF to the account above and include this EXACT code in the transaction comment: {enrollment.payment_reference_code}"
    }

    return JSONResponse(
        content=response_data,
        media_type="application/json; charset=utf-8"
    )


@router.post("/verify-by-code")
async def verify_payment_by_code(
    payment_code: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    ✅ Admin verifies payment using the payment reference code

    Flow:
    1. Admin receives bank transfer with payment code in comment
    2. Admin enters the code here
    3. System finds the enrollment and marks payment as verified
    """
    # Find enrollment by payment code
    enrollment = (
        db.query(SemesterEnrollment)
        .options(
            joinedload(SemesterEnrollment.user),
            joinedload(SemesterEnrollment.semester),
            joinedload(SemesterEnrollment.user_license)
        )
        .filter(SemesterEnrollment.payment_reference_code == payment_code.strip().upper())
        .first()
    )

    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail=f"No enrollment found with payment code: {payment_code}"
        )

    if enrollment.payment_verified:
        raise HTTPException(
            status_code=400,
            detail=f"Payment already verified for this enrollment on {enrollment.payment_verified_at}"
        )

    # Verify payment
    enrollment.verify_payment(admin_user.id)
    db.commit()
    db.refresh(enrollment)

    return {
        "success": True,
        "message": f"Payment verified for {enrollment.user.name}",
        "enrollment_id": enrollment.id,
        "student_name": enrollment.user.name,
        "student_email": enrollment.user.email,
        "specialization": enrollment.specialization_type,
        "semester": enrollment.semester.name,
        "payment_verified_at": enrollment.payment_verified_at,
        "payment_verified_by": admin_user.id
    }
