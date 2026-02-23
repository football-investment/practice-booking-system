"""
Time Provider - Deterministic Time Abstraction Layer

This module provides a centralized, testable interface for getting the current time.
By abstracting time access, we enable deterministic testing without freezegun or
database manipulation.

Usage in production code:
    from app.core.time_provider import now

    current_time = now()
    if session.start_time < now():
        ...

Usage in tests:
    monkeypatch.setattr(
        "app.core.time_provider.now",
        lambda: datetime(2026, 2, 23, 14, 0, 0, tzinfo=timezone.utc)
    )

Benefits:
- No database session boundary issues
- No freezegun dependency
- Fully deterministic test behavior
- Production-safe (no test infrastructure leakage)
"""

from datetime import datetime, timezone


def now() -> datetime:
    """
    Get current UTC time.

    This function is the single source of truth for "current time" in the application.
    In tests, monkeypatch this function to control time flow.

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)
