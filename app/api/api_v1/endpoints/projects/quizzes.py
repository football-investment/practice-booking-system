"""
Project quiz system.

This module handles:
- Adding quizzes to projects
- Listing project quizzes
- Removing quizzes from projects
- Enrollment quiz information
- Project waitlist management
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_or_instructor_user
from .....models.user import User
from .....models.project import Project as ProjectModel, ProjectQuiz
from .....schemas.project import (
    ProjectQuiz as ProjectQuizSchema,
    ProjectQuizCreate,
    ProjectQuizWithDetails
)

router = APIRouter()


@router.post("/{project_id}/quizzes", response_model=ProjectQuizSchema)
def add_quiz_to_project(
    project_id: int,
    quiz_data: ProjectQuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Hozzáad egy quiz-t a projekthez (Admin/Instructor only)
    """
    # Verify project exists and instructor has access
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if instructor owns this project (unless admin)
    if current_user.role.value != 'admin' and project.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )
    
    # Verify quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_data.quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Create project-quiz connection
    project_quiz = ProjectQuiz(**quiz_data.model_dump())
    db.add(project_quiz)
    db.commit()
    db.refresh(project_quiz)
    
    return project_quiz


@router.get("/{project_id}/quizzes", response_model=List[ProjectQuizWithDetails])
def get_project_quizzes(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Lekéri a projekthez kapcsolódó quiz-eket
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_quizzes = db.query(ProjectQuiz).filter(
        ProjectQuiz.project_id == project_id,
        ProjectQuiz.is_active == True
    ).order_by(ProjectQuiz.order_index).all()
    
    # Convert to response format with quiz details
    result = []
    for pq in project_quizzes:
        quiz = db.query(Quiz).filter(Quiz.id == pq.quiz_id).first()
        milestone = None
        if pq.milestone_id:
            milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == pq.milestone_id).first()
        
        quiz_data = {
            "id": pq.id,
            "project_id": pq.project_id,
            "quiz_id": pq.quiz_id,
            "milestone_id": pq.milestone_id,
            "quiz_type": pq.quiz_type,
            "is_required": pq.is_required,
            "minimum_score": pq.minimum_score,
            "order_index": pq.order_index,
            "is_active": pq.is_active,
            "created_at": pq.created_at.isoformat(),
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "category": quiz.category.value if quiz.category else None,
                "difficulty": quiz.difficulty.value if quiz.difficulty else None,
                "time_limit_minutes": quiz.time_limit_minutes,
                "passing_score": quiz.passing_score,
                "xp_reward": quiz.xp_reward
            } if quiz else None,
            "milestone": {
                "id": milestone.id,
                "title": milestone.title,
                "description": milestone.description,
                "order_index": milestone.order_index,
                "required_sessions": milestone.required_sessions,
                "xp_reward": milestone.xp_reward,
                "deadline": milestone.deadline.isoformat() if milestone.deadline else None,
                "is_required": milestone.is_required,
                "project_id": milestone.project_id,
                "created_at": milestone.created_at.isoformat()
            } if milestone else None
        }
        result.append(quiz_data)
    
    return result


@router.delete("/{project_id}/quizzes/{quiz_connection_id}")
def remove_quiz_from_project(
    project_id: int,
    quiz_connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Eltávolít egy quiz-t a projektből
    """
    project_quiz = db.query(ProjectQuiz).filter(
        ProjectQuiz.id == quiz_connection_id,
        ProjectQuiz.project_id == project_id
    ).first()
    
    if not project_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz connection not found"
        )
    
    # Verify project ownership
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if current_user.role.value != 'admin' and project.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )
    
    db.delete(project_quiz)
    db.commit()
    
    return {"message": "Quiz removed from project successfully"}


@router.get("/{project_id}/enrollment-quiz")
def get_enrollment_quiz_info(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Lekéri a projekt enrollment quiz információit
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Find enrollment quiz for this project
    enrollment_quiz = db.query(ProjectQuiz).filter(
        ProjectQuiz.project_id == project_id,
        ProjectQuiz.quiz_type == "enrollment",
        ProjectQuiz.is_active == True
    ).first()
    
    if not enrollment_quiz:
        return {
            "has_enrollment_quiz": False,
            "quiz": None,
            "user_completed": False,
            "user_status": None
        }
    
    # Get quiz details
    quiz = db.query(Quiz).filter(Quiz.id == enrollment_quiz.quiz_id).first()
    
    # Check if user has already completed this quiz for this project
    user_enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()
    
    user_completed = user_enrollment_quiz is not None
    user_status = None
    
    if user_completed:
        # Get the quiz attempt to determine status
        attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == user_enrollment_quiz.quiz_attempt_id
        ).first()
        
        if attempt and attempt.score >= enrollment_quiz.minimum_score:
            user_status = "eligible" if user_enrollment_quiz.enrollment_priority <= project.max_participants else "waiting"
            if user_enrollment_quiz.enrollment_confirmed:
                user_status = "confirmed"
        else:
            user_status = "not_eligible"
    
    return {
        "has_enrollment_quiz": True,
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "time_limit_minutes": quiz.time_limit_minutes,
            "minimum_score": enrollment_quiz.minimum_score
        },
        "user_completed": user_completed,
        "user_status": user_status
    }


@router.get("/{project_id}/waitlist")
def get_project_waitlist(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get anonymized project waitlist/ranking for students (nicknames only)
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get all enrollment quiz results for this project, ordered by priority
    waitlist_data = db.query(ProjectEnrollmentQuiz).options(
        joinedload(ProjectEnrollmentQuiz.user),
        joinedload(ProjectEnrollmentQuiz.quiz_attempt)
    ).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).order_by(ProjectEnrollmentQuiz.enrollment_priority.asc()).all()
    
    if not waitlist_data:
        return {
            "project_id": project_id,
            "project_title": project.title,
            "max_participants": project.max_participants,
            "waitlist": [],
            "total_applicants": 0,
            "user_position": None
        }
    
    # Build anonymized waitlist with nicknames only
    waitlist_entries = []
    user_position = None
    
    for entry in waitlist_data:
        # OPTIMIZED: Use eager-loaded relationships (no queries in loop)
        user = entry.user
        if not user:
            continue

        # Get quiz attempt for score (already loaded via eager loading)
        attempt = entry.quiz_attempt

        if not attempt:
            continue
            
        # Determine status based on priority and confirmation
        if entry.enrollment_confirmed:
            status = "confirmed"
        elif entry.enrollment_priority <= project.max_participants:
            status = "eligible"
        else:
            status = "waiting"
        
        # Use nickname or fallback to "Anonymous" for privacy
        display_name = user.nickname if user.nickname else f"Diák #{entry.enrollment_priority}"
        
        waitlist_entry = {
            "position": entry.enrollment_priority,
            "display_name": display_name,
            "score_percentage": round(attempt.score, 1),
            "status": status,
            "confirmed": entry.enrollment_confirmed,
            "is_current_user": user.id == current_user.id
        }
        
        waitlist_entries.append(waitlist_entry)
        
        # Track current user's position
        if user.id == current_user.id:
            user_position = entry.enrollment_priority
    
    return {
        "project_id": project_id,
        "project_title": project.title,
        "max_participants": project.max_participants,
        "confirmed_count": len([e for e in waitlist_entries if e["confirmed"]]),
        "waitlist": waitlist_entries,
        "total_applicants": len(waitlist_entries),
        "user_position": user_position
    }
