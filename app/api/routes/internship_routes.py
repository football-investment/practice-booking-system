"""
💼 Internship Routes - XP and Level Progression System

Routes for Internship specialization:
- XP progress dashboard
- Level advancement tracking
- Semester completion status
- XP breakdown by session type

5 Semesters (8 Levels): Junior → Mid-Level → Senior → Lead → Principal
NO skills, NO belts - ONLY XP accumulation with strict thresholds.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict

from ...database import get_db
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...services.intern_progression_service import InternProgressionService
from ...dependencies import get_current_user_web
from ...main import templates


router = APIRouter()


@router.get("/instructor/students/{student_id}/xp-progress/{license_id}", response_class=HTMLResponse)
async def instructor_student_xp_progress_page(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Intern XP progress and level tracking page
    Shows current XP, level, thresholds, and breakdown by session type

    TODO: Implement XP progress display
    """
    # Security check: ONLY instructors can access
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="Instructor access required")

    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get license
    license = db.query(UserLicense).filter(
        UserLicense.id == license_id,
        UserLicense.user_id == student_id
    ).first()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    # Verify this is an Internship specialization
    if license.specialization_type != "INTERNSHIP":
        raise HTTPException(status_code=400, detail="This license is not for Internship specialization")

    # Initialize progression service
    progression_service = InternProgressionService(db)

    # Get current level and XP
    current_level = progression_service.get_current_level(license_id)
    level_info = progression_service.get_level_info(current_level)

    # Calculate current XP
    xp_data = progression_service.calculate_current_xp(license_id)

    # Get XP breakdown
    xp_breakdown = progression_service.get_xp_breakdown(license_id)

    # Check progression eligibility
    eligibility = progression_service.check_progression_eligibility(license_id)

    # Get progression history
    progression_history = progression_service.get_progression_history(license_id)

    # Calculate UV opportunity
    uv_opportunity = progression_service.calculate_uv_opportunity(license_id)

    return templates.TemplateResponse(
        "instructor/student_xp_progress.html",  # TODO: Create this template
        {
            "request": request,
            "user": user,
            "student": student,
            "license": license,
            "license_id": license_id,
            "current_level": current_level,
            "level_info": level_info,
            "xp_data": xp_data,
            "xp_breakdown": xp_breakdown,
            "eligibility": eligibility,
            "progression_history": progression_history,
            "uv_opportunity": uv_opportunity,
            "specialization_display": "Internship",
            "specialization_color": "#3498db"  # Blue for Internship
        }
    )


@router.post("/instructor/students/{student_id}/progress-level/{license_id}", response_class=HTMLResponse)
async def instructor_progress_student_level(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor/Admin-only: Progress student to next semester/level
    Validates requirements (attendance, quizzes, XP threshold) and records progression

    TODO: Implement level progression
    """
    # Security check: ONLY instructors/admins can access
    if user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Instructor or Admin access required")

    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get license
    license = db.query(UserLicense).filter(
        UserLicense.id == license_id,
        UserLicense.user_id == student_id
    ).first()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    # Verify this is an Internship specialization
    if license.specialization_type != "INTERNSHIP":
        raise HTTPException(status_code=400, detail="This license is not for Internship specialization")

    # Parse form data
    form_data = await request.form()
    notes = form_data.get("notes", "").strip() or None

    try:
        # Initialize progression service
        progression_service = InternProgressionService(db)

        # Attempt progression
        result = progression_service.progress_to_next_semester(
            user_license_id=license_id,
            approved_by=user.id,
            notes=notes
        )

        # Commit changes
        db.commit()

        # Get updated data
        current_level = progression_service.get_current_level(license_id)
        level_info = progression_service.get_level_info(current_level)
        xp_data = progression_service.calculate_current_xp(license_id)
        xp_breakdown = progression_service.get_xp_breakdown(license_id)
        eligibility = progression_service.check_progression_eligibility(license_id)
        progression_history = progression_service.get_progression_history(license_id)
        uv_opportunity = progression_service.calculate_uv_opportunity(license_id)

        return templates.TemplateResponse(
            "instructor/student_xp_progress.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_level": current_level,
                "level_info": level_info,
                "xp_data": xp_data,
                "xp_breakdown": xp_breakdown,
                "eligibility": eligibility,
                "progression_history": progression_history,
                "uv_opportunity": uv_opportunity,
                "specialization_display": "Internship",
                "specialization_color": "#3498db",
                "success": True,
                "message": f"✅ Successfully progressed to {level_info['name']}!"
            }
        )

    except ValueError as e:
        db.rollback()

        # Reload current state
        progression_service = InternProgressionService(db)
        current_level = progression_service.get_current_level(license_id)
        level_info = progression_service.get_level_info(current_level)
        xp_data = progression_service.calculate_current_xp(license_id)
        xp_breakdown = progression_service.get_xp_breakdown(license_id)
        eligibility = progression_service.check_progression_eligibility(license_id)
        progression_history = progression_service.get_progression_history(license_id)
        uv_opportunity = progression_service.calculate_uv_opportunity(license_id)

        return templates.TemplateResponse(
            "instructor/student_xp_progress.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_level": current_level,
                "level_info": level_info,
                "xp_data": xp_data,
                "xp_breakdown": xp_breakdown,
                "eligibility": eligibility,
                "progression_history": progression_history,
                "uv_opportunity": uv_opportunity,
                "specialization_display": "Internship",
                "specialization_color": "#3498db",
                "error": True,
                "message": f"❌ Progression failed: {str(e)}"
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error progressing level: {str(e)}")
