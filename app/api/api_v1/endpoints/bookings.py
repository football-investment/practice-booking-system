from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime, timedelta, timezone

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_user, get_current_admin_or_instructor_user
from ....models.user import User
from ....models.session import Session as SessionModel
from ....models.booking import Booking, BookingStatus
from ....models.attendance import Attendance, AttendanceStatus
from ....models.semester import Semester
from ....schemas.booking import (
    Booking as BookingSchema, BookingCreate, BookingWithRelations,
    BookingList, BookingConfirm, BookingCancel
)
from ....config import settings

router = APIRouter()


def validate_payment_for_booking(current_user: User) -> None:
    """
    💰 NEW: Validate user has verified payment for session booking
    """
    # Skip payment verification for admins and instructors
    if current_user.role.value in ['admin', 'instructor']:
        print(f"💰 Payment verification skipped for {current_user.role.value}: {current_user.name}")
        return
    
    # Check if student has verified payment
    if not current_user.payment_verified:
        print(f"🚨 Payment verification failed: "
              f"Student {current_user.name} ({current_user.email}) "
              f"tried to book session without verified payment")
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment verification required. Please contact administration to verify your semester fee payment before booking sessions. "
                   "You cannot book sessions or enroll in projects until your payment has been confirmed by an administrator."
        )
    
    print(f"💰 Payment verification passed: {current_user.name} has verified payment")


