from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ....database import get_db
from ....dependencies import get_current_admin_user
from ....models.user import User, UserRole
from ....schemas.user import User as UserSchema

router = APIRouter()


@router.get("/students")
def get_students_payment_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get all students with their payment verification status (Admin only)
    """
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    
    # Add payment verification status to response
    student_responses = []
    for student in students:
        student_data = {
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "nickname": student.nickname,
            "role": student.role.value,
            "is_active": student.is_active,
            "payment_verified": student.payment_verified,
            "payment_verified_at": student.payment_verified_at,
            "payment_verified_by": student.payment_verified_by,
            "payment_status_display": student.payment_status_display,
            "can_enroll_in_semester": student.can_enroll_in_semester,
            "specialization": student.specialization.value if student.specialization else None,
            "onboarding_completed": student.onboarding_completed,
            "created_at": student.created_at
        }
        student_responses.append(student_data)
    
    return student_responses


@router.post("/students/{student_id}/verify")
def verify_student_payment(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Verify payment for a specific student (Admin only)
    """
    # Get student
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Verify payment
    student.verify_payment(current_user)
    db.commit()
    db.refresh(student)
    
    return {
        "message": f"Payment verified for {student.name}",
        "student_id": student.id,
        "verified_by": current_user.name,
        "verified_at": student.payment_verified_at,
        "payment_verified": student.payment_verified
    }


@router.post("/students/{student_id}/unverify")
def unverify_student_payment(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Remove payment verification for a specific student (Admin only)
    """
    # Get student
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Unverify payment
    student.unverify_payment()
    db.commit()
    db.refresh(student)
    
    return {
        "message": f"Payment verification removed for {student.name}",
        "student_id": student.id,
        "unverified_by": current_user.name,
        "payment_verified": student.payment_verified
    }


@router.get("/students/{student_id}/status")
def get_student_payment_status(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get payment verification status for a specific student (Admin only)
    """
    # Get student
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    verifier_name = None
    if student.payment_verified_by:
        verifier = db.query(User).filter(User.id == student.payment_verified_by).first()
        verifier_name = verifier.name if verifier else "Unknown"
    
    return {
        "student_id": student.id,
        "student_name": student.name,
        "student_email": student.email,
        "payment_verified": student.payment_verified,
        "payment_verified_at": student.payment_verified_at,
        "payment_verified_by": student.payment_verified_by,
        "payment_verifier_name": verifier_name,
        "payment_status_display": student.payment_status_display,
        "can_enroll_in_semester": student.can_enroll_in_semester
    }