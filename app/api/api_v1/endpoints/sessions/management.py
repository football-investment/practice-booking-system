"""
Session Management API Endpoints (PHASE 2 - P0)
==============================================

Instructor session management - start, stop, unlock quiz, evaluations.
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
from .....models.session import Session as SessionModel, SessionType
from .....models.quiz import QuizAttempt
from .....models.feedback import Feedback
from .....services.audit_service import AuditService
from .....models.audit_log import AuditAction


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SessionStartResponse(BaseModel):
    """Response from starting a session"""
    success: bool
    message: str
    session_id: int
    actual_start_time: datetime
    session_type: str


class SessionStopResponse(BaseModel):
    """Response from stopping a session"""
    success: bool
    message: str
    session_id: int
    actual_end_time: datetime
    duration_minutes: Optional[float] = None


class UnlockQuizResponse(BaseModel):
    """Response from unlocking quiz"""
    success: bool
    message: str
    session_id: int
    quiz_unlocked: bool


class EvaluateInstructorRequest(BaseModel):
    """Student evaluates instructor"""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback")


class EvaluateInstructorResponse(BaseModel):
    """Response from instructor evaluation"""
    success: bool
    message: str
    feedback_id: int
    rating: int


class EvaluateStudentRequest(BaseModel):
    """Instructor evaluates student"""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback")
    skills_demonstrated: Optional[str] = Field(None, description="Skills observed")


class EvaluateStudentResponse(BaseModel):
    """Response from student evaluation"""
    success: bool
    message: str
    feedback_id: int
    student_id: int
    rating: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/{session_id}/start", response_model=SessionStartResponse)
def start_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Start a session (Instructor only)

    **Business Logic** (from web route):
    - Records actual start time
    - Only for On-Site or Hybrid sessions
    - Instructor must own the session
    - Session must not be already started

    **Permissions:** INSTRUCTOR role required
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can start sessions"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify session type (On-Site or Hybrid only)
    if session.session_type not in [SessionType.on_site, SessionType.hybrid]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timer only available for On-Site and Hybrid sessions"
        )

    # Verify instructor owns this session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your session"
        )

    # Verify session not already started
    if session.actual_start_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already started"
        )

    # Start session
    session.actual_start_time = datetime.now(timezone.utc)
    session.session_status = "in_progress"

    db.commit()
    db.refresh(session)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SESSION_STARTED,
        user_id=current_user.id,
        resource_type="session",
        resource_id=session.id,
        details={"session_id": session.id, "start_time": session.actual_start_time.isoformat()}
    )

    return SessionStartResponse(
        success=True,
        message="Session started successfully",
        session_id=session.id,
        actual_start_time=session.actual_start_time,
        session_type=session.session_type.value
    )


@router.post("/{session_id}/stop", response_model=SessionStopResponse)
def stop_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Stop a session (Instructor only)

    **Business Logic** (from web route):
    - Records actual end time
    - Calculates duration
    - Only for sessions that have been started
    - Instructor must own the session

    **Permissions:** INSTRUCTOR role required
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can stop sessions"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify instructor owns this session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your session"
        )

    # Verify session has been started
    if session.actual_start_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has not been started yet"
        )

    # Verify session not already stopped
    if session.actual_end_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already stopped"
        )

    # Stop session
    session.actual_end_time = datetime.now(timezone.utc)
    session.session_status = "completed"

    # Calculate duration
    duration = (session.actual_end_time - session.actual_start_time).total_seconds() / 60

    db.commit()
    db.refresh(session)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SESSION_COMPLETED,
        user_id=current_user.id,
        resource_type="session",
        resource_id=session.id,
        details={
            "session_id": session.id,
            "end_time": session.actual_end_time.isoformat(),
            "duration_minutes": duration
        }
    )

    return SessionStopResponse(
        success=True,
        message="Session stopped successfully",
        session_id=session.id,
        actual_end_time=session.actual_end_time,
        duration_minutes=round(duration, 2)
    )


@router.post("/{session_id}/unlock-quiz", response_model=UnlockQuizResponse)
def unlock_quiz(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Unlock quiz for a session (Instructor only)

    **Business Logic** (from web route):
    - Allows students to access quiz
    - Instructor must own the session
    - Session must have a quiz assigned

    **Permissions:** INSTRUCTOR role required
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can unlock quizzes"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify instructor owns this session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your session"
        )

    # Verify session has a quiz
    if not session.quiz_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no quiz assigned"
        )

    # Unlock quiz
    session.quiz_unlocked = True

    db.commit()
    db.refresh(session)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.QUIZ_UNLOCKED,
        user_id=current_user.id,
        resource_type="session",
        resource_id=session.id,
        details={"session_id": session.id, "quiz_id": session.quiz_id}
    )

    return UnlockQuizResponse(
        success=True,
        message="Quiz unlocked successfully",
        session_id=session.id,
        quiz_unlocked=True
    )


@router.post("/{session_id}/evaluate-instructor", response_model=EvaluateInstructorResponse)
def evaluate_instructor(
    session_id: int,
    evaluation: EvaluateInstructorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Student evaluates instructor after session

    **Business Logic** (from web route):
    - Students rate instructor performance (1-5)
    - Optional feedback text
    - Student must be enrolled in session
    - Can only evaluate after session

    **Permissions:** STUDENT role required
    """
    # Verify student role
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can evaluate instructors"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Create feedback
    feedback = Feedback(
        session_id=session_id,
        user_id=current_user.id,
        instructor_rating=evaluation.rating,
        comment=evaluation.feedback_text or ""
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.INSTRUCTOR_EVALUATED,
        user_id=current_user.id,
        resource_type="feedback",
        resource_id=feedback.id,
        details={
            "session_id": session_id,
            "instructor_id": session.instructor_id,
            "rating": evaluation.rating
        }
    )

    return EvaluateInstructorResponse(
        success=True,
        message="Instructor evaluation submitted",
        feedback_id=feedback.id,
        rating=evaluation.rating
    )


@router.post("/{session_id}/evaluate-student/{student_id}", response_model=EvaluateStudentResponse)
def evaluate_student(
    session_id: int,
    student_id: int,
    evaluation: EvaluateStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Instructor evaluates student after session

    **Business Logic** (from web route):
    - Instructors rate student performance (1-5)
    - Optional feedback and skills observed
    - Instructor must own the session
    - Student must be enrolled in session

    **Permissions:** INSTRUCTOR role required
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can evaluate students"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify instructor owns this session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your session"
        )

    # Verify student exists
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.STUDENT
    ).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Create feedback
    feedback = Feedback(
        session_id=session_id,
        user_id=current_user.id,
        rating=evaluation.rating,
        session_quality=evaluation.rating,
        comment=evaluation.feedback_text or ""
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.STUDENT_EVALUATED,
        user_id=current_user.id,
        resource_type="feedback",
        resource_id=feedback.id,
        details={
            "session_id": session_id,
            "student_id": student_id,
            "rating": evaluation.rating
        }
    )

    return EvaluateStudentResponse(
        success=True,
        message="Student evaluation submitted",
        feedback_id=feedback.id,
        student_id=student_id,
        rating=evaluation.rating
    )
