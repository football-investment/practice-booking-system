"""
Enrollment status tracking and progress monitoring.

This module handles:
- User's enrollment status retrieval
- Enrollment progress tracking
- Status summaries for dashboards
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .......database import get_db
from .......dependencies import get_current_user
from .......models.user import User
from .......models.project import (
    Project as ProjectModel,
    ProjectEnrollment,
    ProjectStatus,
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    ProjectQuiz,
    ProjectEnrollmentQuiz,
    MilestoneStatus
)
from .......models.quiz import QuizAttempt

router = APIRouter()


@router.get("/my/summary")
def get_my_project_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get project summary for student dashboard
    """
    # Get all active and not_eligible enrollments
    active_enrollments = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            or_(
                ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value,
                ProjectEnrollment.status == ProjectEnrollmentStatus.NOT_ELIGIBLE.value
            )
        )
    ).all()

    # For backward compatibility, get the first active one as current_enrollment
    current_enrollment = None
    for enrollment in active_enrollments:
        if enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            current_enrollment = enrollment
            break

    # Get available projects (active projects with spots available)
    available_projects = db.query(ProjectModel).filter(
        ProjectModel.status == ProjectStatus.ACTIVE.value
    ).all()

    # Filter projects where user is not already enrolled
    user_enrolled_projects = db.query(ProjectEnrollment.project_id).filter(
        ProjectEnrollment.user_id == current_user.id
    ).subquery()

    available_projects = db.query(ProjectModel).filter(
        and_(
            ProjectModel.status == ProjectStatus.ACTIVE.value,
            ~ProjectModel.id.in_(user_enrolled_projects)
        )
    ).all()

    # Convert to dicts for response (computed fields are properties)
    available_projects_data = []
    for project in available_projects:
        available_projects_data.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "semester_id": project.semester_id,
            "instructor_id": project.instructor_id,
            "max_participants": project.max_participants,
            "required_sessions": project.required_sessions,
            "xp_reward": project.xp_reward,
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "enrolled_count": project.enrolled_count,
            "available_spots": project.available_spots
        })

    # Get completed projects count and XP
    completed_enrollments = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.COMPLETED.value
        )
    ).all()

    total_xp = sum(e.project.xp_reward for e in completed_enrollments if e.instructor_approved)

    # Simple dict response for now
    current_project_data = None
    if current_enrollment:
        current_project_data = {
            "id": current_enrollment.id,
            "project_id": current_enrollment.project_id,
            "project_title": current_enrollment.project.title,
            "status": current_enrollment.status,
            "progress_status": current_enrollment.progress_status,
            "completion_percentage": current_enrollment.completion_percentage,
            "enrolled_at": current_enrollment.enrolled_at.isoformat()
        }

    # Build list of all enrolled projects (including not_eligible)
    enrolled_projects_data = []
    for enrollment in active_enrollments:
        enrolled_projects_data.append({
            "id": enrollment.id,
            "project_id": enrollment.project_id,
            "project_title": enrollment.project.title,
            "status": enrollment.status,
            "progress_status": enrollment.progress_status,
            "completion_percentage": enrollment.completion_percentage,
            "enrolled_at": enrollment.enrolled_at.isoformat()
        })

    return {
        "current_project": current_project_data,
        "enrolled_projects": enrolled_projects_data,
        "available_projects": available_projects_data,
        "total_projects_completed": len(completed_enrollments),
        "total_xp_from_projects": total_xp
    }


