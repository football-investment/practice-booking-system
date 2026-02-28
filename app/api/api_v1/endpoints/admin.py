"""
Admin Dashboard API Endpoints
=============================

Admin-only endpoints for dashboard statistics and management.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from ....database import get_db
from ....models.user import User, UserRole
from ....models.booking import Booking
from ....models.session import Session as SessionTypel
from ....models.user_progress import SpecializationProgress
from ....models.license import UserLicense
from ....dependencies import get_current_admin_user
from ....services.audit_service import AuditService
from ....models.audit_log import AuditAction


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class MotivationAssessmentRequest(BaseModel):
    """Admin/Instructor motivation assessment for student"""
    goal_clarity: int = Field(..., ge=1, le=5, description="Goal clarity score (1-5)")
    commitment_level: int = Field(..., ge=1, le=5, description="Commitment level (1-5)")
    engagement: int = Field(..., ge=1, le=5, description="Engagement score (1-5)")
    progress_mindset: int = Field(..., ge=1, le=5, description="Progress mindset (1-5)")
    initiative: int = Field(..., ge=1, le=5, description="Initiative score (1-5)")
    notes: Optional[str] = Field("", description="Optional assessment notes")


class MotivationAssessmentResponse(BaseModel):
    """Response from motivation assessment submission"""
    success: bool
    message: str
    student_id: int
    specialization: str
    average_score: float
    assessed_by: str


@router.get("/stats", response_model=Dict[str, Any])
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get admin dashboard statistics

    Returns:
        {
            'total_users': int,
            'active_users': int,
            'total_students': int,
            'total_instructors': int,
            'total_sessions': int,
            'total_bookings': int,
            'total_progress_records': int,
            'total_licenses': int
        }

    Permissions:
        - ADMIN role required
    """
    try:
        # User statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        total_students = db.query(func.count(User.id)).filter(User.role == UserRole.STUDENT).scalar() or 0
        total_instructors = db.query(func.count(User.id)).filter(User.role == UserRole.INSTRUCTOR).scalar() or 0

        # Session and booking statistics
        total_sessions = db.query(func.count(SessionTypel.id)).scalar() or 0
        total_bookings = db.query(func.count(Booking.id)).scalar() or 0

        # Progress and license statistics
        total_progress_records = db.query(func.count(SpecializationProgress.id)).scalar() or 0
        total_licenses = db.query(func.count(UserLicense.id)).scalar() or 0

        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_sessions': total_sessions,
            'total_bookings': total_bookings,
            'total_progress_records': total_progress_records,
            'total_licenses': total_licenses
        }
    except Exception as e:
        # Return zeros on error
        return {
            'total_users': 0,
            'active_users': 0,
            'total_students': 0,
            'total_instructors': 0,
            'total_sessions': 0,
            'total_bookings': 0,
            'total_progress_records': 0,
            'total_licenses': 0,
            'error': str(e)
        }


@router.post("/students/{student_id}/motivation/{specialization}", response_model=MotivationAssessmentResponse)
def submit_motivation_assessment(
    student_id: int,
    specialization: str,
    data: MotivationAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin/Instructor submits motivation assessment for student

    **Business Logic (from web route):**
    - Validates scores (1-5)
    - Stores motivation data in license.motivation_scores
    - Calculates and stores average score
    - Records assessor information
    - Creates audit log

    **Permissions:**
    - ADMIN or INSTRUCTOR role required

    **Scores (1-5):**
    - goal_clarity: Student's clarity about goals
    - commitment_level: Level of commitment shown
    - engagement: Active participation and engagement
    - progress_mindset: Growth mindset and learning attitude
    - initiative: Self-starting and proactive behavior
    """
    # Permission check (already enforced by get_current_admin_user, but web route also allows instructors)
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Instructor access required"
        )

    # Get student
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.STUDENT
    ).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found"
        )

    # Get student's license for this specialization
    license = db.query(UserLicense).filter(
        UserLicense.user_id == student_id,
        UserLicense.specialization_type == specialization
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student does not have {specialization} license"
        )

    # Create motivation scores JSON
    scores = [
        data.goal_clarity,
        data.commitment_level,
        data.engagement,
        data.progress_mindset,
        data.initiative
    ]

    motivation_data = {
        "goal_clarity": data.goal_clarity,
        "commitment_level": data.commitment_level,
        "engagement": data.engagement,
        "progress_mindset": data.progress_mindset,
        "initiative": data.initiative,
        "notes": data.notes,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "assessed_by_id": current_user.id,
        "assessed_by_name": current_user.name
    }

    # Calculate average
    average_score = sum(scores) / len(scores)

    # Update license
    license.motivation_scores = motivation_data
    license.average_motivation_score = average_score
    license.motivation_last_assessed_at = datetime.now(timezone.utc)
    license.motivation_assessed_by = current_user.id

    db.commit()
    db.refresh(license)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.MOTIVATION_ASSESSED,
        user_id=current_user.id,
        resource_type="license",
        resource_id=license.id,
        details={
            "student_id": student_id,
            "student_name": student.name,
            "specialization": specialization,
            "average_score": average_score,
            "scores": motivation_data
        }
    )

    return MotivationAssessmentResponse(
        success=True,
        message=f"Motivation assessment saved for {student.name}",
        student_id=student_id,
        specialization=specialization,
        average_score=round(average_score, 2),
        assessed_by=current_user.name
    )
