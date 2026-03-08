"""
Booking payload factory for smoke and E2E tests.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.factories.booking_factory import create_booking_payload, cancel_booking_payload
"""

from __future__ import annotations


def create_booking_payload(session_id: int) -> dict:
    """
    Payload for POST /api/v1/bookings/.

    Args:
        session_id: The session to book.
    """
    return {"session_id": session_id}


def cancel_booking_payload(reason: str = "Test cancellation") -> dict:
    """
    Payload for DELETE /api/v1/bookings/{id} or
    POST /api/v1/bookings/{id}/cancel.

    Args:
        reason: Human-readable cancellation reason.
    """
    return {"reason": reason}