@router.get("/", response_model=BookingList)
def get_all_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None),
    status: Optional[BookingStatus] = Query(None)
) -> Any:
    """Get all bookings (Admin only)"""
    query = db.query(Booking)
    
    # Apply filters
    if semester_id:
        query = query.join(SessionModel).filter(SessionModel.semester_id == semester_id)
    if status:
        query = query.filter(Booking.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    bookings = query.offset(offset).limit(size).all()
    
    # Convert to response schema
    booking_responses = []
    for booking in bookings:
        booking_responses.append(BookingWithRelations(
            **booking.__dict__,
            user=booking.user,
            session=booking.session
        ))
    
    return BookingList(
        bookings=booking_responses,
        total=total,
        page=page,
        size=size
    )


@router.post("/", response_model=BookingSchema)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create new booking
    """
    # 💰 NEW: Validate payment verification for booking
    validate_payment_for_booking(current_user)
    
    # Check if session exists
    session = db.query(SessionModel).filter(SessionModel.id == booking_data.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if user already has an ACTIVE booking for this session (exclude cancelled)
    existing_booking = db.query(Booking).filter(
        and_(
            Booking.user_id == current_user.id, 
            Booking.session_id == booking_data.session_id,
            Booking.status != BookingStatus.CANCELLED
        )
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active booking for this session (Status: {existing_booking.status})"
        )
    
    # Check if session is in the past (basic validation)
    current_time = datetime.now()
    session_start_naive = session.date_start.replace(tzinfo=None) if session.date_start.tzinfo else session.date_start
    
    if session_start_naive < current_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot book past sessions"
        )
    
    # Note: Booking deadline temporarily disabled for testing
    # TODO: Re-enable with proper timezone handling in production
    
    # Check capacity and determine status
    confirmed_count = db.query(func.count(Booking.id)).filter(
        and_(Booking.session_id == booking_data.session_id, Booking.status == BookingStatus.CONFIRMED)
    ).scalar() or 0
    
    if confirmed_count < session.capacity:
        booking_status = BookingStatus.CONFIRMED
        waitlist_position = None
    else:
        booking_status = BookingStatus.WAITLISTED
        waitlist_position = db.query(func.count(Booking.id)).filter(
            and_(Booking.session_id == booking_data.session_id, Booking.status == BookingStatus.WAITLISTED)
        ).scalar() + 1
    
    booking = Booking(
        user_id=current_user.id,
        session_id=booking_data.session_id,
        status=booking_status,
        waitlist_position=waitlist_position,
        notes=booking_data.notes
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return booking


@router.get("/me", response_model=BookingList)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None),
    status: Optional[BookingStatus] = Query(None)
) -> Any:
    """
    Get current user's bookings
    """
    query = db.query(Booking).filter(Booking.user_id == current_user.id)
    
    # Apply filters
    if semester_id:
        query = query.join(SessionModel).filter(SessionModel.semester_id == semester_id)
    if status:
        query = query.filter(Booking.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    bookings = query.offset(offset).limit(size).all()
    
    # Convert to response schema with attendance calculation
    booking_responses = []
    for booking in bookings:
        # Check if user attended this session
        attendance = db.query(Attendance).filter(
            and_(
                Attendance.user_id == current_user.id,
                Attendance.session_id == booking.session_id,
                Attendance.status == AttendanceStatus.PRESENT
            )
        ).first()
        
        attended = attendance is not None
        
        booking_responses.append(BookingWithRelations(
            **booking.__dict__,
            user=booking.user,
            session=booking.session,
            attended=attended
        ))
    
    return BookingList(
        bookings=booking_responses,
        total=total,
        page=page,
        size=size
    )


@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Cancel own booking and auto-promote from waitlist
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user owns the booking
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own bookings"
        )
    
    # Check if session has already started
    if datetime.now() > booking.session.date_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel booking for past sessions"
        )
    
    # Store original status for promotion logic
    original_status = booking.status
    session_id = booking.session_id
    
    # Cancel the booking
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.now()
    
    promoted_user = None
    
    # AUTO-PROMOTION LOGIC: Only if cancelled booking was CONFIRMED
    if original_status == BookingStatus.CONFIRMED:
        # Find next person on waitlist (lowest position number)
        next_waitlisted = db.query(Booking).filter(
            and_(
                Booking.session_id == session_id,
                Booking.status == BookingStatus.WAITLISTED
            )
        ).order_by(Booking.waitlist_position.asc()).first()
        
        if next_waitlisted:
            # Promote from waitlist to confirmed
            next_waitlisted.status = BookingStatus.CONFIRMED
            promoted_user_id = next_waitlisted.user_id
            promoted_user = db.query(User).filter(User.id == promoted_user_id).first()
            
            # Clear their waitlist position
            next_waitlisted.waitlist_position = None
            
            # Update all remaining waitlist positions (move everyone up)
            remaining_waitlist = db.query(Booking).filter(
                and_(
                    Booking.session_id == session_id,
                    Booking.status == BookingStatus.WAITLISTED,
                    Booking.id != next_waitlisted.id
                )
            ).all()
            
            for booking_item in remaining_waitlist:
                if booking_item.waitlist_position and booking_item.waitlist_position > 0:
                    booking_item.waitlist_position -= 1
    
    db.commit()
    
    # Return enhanced response with promotion info
    response = {
        "message": "Booking cancelled successfully",
        "cancelled_booking_id": booking_id,
        "session_id": session_id
    }
    
    if promoted_user:
        response["promotion"] = {
            "promoted_user_name": promoted_user.name,
            "promoted_user_email": promoted_user.email,
            "message": f"{promoted_user.name} has been promoted from waitlist to confirmed"
        }
    
    return response


@router.get("/my-stats")
def get_my_booking_statistics(
    semester_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user's booking statistics"""
    
    # Base query for user's bookings
    bookings_query = db.query(Booking).filter(Booking.user_id == current_user.id)
    
    # Filter by semester if provided
    if semester_id:
        bookings_query = bookings_query.join(SessionModel).filter(
            SessionModel.semester_id == semester_id
        )
    
    # Basic statistics
    total_bookings = bookings_query.count()
    confirmed_bookings = bookings_query.filter(Booking.status == BookingStatus.CONFIRMED).count()
    cancelled_bookings = bookings_query.filter(Booking.status == BookingStatus.CANCELLED).count()
    waitlisted_bookings = bookings_query.filter(Booking.status == BookingStatus.WAITLISTED).count()
    
    # Attendance statistics using Attendance model
    attended_sessions = db.query(Attendance).filter(
        and_(
            Attendance.user_id == current_user.id,
            Attendance.status == AttendanceStatus.PRESENT
        )
    )
    
    # Filter attendance by semester if provided
    if semester_id:
        attended_sessions = attended_sessions.join(SessionModel).filter(
            SessionModel.semester_id == semester_id
        )
    
    attended_count = attended_sessions.count()
    
    # Calculate rates
    attendance_rate = round((attended_count / max(confirmed_bookings, 1)) * 100, 1)
    booking_success_rate = round((confirmed_bookings / max(total_bookings, 1)) * 100, 1)
    
    # Current semester info
    current_semester = None
    if semester_id:
        current_semester = db.query(Semester).filter(Semester.id == semester_id).first()
    else:
        # Get active semester
        current_date = datetime.now().date()
        current_semester = db.query(Semester).filter(
            and_(
                Semester.start_date <= current_date,
                Semester.end_date >= current_date
            )
        ).first()
    
    # Calculate semester progress if we have a current semester
    semester_progress = None
    if current_semester:
        total_days = (current_semester.end_date - current_semester.start_date).days
        elapsed_days = (current_date - current_semester.start_date).days
        semester_progress = max(0, min(100, round((elapsed_days / max(total_days, 1)) * 100, 1)))
    
    return {
        "user_id": current_user.id,
        "user_name": current_user.name,
        "statistics": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "waitlisted_bookings": waitlisted_bookings,
            "attended_sessions": attended_count,
            "attendance_rate": attendance_rate,
            "booking_success_rate": booking_success_rate
        },
        "current_semester": {
            "id": current_semester.id if current_semester else None,
            "name": current_semester.name if current_semester else None,
            "progress_percentage": semester_progress
        } if current_semester else None,
        "generated_at": datetime.now().isoformat()
    }