@router.get("/{project_id}/enrollment-status")
def get_project_enrollment_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get user's enrollment status for a specific project
    """
    # Check if user has a project enrollment
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()

    if enrollment:
        # User has enrollment record - return actual status
        if enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            return {
                "user_status": "confirmed",
                "message": "Your enrollment has been confirmed! Welcome to the project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.NOT_ELIGIBLE.value:
            return {
                "user_status": "not_eligible",
                "message": "Unfortunately, you did not meet the minimum requirements for this project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.COMPLETED.value:
            return {
                "user_status": "completed",
                "message": "You have completed this project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
            return {
                "user_status": "withdrawn",
                "message": "You have withdrawn from this project.",
                "enrollment_id": enrollment.id
            }

    # Find project's enrollment quiz
    project_quiz = db.query(ProjectQuiz).filter(
        and_(
            ProjectQuiz.project_id == project_id,
            ProjectQuiz.quiz_type == "enrollment",
            ProjectQuiz.is_active == True
        )
    ).first()

    if not project_quiz:
        # No enrollment quiz required
        return {
            "user_status": "no_quiz_required",
            "message": "No enrollment quiz required for this project."
        }

    # Check if user has completed the quiz
    quiz_attempt = db.query(QuizAttempt).filter(
        and_(
            QuizAttempt.quiz_id == project_quiz.quiz_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.completed_at.isnot(None)
        )
    ).first()

    if not quiz_attempt:
        # No quiz attempt yet
        return {
            "user_status": "quiz_required",
            "message": "Please complete the enrollment quiz to continue.",
            "quiz_id": project_quiz.quiz_id
        }

    # Check if there's an enrollment quiz record for more detailed status
    user_enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()

    if user_enrollment_quiz and quiz_attempt.passed:
        # Get total applicants for this project
        total_applicants = db.query(ProjectEnrollmentQuiz).filter(
            ProjectEnrollmentQuiz.project_id == project_id
        ).count()

        # Get project for max_participants
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        can_confirm = user_enrollment_quiz.enrollment_priority <= project.max_participants

        # Determine detailed status
        if user_enrollment_quiz.enrollment_confirmed:
            user_status = "confirmed"
            message = "Your enrollment has been confirmed! Welcome to the project."
        elif can_confirm:
            user_status = "eligible"
            message = "Congratulations! You are eligible to enroll in this project."
        else:
            user_status = "waiting"
            message = "You are on the waiting list. We will notify you if a spot becomes available."

        return {
            "user_status": user_status,
            "message": message,
            "quiz_score": quiz_attempt.score,
            "enrollment_priority": user_enrollment_quiz.enrollment_priority,
            "total_applicants": total_applicants,
            "can_confirm": can_confirm and not user_enrollment_quiz.enrollment_confirmed,
            "enrollment_confirmed": user_enrollment_quiz.enrollment_confirmed
        }

    # Quiz completed but no enrollment record means something went wrong
    # This should not happen with our new logic, but handle it gracefully
    if quiz_attempt.passed:
        return {
            "user_status": "eligible",
            "message": "Quiz passed! You are eligible for enrollment.",
            "quiz_score": quiz_attempt.score
        }
    else:
        return {
            "user_status": "not_eligible",
            "message": "Unfortunately, you did not meet the minimum requirements for this project.",
            "quiz_score": quiz_attempt.score
        }


@router.get("/{project_id}/progress")
def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get detailed project progress for current user
    """
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

    # Calculate overall progress based on completed milestones
    total_milestones = len(enrollment.project.milestones)
    completed_milestones = len([
        mp for mp in enrollment.milestone_progress
        if mp.status == MilestoneStatus.APPROVED.value
    ])

    overall_progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0

    # Find next milestone
    next_milestone = None
    for milestone in enrollment.project.milestones:
        milestone_progress = next(
            (mp for mp in enrollment.milestone_progress if mp.milestone_id == milestone.id),
            None
        )
        if not milestone_progress or milestone_progress.status in [MilestoneStatus.PENDING.value, MilestoneStatus.IN_PROGRESS.value]:
            next_milestone = milestone
            break

    # Calculate sessions remaining
    sessions_completed = sum(mp.sessions_completed for mp in enrollment.milestone_progress)
    sessions_remaining = max(0, enrollment.project.required_sessions - sessions_completed)

    # Simple dict response
    next_milestone_data = None
    if next_milestone:
        next_milestone_data = {
            "id": next_milestone.id,
            "title": next_milestone.title,
            "description": next_milestone.description,
            "required_sessions": next_milestone.required_sessions,
            "xp_reward": next_milestone.xp_reward,
            "deadline": next_milestone.deadline.isoformat() if next_milestone.deadline else None
        }

    milestone_progress_data = []
    for mp in enrollment.milestone_progress:
        milestone_progress_data.append({
            "id": mp.id,
            "milestone_id": mp.milestone_id,
            "milestone_title": mp.milestone.title,
            "status": mp.status,
            "sessions_completed": mp.sessions_completed,
            "sessions_required": mp.milestone.required_sessions,
            "submitted_at": mp.submitted_at.isoformat() if mp.submitted_at else None,
            "instructor_feedback": mp.instructor_feedback
        })

    return {
        "project_title": enrollment.project.title,
        "enrollment_status": enrollment.status,
        "progress_status": enrollment.progress_status,
        "completion_percentage": enrollment.completion_percentage,
        "overall_progress": overall_progress,
        "sessions_completed": sessions_completed,
        "sessions_remaining": sessions_remaining,
        "milestone_progress": milestone_progress_data,
        "next_milestone": next_milestone_data
    }
