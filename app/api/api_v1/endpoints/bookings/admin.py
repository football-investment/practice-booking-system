"""
Admin booking operations
Get all bookings, confirm, cancel, and update attendance
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional

from .....database import get_db
from .....dependencies import get_current_admin_user, get_current_admin_or_instructor_user
from .....models.user import User
from .....models.session import Session as SessionTypel
from .....models.booking import Booking, BookingStatus
from .....models.attendance import Attendance, AttendanceStatus
from .....schemas.booking import (
    Booking as BookingSchema, BookingWithRelations,
    BookingList, BookingCancel
)
from .helpers import auto_promote_from_waitlist

router = APIRouter()


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
        query = query.join(SessionTypel).filter(SessionTypel.semester_id == semester_id)
    if status:
        query = query.filter(Booking.status == status)

    # Get total count
    total = query.count()

    # OPTIMIZED: Eager load relationships to avoid N+1 query pattern
    query = query.options(
        joinedload(Booking.user),
        joinedload(Booking.session)
    )

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
        promotion_result = auto_promote_from_waitlist(db, session_id)
        if promotion_result:
            promoted_user, _ = promotion_result

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
