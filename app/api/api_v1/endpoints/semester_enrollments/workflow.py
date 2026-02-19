"""
Enrollment request approval workflow
Handles approve/reject operations for enrollment requests
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .....database import get_db
from .....dependencies import get_current_user_web
from .....models.user import User, UserRole
from .....models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from .schemas import EnrollmentRejection

router = APIRouter()


@router.post("/{enrollment_id}/approve")
async def approve_enrollment_request(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    """
    ✅ Admin or Master Instructor approves a PENDING enrollment request

    **Who can approve:**
    - 🥋 Master Instructor of the semester
    - 👑 Admin (can override)

    Changes:
    - request_status: PENDING → APPROVED
    - is_active: False → True
    - approved_at: set to now
    - approved_by: set to current_user.id
    """
    # Get enrollment with semester info
    enrollment = (
        db.query(SemesterEnrollment)
        .options(joinedload(SemesterEnrollment.semester))
        .filter(SemesterEnrollment.id == enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enrollment.request_status != EnrollmentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve enrollment with status {enrollment.request_status.value}"
        )

    # 🔐 Permission check: Admin OR Master Instructor of this semester
    is_admin = current_user.role == UserRole.ADMIN
    is_master_instructor = (
        current_user.role == UserRole.INSTRUCTOR and
        enrollment.semester.master_instructor_id == current_user.id
    )

    if not (is_admin or is_master_instructor):
        raise HTTPException(
            status_code=403,
            detail="Only the master instructor of this semester or admin can approve enrollments"
        )

    # Use model method
    enrollment.approve(current_user.id)
    db.commit()

    return {
        "success": True,
        "message": f"Enrollment approved for {enrollment.user.name}",
        "enrollment_id": enrollment.id,
        "request_status": enrollment.request_status.value,
        "approved_by": "Master Instructor" if is_master_instructor else "Admin"
    }


@router.post("/{enrollment_id}/reject")
async def reject_enrollment_request(
    enrollment_id: int,
    rejection: EnrollmentRejection,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
):
    """
    ❌ Admin or Master Instructor rejects a PENDING enrollment request

    **Who can reject:**
    - 🥋 Master Instructor of the semester
    - 👑 Admin (can override)

    Changes:
    - request_status: PENDING → REJECTED
    - is_active: False (remains)
    - approved_at: set to now
    - approved_by: set to current_user.id
    - rejection_reason: set to provided reason
    """
    enrollment = (
        db.query(SemesterEnrollment)
        .options(
            joinedload(SemesterEnrollment.user),
            joinedload(SemesterEnrollment.semester)
        )
        .filter(SemesterEnrollment.id == enrollment_id)
        .first()
    )

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enrollment.request_status != EnrollmentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject enrollment with status {enrollment.request_status.value}"
        )

    # 🔐 Permission check: Admin OR Master Instructor of this semester
    is_admin = current_user.role == UserRole.ADMIN
    is_master_instructor = (
        current_user.role == UserRole.INSTRUCTOR and
        enrollment.semester.master_instructor_id == current_user.id
    )

    if not (is_admin or is_master_instructor):
        raise HTTPException(
            status_code=403,
            detail="Only the master instructor of this semester or admin can reject enrollments"
        )

    # Use model method
    enrollment.reject(current_user.id, rejection.reason or "No reason provided")
    db.commit()

    return {
        "success": True,
        "message": f"Enrollment rejected for {enrollment.user.name}",
        "enrollment_id": enrollment.id,
        "request_status": enrollment.request_status.value,
        "rejection_reason": enrollment.rejection_reason
    }
