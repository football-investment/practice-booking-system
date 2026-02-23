"""
Session Check-In Endpoint

Instructor marks session as STARTED (pre-session check-in).
Performance target: p95 < 200ms
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel

router = APIRouter()


class SessionCheckInResponse(BaseModel):
    """Session check-in response schema"""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    session_id: int
    session_status: str
    checked_in_at: datetime


@router.post("/{session_id}/check-in", response_model=SessionCheckInResponse)
def check_in_to_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Instructor checks in to session (marks PENDING → STARTED).

    **Authorization:** Instructor only, must be assigned to session
    **Performance Target:** p95 < 200ms

    **Business Logic:**
    1. Verify session exists
    2. Verify current user is assigned instructor
    3. Verify session status is 'scheduled' or 'pending'
    4. Update session status to 'in_progress'

    **Returns:**
    - Success status
    - Session ID
    - Updated session status ('in_progress')
    - Check-in timestamp

    **Raises:**
    - 403: User is not an instructor OR not assigned to session
    - 404: Session not found
    - 400: Session already in_progress or completed
    """
    # 1. Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can check in to sessions"
        )

    # 2. Fetch session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    # 3. Verify instructor is assigned to session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not assigned to session {session_id}"
        )

    # 4. Verify session status allows check-in
    if session.session_status not in ['scheduled', 'pending', None]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session already {session.session_status}, cannot check in"
        )

    # 5. Update session status to in_progress
    session.session_status = 'in_progress'
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return SessionCheckInResponse(
        success=True,
        message="Checked in to session successfully",
        session_id=session.id,
        session_status=session.session_status,
        checked_in_at=datetime.utcnow()
    )
