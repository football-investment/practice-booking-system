from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_or_instructor_user
from ....models.user import User
from ....models.session import Session as SessionTypel
from ....models.feedback import Feedback
from ....models.booking import Booking, BookingStatus
from ....schemas.feedback import (
    Feedback as FeedbackSchema, FeedbackCreate, FeedbackUpdate,
    FeedbackWithRelations, FeedbackList, FeedbackSummary
)

router = APIRouter()


@router.get("/", response_model=FeedbackList)
def get_all_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    session_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None)
) -> Any:
    """Get all feedback (Admin/Instructor only)"""
    query = db.query(Feedback)
    
    # Apply filters
    if session_id:
        query = query.filter(Feedback.session_id == session_id)
    if user_id:
        query = query.filter(Feedback.user_id == user_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    feedback_items = query.offset(offset).limit(size).all()
    
    # Convert to response schema
    feedback_responses = []
    for feedback in feedback_items:
        feedback_responses.append(FeedbackWithRelations(
            **feedback.__dict__,
            user=feedback.user,
            session=feedback.session
        ))
    
    return FeedbackList(
        feedbacks=feedback_responses,
        total=total,
        page=page,
        size=size
    )


@router.post("/", response_model=FeedbackSchema)
def create_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create feedback for a session

    🔒 RULE #4: Feedback can only be submitted within 24 hours after session ends
    """
    # Check if session exists
    session = db.query(SessionTypel).filter(SessionTypel.id == feedback_data.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # 🔒 RULE #4: Validate 24-hour feedback window
    from datetime import datetime, timedelta, timezone
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    session_end_naive = session.date_end.replace(tzinfo=None) if session.date_end.tzinfo else session.date_end

    # Feedback window: session end → session end + 24h
    feedback_window_end = session_end_naive + timedelta(hours=24)

    if current_time < session_end_naive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide feedback before session ends"
        )

    if current_time > feedback_window_end:
        hours_since_session = (current_time - session_end_naive).total_seconds() / 3600
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feedback window closed. You can only provide feedback within 24 hours after session ends. "
                   f"Session ended {hours_since_session:.1f} hours ago."
        )

    # Check if user has a confirmed booking for this session
    booking = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.session_id == feedback_data.session_id,
        Booking.status == BookingStatus.CONFIRMED
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only provide feedback for sessions you have attended"
        )
    
    # Check if feedback already exists
    existing_feedback = db.query(Feedback).filter(
        Feedback.user_id == current_user.id,
        Feedback.session_id == feedback_data.session_id
    ).first()
    
    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already provided feedback for this session"
        )
    
    feedback = Feedback(
        user_id=current_user.id,
        **feedback_data.model_dump()
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback


@router.get("/me", response_model=FeedbackList)
def get_my_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None)
) -> Any:
    """
    Get current user's feedback
    """
    query = db.query(Feedback).filter(Feedback.user_id == current_user.id)
    
    # Apply filters
    if semester_id:
        query = query.join(SessionTypel).filter(SessionTypel.semester_id == semester_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    feedbacks = query.offset(offset).limit(size).all()
    
    # Convert to response schema
    feedback_responses = []
    for feedback in feedbacks:
        feedback_responses.append(FeedbackWithRelations(
            **feedback.__dict__,
            user=feedback.user if not feedback.is_anonymous else None,
            session=feedback.session
        ))
    
    return FeedbackList(
        feedbacks=feedback_responses,
        total=total,
        page=page,
        size=size
    )


@router.patch("/{feedback_id}", response_model=FeedbackSchema)
def update_feedback(
    feedback_id: int,
    feedback_update: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update own feedback
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Check if user owns the feedback
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own feedback"
        )
    
    # Update fields
    update_data = feedback_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feedback, field, value)
    
    db.commit()
    db.refresh(feedback)
    
    return feedback


@router.delete("/{feedback_id}")
def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete own feedback
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Check if user owns the feedback
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own feedback"
        )
    
    db.delete(feedback)
    db.commit()
    
    return {"message": "Feedback deleted successfully"}


@router.get("/sessions/{session_id}", response_model=FeedbackList)
def get_session_feedback(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get feedback for a session (Admin/Instructor only)
    """
    # Check if session exists
    session = db.query(SessionTypel).filter(SessionTypel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    query = db.query(Feedback).filter(Feedback.session_id == session_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    feedbacks = query.offset(offset).limit(size).all()
    
    # Convert to response schema
    feedback_responses = []
    for feedback in feedbacks:
        feedback_responses.append(FeedbackWithRelations(
            **feedback.__dict__,
            user=feedback.user if not feedback.is_anonymous else None,
            session=feedback.session
        ))
    
    return FeedbackList(
        feedbacks=feedback_responses,
        total=total,
        page=page,
        size=size
    )


@router.get("/sessions/{session_id}/summary", response_model=FeedbackSummary)
def get_session_feedback_summary(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Get feedback summary for a session (Admin/Instructor only)
    """
    # Check if session exists
    session = db.query(SessionTypel).filter(SessionTypel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Calculate statistics
    feedbacks = db.query(Feedback).filter(Feedback.session_id == session_id).all()
    
    if not feedbacks:
        return FeedbackSummary(
            session_id=session_id,
            average_rating=0.0,
            total_feedback=0,
            rating_distribution={},
            recent_comments=[]
        )
    
    # Calculate average rating
    average_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
    
    # Calculate rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        count = len([f for f in feedbacks if int(f.rating) == i])
        rating_distribution[str(i)] = count
    
    # Get recent comments (non-anonymous, last 5)
    recent_comments = [
        f.comment for f in feedbacks 
        if f.comment and not f.is_anonymous
    ][-5:]
    
    return FeedbackSummary(
        session_id=session_id,
        average_rating=round(average_rating, 2),
        total_feedback=len(feedbacks),
        rating_distribution=rating_distribution,
        recent_comments=recent_comments
    )


@router.get("/instructor/my")
def get_instructor_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get feedback for current instructor's sessions
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Get feedback from instructor's sessions
    query = db.query(Feedback).join(
        SessionTypel, Feedback.session_id == SessionTypel.id
    ).filter(
        SessionTypel.instructor_id == current_user.id
    ).order_by(Feedback.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    feedbacks = query.offset(offset).limit(size).all()
    
    # Build response with session and user info
    feedback_list = []
    for feedback in feedbacks:
        feedback_dict = {
            'id': feedback.id,
            'session_id': feedback.session_id,
            'session': {
                'id': feedback.session.id,
                'title': feedback.session.title,
                'date_start': feedback.session.date_start.isoformat()
            } if feedback.session else None,
            'user_id': feedback.user_id if not feedback.is_anonymous else None,
            'user': {
                'id': feedback.user.id,
                'name': feedback.user.name
            } if feedback.user and not feedback.is_anonymous else None,
            'rating': feedback.rating,
            'comment': feedback.comment,
            'is_anonymous': feedback.is_anonymous,
            'created_at': feedback.created_at.isoformat()
        }
        feedback_list.append(feedback_dict)
    
    return {
        'feedback': feedback_list,
        'total': total,
        'page': page,
        'size': size
    }