"""
Project milestone management.

This module handles:
- Milestone submission by students
- Milestone approval/rejection by instructors
- Milestone progression tracking
- Project completion detection
"""
from typing import Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, ConfigDict

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.project import (
    Project as ProjectModel,
    ProjectEnrollment,
    ProjectMilestone,
    ProjectMilestoneProgress,
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus
)
from .....services.gamification import GamificationService

router = APIRouter()


class ProjectActionRequest(BaseModel):
    """Empty request schema for project action endpoints - validates no extra fields"""
    model_config = ConfigDict(extra='forbid')


@router.post("/{project_id}/milestones/{milestone_id}/submit")
def submit_milestone(
    project_id: int,
    milestone_id: int,
    request_data: ProjectActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Submit milestone for review (Student only)
    """
    # Verify student role
    if current_user.role.value != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit milestones"
        )
    
    # Get enrollment
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active enrollment found for this project"
        )
    
    # Get milestone progress
    milestone_progress = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment.id,
            ProjectMilestoneProgress.milestone_id == milestone_id
        )
    ).first()
    
    if not milestone_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone progress not found"
        )
    
    # Check if milestone is in progress
    if milestone_progress.status != MilestoneStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Milestone must be in progress to submit. Current status: {milestone_progress.status}"
        )
    
    # Check if required sessions are completed
    milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
    if milestone_progress.sessions_completed < milestone.required_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need to complete {milestone.required_sessions} sessions. Currently completed: {milestone_progress.sessions_completed}"
        )
    
    # Submit milestone
    milestone_progress.status = MilestoneStatus.SUBMITTED.value
    milestone_progress.submitted_at = datetime.now(timezone.utc)
    milestone_progress.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(milestone_progress)
    
    return {
        "message": "Milestone submitted successfully",
        "milestone_id": milestone_id,
        "status": milestone_progress.status,
        "submitted_at": milestone_progress.submitted_at
    }


@router.post("/{project_id}/milestones/{milestone_id}/approve")
def approve_milestone(
    project_id: int,
    milestone_id: int,
    request_data: ProjectActionRequest,
    feedback: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Approve milestone (Instructor only)
    """
    # Verify instructor role and project ownership
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can approve milestones"
        )
    
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Get milestone progress for all enrollments
    milestone_progresses = db.query(ProjectMilestoneProgress).join(
        ProjectEnrollment, ProjectMilestoneProgress.enrollment_id == ProjectEnrollment.id
    ).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectMilestoneProgress.milestone_id == milestone_id,
            ProjectMilestoneProgress.status == MilestoneStatus.SUBMITTED.value
        )
    ).all()
    
    if not milestone_progresses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submitted milestones found for approval"
        )
    
    approved_count = 0
    for milestone_progress in milestone_progresses:
        # Approve milestone
        milestone_progress.status = MilestoneStatus.APPROVED.value
        milestone_progress.instructor_feedback = feedback
        milestone_progress.instructor_approved_at = datetime.now(timezone.utc)
        milestone_progress.updated_at = datetime.now(timezone.utc)
        
        # Award XP for milestone completion
        milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
        if milestone:
            gamification_service = GamificationService(db)
            user_stats = gamification_service.get_or_create_user_stats(milestone_progress.enrollment.user_id)
            user_stats.total_xp = (user_stats.total_xp or 0) + milestone.xp_reward
            
        # Activate next milestone if this was approved
        _activate_next_milestone(db, milestone_progress.enrollment_id, milestone_id)
        
        approved_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully approved {approved_count} milestone submissions",
        "milestone_id": milestone_id,
        "approved_count": approved_count
    }


@router.post("/{project_id}/milestones/{milestone_id}/reject")
def reject_milestone(
    project_id: int,
    milestone_id: int,
    feedback: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Reject milestone (Instructor only)
    """
    # Verify instructor role and project ownership
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can reject milestones"
        )
    
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Get milestone progress for all enrollments
    milestone_progresses = db.query(ProjectMilestoneProgress).join(
        ProjectEnrollment, ProjectMilestoneProgress.enrollment_id == ProjectEnrollment.id
    ).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectMilestoneProgress.milestone_id == milestone_id,
            ProjectMilestoneProgress.status == MilestoneStatus.SUBMITTED.value
        )
    ).all()
    
    if not milestone_progresses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submitted milestones found for rejection"
        )
    
    rejected_count = 0
    for milestone_progress in milestone_progresses:
        # Reject milestone - return to IN_PROGRESS
        milestone_progress.status = MilestoneStatus.IN_PROGRESS.value
        milestone_progress.instructor_feedback = feedback
        milestone_progress.updated_at = datetime.now(timezone.utc)
        # Clear submitted_at and instructor_approved_at
        milestone_progress.submitted_at = None
        milestone_progress.instructor_approved_at = None
        
        rejected_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully rejected {rejected_count} milestone submissions",
        "milestone_id": milestone_id,
        "rejected_count": rejected_count,
        "feedback": feedback
    }


def _activate_next_milestone(db: Session, enrollment_id: int, current_milestone_id: int):
    """
    Activate the next milestone in sequence after current milestone is approved
    """
    # Get current milestone order
    current_milestone = db.query(ProjectMilestone).filter(
        ProjectMilestone.id == current_milestone_id
    ).first()
    
    if not current_milestone:
        return
    
    # Find next milestone by order_index
    next_milestone = db.query(ProjectMilestone).filter(
        and_(
            ProjectMilestone.project_id == current_milestone.project_id,
            ProjectMilestone.order_index > current_milestone.order_index
        )
    ).order_by(ProjectMilestone.order_index).first()
    
    if not next_milestone:
        # No more milestones - check if project is complete
        _check_project_completion(db, enrollment_id)
        return
    
    # Activate next milestone
    next_milestone_progress = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment_id,
            ProjectMilestoneProgress.milestone_id == next_milestone.id
        )
    ).first()
    
    if next_milestone_progress and next_milestone_progress.status == MilestoneStatus.PENDING.value:
        next_milestone_progress.status = MilestoneStatus.IN_PROGRESS.value
        next_milestone_progress.updated_at = datetime.now(timezone.utc)


def _check_project_completion(db: Session, enrollment_id: int):
    """
    Check if all milestones are completed and award project completion XP
    """
    enrollment = db.query(ProjectEnrollment).filter(ProjectEnrollment.id == enrollment_id).first()
    if not enrollment:
        return
    
    # Check if all milestones are approved
    total_milestones = db.query(ProjectMilestone).filter(
        ProjectMilestone.project_id == enrollment.project_id
    ).count()
    
    approved_milestones = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment_id,
            ProjectMilestoneProgress.status == MilestoneStatus.APPROVED.value
        )
    ).count()
    
    if total_milestones == approved_milestones:
        # Project completed - award bonus XP
        gamification_service = GamificationService(db)
        user_stats = gamification_service.get_or_create_user_stats(enrollment.user_id)
        user_stats.total_xp = (user_stats.total_xp or 0) + enrollment.project.xp_reward
        
        # Update enrollment status
        enrollment.status = ProjectEnrollmentStatus.COMPLETED.value
        enrollment.progress_status = ProjectProgressStatus.COMPLETED.value
        enrollment.completed_at = datetime.now(timezone.utc)
        enrollment.completion_percentage = 100.0
