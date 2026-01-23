"""
⚽ LFA Player Routes - Skills-Based Assessment System

Routes for LFA Player specialization (U6-U11, Amateur, Pro):
- Football skills assessment (6 skills with points/percentage)
- Skills history and averages
- Skills progress tracking

NO levels, NO belts, NO XP - ONLY skills with averages.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.user import User, UserRole
from ...models.license import UserLicense
from ...services.football_skill_service import FootballSkillService
from ...dependencies import get_current_user_web
from ...main import templates
from pydantic import ValidationError


router = APIRouter()


# Skill display configuration
SKILL_NAMES = ['heading', 'shooting', 'crossing', 'passing', 'dribbling', 'ball_control']

SKILL_DISPLAY_NAMES = {
    'heading': 'Heading',
    'shooting': 'Shooting',
    'crossing': 'Crossing',
    'passing': 'Passing',
    'dribbling': 'Dribbling',
    'ball_control': 'Ball Control'
}

SKILL_EMOJIS = {
    'heading': '🎯',
    'shooting': '⚽',
    'crossing': '🎪',
    'passing': '🎯',
    'dribbling': '⚡',
    'ball_control': '🧘'
}


@router.get("/instructor/students/{student_id}/skills-v2/{license_id}", response_class=HTMLResponse)
async def instructor_student_skills_v2_page(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: V2 Football skills assessment page (points-based with averaging)
    Shows current averages, assessment counts, and history for each skill
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

    # Verify this is an LFA Player specialization
    if not license.specialization_type.startswith("LFA_PLAYER_"):
        raise HTTPException(status_code=400, detail="This license is not for an LFA Player specialization")

    # Initialize skill service
    skill_service = FootballSkillService(db)

    # Get current averages and counts for all 6 skills
    skills_data = []

    for skill_name in SKILL_NAMES:
        # Get assessment history
        history_response = skill_service.get_assessment_history(license_id, skill_name, limit=3)

        skills_data.append({
            'name': skill_name,
            'display_name': SKILL_DISPLAY_NAMES[skill_name],
            'emoji': SKILL_EMOJIS[skill_name],
            'current_average': history_response.current_average,
            'assessment_count': history_response.assessment_count,
            'recent_assessments': [
                {
                    'points_earned': a.points_earned,
                    'points_total': a.points_total,
                    'percentage': a.percentage,
                    'assessed_at': a.assessed_at,
                    'assessor_name': a.assessor_name,
                    'notes': a.notes
                }
                for a in history_response.assessments
            ]
        })

    # Get specialization display info
    specialization_display = license.specialization_type.replace('_', ' ').title()
    specialization_color = '#f39c12'  # Orange for LFA Player

    # Build dictionaries for template compatibility
    assessment_averages = {skill['name']: skill['current_average'] for skill in skills_data}
    assessment_counts = {skill['name']: skill['assessment_count'] for skill in skills_data}
    assessment_history = {skill['name']: skill['recent_assessments'] for skill in skills_data}

    return templates.TemplateResponse(
        "instructor/student_skills_v2.html",
        {
            "request": request,
            "user": user,
            "student": student,
            "license": license,
            "license_id": license_id,
            "skills_data": skills_data,
            "assessment_averages": assessment_averages,
            "assessment_counts": assessment_counts,
            "assessment_history": assessment_history,
            "specialization_display": specialization_display,
            "specialization_color": specialization_color
        }
    )


@router.post("/instructor/students/{student_id}/skills-v2/{license_id}", response_class=HTMLResponse)
async def instructor_student_skills_v2_submit(
    request: Request,
    student_id: int,
    license_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor-only: Submit V2 football skills assessment (points-based)
    Creates assessments for all 6 skills and auto-recalculates averages
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

    # Verify this is an LFA Player specialization
    if not license.specialization_type.startswith("LFA_PLAYER_"):
        raise HTTPException(status_code=400, detail="This license is not for an LFA Player specialization")

    # Parse form data
    form_data = await request.form()

    try:
        # Build bulk assessment data from form
        assessments_dict = {}
        for skill_name in SKILL_NAMES:
            points_earned = int(form_data.get(f"{skill_name}_earned", 0))
            points_total = int(form_data.get(f"{skill_name}_total", 10))
            notes = form_data.get(f"{skill_name}_notes", "").strip() or None

            assessments_dict[skill_name] = {
                'points_earned': points_earned,
                'points_total': points_total,
                'notes': notes
            }

        # Initialize skill service and create assessments
        skill_service = FootballSkillService(db)
        results = skill_service.bulk_create_assessments(
            user_license_id=license_id,
            assessments=assessments_dict,
            assessed_by=user.id
        )

        # Commit changes
        db.commit()

        # Reload data for display
        skills_data = []

        for skill_name in SKILL_NAMES:
            # Get updated assessment history
            history_response = skill_service.get_assessment_history(license_id, skill_name, limit=3)

            skills_data.append({
                'name': skill_name,
                'display_name': SKILL_DISPLAY_NAMES[skill_name],
                'emoji': SKILL_EMOJIS[skill_name],
                'current_average': history_response.current_average,
                'assessment_count': history_response.assessment_count,
                'recent_assessments': [
                    {
                        'points_earned': a.points_earned,
                        'points_total': a.points_total,
                        'percentage': a.percentage,
                        'assessed_at': a.assessed_at,
                        'assessor_name': a.assessor_name,
                        'notes': a.notes
                    }
                    for a in history_response.assessments
                ]
            })

        # Get specialization display info
        specialization_display = license.specialization_type.replace('_', ' ').title()
        specialization_color = '#f39c12'  # Orange for LFA Player

        # Build dictionaries for template compatibility
        assessment_averages = {skill['name']: skill['current_average'] for skill in skills_data}
        assessment_counts = {skill['name']: skill['assessment_count'] for skill in skills_data}
        assessment_history = {skill['name']: skill['recent_assessments'] for skill in skills_data}

        return templates.TemplateResponse(
            "instructor/student_skills_v2.html",
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "skills_data": skills_data,
                "assessment_averages": assessment_averages,
                "assessment_counts": assessment_counts,
                "assessment_history": assessment_history,
                "specialization_display": specialization_display,
                "specialization_color": specialization_color,
                "success": True,
                "message": f"✅ Successfully assessed all 6 skills! Averages updated automatically."
            }
        )

    except ValidationError as e:
        # Validation error - show form with error messages
        db.rollback()

        # Reload current state
        skill_service = FootballSkillService(db)
        skills_data = []

        for skill_name in SKILL_NAMES:
            history_response = skill_service.get_assessment_history(license_id, skill_name, limit=3)
            skills_data.append({
                'name': skill_name,
                'display_name': SKILL_DISPLAY_NAMES[skill_name],
                'emoji': SKILL_EMOJIS[skill_name],
                'current_average': history_response.current_average,
                'assessment_count': history_response.assessment_count,
                'recent_assessments': [
                    {
                        'points_earned': a.points_earned,
                        'points_total': a.points_total,
                        'percentage': a.percentage,
                        'assessed_at': a.assessed_at,
                        'assessor_name': a.assessor_name,
                        'notes': a.notes
                    }
                    for a in history_response.assessments
                ]
            })

        specialization_display = license.specialization_type.replace('_', ' ').title()
        specialization_color = '#f39c12'

        # Build dictionaries for template compatibility
        assessment_averages = {skill['name']: skill['current_average'] for skill in skills_data}
        assessment_counts = {skill['name']: skill['assessment_count'] for skill in skills_data}
        assessment_history = {skill['name']: skill['recent_assessments'] for skill in skills_data}

        return templates.TemplateResponse(
            "instructor/student_skills_v2.html",
            {
                "request": request,
                "user": user,
                "student": student,
                "license": license,
                "license_id": license_id,
                "skills_data": skills_data,
                "assessment_averages": assessment_averages,
                "assessment_counts": assessment_counts,
                "assessment_history": assessment_history,
                "specialization_display": specialization_display,
                "specialization_color": specialization_color,
                "error": True,
                "message": f"❌ Validation error: {str(e)}"
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating assessment: {str(e)}")
