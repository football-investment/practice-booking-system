from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_user
from ....models.user import User
from ....models.semester import Semester
from ....models.group import Group
from ....models.session import Session as SessionModel
from ....models.booking import Booking
from ....schemas.semester import (
    Semester as SemesterSchema, SemesterCreate, SemesterUpdate,
    SemesterWithStats, SemesterList
)

router = APIRouter()


@router.post("/", response_model=SemesterSchema)
def create_semester(
    semester_data: SemesterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Create new semester (Admin only)
    """
    # Check if semester code already exists
    existing_semester = db.query(Semester).filter(Semester.code == semester_data.code).first()
    if existing_semester:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Semester with this code already exists"
        )
    
    semester = Semester(**semester_data.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    
    return semester


@router.get("/", response_model=SemesterList)
def list_semesters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List all active semesters with statistics
    """
    current_date = datetime.now().date()
    semesters = db.query(Semester).filter(
        and_(
            Semester.is_active == True,
            Semester.end_date >= current_date
        )
    ).order_by(Semester.start_date.desc()).all()
    
    semester_stats = []
    for semester in semesters:
        # Calculate statistics
        total_groups = db.query(func.count(Group.id)).filter(Group.semester_id == semester.id).scalar() or 0
        total_sessions = db.query(func.count(SessionModel.id)).filter(SessionModel.semester_id == semester.id).scalar() or 0
        total_bookings = db.query(func.count(Booking.id)).join(SessionModel).filter(SessionModel.semester_id == semester.id).scalar() or 0
        
        # Count active users (users with bookings in this semester)
        active_users = db.query(func.count(func.distinct(Booking.user_id))).join(SessionModel).filter(SessionModel.semester_id == semester.id).scalar() or 0
        
        semester_stats.append(SemesterWithStats(
            **semester.__dict__,
            total_groups=total_groups,
            total_sessions=total_sessions,
            total_bookings=total_bookings,
            active_users=active_users
        ))
    
    return SemesterList(
        semesters=semester_stats,
        total=len(semester_stats)
    )


@router.get("/active", response_model=SemesterSchema)
def get_active_semester(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get currently active semester"""
    current_date = datetime.now().date()
    
    active_semester = db.query(Semester).filter(
        and_(
            Semester.start_date <= current_date,
            Semester.end_date >= current_date,
            Semester.is_active == True
        )
    ).first()
    
    if not active_semester:
        raise HTTPException(
            status_code=404,
            detail="No active semester found"
        )
    
    return active_semester


@router.get("/{semester_id}", response_model=SemesterWithStats)
def get_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get semester by ID with statistics
    """
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Calculate statistics
    total_groups = db.query(func.count(Group.id)).filter(Group.semester_id == semester.id).scalar() or 0
    total_sessions = db.query(func.count(SessionModel.id)).filter(SessionModel.semester_id == semester.id).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).join(SessionModel).filter(SessionModel.semester_id == semester.id).scalar() or 0
    active_users = db.query(func.count(func.distinct(Booking.user_id))).join(SessionModel).filter(SessionModel.semester_id == semester.id).scalar() or 0
    
    return SemesterWithStats(
        **semester.__dict__,
        total_groups=total_groups,
        total_sessions=total_sessions,
        total_bookings=total_bookings,
        active_users=active_users
    )


@router.patch("/{semester_id}", response_model=SemesterSchema)
def update_semester(
    semester_id: int,
    semester_update: SemesterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Update semester (Admin only)
    """
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Check code uniqueness if code is being updated
    if semester_update.code and semester_update.code != semester.code:
        existing_semester = db.query(Semester).filter(Semester.code == semester_update.code).first()
        if existing_semester:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Semester with this code already exists"
            )
    
    # Update fields
    update_data = semester_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(semester, field, value)
    
    db.commit()
    db.refresh(semester)
    
    return semester


@router.delete("/{semester_id}")
def delete_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Delete semester (Admin only)
    """
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Check if there are any sessions in this semester
    session_count = db.query(func.count(SessionModel.id)).filter(SessionModel.semester_id == semester_id).scalar()
    if session_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete semester with existing sessions"
        )
    
    db.delete(semester)
    db.commit()
    
    return {"message": "Semester deleted successfully"}