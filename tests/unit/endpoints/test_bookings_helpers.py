"""
Unit tests for app/api/api_v1/endpoints/bookings/helpers.py.

Targets 71% branch coverage gap on auto_promote_from_waitlist().
All branches: no waitlist → None, empty remaining, waitlist_position=None,
waitlist_position=0, normal decrement.
"""

import pytest
from unittest.mock import MagicMock, call

from app.api.api_v1.endpoints.bookings.helpers import auto_promote_from_waitlist
from app.models.booking import Booking, BookingStatus
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chain_db(first_val=None, all_val=None):
    """
    Build a mock DB that handles:
      db.query(Booking)
        .filter(...)
        .with_for_update()
        .order_by(...)
        .first()   →  first_val          (first Booking query)

      db.query(Booking)
        .filter(...)
        .all()     →  all_val or []      (second Booking query)

      db.query(User)
        .filter(...)
        .first()   →  MagicMock (promoted user)

    Route by model type so call order doesn't matter.
    Both Booking queries share one chain — .first() returns first_val,
    .all() returns all_val.
    """
    # Single chain for all Booking queries (supports both .first() and .all())
    bk_chain = MagicMock()
    bk_chain.filter.return_value = bk_chain
    bk_chain.with_for_update.return_value = bk_chain
    bk_chain.order_by.return_value = bk_chain
    bk_chain.first.return_value = first_val
    bk_chain.all.return_value = all_val if all_val is not None else []

    # User query chain
    user_chain = MagicMock()
    user_chain.filter.return_value = user_chain
    user_chain.first.return_value = MagicMock(spec=User)

    def _side_effect(model):
        if model is User:
            return user_chain
        return bk_chain  # Booking queries

    db = MagicMock()
    db.query.side_effect = _side_effect
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAutoPromoteFromWaitlist:

    def test_no_waitlisted_booking_returns_none(self):
        db = _chain_db(first_val=None)
        result = auto_promote_from_waitlist(db, session_id=1)
        assert result is None

    def test_empty_remaining_waitlist_no_decrement(self):
        promoted = MagicMock(spec=Booking)
        promoted.user_id = 42
        promoted.status = BookingStatus.WAITLISTED
        promoted.waitlist_position = 1

        db = _chain_db(first_val=promoted, all_val=[])
        result = auto_promote_from_waitlist(db, session_id=1)

        assert result is not None
        assert promoted.status == BookingStatus.CONFIRMED
        assert promoted.waitlist_position is None

    def test_waitlist_position_none_not_decremented(self):
        promoted = MagicMock(spec=Booking)
        promoted.user_id = 42
        promoted.status = BookingStatus.WAITLISTED
        promoted.waitlist_position = 1

        # Remaining booking has position=None (falsy first condition)
        remaining = MagicMock(spec=Booking)
        remaining.waitlist_position = None
        original_position = None

        db = _chain_db(first_val=promoted, all_val=[remaining])
        auto_promote_from_waitlist(db, session_id=1)

        assert remaining.waitlist_position is None  # Not modified

    def test_waitlist_position_zero_not_decremented(self):
        promoted = MagicMock(spec=Booking)
        promoted.user_id = 42
        promoted.status = BookingStatus.WAITLISTED
        promoted.waitlist_position = 1

        remaining = MagicMock(spec=Booking)
        remaining.waitlist_position = 0  # falsy first condition

        db = _chain_db(first_val=promoted, all_val=[remaining])
        auto_promote_from_waitlist(db, session_id=1)

        assert remaining.waitlist_position == 0  # Not decremented

    def test_normal_decrement_of_remaining_positions(self):
        promoted = MagicMock(spec=Booking)
        promoted.user_id = 42
        promoted.status = BookingStatus.WAITLISTED
        promoted.waitlist_position = 1

        r1 = MagicMock(spec=Booking)
        r1.waitlist_position = 2

        r2 = MagicMock(spec=Booking)
        r2.waitlist_position = 3

        db = _chain_db(first_val=promoted, all_val=[r1, r2])
        auto_promote_from_waitlist(db, session_id=1)

        assert r1.waitlist_position == 1  # Decremented
        assert r2.waitlist_position == 2  # Decremented

    def test_returns_tuple_of_user_and_booking_id(self):
        promoted = MagicMock(spec=Booking)
        promoted.user_id = 99
        promoted.id = 77
        promoted.status = BookingStatus.WAITLISTED
        promoted.waitlist_position = 1

        db = _chain_db(first_val=promoted, all_val=[])
        result = auto_promote_from_waitlist(db, session_id=5)

        assert result is not None
        user, booking_id = result
        assert booking_id == 77
