"""
Session payload factory for smoke and E2E tests.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.factories.session_factory import create_session_payload
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def create_session_payload(
    semester_id: int,
    campus_id: int,
    *,
    capacity: int = 1,
    hours_from_now: int = 48,
    duration_minutes: int = 90,
    title: str = "Smoke Test Session",
    credit_cost: int = 0,
) -> dict:
    """
    Minimal-valid payload for POST /api/v1/sessions/.

    Notes:
    - date_start is set hours_from_now in the future (default 48h).
      This satisfies the 24h advance-booking rule.
    - No target_specialization field → session.is_accessible_to_all=True
      (bypasses validate_can_book_session spec check).
    - capacity=1 is the minimum useful value for booking lifecycle tests.

    Args:
        semester_id: The semester (tournament) to attach the session to.
        campus_id: Campus where the session is held.
        capacity: Max confirmed bookings (default 1 for waitlist tests).
        hours_from_now: Start time offset in hours from now (default 48).
        duration_minutes: Session length in minutes (default 90).
        title: Session title for identification.
        credit_cost: Credits required to book (default 0 — free).
    """
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=hours_from_now)
    end = start + timedelta(minutes=duration_minutes)

    return {
        "title": title,
        "date_start": start.replace(tzinfo=None).isoformat(),
        "date_end": end.replace(tzinfo=None).isoformat(),
        "semester_id": semester_id,
        "campus_id": campus_id,
        "capacity": capacity,
        "credit_cost": credit_cost,
        "session_type": "on_site",
    }
