"""
CRUD operations for semester enrollments
Creating, deleting, and toggling enrollments
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from .....database import get_db
from .....dependencies import get_current_admin_user_web
from .....models.user import User, UserRole
from .....models.semester import Semester
from .....models.license import UserLicense
from .....models.semester_enrollment import SemesterEnrollment
from .schemas import EnrollmentCreate
from .....services.age_category_service import (
    calculate_age_at_season_start,
    get_automatic_age_category,
    get_current_season_year
)

router = APIRouter()


@router.post("/enroll")
async def create_enrollment(
    request: Request,
    enrollment: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Dict[str, Any]:
    """
    Enroll a student in a specialization for a specific semester (Admin only)
    """
    # Validate student exists
    student = db.query(User).filter(User.id == enrollment.user_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Validate semester exists
    semester = db.query(Semester).filter(Semester.id == enrollment.semester_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")

    # Validate user_license exists and belongs to student
    user_license = db.query(UserLicense).filter(
        UserLicense.id == enrollment.user_license_id,
        UserLicense.user_id == enrollment.user_id
    ).first()
    if not user_license:
        raise HTTPException(status_code=404, detail="UserLicense not found or does not belong to student")

    # Check if enrollment already exists
    existing = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id == enrollment.user_id,
        SemesterEnrollment.semester_id == enrollment.semester_id,
        SemesterEnrollment.user_license_id == enrollment.user_license_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this specialization for this semester")

    # 🎯 NEW: Calculate automatic age category based on date_of_birth
    age_category = None
    if student.date_of_birth:
        season_year = get_current_season_year()
        age_at_season_start = calculate_age_at_season_start(student.date_of_birth, season_year)
        age_category = get_automatic_age_category(age_at_season_start)
        # age_category will be "PRE", "YOUTH", or None (if > 18, instructor must assign)

    # Create enrollment
    new_enrollment = SemesterEnrollment(
        user_id=enrollment.user_id,
        semester_id=enrollment.semester_id,
        user_license_id=enrollment.user_license_id,
        payment_verified=False,
        is_active=True,
        enrolled_at=datetime.utcnow(),
        age_category=age_category,  # 🎯 NEW: Auto-assign based on age
        age_category_overridden=False  # 🎯 NEW: Not overridden yet
    )

    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)

    return {
        "success": True,
        "message": f"Enrolled {student.name} in {user_license.specialization_type} for {semester.code}",
        "enrollment_id": new_enrollment.id
    }


@router.delete("/{enrollment_id}")
async def delete_enrollment(
    request: Request,
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Dict[str, Any]:
    """
    Delete an enrollment (Admin only)
    Warning: This does NOT delete the UserLicense (progress is preserved)
    """
    enrollment = db.query(SemesterEnrollment).filter(SemesterEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    db.delete(enrollment)
    db.commit()

    return {
        "success": True,
        "message": "Enrollment deleted successfully (UserLicense progress preserved)"
    }


@router.post("/{enrollment_id}/toggle-active")
async def toggle_enrollment_active(
    request: Request,
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Dict[str, Any]:
    """
    Toggle enrollment active status (Admin only)
    """
    enrollment = db.query(SemesterEnrollment).filter(SemesterEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enrollment.is_active:
        enrollment.deactivate()
        message = "Enrollment deactivated"
    else:
        enrollment.reactivate()
        message = "Enrollment reactivated"

    db.commit()

    return {
        "success": True,
        "message": message,
        "is_active": enrollment.is_active
    }
