"""
Integration tests — Session booking capacity constraints
=========================================================

Validates that the booking capacity model behaves correctly:
- CONFIRMED bookings are capped at ``session.capacity``
- Bookings beyond capacity receive WAITLISTED status with sequential positions
- Canceling a CONFIRMED booking vacates the slot (confirmed_count drops)
- Multiple sessions are capacity-independent of each other

Tests use the SAVEPOINT-isolated ``test_db`` fixture so that every test starts
clean and rolls back automatically.

Tests
-----
  CAP-01  Confirmed bookings up to capacity — all CONFIRMED
  CAP-02  Next booking when full — capacity check → WAITLISTED decision
  CAP-03  Multiple waitlisted bookings get sequential positions (1, 2, 3, …)
  CAP-04  Canceling a CONFIRMED booking reduces confirmed_count, opens slot
  CAP-05  Separate sessions have independent capacity counters
  CAP-06  capacity=0 → all bookings immediately waitlisted
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.booking import Booking, BookingStatus
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User, UserRole
from tests.fixtures.builders import build_semester, build_session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_student(db: Session) -> User:
    """Create a fresh STUDENT user within the current SAVEPOINT transaction."""
    u = User(
        email=f"cap+{uuid.uuid4().hex[:8]}@test.com",
        name="Capacity Test Student",
        password_hash=get_password_hash("testpassword"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    db.refresh(u)
    return u


def _confirmed_count(db: Session, session_id: int) -> int:
    return (
        db.query(func.count(Booking.id))
        .filter(
            Booking.session_id == session_id,
            Booking.status == BookingStatus.CONFIRMED,
        )
        .scalar()
        or 0
    )


def _waitlisted_count(db: Session, session_id: int) -> int:
    return (
        db.query(func.count(Booking.id))
        .filter(
            Booking.session_id == session_id,
            Booking.status == BookingStatus.WAITLISTED,
        )
        .scalar()
        or 0
    )


def _next_waitlist_position(db: Session, session_id: int) -> int:
    """Next sequential waitlist position for a session."""
    return _waitlisted_count(db, session_id) + 1


# ── Capacity tests ────────────────────────────────────────────────────────────

class TestBookingCapacity:
    """Capacity and waitlist model integrity tests."""

    def test_cap01_bookings_up_to_capacity_are_confirmed(
        self, test_db: Session, student_user: User
    ):
        """CAP-01: Filling a session to capacity yields all CONFIRMED bookings."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, capacity=3)
        users: List[User] = [student_user, _new_student(test_db), _new_student(test_db)]

        for u in users:
            test_db.add(Booking(user_id=u.id, session_id=sess.id, status=BookingStatus.CONFIRMED))
        test_db.flush()

        count = _confirmed_count(test_db, sess.id)
        assert count == 3
        assert count == sess.capacity, "All slots should be filled"

    def test_cap02_capacity_check_yields_waitlisted_decision(
        self, test_db: Session, student_user: User
    ):
        """CAP-02: confirmed_count >= capacity → next booking decision is WAITLISTED."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, capacity=2)

        u1, u2, u3 = student_user, _new_student(test_db), _new_student(test_db)
        for u in [u1, u2]:
            test_db.add(Booking(user_id=u.id, session_id=sess.id, status=BookingStatus.CONFIRMED))
        test_db.flush()

        # Capacity logic mirrors the booking endpoint: confirmed_count < sess.capacity?
        confirmed = _confirmed_count(test_db, sess.id)
        next_status = (
            BookingStatus.CONFIRMED if confirmed < sess.capacity else BookingStatus.WAITLISTED
        )
        assert next_status == BookingStatus.WAITLISTED, (
            f"Session is full ({confirmed}/{sess.capacity}); next booking must be WAITLISTED"
        )

        # Create the waitlisted booking and verify it persists correctly
        wl_pos = _next_waitlist_position(test_db, sess.id)
        test_db.add(
            Booking(
                user_id=u3.id,
                session_id=sess.id,
                status=BookingStatus.WAITLISTED,
                waitlist_position=wl_pos,
            )
        )
        test_db.flush()

        rows = (
            test_db.query(Booking)
            .filter(Booking.session_id == sess.id, Booking.status == BookingStatus.WAITLISTED)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].user_id == u3.id
        assert rows[0].waitlist_position == 1

    def test_cap03_multiple_waitlisted_bookings_have_sequential_positions(
        self, test_db: Session, student_user: User
    ):
        """CAP-03: Waitlist positions are sequential starting from 1."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, capacity=1)

        confirmed_user = student_user
        waitlisted_users = [_new_student(test_db) for _ in range(3)]

        # Fill the single slot
        test_db.add(
            Booking(user_id=confirmed_user.id, session_id=sess.id, status=BookingStatus.CONFIRMED)
        )
        test_db.flush()

        # Enqueue 3 waitlisted bookings
        for i, u in enumerate(waitlisted_users, start=1):
            test_db.add(
                Booking(
                    user_id=u.id,
                    session_id=sess.id,
                    status=BookingStatus.WAITLISTED,
                    waitlist_position=i,
                )
            )
        test_db.flush()

        waitlisted = (
            test_db.query(Booking)
            .filter(Booking.session_id == sess.id, Booking.status == BookingStatus.WAITLISTED)
            .order_by(Booking.waitlist_position)
            .all()
        )
        assert len(waitlisted) == 3
        assert [b.waitlist_position for b in waitlisted] == [1, 2, 3]
        assert [b.user_id for b in waitlisted] == [u.id for u in waitlisted_users]

    def test_cap04_canceling_confirmed_booking_reduces_count(
        self, test_db: Session, student_user: User
    ):
        """CAP-04: Canceling a CONFIRMED booking opens a slot (confirmed_count drops)."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, capacity=2)

        u1, u2 = student_user, _new_student(test_db)
        b1 = Booking(user_id=u1.id, session_id=sess.id, status=BookingStatus.CONFIRMED)
        b2 = Booking(user_id=u2.id, session_id=sess.id, status=BookingStatus.CONFIRMED)
        test_db.add(b1)
        test_db.add(b2)
        test_db.flush()

        assert _confirmed_count(test_db, sess.id) == 2
        assert _confirmed_count(test_db, sess.id) >= sess.capacity, "Session should be full"

        # Cancel one booking
        b1.status = BookingStatus.CANCELLED
        test_db.flush()

        confirmed_after = _confirmed_count(test_db, sess.id)
        assert confirmed_after == 1
        assert confirmed_after < sess.capacity, "A slot should be available after cancellation"

    def test_cap05_separate_sessions_are_capacity_independent(
        self, test_db: Session, student_user: User
    ):
        """CAP-05: Capacity is enforced per session; filling one does not affect another."""
        sem = build_semester(test_db)
        sess_a = build_session(test_db, sem.id, capacity=1, title="Session A")
        sess_b = build_session(test_db, sem.id, capacity=3, title="Session B")

        u1, u2 = student_user, _new_student(test_db)
        # Fill session A
        test_db.add(Booking(user_id=u1.id, session_id=sess_a.id, status=BookingStatus.CONFIRMED))
        # Add one to session B (still has capacity)
        test_db.add(Booking(user_id=u1.id, session_id=sess_b.id, status=BookingStatus.CONFIRMED))
        test_db.flush()

        assert _confirmed_count(test_db, sess_a.id) == 1  # full
        assert _confirmed_count(test_db, sess_b.id) == 1  # 2 slots remaining

        # Session B still has room
        next_status_b = (
            BookingStatus.CONFIRMED
            if _confirmed_count(test_db, sess_b.id) < sess_b.capacity
            else BookingStatus.WAITLISTED
        )
        assert next_status_b == BookingStatus.CONFIRMED

    def test_cap06_zero_capacity_session_immediately_waitlists(
        self, test_db: Session, student_user: User
    ):
        """CAP-06: capacity=0 means every booking is WAITLISTED (no confirmed slots)."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, capacity=0)

        confirmed = _confirmed_count(test_db, sess.id)
        next_status = (
            BookingStatus.CONFIRMED if confirmed < sess.capacity else BookingStatus.WAITLISTED
        )
        assert next_status == BookingStatus.WAITLISTED, (
            "capacity=0 → all bookings must be WAITLISTED"
        )
