"""
Query endpoints for semester enrollments
Gets enrollment data by semester or student
"""
from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from .....database import get_db
from .....dependencies import get_current_admin_user
from .....models.user import User
from .....models.semester_enrollment import SemesterEnrollment
from .schemas import EnrollmentResponse

router = APIRouter()


@router.get("/semesters/{semester_id}/enrollments")
async def get_semester_enrollments(
    request: Request,
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[EnrollmentResponse]:
    """
    Get all enrollments for a specific semester (Admin only)
    Returns enriched data with user and semester information
    """
    enrollments = (
        db.query(SemesterEnrollment)
        .options(
            joinedload(SemesterEnrollment.user),
            joinedload(SemesterEnrollment.semester),
            joinedload(SemesterEnrollment.user_license)
        )
        .filter(SemesterEnrollment.semester_id == semester_id)
        .order_by(SemesterEnrollment.user_id, SemesterEnrollment.enrolled_at.desc())
        .all()
    )

    return [
        EnrollmentResponse(
            id=e.id,
            user_id=e.user_id,
            user_email=e.user.email,
            user_name=e.user.name,
            semester_id=e.semester_id,
            semester_code=e.semester.code,
            semester_name=e.semester.name,
            specialization_type=e.user_license.specialization_type,
            user_license_id=e.user_license_id,
            payment_verified=e.payment_verified,
            payment_verified_at=e.payment_verified_at,
            is_active=e.is_active,
            request_status=e.request_status.value,  # Convert enum to string
            enrolled_at=e.enrolled_at
        )
        for e in enrollments
    ]


@router.get("/students/{student_id}/enrollments")
async def get_student_enrollments(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[EnrollmentResponse]:
    """
    Get all enrollments for a specific student across all semesters (Admin only)
    """
    enrollments = (
        db.query(SemesterEnrollment)
        .options(
            joinedload(SemesterEnrollment.user),
            joinedload(SemesterEnrollment.semester),
            joinedload(SemesterEnrollment.user_license)
        )
        .filter(SemesterEnrollment.user_id == student_id)
        .order_by(SemesterEnrollment.semester_id.desc(), SemesterEnrollment.enrolled_at.desc())
        .all()
    )

    return [
        EnrollmentResponse(
            id=e.id,
            user_id=e.user_id,
            user_email=e.user.email,
            user_name=e.user.name,
            semester_id=e.semester_id,
            semester_code=e.semester.code,
            semester_name=e.semester.name,
            specialization_type=e.user_license.specialization_type,
            user_license_id=e.user_license_id,
            payment_verified=e.payment_verified,
            payment_verified_at=e.payment_verified_at,
            is_active=e.is_active,
            request_status=e.request_status.value,  # Convert enum to string
            enrolled_at=e.enrolled_at
        )
        for e in enrollments
    ]
