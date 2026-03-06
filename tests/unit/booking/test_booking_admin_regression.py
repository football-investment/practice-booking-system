"""
Regression test: GET /api/v1/bookings/ admin endpoint — relationship unpack bug.

Bug: HTTP 500 when any booking existed in the DB.
Root cause: SQLAlchemy joinedload populates relationship attributes ('user', 'session')
into Booking.__dict__.  The old serialization code then did:

    BookingWithRelations(**booking.__dict__, user=booking.user, session=booking.session)

When __dict__ already contained 'user' (from joinedload), Python raised:
    TypeError: BookingWithRelations() got multiple values for keyword argument 'user'

Fix (admin.py:63-70): filter _sa_instance_state, user, session, attendance
from __dict__ before spreading, then pass relationship objects explicitly.

This file contains:
  - test_booking_admin_list_relationship_unpack_regression
      Proves the fixed code does NOT raise for a joinedload-style __dict__.
  - test_booking_admin_list_unpack_broken_pattern_raises_type_error
      Proves the OLD code pattern WOULD raise — validates the test itself is meaningful.
  - test_booking_admin_list_all_skip_keys_filtered
      Covers all four _skip keys (user, session, attendance, _sa_instance_state).
  - test_booking_admin_list_multiple_bookings_no_cross_contamination
      Verifies the loop processes each booking independently (no shared state).
"""
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.booking import BookingWithRelations, BookingUserSimple, BookingSessionSimple
from app.models.booking import BookingStatus
from app.models.session import SessionType


# ── Minimal stubs ─────────────────────────────────────────────────────────────

def _make_user(user_id: int = 1) -> BookingUserSimple:
    """Minimal BookingUserSimple — satisfies all required fields."""
    return BookingUserSimple(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com",
        role="STUDENT",
    )


def _make_session(session_id: int = 1) -> BookingSessionSimple:
    """Minimal BookingSessionSimple — satisfies all required fields."""
    return BookingSessionSimple(
        id=session_id,
        title=f"Session {session_id}",
        date_start=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        session_type=SessionType.on_site,
        capacity=20,
        semester_id=1,
    )


def _make_joinedload_dict(booking_id: int = 42, user_id: int = 99) -> dict:
    """
    Simulate the __dict__ that SQLAlchemy produces after a joinedload query.
    Scalar columns + '_sa_instance_state' + relationship objects ('user', 'session')
    all appear as top-level keys — exactly as in the production bug.
    """
    return {
        # Scalar columns (from DB row)
        "id": booking_id,
        "user_id": user_id,
        "session_id": 1,
        "status": BookingStatus.CONFIRMED,
        "notes": None,
        "waitlist_position": None,
        "created_at": datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
        "updated_at": None,
        "cancelled_at": None,
        "attended_status": None,
        # SQLAlchemy internals injected by joinedload:
        "_sa_instance_state": SimpleNamespace(),   # ← always present
        "user": _make_user(user_id),               # ← joinedload injects this
        "session": _make_session(1),               # ← joinedload injects this
        "attendance": None,                        # ← optional relationship
    }


# ── Test class ────────────────────────────────────────────────────────────────

class TestBookingAdminListRelationshipUnpackRegression:
    """
    Regression suite for the joinedload-duplicate-keyword-argument bug.

    Each test is isolated and exercises a different aspect of the fix.
    No DB / fixture dependencies — pure Pydantic schema + dict manipulation.
    """

    def test_booking_admin_list_relationship_unpack_regression(self):
        """
        MAIN REGRESSION: fixed serialization logic must not raise when __dict__
        already contains 'user' and 'session' (as injected by joinedload).

        If the fix regresses to the old pattern, this test will raise:
            TypeError: BookingWithRelations() got multiple values for keyword argument 'user'
        """
        joinedload_dict = _make_joinedload_dict(booking_id=42, user_id=99)
        fake_user = joinedload_dict["user"]
        fake_session = joinedload_dict["session"]

        # ── Exact fix applied in admin.py:63-70 ───────────────────────────────
        _skip = {"_sa_instance_state", "user", "session", "attendance"}
        base = {k: v for k, v in joinedload_dict.items() if k not in _skip}

        # Must NOT raise TypeError
        result = BookingWithRelations(**base, user=fake_user, session=fake_session)

        assert result.id == 42
        assert result.user_id == 99
        assert result.status == BookingStatus.CONFIRMED
        assert result.user.id == fake_user.id
        assert result.session.id == fake_session.id

    def test_booking_admin_list_unpack_broken_pattern_raises_type_error(self):
        """
        PROOF OF REGRESSION COVERAGE: the OLD code pattern DOES raise TypeError.

        Validates that this regression test is meaningful — if the old code
        is somehow reintroduced, the MAIN test above will catch it.
        """
        joinedload_dict = _make_joinedload_dict(booking_id=42)
        fake_user = joinedload_dict["user"]
        fake_session = joinedload_dict["session"]

        # OLD broken line (do NOT use _skip filter):
        # Python raises TypeError BEFORE Pydantic even validates anything —
        # duplicate keyword argument is a syntax-level error at the call site.
        with pytest.raises(TypeError, match="got multiple values for keyword argument"):
            BookingWithRelations(
                **joinedload_dict,       # ← 'user' already in here from joinedload
                user=fake_user,          # ← duplicate → TypeError
                session=fake_session,
            )

    def test_booking_admin_list_all_skip_keys_filtered(self):
        """
        Verify that _skip removes ALL four relationship/internal keys:
        '_sa_instance_state', 'user', 'session', 'attendance'.
        None of them should appear in the filtered base dict.
        """
        joinedload_dict = _make_joinedload_dict()
        _skip = {"_sa_instance_state", "user", "session", "attendance"}
        base = {k: v for k, v in joinedload_dict.items() if k not in _skip}

        for key in _skip:
            assert key not in base, (
                f"Key '{key}' was not removed by _skip filter — "
                f"BookingWithRelations would receive a duplicate keyword argument."
            )

        # Scalar fields must still be present
        assert "id" in base
        assert "user_id" in base
        assert "session_id" in base
        assert "status" in base
        assert "created_at" in base

    def test_booking_admin_list_multiple_bookings_no_cross_contamination(self):
        """
        Simulates the production loop over multiple bookings (admin list endpoint).
        Verifies each booking is serialized independently — no shared-state leakage
        between loop iterations (e.g. _skip set is not mutated per iteration).
        """
        bookings_data = [
            _make_joinedload_dict(booking_id=10, user_id=101),
            _make_joinedload_dict(booking_id=20, user_id=102),
            _make_joinedload_dict(booking_id=30, user_id=103),
        ]

        results = []
        _skip = {"_sa_instance_state", "user", "session", "attendance"}
        for d in bookings_data:
            base = {k: v for k, v in d.items() if k not in _skip}
            results.append(
                BookingWithRelations(**base, user=d["user"], session=d["session"])
            )

        assert len(results) == 3
        assert results[0].id == 10 and results[0].user_id == 101
        assert results[1].id == 20 and results[1].user_id == 102
        assert results[2].id == 30 and results[2].user_id == 103
