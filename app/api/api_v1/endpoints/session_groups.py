"""
Session Group Assignment Endpoints

Dynamic group creation at session start.

Workflow:
1. HEAD_COACH starts session check-in
2. HEAD_COACH marks students as PRESENT
3. HEAD_COACH triggers auto-assign or manually creates groups
4. Groups visible to all instructors and students
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Session as SessionModel, UserRole
from app.services.session_group_service import SessionGroupService

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class GroupStudentResponse(BaseModel):
    """Student in a group"""
    student_id: int
    student_name: str

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    """Session group with students"""
    id: int
    session_id: int
    group_number: int
    instructor_id: int
    instructor_name: Optional[str] = None
    student_count: int
    students: List[GroupStudentResponse]

    class Config:
        from_attributes = True


class GroupSummaryResponse(BaseModel):
    """Summary of all groups in a session"""
    session_id: int
    total_students: int
    total_instructors: int
    groups: List[dict]


class AutoAssignRequest(BaseModel):
    """Request to auto-assign students to groups"""
    session_id: int


class MoveStudentRequest(BaseModel):
    """Request to move student between groups"""
    student_id: int
    from_group_id: int
    to_group_id: int


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/auto-assign", response_model=GroupSummaryResponse)
def auto_assign_groups(
    request: AutoAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-assign present students to groups

    Algorithm:
    - Gets all students marked PRESENT
    - Gets available instructors
    - Distributes students evenly

    Example:
    - 2 instructors, 6 students → 2 groups of 3
    - 2 instructors, 7 students → 1 group of 4, 1 group of 3

    Authorization: Head coach or instructor for this session
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found"
        )

    # Authorization: Must be instructor for this session or admin
    if current_user.role != UserRole.ADMIN:
        if session.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the session instructor can create groups"
            )

    # Auto-assign
    try:
        created_groups = SessionGroupService.auto_assign_groups(
            db,
            session_id=request.session_id,
            created_by_user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Return summary
    summary = SessionGroupService.get_group_summary(db, request.session_id)
    return GroupSummaryResponse(**summary)


@router.get("/{session_id}", response_model=GroupSummaryResponse)
def get_session_groups(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all groups for a session

    Returns group assignments with instructor and student details.
    Visible to all users (students see their group, instructors see all).
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    summary = SessionGroupService.get_group_summary(db, session_id)
    return GroupSummaryResponse(**summary)


@router.post("/move-student", status_code=status.HTTP_200_OK)
def move_student(
    request: MoveStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Move a student from one group to another

    Used for manual adjustments by head coach.

    Authorization: Head coach or admin
    """
    # Get session from group
    from app.models import SessionGroupAssignment
    from_group = db.query(SessionGroupAssignment).filter(
        SessionGroupAssignment.id == request.from_group_id
    ).first()

    if not from_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source group {request.from_group_id} not found"
        )

    session = from_group.session
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Authorization
    if current_user.role != UserRole.ADMIN:
        if session.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the session instructor can move students between groups"
            )

    # Move student
    success = SessionGroupService.move_student_to_group(
        db,
        student_id=request.student_id,
        from_group_id=request.from_group_id,
        to_group_id=request.to_group_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to move student. Student may not be in source group."
        )

    return {"message": "Student moved successfully"}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_groups(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all groups for a session (reset)

    Used if head coach wants to re-assign from scratch.

    Authorization: Head coach or admin
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    # Authorization
    if current_user.role != UserRole.ADMIN:
        if session.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the session instructor can delete groups"
            )

    SessionGroupService.delete_all_groups(db, session_id)
    return None
