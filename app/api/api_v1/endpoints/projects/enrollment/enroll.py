"""
Core enrollment operations for project enrollment.

This module handles:
- Student enrollment in projects
- Withdrawal from projects
- Re-enrollment after withdrawal
- Current active project retrieval
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from ..validators import (
    validate_semester_enrollment,
    validate_specialization_enrollment,
    validate_payment_enrollment
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import (
    Project as ProjectModel,
    ProjectEnrollment,
    ProjectMilestone,
    ProjectMilestoneProgress,
    ProjectStatus,
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus
)
from app.schemas.project import ProjectEnrollment as ProjectEnrollmentSchema

router = APIRouter()


@router.post("/{project_id}/enroll", response_model=ProjectEnrollmentSchema)
def enroll_in_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Enroll current user in project (Students only)
    """
    if current_user.role.value != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll in projects"
        )

    # 🔒 CRITICAL: Validate semester enrollment eligibility
    validate_semester_enrollment(project_id, current_user, db)

    # 🎓 NEW: Validate specialization enrollment eligibility
    validate_specialization_enrollment(project_id, current_user, db)

    # 💰 REFACTORED: Validate semester enrollment payment verification
    validate_payment_enrollment(current_user, db)

    # Check if project exists and is active
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.status == ProjectStatus.ACTIVE.value
        )
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not active"
        )

    # Check if already enrolled
    existing_enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()

    if existing_enrollment:
        if existing_enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already enrolled in this project"
            )
        elif existing_enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
            # Allow re-enrollment
            existing_enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
            existing_enrollment.progress_status = ProjectProgressStatus.PLANNING.value
            db.commit()
            db.refresh(existing_enrollment)
            return existing_enrollment

    # Check if project has available spots
    if project.enrolled_count >= project.max_participants:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is full"
        )

    # Create enrollment
    enrollment = ProjectEnrollment(
        project_id=project_id,
        user_id=current_user.id,
        status=ProjectEnrollmentStatus.ACTIVE.value,
        progress_status=ProjectProgressStatus.PLANNING.value
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    # Create milestone progress records for all milestones
    milestones = db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project_id).all()
    for milestone in milestones:
        milestone_progress = ProjectMilestoneProgress(
            enrollment_id=enrollment.id,
            milestone_id=milestone.id,
            status=MilestoneStatus.PENDING.value
        )
        db.add(milestone_progress)

    db.commit()

    return enrollment


@router.delete("/{project_id}/enroll")
def withdraw_from_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Withdraw current user from project
    """
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enrollment found for this project"
        )

    # If already withdrawn, return success message
    if enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
        return {"message": "Already withdrawn from project"}

    # Only allow withdrawal from active enrollments
    if enrollment.status != ProjectEnrollmentStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot withdraw from project with status: {enrollment.status}"
        )

    # Update status to withdrawn
    enrollment.status = ProjectEnrollmentStatus.WITHDRAWN.value
    db.commit()

    return {"message": "Successfully withdrawn from project"}


@router.get("/my/current")
def get_my_current_project(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user's active project enrollment
    """
    enrollment = db.query(ProjectEnrollment).options(
        joinedload(ProjectEnrollment.project)
    ).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).first()

    if not enrollment:
        return None

    # Return simplified structure
    return {
        "id": enrollment.id,
        "project_id": enrollment.project_id,
        "project_title": enrollment.project.title if enrollment.project else "Unknown",
        "status": enrollment.status,
        "progress_status": enrollment.progress_status,
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
    }
