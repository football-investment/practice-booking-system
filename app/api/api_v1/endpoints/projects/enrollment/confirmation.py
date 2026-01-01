"""
Enrollment confirmation and quiz completion.

This module handles:
- Enrollment quiz completion and priority ranking
- Enrollment confirmation
- Priority recalculation
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import (
    Project as ProjectModel,
    ProjectEnrollment,
    ProjectEnrollmentQuiz,
    ProjectEnrollmentStatus,
    ProjectProgressStatus
)
from app.models.quiz import QuizAttempt
from app.schemas.project import EnrollmentPriorityResponse
from app.services.gamification import GamificationService

router = APIRouter()


@router.post("/{project_id}/enrollment-quiz", response_model=EnrollmentPriorityResponse)
def complete_enrollment_quiz(
    project_id: int,
    quiz_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Értékeli a jelentkezési quiz eredményét és meghatározza a rangsorolási pozíciót
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get quiz attempt
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == quiz_attempt_id,
        QuizAttempt.user_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found"
        )

    # Check if enrollment quiz record already exists
    existing_enrollment = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()

    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enrollment quiz already completed for this project"
        )

    # Calculate priority based on score and application time
    all_attempts = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).all()

    # Simple ranking: sort by score (desc), then by attempt time (asc)
    enrollment_priority = 1
    for existing in all_attempts:
        existing_attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == existing.quiz_attempt_id
        ).first()

        if existing_attempt and (
            existing_attempt.score > attempt.score or
            (existing_attempt.score == attempt.score and existing_attempt.completed_at < attempt.completed_at)
        ):
            enrollment_priority += 1

    # Create enrollment quiz record
    enrollment_quiz = ProjectEnrollmentQuiz(
        project_id=project_id,
        user_id=current_user.id,
        quiz_attempt_id=quiz_attempt_id,
        enrollment_priority=enrollment_priority,
        enrollment_confirmed=False
    )
    db.add(enrollment_quiz)
    db.commit()

    # Update priorities for others
    _recalculate_enrollment_priorities(db, project_id)

    return EnrollmentPriorityResponse(
        user_id=current_user.id,
        project_id=project_id,
        quiz_score=attempt.score,
        enrollment_priority=enrollment_priority,
        total_applicants=len(all_attempts) + 1,
        is_eligible=attempt.score >= 75.0,  # Minimum score
        can_confirm=enrollment_priority <= project.max_participants
    )


@router.post("/{project_id}/confirm-enrollment")
def confirm_project_enrollment(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Megerősíti a projekt jelentkezést
    """
    # Get enrollment quiz record
    enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()

    if not enrollment_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment quiz not found"
        )

    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    # Check if user is eligible (within capacity based on priority)
    if enrollment_quiz.enrollment_priority > project.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not eligible for enrollment based on priority ranking"
        )

    # Check if already enrolled
    existing_enrollment = db.query(ProjectEnrollment).filter(
        ProjectEnrollment.project_id == project_id,
        ProjectEnrollment.user_id == current_user.id
    ).first()

    if existing_enrollment:
        if existing_enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            return {"message": "Already enrolled in project"}

    # Create or update enrollment
    if not existing_enrollment:
        enrollment = ProjectEnrollment(
            project_id=project_id,
            user_id=current_user.id,
            status=ProjectEnrollmentStatus.ACTIVE.value,
            progress_status=ProjectProgressStatus.PLANNING.value
        )
        db.add(enrollment)
    else:
        existing_enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        existing_enrollment.progress_status = ProjectProgressStatus.PLANNING.value

    # Mark enrollment as confirmed
    enrollment_quiz.enrollment_confirmed = True

    db.commit()

    # Check for first-time project enrollment achievements
    gamification_service = GamificationService(db)
    gamification_service.check_first_project_enrollment(current_user.id, project_id)
    # Also check for newcomer welcome achievement
    gamification_service.check_newcomer_welcome(current_user.id)

    return {"message": "Enrollment confirmed successfully"}


def _recalculate_enrollment_priorities(db: Session, project_id: int):
    """
    Újraszámolja az enrollment prioritásokat egy projekthez
    """
    enrollments = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).all()

    # Sort by score (desc), then by completion time (asc)
    enrollment_data = []
    for enrollment in enrollments:
        attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == enrollment.quiz_attempt_id
        ).first()
        if attempt:
            enrollment_data.append({
                'enrollment': enrollment,
                'score': attempt.score,
                'completed_at': attempt.completed_at
            })

    # Sort and assign priorities
    enrollment_data.sort(key=lambda x: (-x['score'], x['completed_at']))

    for i, data in enumerate(enrollment_data):
        data['enrollment'].enrollment_priority = i + 1

    db.commit()
