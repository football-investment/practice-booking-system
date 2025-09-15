from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_or_instructor_user
from ....models.user import User
from ....models.session import Session as SessionModel
from ....models.booking import Booking, BookingStatus
from ....models.attendance import Attendance, AttendanceStatus
from ....schemas.attendance import (
    Attendance as AttendanceSchema, AttendanceCreate, AttendanceUpdate,
    AttendanceWithRelations, AttendanceList, AttendanceCheckIn
)

router = APIRouter()


@router.post("/", response_model=AttendanceSchema)
def create_attendance(
    attendance_data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Create attendance record (Admin/Instructor only)
    """
    # Check if booking exists and is confirmed
    booking = db.query(Booking).filter(Booking.id == attendance_data.booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only create attendance for confirmed bookings"
        )
    
    # Check if attendance already exists
    existing_attendance = db.query(Attendance).filter(Attendance.booking_id == attendance_data.booking_id).first()
    if existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance record already exists for this booking"
        )
    
    attendance = Attendance(
        **attendance_data.model_dump(),
        marked_by=current_user.id
    )
    
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    
    return attendance


@router.get("/", response_model=AttendanceList)
def list_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user),
    session_id: int = Query(...)
) -> Any:
    """
    List attendance for a session (Admin/Instructor only)
    """
    # Check if session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    attendances = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    
    # Convert to response schema
    attendance_responses = []
    for attendance in attendances:
        attendance_responses.append(AttendanceWithRelations(
            **attendance.__dict__,
            user=attendance.user,
            session=attendance.session,
            booking=attendance.booking,
            marker=attendance.marker
        ))
    
    return AttendanceList(
        attendances=attendance_responses,
        total=len(attendance_responses)
    )


@router.post("/{booking_id}/checkin", response_model=AttendanceSchema)
def checkin(
    booking_id: int,
    checkin_data: AttendanceCheckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check in to a session
    """
    # Check if booking exists and belongs to current user
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check in to your own bookings"
        )
    
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only check in to confirmed bookings"
        )
    
    # Check if session is active
    session = booking.session
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if current_time < session.date_start or current_time > session.date_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not currently active"
        )
    
    # Check if attendance record exists
    attendance = db.query(Attendance).filter(Attendance.booking_id == booking_id).first()
    if not attendance:
        # Create new attendance record
        attendance = Attendance(
            user_id=current_user.id,
            session_id=session.id,
            booking_id=booking_id,
            status=AttendanceStatus.PRESENT,
            check_in_time=current_time,
            notes=checkin_data.notes
        )
        db.add(attendance)
    else:
        # Update existing record
        attendance.check_in_time = current_time
        attendance.status = AttendanceStatus.PRESENT
        if checkin_data.notes:
            attendance.notes = checkin_data.notes
    
    db.commit()
    db.refresh(attendance)
    
    return attendance


@router.patch("/{attendance_id}", response_model=AttendanceSchema)
def update_attendance(
    attendance_id: int,
    attendance_update: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Update attendance record (Admin/Instructor only)
    """
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    # Update fields
    update_data = attendance_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attendance, field, value)
    
    attendance.marked_by = current_user.id
    
    db.commit()
    db.refresh(attendance)
    
    return attendance


@router.get("/instructor/overview")
def get_instructor_attendance_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get attendance overview for current instructor's sessions
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Import here to avoid circular imports
    from ....models.session import Session as SessionModel
    from ....models.booking import Booking
    
    # Get instructor's sessions with attendance stats
    query = db.query(SessionModel).filter(
        SessionModel.instructor_id == current_user.id
    ).order_by(SessionModel.date_start.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    sessions = query.offset(offset).limit(size).all()
    
    # Build response with attendance stats
    session_list = []
    for session in sessions:
        # Get attendance count
        attendance_count = db.query(func.count(Attendance.id)).filter(
            Attendance.session_id == session.id
        ).scalar() or 0
        
        # Get booking count
        booking_count = db.query(func.count(Booking.id)).filter(
            Booking.session_id == session.id
        ).scalar() or 0
        
        session_dict = {
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'date_start': session.date_start.isoformat(),
            'date_end': session.date_end.isoformat(),
            'location': session.location,
            'capacity': session.capacity,
            'level': session.level,
            'sport_type': session.sport_type,
            'current_bookings': booking_count,
            'attendance_count': attendance_count,
            'created_at': session.created_at.isoformat(),
        }
        session_list.append(session_dict)
    
    return {
        'sessions': session_list,
        'total': total,
        'page': page,
        'size': size
    }