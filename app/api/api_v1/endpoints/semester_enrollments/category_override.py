"""
Instructor Override for Age Categories
Allows instructors to manually change student age categories

Business Rules:
- Instructors can change 14+ year-olds between YOUTH/AMATEUR/PRO anytime (even mid-season)
- Students aged 5-13 MUST stay in PRE (cannot override)
- Admins can override any category (with warnings)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from .....database import get_db
from .....dependencies import get_current_user_web
from .....models.user import User, UserRole
from .....models.semester_enrollment import SemesterEnrollment
from .....services.age_category_service import (
    calculate_age_at_season_start,
    get_current_season_year,
    validate_age_category_override
)
from .schemas import CategoryOverride

router = APIRouter()


@router.post("/{enrollment_id}/override-category")
async def override_age_category(
    request: Request,
    enrollment_id: int,
    override: CategoryOverride,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web)
) -> Dict[str, Any]:
    """
    🎯 Override age category for a student enrollment.

    **Permissions**:
    - 🥋 Instructor (any instructor)
    - 👑 Admin (can override any, with warnings)

    **Business Rules**:
    - ✅ 14+ year-olds can be moved between YOUTH/AMATEUR/PRO anytime (even mid-season)
    - ❌ 5-13 year-olds MUST stay in PRE (cannot override)
    - 🔒 Season lock: Category is determined at July 1 and stays fixed
    - 📝 Override is audited (who, when)

    **Example**:
    - Student born 2007-12-06, season 2025/26 (July 1, 2025)
    - Age at season start: 17 years
    - Default: YOUTH
    - Instructor can override to: AMATEUR or PRO
    """
    # Permission check: instructor or admin
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only instructors and admins can override age categories"
        )

    # Get enrollment with student info
    enrollment = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.id == enrollment_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    # Business rule validation: Check if student's age allows override
    student = enrollment.user
    if student.date_of_birth:
        season_year = get_current_season_year()
        age_at_season_start = calculate_age_at_season_start(student.date_of_birth, season_year)

        # Validate override
        is_valid, error_message = validate_age_category_override(age_at_season_start, override.age_category)

        if not is_valid:
            # Admin can override with warning, instructor cannot
            if current_user.role == UserRole.ADMIN:
                # Log warning but allow
                print(f"⚠️ ADMIN OVERRIDE WARNING: {error_message}")
            else:
                raise HTTPException(status_code=400, detail=error_message)

    # Update enrollment
    enrollment.age_category = override.age_category
    enrollment.age_category_overridden = True
    enrollment.age_category_overridden_at = datetime.utcnow()
    enrollment.age_category_overridden_by = current_user.id

    db.commit()
    db.refresh(enrollment)

    return {
        "success": True,
        "message": f"Age category changed to {override.age_category}",
        "enrollment_id": enrollment.id,
        "age_category": enrollment.age_category,
        "overridden_by": current_user.name,
        "overridden_at": enrollment.age_category_overridden_at.isoformat() if enrollment.age_category_overridden_at else None
    }
