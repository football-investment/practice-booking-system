"""
Shared session components package.

This package contains reusable components for both regular sessions
and tournament sessions.

Modules:
    - attendance_core: Core attendance functionality
"""

from .attendance_core import (
    calculate_attendance_summary,
    render_attendance_status_badge,
)

__all__ = [
    "calculate_attendance_summary",
    "render_attendance_status_badge",
]
