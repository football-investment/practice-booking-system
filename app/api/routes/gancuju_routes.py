"""
🥋 Gancuju Player Routes - Belt Progression System

Routes for Gancuju Player specialization:
- Belt status display
- Belt promotion requests
- Belt promotion approval (instructor/admin)
- Belt history and progression timeline

8 Belts: White → Yellow → Green → Blue → Brown → Grey → Black → Red
NO skills, NO XP - ONLY belt progression through requirements.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict

from ...database import get_db
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...services.gancuju_belt_service import GancujuBeltService
from ...dependencies import get_current_user_web
from ...main import templates


router = APIRouter()


@router.get("/instructor/students/{student_id}/belt-status/{license_id}", response_class=HTMLResponse)
async def instructor_student_belt_status_page(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Gancuju belt status and progression page
    Shows current belt, next belt requirements, and progression history

    TODO: Implement belt status display
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

    # Verify this is a Gancuju Player specialization
    if license.specialization_type != "GANCUJU_PLAYER":
        raise HTTPException(status_code=400, detail="This license is not for Gancuju Player specialization")

    # Initialize belt service
    belt_service = GancujuBeltService(db)

    # Get current belt status
    current_belt = belt_service.get_current_belt(license_id)
    belt_info = belt_service.get_belt_info(current_belt)
    next_belt = belt_service.get_next_belt(current_belt)
    next_belt_info = belt_service.get_belt_info(next_belt) if next_belt else None

    # Check promotion eligibility
    eligibility = belt_service.check_promotion_eligibility(license_id)

    # Get belt history
    belt_history = belt_service.get_belt_history(license_id)

    return templates.TemplateResponse(
        "instructor/student_belt_status.html",  # TODO: Create this template
        {
            "request": request,
            "user": user,
            "student": student,
            "license": license,
            "license_id": license_id,
            "current_belt": current_belt,
            "belt_info": belt_info,
            "next_belt": next_belt,
            "next_belt_info": next_belt_info,
            "eligibility": eligibility,
            "belt_history": belt_history,
            "specialization_display": "Gancuju Player",
            "specialization_color": "#9b59b6"  # Purple for Gancuju
        }
    )


@router.post("/instructor/students/{student_id}/promote-belt/{license_id}", response_class=HTMLResponse)
async def instructor_promote_belt(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Promote student to next belt
    Validates requirements and records promotion in history

    TODO: Implement belt promotion
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

    # Verify this is a Gancuju Player specialization
    if license.specialization_type != "GANCUJU_PLAYER":
        raise HTTPException(status_code=400, detail="This license is not for Gancuju Player specialization")

    # Parse form data
    form_data = await request.form()
    notes = form_data.get("notes", "").strip() or None
    exam_score_str = form_data.get("exam_score", "").strip()
    exam_notes = form_data.get("exam_notes", "").strip() or None

    # Parse exam score if provided
    exam_score = None
    if exam_score_str:
        try:
            exam_score = int(exam_score_str)
            if exam_score < 0 or exam_score > 100:
                raise ValueError("Exam score must be between 0-100")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid exam score: {str(e)}")

    try:
        # Initialize belt service
        belt_service = GancujuBeltService(db)

        # Attempt promotion
        result = belt_service.promote_to_next_belt(
            user_license_id=license_id,
            promoted_by=user.id,
            notes=notes,
            exam_score=exam_score,
            exam_notes=exam_notes
        )

        # Commit changes
        db.commit()

        # Get updated belt status
        current_belt = belt_service.get_current_belt(license_id)
        belt_info = belt_service.get_belt_info(current_belt)
        next_belt = belt_service.get_next_belt(current_belt)
        next_belt_info = belt_service.get_belt_info(next_belt) if next_belt else None
        eligibility = belt_service.check_promotion_eligibility(license_id)
        belt_history = belt_service.get_belt_history(license_id)

        return templates.TemplateResponse(
            "instructor/student_belt_status.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_belt": current_belt,
                "belt_info": belt_info,
                "next_belt": next_belt,
                "next_belt_info": next_belt_info,
                "eligibility": eligibility,
                "belt_history": belt_history,
                "specialization_display": "Gancuju Player",
                "specialization_color": "#9b59b6",
                "success": True,
                "message": f"✅ Successfully promoted to {belt_info['name']}!"
            }
        )

    except ValueError as e:
        db.rollback()

        # Reload current state
        belt_service = GancujuBeltService(db)
        current_belt = belt_service.get_current_belt(license_id)
        belt_info = belt_service.get_belt_info(current_belt)
        next_belt = belt_service.get_next_belt(current_belt)
        next_belt_info = belt_service.get_belt_info(next_belt) if next_belt else None
        eligibility = belt_service.check_promotion_eligibility(license_id)
        belt_history = belt_service.get_belt_history(license_id)

        return templates.TemplateResponse(
            "instructor/student_belt_status.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_belt": current_belt,
                "belt_info": belt_info,
                "next_belt": next_belt,
                "next_belt_info": next_belt_info,
                "eligibility": eligibility,
                "belt_history": belt_history,
                "specialization_display": "Gancuju Player",
                "specialization_color": "#9b59b6",
                "error": True,
                "message": f"❌ Promotion failed: {str(e)}"
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error promoting belt: {str(e)}")