@router.post("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Confirm booking (Admin only)
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    booking.status = BookingStatus.CONFIRMED
    db.commit()
    
    return {"message": "Booking confirmed successfully"}


@router.post("/{booking_id}/cancel")
def admin_cancel_booking(
    booking_id: int,
    cancel_data: BookingCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Cancel booking (Admin only) and auto-promote from waitlist
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Store original status for promotion logic
    original_status = booking.status
    session_id = booking.session_id
    
    # Cancel the booking
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.now()
    booking.notes = cancel_data.reason
    
    promoted_user = None
    
    # AUTO-PROMOTION LOGIC: Only if cancelled booking was CONFIRMED
    if original_status == BookingStatus.CONFIRMED:
        # Find next person on waitlist (lowest position number)
        next_waitlisted = db.query(Booking).filter(
            and_(
                Booking.session_id == session_id,
                Booking.status == BookingStatus.WAITLISTED
            )
        ).order_by(Booking.waitlist_position.asc()).first()
        
        if next_waitlisted:
            # Promote from waitlist to confirmed
            next_waitlisted.status = BookingStatus.CONFIRMED
            promoted_user_id = next_waitlisted.user_id
            promoted_user = db.query(User).filter(User.id == promoted_user_id).first()
            
            # Clear their waitlist position
            next_waitlisted.waitlist_position = None
            
            # Update all remaining waitlist positions (move everyone up)
            remaining_waitlist = db.query(Booking).filter(
                and_(
                    Booking.session_id == session_id,
                    Booking.status == BookingStatus.WAITLISTED,
                    Booking.id != next_waitlisted.id
                )
            ).all()
            
            for booking_item in remaining_waitlist:
                if booking_item.waitlist_position and booking_item.waitlist_position > 0:
                    booking_item.waitlist_position -= 1
    
    db.commit()
    
    # Return enhanced response with promotion info
    response = {
        "message": "Booking cancelled by admin",
        "cancelled_booking_id": booking_id,
        "session_id": session_id
    }
    
    if promoted_user:
        response["promotion"] = {
            "promoted_user_name": promoted_user.name,
            "promoted_user_email": promoted_user.email,
            "message": f"{promoted_user.name} has been promoted from waitlist to confirmed"
        }
    
    return response


@router.get("/my-stats")
def get_my_booking_statistics(
    semester_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user's booking statistics"""
    
    # Base query for user's bookings
    bookings_query = db.query(Booking).filter(Booking.user_id == current_user.id)
    
    # Filter by semester if provided
    if semester_id:
        bookings_query = bookings_query.join(SessionModel).filter(
            SessionModel.semester_id == semester_id
        )
    
    # Basic statistics
    total_bookings = bookings_query.count()
    confirmed_bookings = bookings_query.filter(Booking.status == BookingStatus.CONFIRMED).count()
    cancelled_bookings = bookings_query.filter(Booking.status == BookingStatus.CANCELLED).count()
    waitlisted_bookings = bookings_query.filter(Booking.status == BookingStatus.WAITLISTED).count()
    
    # Attendance statistics using Attendance model
    attended_sessions = db.query(Attendance).filter(
        and_(
            Attendance.user_id == current_user.id,
            Attendance.status == AttendanceStatus.PRESENT
        )
    )
    
    # Filter attendance by semester if provided
    if semester_id:
        attended_sessions = attended_sessions.join(SessionModel).filter(
            SessionModel.semester_id == semester_id
        )
    
    attended_count = attended_sessions.count()
    
    # Calculate rates
    attendance_rate = round((attended_count / max(confirmed_bookings, 1)) * 100, 1)
    booking_success_rate = round((confirmed_bookings / max(total_bookings, 1)) * 100, 1)
    
    # Current semester info
    current_semester = None
    if semester_id:
        current_semester = db.query(Semester).filter(Semester.id == semester_id).first()
    else:
        # Get active semester
        current_date = datetime.now().date()
        current_semester = db.query(Semester).filter(
            and_(
                Semester.start_date <= current_date,
                Semester.end_date >= current_date
            )
        ).first()
    
    # Calculate semester progress if we have a current semester
    semester_progress = None
    if current_semester:
        total_days = (current_semester.end_date - current_semester.start_date).days
        elapsed_days = (current_date - current_semester.start_date).days
        semester_progress = max(0, min(100, round((elapsed_days / max(total_days, 1)) * 100, 1)))
    
    return {
        "user_id": current_user.id,
        "user_name": current_user.name,
        "statistics": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "waitlisted_bookings": waitlisted_bookings,
            "attended_sessions": attended_count,
            "attendance_rate": attendance_rate,
            "booking_success_rate": booking_success_rate
        },
        "current_semester": {
            "id": current_semester.id if current_semester else None,
            "name": current_semester.name if current_semester else None,
            "progress_percentage": semester_progress
        } if current_semester else None,
        "generated_at": datetime.now().isoformat()
    }

@router.patch("/{booking_id}/attendance", response_model=BookingSchema)
def update_booking_attendance(
    booking_id: int,
    attendance_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """Update booking attendance status (Admin/Instructor only)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Validate attendance status
    valid_statuses = ['present', 'absent', 'late', 'excused']
    attendance_status = attendance_data.get("status")
    if attendance_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid attendance status. Must be one of: {valid_statuses}"
        )
    
    # Update or create attendance record
    if booking.attendance:
        booking.attendance.status = AttendanceStatus(attendance_status)
        booking.attendance.notes = attendance_data.get("notes", booking.attendance.notes)
        booking.attendance.marked_by = current_user.id
    else:
        attendance = Attendance(
            user_id=booking.user_id,
            session_id=booking.session_id,
            booking_id=booking.id,
            status=AttendanceStatus(attendance_status),
            notes=attendance_data.get("notes"),
            marked_by=current_user.id
        )
        db.add(attendance)
    
    # Sync the booking's attended_status field
    booking.update_attendance_status()
    
    db.commit()
    db.refresh(booking)
    
    return booking
