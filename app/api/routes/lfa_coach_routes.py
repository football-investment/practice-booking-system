"""
👨‍🏫 LFA Coach Routes - Certification System

Routes for LFA Coach specialization:
- Certification status display
- Teaching hours tracking
- Certification exam management
- Certification approval (admin-only)

8 Certifications: Pre Assistant → Pre Head → Youth Assistant → Youth Head
                  → Amateur Assistant → Amateur Head → Pro Assistant → Pro Head
NO skills, NO belts, NO XP - ONLY certifications with teaching hours.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict

from ...database import get_db
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...services.coach_certification_service import CoachCertificationService
from ...dependencies import get_current_user_web
from ...main import templates


router = APIRouter()


@router.get("/instructor/students/{student_id}/certification-status/{license_id}", response_class=HTMLResponse)
async def instructor_student_certification_page(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Coach certification status and tracking page
    Shows current certification, next requirements, teaching hours, and history

    TODO: Implement certification status display
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

    # Verify this is an LFA Coach specialization
    if license.specialization_type != "LFA_COACH":
        raise HTTPException(status_code=400, detail="This license is not for LFA Coach specialization")

    # Initialize certification service
    cert_service = CoachCertificationService(db)

    # Get current certification
    current_cert = cert_service.get_current_certification(license_id)
    cert_info = cert_service.get_certification_info(current_cert)
    next_cert = cert_service.get_next_certification(current_cert)
    next_cert_info = cert_service.get_certification_info(next_cert) if next_cert else None

    # Check certification eligibility
    eligibility = cert_service.check_certification_eligibility(license_id)

    # Get teaching hours summary
    teaching_hours = cert_service.get_teaching_hours_summary(license_id)

    # Get certification history
    cert_history = cert_service.get_certification_history(license_id)

    return templates.TemplateResponse(
        "instructor/student_certification.html",  # TODO: Create this template
        {
            "request": request,
            "user": user,
            "student": student,
            "license": license,
            "license_id": license_id,
            "current_cert": current_cert,
            "cert_info": cert_info,
            "next_cert": next_cert,
            "next_cert_info": next_cert_info,
            "eligibility": eligibility,
            "teaching_hours": teaching_hours,
            "cert_history": cert_history,
            "specialization_display": "LFA Coach",
            "specialization_color": "#e74c3c"  # Red for Coach
        }
    )


@router.post("/instructor/students/{student_id}/certify/{license_id}", response_class=HTMLResponse)
async def instructor_certify_coach(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor/Admin-only: Certify coach for next level
    Validates requirements (age, teaching hours, exam, feedback) and records certification

    TODO: Implement certification
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

    # Verify this is an LFA Coach specialization
    if license.specialization_type != "LFA_COACH":
        raise HTTPException(status_code=400, detail="This license is not for LFA Coach specialization")

    # Parse form data
    form_data = await request.form()
    exam_score = float(form_data.get("exam_score", 0))
    notes = form_data.get("notes", "").strip() or None

    try:
        # Initialize certification service
        cert_service = CoachCertificationService(db)

        # Attempt certification
        result = cert_service.certify_next_level(
            user_license_id=license_id,
            certified_by=user.id,
            exam_score=exam_score,
            notes=notes
        )

        # Commit changes
        db.commit()

        # Get updated data
        current_cert = cert_service.get_current_certification(license_id)
        cert_info = cert_service.get_certification_info(current_cert)
        next_cert = cert_service.get_next_certification(current_cert)
        next_cert_info = cert_service.get_certification_info(next_cert) if next_cert else None
        eligibility = cert_service.check_certification_eligibility(license_id)
        teaching_hours = cert_service.get_teaching_hours_summary(license_id)
        cert_history = cert_service.get_certification_history(license_id)

        return templates.TemplateResponse(
            "instructor/student_certification.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_cert": current_cert,
                "cert_info": cert_info,
                "next_cert": next_cert,
                "next_cert_info": next_cert_info,
                "eligibility": eligibility,
                "teaching_hours": teaching_hours,
                "cert_history": cert_history,
                "specialization_display": "LFA Coach",
                "specialization_color": "#e74c3c",
                "success": True,
                "message": f"✅ Successfully certified as {cert_info['name']}!"
            }
        )

    except ValueError as e:
        db.rollback()

        # Reload current state
        cert_service = CoachCertificationService(db)
        current_cert = cert_service.get_current_certification(license_id)
        cert_info = cert_service.get_certification_info(current_cert)
        next_cert = cert_service.get_next_certification(current_cert)
        next_cert_info = cert_service.get_certification_info(next_cert) if next_cert else None
        eligibility = cert_service.check_certification_eligibility(license_id)
        teaching_hours = cert_service.get_teaching_hours_summary(license_id)
        cert_history = cert_service.get_certification_history(license_id)

        return templates.TemplateResponse(
            "instructor/student_certification.html",  # TODO: Create this template
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "current_cert": current_cert,
                "cert_info": cert_info,
                "next_cert": next_cert,
                "next_cert_info": next_cert_info,
                "eligibility": eligibility,
                "teaching_hours": teaching_hours,
                "cert_history": cert_history,
                "specialization_display": "LFA Coach",
                "specialization_color": "#e74c3c",
                "error": True,
                "message": f"❌ Certification failed: {str(e)}"
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error certifying coach: {str(e)}")


@router.post("/instructor/students/{student_id}/track-teaching-hours/{license_id}")
async def track_teaching_hours(
    request: Request,
    student_id: int,
    license_id: int,
    session_id: int,
    hours: float,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Track teaching hours for a coach
    Records verified teaching hours linked to a specific session

    TODO: Implement teaching hours tracking
    """
    # Security check: ONLY instructors can access
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="Instructor access required")

    # Get license
    license = db.query(UserLicense).filter(
        UserLicense.id == license_id,
        UserLicense.user_id == student_id
    ).first()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    # Verify this is an LFA Coach specialization
    if license.specialization_type != "LFA_COACH":
        raise HTTPException(status_code=400, detail="This license is not for LFA Coach specialization")

    try:
        # Initialize certification service
        cert_service = CoachCertificationService(db)

        # Track teaching hours
        result = cert_service.track_teaching_hours(
            user_license_id=license_id,
            session_id=session_id,
            hours=hours,
            verified_by=user.id
        )

        # Commit changes
        db.commit()

        return {
            "success": True,
            "message": f"Successfully tracked {hours} teaching hours",
            "total_hours": result['total_hours']
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error tracking teaching hours: {str(e)}")
