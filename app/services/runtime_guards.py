"""
Runtime invariant guards — fire AFTER db.commit(), never block the request.
===========================================================================

Called from route post-commit hooks. These are NOT unit tests — they run in
production on every enrollment/withdrawal operation.

On violation:
  - Log CRITICAL (visible in all log aggregators, pagerduty-triggerable)
  - Increment ``invariant_violations_total`` counter (visible on /metrics)

Design principles:
  - Non-blocking: guards NEVER raise, NEVER write to DB
  - Called only AFTER commit so the checked state is durable
  - Each guard is independently safe (wrapped in try/except)
  - A non-zero ``invariant_violations_total`` counter = data consistency bug
    that must be investigated immediately

Covered invariants:
  GUARD-01  credit_balance >= 0       (user.credit_balance must never go negative)
  GUARD-02  confirmed_count <= capacity  (per session, at all times)
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.metrics import metrics
from ..models.booking import Booking, BookingStatus
from ..models.session import Session as SessionModel
from ..models.user import User

_logger = logging.getLogger(__name__)


# ── GUARD-01: credit balance ──────────────────────────────────────────────────

def guard_credit_balance(db: Session, user_id: int) -> None:
    """
    INVARIANT: user.credit_balance >= 0.

    Negative balance means credits were deducted beyond zero — a financial
    integrity bug. The DB CHECK constraint is the last line of defense; this
    guard fires a CRITICAL log so it is visible in monitoring BEFORE the DB
    constraint is hit.

    Args:
        db:       Live SQLAlchemy session (post-commit).
        user_id:  ID of the user whose balance to inspect.
    """
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if user is not None and user.credit_balance < 0:
            _logger.critical(
                "GUARD-01 INVARIANT VIOLATION: credit_balance < 0 — "
                "user_id=%s credit_balance=%s",
                user_id,
                user.credit_balance,
            )
            metrics.increment("invariant_violations_total")
    except Exception:
        _logger.exception(
            "guard_credit_balance: unexpected error checking user_id=%s", user_id
        )


# ── GUARD-02: session capacity ────────────────────────────────────────────────

def guard_capacity(db: Session, session_id: int) -> None:
    """
    INVARIANT: confirmed_count(session) <= session.capacity.

    More confirmed bookings than capacity means the pessimistic lock or the
    capacity check in the service layer failed. A CRITICAL log is emitted so
    operations can investigate and manually resolve overbooking.

    Args:
        db:          Live SQLAlchemy session (post-commit).
        session_id:  ID of the session to inspect.
    """
    try:
        confirmed = (
            db.query(Booking)
            .filter_by(session_id=session_id, status=BookingStatus.CONFIRMED)
            .count()
        )
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if (
            session is not None
            and session.capacity is not None
            and confirmed > session.capacity
        ):
            _logger.critical(
                "GUARD-02 INVARIANT VIOLATION: confirmed_count > capacity — "
                "session_id=%s confirmed=%s capacity=%s",
                session_id,
                confirmed,
                session.capacity,
            )
            metrics.increment("invariant_violations_total")
    except Exception:
        _logger.exception(
            "guard_capacity: unexpected error checking session_id=%s", session_id
        )


# ── Composite hooks (called from route layer) ─────────────────────────────────

def guard_post_enroll(db: Session, *, user_id: int, enrollment_id: int) -> None:
    """
    Post-enrollment composite guard.

    Checks:
      - GUARD-01: credit_balance >= 0 for the enrolling user
      - GUARD-02: confirmed_count <= capacity for each CONFIRMED booking
                  created by this enrollment

    Args:
        db:            Live SQLAlchemy session (post-commit).
        user_id:       Enrolling user's ID.
        enrollment_id: ID of the newly created/reactivated enrollment.
    """
    guard_credit_balance(db, user_id)
    try:
        confirmed_bookings = (
            db.query(Booking)
            .filter_by(enrollment_id=enrollment_id, status=BookingStatus.CONFIRMED)
            .all()
        )
        for booking in confirmed_bookings:
            guard_capacity(db, booking.session_id)
    except Exception:
        _logger.exception(
            "guard_post_enroll: error querying bookings for enrollment_id=%s",
            enrollment_id,
        )


def guard_post_withdraw(db: Session, *, user_id: int) -> None:
    """
    Post-withdrawal composite guard.

    Checks:
      - GUARD-01: credit_balance >= 0 after the refund is applied

    Capacity is NOT checked after withdraw: a withdrawal reduces confirmed
    count, so capacity cannot be violated by the withdraw operation itself.

    Args:
        db:       Live SQLAlchemy session (post-commit).
        user_id:  Withdrawing user's ID.
    """
    guard_credit_balance(db, user_id)
