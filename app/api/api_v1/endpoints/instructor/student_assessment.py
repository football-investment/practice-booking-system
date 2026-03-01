"""
Instructor Student Assessment API Endpoints (PHASE 2 - P1)
==========================================================

Instructor tools for assessing student football skills.
Reuses business logic from web routes with clean JSON API interface.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.license import UserLicense
from .....services.audit_service import AuditService
from .....models.audit_log import AuditAction
from .....services.football_skill_service import FootballSkillService


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class UpdateSkillsRequest(BaseModel):
    """Request to update student football skills (V1 - direct update)"""
    heading: float = Field(..., ge=0, le=100, description="Heading skill (0-100)")
    shooting: float = Field(..., ge=0, le=100, description="Shooting skill (0-100)")
    crossing: float = Field(..., ge=0, le=100, description="Crossing skill (0-100)")
    passing: float = Field(..., ge=0, le=100, description="Passing skill (0-100)")
    dribbling: float = Field(..., ge=0, le=100, description="Dribbling skill (0-100)")
    ball_control: float = Field(..., ge=0, le=100, description="Ball control skill (0-100)")
    instructor_notes: Optional[str] = Field(None, description="Optional instructor notes")


class UpdateSkillsResponse(BaseModel):
    """Response from updating student skills"""
    success: bool
    message: str
    student_id: int
    license_id: int
    skills: dict
    updated_at: datetime


class SkillAssessmentV2(BaseModel):
    """Single skill assessment for V2 (points-based)"""
    points_earned: int = Field(..., ge=0, description="Points earned in assessment")
    points_total: int = Field(..., gt=0, description="Total points possible")
    notes: Optional[str] = Field(None, description="Optional notes")


class UpdateSkillsV2Request(BaseModel):
    """Request to create skill assessments (V2 - points-based with history)"""
    heading: SkillAssessmentV2
    shooting: SkillAssessmentV2
    crossing: SkillAssessmentV2
    passing: SkillAssessmentV2
    dribbling: SkillAssessmentV2
    ball_control: SkillAssessmentV2


class UpdateSkillsV2Response(BaseModel):
    """Response from creating skill assessments"""
    success: bool
    message: str
    student_id: int
    license_id: int
    assessments_created: int
    skill_averages: dict


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/instructor/students/{student_id}/skills/{license_id}", response_model=UpdateSkillsResponse)
def update_student_skills(
    student_id: int,
    license_id: int,
    skills: UpdateSkillsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update student football skills (V1 - Direct Update)

    **Business Logic** (from web route):
    - Direct update of 6 football skills (0-100 scale)
    - Stores in license.football_skills dict
    - Updates skills_last_updated_at and skills_updated_by
    - Optional instructor notes

    **Permissions:** INSTRUCTOR role required
    **Specializations:** LFA_PLAYER_* only
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can update student skills"
        )

    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get license
    license = db.query(UserLicense).filter(
        UserLicense.id == license_id,
        UserLicense.user_id == student_id
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    # Verify LFA Player specialization
    if not license.specialization_type.startswith("LFA_PLAYER_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Football skills are only available for LFA Player specializations"
        )

    # Build skills dict (round to 1 decimal)
    skills_dict = {
        "heading": round(skills.heading, 1),
        "shooting": round(skills.shooting, 1),
        "crossing": round(skills.crossing, 1),
        "passing": round(skills.passing, 1),
        "dribbling": round(skills.dribbling, 1),
        "ball_control": round(skills.ball_control, 1)
    }

    # Update license
    license.football_skills = skills_dict
    license.skills_last_updated_at = datetime.now(timezone.utc)
    license.skills_updated_by = current_user.id

    # Update instructor notes if provided
    if skills.instructor_notes and skills.instructor_notes.strip():
        license.instructor_notes = skills.instructor_notes.strip()

    db.commit()
    db.refresh(license)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        resource_type="football_skills",
        resource_id=license_id,
        details={
            "student_id": student_id,
            "student_email": student.email,
            "specialization": license.specialization_type,
            "skills": skills_dict,
            "instructor_notes": skills.instructor_notes
        }
    )

    return UpdateSkillsResponse(
        success=True,
        message="Football skills updated successfully",
        student_id=student_id,
        license_id=license_id,
        skills=skills_dict,
        updated_at=license.skills_last_updated_at
    )


@router.post("/instructor/students/{student_id}/skills-v2/{license_id}", response_model=UpdateSkillsV2Response)
def update_student_skills_v2(
    student_id: int,
    license_id: int,
    assessments: UpdateSkillsV2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create student skill assessments (V2 - Points-Based with History)

    **Business Logic** (from web route):
    - Points-based assessment system (earned/total)
    - Creates assessment records with history
    - Auto-calculates rolling averages
    - Supports per-skill notes

    **Permissions:** INSTRUCTOR role required
    **Specializations:** LFA_PLAYER_* only
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can create skill assessments"
        )

    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get license
    license = db.query(UserLicense).filter(
        UserLicense.id == license_id,
        UserLicense.user_id == student_id
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    # Verify LFA Player specialization
    if not license.specialization_type.startswith("LFA_PLAYER_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This license is not for an LFA Player specialization"
        )

    # Build assessments dict for bulk creation
    assessments_dict = {
        "heading": {
            "points_earned": assessments.heading.points_earned,
            "points_total": assessments.heading.points_total,
            "notes": assessments.heading.notes
        },
        "shooting": {
            "points_earned": assessments.shooting.points_earned,
            "points_total": assessments.shooting.points_total,
            "notes": assessments.shooting.notes
        },
        "crossing": {
            "points_earned": assessments.crossing.points_earned,
            "points_total": assessments.crossing.points_total,
            "notes": assessments.crossing.notes
        },
        "passing": {
            "points_earned": assessments.passing.points_earned,
            "points_total": assessments.passing.points_total,
            "notes": assessments.passing.notes
        },
        "dribbling": {
            "points_earned": assessments.dribbling.points_earned,
            "points_total": assessments.dribbling.points_total,
            "notes": assessments.dribbling.notes
        },
        "ball_control": {
            "points_earned": assessments.ball_control.points_earned,
            "points_total": assessments.ball_control.points_total,
            "notes": assessments.ball_control.notes
        }
    }

    # Create assessments using FootballSkillService
    skill_service = FootballSkillService(db)
    results = skill_service.bulk_create_assessments(
        user_license_id=license_id,
        assessments=assessments_dict,
        assessed_by=current_user.id
    )

    db.commit()

    # Get updated averages for response
    skill_averages = {}
    for skill_name in ["heading", "shooting", "crossing", "passing", "dribbling", "ball_control"]:
        history_response = skill_service.get_assessment_history(license_id, skill_name, limit=1)
        skill_averages[skill_name] = history_response.current_average

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.CREATE,
        user_id=current_user.id,
        resource_type="football_skill_assessment",
        resource_id=license_id,
        details={
            "student_id": student_id,
            "student_email": student.email,
            "specialization": license.specialization_type,
            "assessments_count": len(results),
            "skill_averages": skill_averages
        }
    )

    return UpdateSkillsV2Response(
        success=True,
        message="Skill assessments created successfully",
        student_id=student_id,
        license_id=license_id,
        assessments_created=len(results),
        skill_averages=skill_averages
    )
