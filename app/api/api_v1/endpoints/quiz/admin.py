"""
Admin quiz management
Create, manage, and view quiz statistics
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....schemas.quiz import (
    QuizCreate, QuizResponse, QuizListItem, QuizStatistics
)
from .....services.quiz_service import QuizService
from .helpers import get_quiz_service

router = APIRouter()

@router.post("/", response_model=QuizResponse)
def create_quiz(
    quiz_data: QuizCreate,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Create a new quiz (instructors/admins only)"""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can create quizzes"
        )
    
    quiz = quiz_service.create_quiz(quiz_data)
    return quiz

@router.get("/admin/{quiz_id}", response_model=QuizResponse)
def get_quiz_admin(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get quiz with all details including correct answers (admin view)"""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can view quiz details"
        )
    
    quiz = quiz_service.get_quiz_by_id(quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return quiz

@router.get("/admin/all", response_model=List[QuizListItem])
def get_all_quizzes_admin(
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
    db: Session = Depends(get_db)
):
    """Get all quizzes for admin/instructor management"""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can manage quizzes"
        )
    
    from app.models.quiz import Quiz
    quizzes = db.query(Quiz).order_by(Quiz.category, Quiz.title).all()
    
    return [
        QuizListItem(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            category=quiz.category,
            difficulty=quiz.difficulty,
            time_limit_minutes=quiz.time_limit_minutes,
            xp_reward=quiz.xp_reward,
            question_count=len(quiz.questions),
            is_active=quiz.is_active,
            created_at=quiz.created_at
        )
        for quiz in quizzes
    ]

@router.get("/statistics/{quiz_id}", response_model=QuizStatistics)
def get_quiz_statistics(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get statistics for a specific quiz"""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can view quiz statistics"
        )
    
    return quiz_service.get_quiz_statistics(quiz_id)

@router.get("/leaderboard/{quiz_id}")
def get_quiz_leaderboard(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get leaderboard for a specific quiz"""
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can view leaderboards"
        )
    
    return quiz_service.get_quiz_leaderboard(quiz_id)