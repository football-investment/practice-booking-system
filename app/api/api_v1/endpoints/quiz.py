from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....database import get_db
from ....dependencies import get_current_user
from ....models.user import User, UserRole
from ....models.quiz import QuizCategory, QuizDifficulty
from ....services.quiz_service import QuizService
from ....services.competency_service import CompetencyService
from ....services.adaptive_learning_service import AdaptiveLearningService
from ....schemas.quiz import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListItem, QuizPublic,
    QuizAttemptStart, QuizAttemptSubmit, QuizAttemptResponse, QuizAttemptSummary,
    UserQuizStatistics, QuizStatistics, QuizDashboardOverview, QuizCategoryProgress
)

router = APIRouter()

def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(db)

# Public quiz endpoints (for students)

@router.get("/available", response_model=List[QuizListItem])
def get_available_quizzes(
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get all quizzes available for the current user (not yet completed)"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access quizzes"
        )
    
    quizzes = quiz_service.get_available_quizzes(current_user.id)
    
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

@router.get("/category/{category}", response_model=List[QuizListItem])
def get_quizzes_by_category(
    category: QuizCategory,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get all quizzes in a specific category"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access quizzes"
        )
    
    quizzes = quiz_service.get_quizzes_by_category(category)
    
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

@router.get("/{quiz_id}", response_model=QuizPublic)
def get_quiz_for_taking(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get quiz details for taking (without correct answers)"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can take quizzes"
        )
    
    # Check if quiz is already completed
    if quiz_service.is_quiz_completed_by_user(current_user.id, quiz_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz already completed"
        )
    
    quiz = quiz_service.get_quiz_by_id(quiz_id)
    if not quiz or not quiz.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found or inactive"
        )
    
    return quiz

@router.post("/start", response_model=QuizAttemptResponse)
def start_quiz_attempt(
    attempt_data: QuizAttemptStart,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Start a new quiz attempt"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can take quizzes"
        )
    
    try:
        attempt = quiz_service.start_quiz_attempt(current_user.id, attempt_data.quiz_id)
        return attempt
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/submit", response_model=QuizAttemptResponse)
def submit_quiz_attempt(
    submission: QuizAttemptSubmit,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
    db: Session = Depends(get_db)
):
    """Submit quiz attempt with answers"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can take quizzes"
        )

    try:
        # Submit quiz and get results
        attempt = quiz_service.submit_quiz_attempt(current_user.id, submission)

        # ==========================================
        # 🆕 HOOK 1: AUTOMATIC COMPETENCY ASSESSMENT
        # ==========================================
        # Use SEPARATE session to avoid transaction conflicts
        from ....database import SessionLocal
        hook_db = None

        try:
            # Create new session for hooks
            hook_db = SessionLocal()

            # Initialize services with separate session
            comp_service = CompetencyService(hook_db)
            adapt_service = AdaptiveLearningService(hook_db)

            # Get quiz details for competency assessment
            quiz = quiz_service.get_quiz_by_id(attempt.quiz_id)

            # Assess competency from quiz (automatic based on quiz category/metadata)
            if quiz and attempt.score is not None:
                comp_service.assess_from_quiz(
                    user_id=current_user.id,
                    quiz_id=quiz.id,
                    quiz_attempt_id=attempt.id,
                    score=float(attempt.score)
                )

            # Update adaptive learning profile
            adapt_service.update_profile_metrics(current_user.id)

            # Generate new recommendations if score is low (struggling student)
            if attempt.score and attempt.score < 70:
                adapt_service.generate_recommendations(
                    user_id=current_user.id,
                    refresh=True
                )

            # Commit hook transaction
            hook_db.commit()

        except Exception as e:
            # Log error but don't fail quiz submission
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in post-quiz hooks for user {current_user.id}: {e}")
            if hook_db:
                hook_db.rollback()
            # Continue with quiz result response

        finally:
            # Always close the hook session
            if hook_db:
                hook_db.close()

        # ==========================================
        # 🏆 GAMIFICATION: Check for achievement unlocks
        # ==========================================
        from ....services.gamification import GamificationService
        gamification_service = GamificationService(db)
        try:
            # Check for quiz completion achievement
            unlocked = gamification_service.check_and_unlock_achievements(
                user_id=current_user.id,
                trigger_action="complete_quiz"
            )

            # Check for perfect score achievement if score is 100%
            if attempt.score and attempt.score >= 100:
                perfect_score_unlocked = gamification_service.check_and_unlock_achievements(
                    user_id=current_user.id,
                    trigger_action="quiz_perfect_score",
                    context={"score": attempt.score}
                )
                unlocked.extend(perfect_score_unlocked)

            if unlocked:
                print(f"🎉 Unlocked {len(unlocked)} achievement(s) for user {current_user.id}")
        except Exception as e:
            # Don't fail quiz submission if achievement check fails
            print(f"⚠️  Achievement check failed: {e}")

        return attempt
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/attempts/my", response_model=List[QuizAttemptSummary])
def get_my_quiz_attempts(
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get current user's quiz attempts"""
    attempts = quiz_service.get_user_quiz_attempts(current_user.id)
    
    return [
        QuizAttemptSummary(
            id=attempt.id,
            quiz_title=quiz_service.get_quiz_by_id(attempt.quiz_id).title,
            quiz_category=quiz_service.get_quiz_by_id(attempt.quiz_id).category,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            score=attempt.score,
            passed=attempt.passed,
            xp_awarded=attempt.xp_awarded,
            time_spent_minutes=attempt.time_spent_minutes
        )
        for attempt in attempts
    ]

@router.get("/statistics/my", response_model=UserQuizStatistics)
def get_my_quiz_statistics(
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get current user's quiz statistics"""
    return quiz_service.get_user_quiz_statistics(current_user.id)

@router.get("/dashboard/overview", response_model=QuizDashboardOverview)
def get_quiz_dashboard_overview(
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """Get quiz dashboard overview for student"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access quiz dashboard"
        )
    
    available_quizzes = quiz_service.get_available_quizzes(current_user.id)
    attempts = quiz_service.get_user_quiz_attempts(current_user.id)
    stats = quiz_service.get_user_quiz_statistics(current_user.id)
    
    completed_quizzes = len([a for a in attempts if a.completed_at])
    total_xp = sum([a.xp_awarded for a in attempts])
    
    recent_attempts = [
        QuizAttemptSummary(
            id=attempt.id,
            quiz_title=quiz_service.get_quiz_by_id(attempt.quiz_id).title,
            quiz_category=quiz_service.get_quiz_by_id(attempt.quiz_id).category,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            score=attempt.score,
            passed=attempt.passed,
            xp_awarded=attempt.xp_awarded,
            time_spent_minutes=attempt.time_spent_minutes
        )
        for attempt in attempts[:5]  # Last 5 attempts
    ]
    
    return QuizDashboardOverview(
        available_quizzes=len(available_quizzes),
        completed_quizzes=completed_quizzes,
        total_xp_from_quizzes=total_xp,
        best_category=stats.favorite_category,
        recent_attempts=recent_attempts
    )

# Admin/Instructor endpoints

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