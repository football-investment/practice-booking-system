"""
Shared helper functions for booking operations
Includes auto-promotion logic and validation helpers
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .....models.booking import Booking, BookingStatus
from .....models.user import User


def auto_promote_from_waitlist(
    db: Session,
    session_id: int
) -> Optional[Tuple[User, int]]:
    """
    Auto-promote the next person from waitlist to confirmed

    Returns:
        Tuple of (promoted_user, booking_id) if promotion occurred, None otherwise
    """
    # B04: Lock the top-of-waitlist row — prevents two concurrent cancel callbacks
    # both selecting the same row and both promoting it (double-promotion).
    next_waitlisted = db.query(Booking).filter(
        and_(
            Booking.session_id == session_id,
            Booking.status == BookingStatus.WAITLISTED
        )
    ).with_for_update().order_by(Booking.waitlist_position.asc()).first()

    if not next_waitlisted:
        return None

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

    return (promoted_user, next_waitlisted.id)
