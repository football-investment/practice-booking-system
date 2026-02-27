"""
Student booking operations
Create, view, cancel bookings and view statistics
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.session import Session as SessionTypel
from .....models.booking import Booking, BookingStatus
from .....models.attendance import Attendance, AttendanceStatus
from .....models.semester import Semester
from .....schemas.booking import (
    Booking as BookingSchema, BookingCreate, BookingWithRelations,
    BookingList
)
from .....api.helpers.spec_validation import validate_can_book_session
from .helpers import auto_promote_from_waitlist

router = APIRouter()


@router.post("/", response_model=BookingSchema)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create new booking - STUDENTS ONLY

    🎯 REFACTORED: Uses spec services for validation
    - Session-based (LFA Player): Requires only UserLicense
    - Semester-based (Coach/Internship): Requires UserLicense + SemesterEnrollment + payment
    """
    # 🔒 CRITICAL: Only STUDENTS can book sessions!
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can book sessions. Instructors and admins cannot book sessions."
        )

    # Check if session exists
    session = db.query(SessionTypel).filter(SessionTypel.id == booking_data.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # ✅ NEW: Spec-specific validation using new services
    # This automatically handles:
    # - Session-based (LFA Player): Only checks UserLicense
    # - Semester-based (Coach/Internship): Checks UserLicense + SemesterEnrollment + payment_verified
    # - Age eligibility validation
    # - Cross-specialization protection
    can_book, reason = validate_can_book_session(current_user, session, db)

    if not can_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
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

    # ✅ VALIDATE BOOKING DEADLINE: Must book at least 24 hours before session
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    session_start_naive = session.date_start.replace(tzinfo=None) if session.date_start.tzinfo else session.date_start

    # Check if session is in the past
    if session_start_naive < current_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot book past sessions"
        )

    # 🔒 RULE #1: 24-hour booking deadline
    booking_deadline = session_start_naive - timedelta(hours=24)
    if current_time > booking_deadline:
        hours_until_session = (session_start_naive - current_time).total_seconds() / 3600
        raise HTTPException(
            status_code=400,
            detail=f"Booking deadline passed. You must book at least 24 hours before the session starts. "
                   f"Session starts in {hours_until_session:.1f} hours."
        )

    # B02: Lock session row before capacity read — serialises concurrent bookings.
    # Thread B blocks here until Thread A commits, then sees the updated count.
    db.query(SessionTypel).filter(
        SessionTypel.id == booking_data.session_id
    ).with_for_update().one()

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
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        orig = str(getattr(e, "orig", e))
        if "uq_active_booking" in orig:
            raise HTTPException(
                status_code=409,
                detail="You already have an active booking for this session (concurrent duplicate request blocked)",
            )
        raise HTTPException(status_code=409, detail=f"Database constraint violation: {orig}")
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

    # OPTIMIZED: Batch fetch attendance status (reduces N+1 queries to 1 query)
    session_ids = [b.session_id for b in bookings]
    attended_sessions = db.query(Attendance.session_id).filter(
        and_(
            Attendance.user_id == current_user.id,
            Attendance.session_id.in_(session_ids),
            Attendance.status == AttendanceStatus.present
        )
    ).all()
    attended_session_ids = {row.session_id for row in attended_sessions}

    # Convert to response schema with attendance calculation
    booking_responses = []
    for booking in bookings:
        attended = booking.session_id in attended_session_ids

        # Explicitly create schema object instead of using __dict__
        booking_responses.append(BookingWithRelations(
            id=booking.id,
            user_id=booking.user_id,
            session_id=booking.session_id,
            status=booking.status,
            waitlist_position=booking.waitlist_position,
            notes=booking.notes,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            cancelled_at=booking.cancelled_at,
            attended_status=booking.attended_status,
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


@router.get("/{booking_id}", response_model=BookingWithRelations)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get a specific booking by ID.
    Students can only view their own bookings.
    Admins and instructors can view any booking.
    """
    booking = db.query(Booking).options(
        joinedload(Booking.user),
        joinedload(Booking.session)
    ).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Authorization: Students can only view their own bookings
    if current_user.role == UserRole.STUDENT and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")

    # Check attendance
    attendance = db.query(Attendance).filter(
        and_(
            Attendance.user_id == booking.user_id,
            Attendance.session_id == booking.session_id,
            Attendance.status == AttendanceStatus.present
        )
    ).first()

    attended = attendance is not None

    # Return booking with relations
    return BookingWithRelations(
        id=booking.id,
        user_id=booking.user_id,
        session_id=booking.session_id,
        status=booking.status,
        waitlist_position=booking.waitlist_position,
        notes=booking.notes,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        cancelled_at=booking.cancelled_at,
        attended_status=booking.attended_status,
        user=booking.user,
        session=booking.session,
        attended=attended
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
    # B05: Lock booking row — prevents concurrent student + admin cancel both
    # reading status=CONFIRMED and both triggering auto_promote → overbooking.
    booking = db.query(Booking).filter(Booking.id == booking_id).with_for_update().first()
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

    # B05: Guard against double-cancel — after the lock, re-read status is safe.
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
        )

    # ✅ VALIDATE CANCELLATION DEADLINE: Must cancel at least 12 hours before session
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    session_start = booking.session.date_start.replace(tzinfo=None) if booking.session.date_start.tzinfo else booking.session.date_start

    # Check if session has already started
    if current_time > session_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel booking for past sessions"
        )

    # 🔒 RULE #2: 12-hour cancellation deadline
    cancellation_deadline = session_start - timedelta(hours=12)
    if current_time > cancellation_deadline:
        hours_until_session = (session_start - current_time).total_seconds() / 3600
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cancellation deadline passed. You must cancel at least 12 hours before the session starts. "
                   f"Session starts in {hours_until_session:.1f} hours."
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
        promotion_result = auto_promote_from_waitlist(db, session_id)
        if promotion_result:
            promoted_user, _ = promotion_result

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
        bookings_query = bookings_query.join(SessionTypel).filter(
            SessionTypel.semester_id == semester_id
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
            Attendance.status == AttendanceStatus.present
        )
    )

    # Filter attendance by semester if provided
    if semester_id:
        attended_sessions = attended_sessions.join(SessionTypel).filter(
            SessionTypel.semester_id == semester_id
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
