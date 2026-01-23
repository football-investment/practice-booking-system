"""
Tournament Enrollment Service - Student enrollment and booking logic

This module handles student enrollment and auto-booking for tournaments.

Functions:
    - auto_book_students: Automatically book students for tournament sessions
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.session import Session as SessionModel
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole


def auto_book_students(
    db: Session,
    session_ids: List[int],
    capacity_percentage: int = 70
) -> Dict[int, List[int]]:
    """
    Auto-book students for tournament sessions

    This function automatically creates bookings for active students
    up to a specified percentage of each session's capacity.

    Args:
        db: Database session
        session_ids: List of session IDs to book
        capacity_percentage: Percentage of capacity to fill (default: 70%)

    Returns:
        Dict mapping session_id -> list of booked user_ids

    Example:
        >>> bookings = auto_book_students(db, [123, 124], capacity_percentage=80)
        >>> # {123: [1, 2, 3], 124: [1, 2, 3, 4]}
    """
    bookings_map = {}

    # Get all active students
    students = db.query(User).filter(
        and_(
            User.role == UserRole.STUDENT,
            User.is_active == True
        )
    ).all()

    if not students:
        return bookings_map

    for session_id in session_ids:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            continue

        # Calculate target bookings
        target_bookings = int(session.capacity * (capacity_percentage / 100))
        target_bookings = min(target_bookings, len(students))

        # Book first N students
        booked_user_ids = []
        for i in range(target_bookings):
            student = students[i % len(students)]  # Cycle through students

            booking = Booking(
                user_id=student.id,
                session_id=session_id,
                status=BookingStatus.CONFIRMED
            )
            db.add(booking)
            booked_user_ids.append(student.id)

        bookings_map[session_id] = booked_user_ids

    db.commit()
    return bookings_map
