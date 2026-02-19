"""
Tournament instructor components package.

This package contains UI components for tournament instructors (master instructors).

Modules:
    - tournament_checkin: Tournament-specific check-in wizard (2 attendance statuses)
"""

from .tournament_checkin import render_tournament_checkin

__all__ = [
    "render_tournament_checkin",
]
