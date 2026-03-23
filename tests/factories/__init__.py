"""
Global test payload factory layer.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.factories import create_student_payload, login_payload
    from tests.factories.session_factory import create_session_payload
    from tests.factories.booking_factory import create_booking_payload
    from tests.factories.enrollment_factory import enroll_in_tournament_payload
"""

from .user_factory import (
    create_student_payload,
    create_instructor_payload,
    create_admin_payload,
    login_payload,
    change_password_payload,
)
from .session_factory import create_session_payload
from .booking_factory import create_booking_payload, cancel_booking_payload
from .enrollment_factory import (
    enroll_in_tournament_payload,
    approve_enrollment_payload,
    reject_enrollment_payload,
)
from .game_factory import PlayerFactory, TournamentFactory

__all__ = [
    "create_student_payload",
    "create_instructor_payload",
    "create_admin_payload",
    "login_payload",
    "change_password_payload",
    "create_session_payload",
    "create_booking_payload",
    "cancel_booking_payload",
    "enroll_in_tournament_payload",
    "approve_enrollment_payload",
    "reject_enrollment_payload",
    "PlayerFactory",
    "TournamentFactory",
]
