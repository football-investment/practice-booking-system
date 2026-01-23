"""
Database Verification Helpers for E2E Tests

These utilities provide reusable database state verification functions
to ensure consistency across tournament workflow tests.

Usage:
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.models.semester_enrollment import EnrollmentStatus
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment
from app.models.booking import Booking
from app.models.attendance import Attendance
from app.models.user import User


def verify_tournament_state(
    db_session: Session,
    tournament_id: int,
    expected_status: str,
    expected_tournament_type_id: Optional[int] = None,
    expected_sessions_generated: Optional[bool] = None,
    expected_max_players: Optional[int] = None
) -> Dict[str, Any]:
    """
    Verify tournament (Semester) state in database

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID to verify
        expected_status: Expected tournament_status string (e.g., "COMPLETED")
        expected_tournament_type_id: Expected tournament type ID (optional)
        expected_sessions_generated: Expected sessions_generated flag (optional)
        expected_max_players: Expected max_players value (optional)

    Returns:
        Dict with verification results and tournament data

    Raises:
        AssertionError: If verification fails
    """
    tournament = db_session.query(Semester).filter_by(id=tournament_id).first()

    assert tournament is not None, f"Tournament {tournament_id} not found in database"
    assert tournament.tournament_status == expected_status, \
        f"Expected status {expected_status}, got {tournament.tournament_status}"

    if expected_tournament_type_id is not None:
        assert tournament.tournament_type_id == expected_tournament_type_id, \
            f"Expected tournament_type_id {expected_tournament_type_id}, got {tournament.tournament_type_id}"

    if expected_sessions_generated is not None:
        assert tournament.sessions_generated == expected_sessions_generated, \
            f"Expected sessions_generated {expected_sessions_generated}, got {tournament.sessions_generated}"

    if expected_max_players is not None:
        assert tournament.max_players == expected_max_players, \
            f"Expected max_players {expected_max_players}, got {tournament.max_players}"

    return {
        "tournament_id": tournament.id,
        "name": tournament.name,
        "status": tournament.tournament_status,
        "tournament_type_id": tournament.tournament_type_id,
        "sessions_generated": tournament.sessions_generated,
        "sessions_generated_at": tournament.sessions_generated_at,
        "max_players": tournament.max_players,
        "reward_policy_snapshot": tournament.reward_policy_snapshot
    }


def verify_enrollment_consistency(
    db_session: Session,
    tournament_id: int,
    expected_count: int,
    expected_status: EnrollmentStatus = EnrollmentStatus.APPROVED
) -> List[SemesterEnrollment]:
    """
    Verify enrollment consistency for a tournament

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID
        expected_count: Expected number of active enrollments
        expected_status: Expected EnrollmentStatus for all enrollments

    Returns:
        List of SemesterEnrollment objects

    Raises:
        AssertionError: If verification fails
    """
    enrollments = db_session.query(SemesterEnrollment).filter_by(
        semester_id=tournament_id,
        is_active=True
    ).all()

    assert len(enrollments) == expected_count, \
        f"Expected {expected_count} enrollments, got {len(enrollments)}"

    # Verify all enrollments have expected status
    for enrollment in enrollments:
        assert enrollment.request_status == expected_status, \
            f"Enrollment {enrollment.id} has status {enrollment.request_status}, expected {expected_status}"
        assert enrollment.is_active is True

    return enrollments


def verify_session_structure(
    db_session: Session,
    tournament_id: int,
    expected_count: int,
    expected_auto_generated: bool = True,
    expected_phases: Optional[Dict[str, int]] = None
) -> List[SessionModel]:
    """
    Verify session structure for a tournament

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID
        expected_count: Expected total number of sessions
        expected_auto_generated: Expected auto_generated flag value
        expected_phases: Dict mapping phase names to expected counts
                        Example: {"Knockout": 7} or {"Knockout": {"QF": 4, "SF": 2, "F": 1}}

    Returns:
        List of SessionModel objects

    Raises:
        AssertionError: If verification fails
    """
    sessions = db_session.query(SessionModel).filter_by(
        semester_id=tournament_id,
        auto_generated=expected_auto_generated
    ).all()

    assert len(sessions) == expected_count, \
        f"Expected {expected_count} sessions, got {len(sessions)}"

    # Verify all sessions have required tournament metadata
    for session in sessions:
        assert session.auto_generated == expected_auto_generated
        if expected_auto_generated:
            assert session.tournament_phase is not None, \
                f"Session {session.id} missing tournament_phase"
            assert session.tournament_round is not None, \
                f"Session {session.id} missing tournament_round"

    # Verify phase distribution if specified
    if expected_phases is not None:
        phase_counts = {}
        for session in sessions:
            phase = session.tournament_phase
            if phase not in phase_counts:
                phase_counts[phase] = 0
            phase_counts[phase] += 1

        for phase, expected in expected_phases.items():
            actual = phase_counts.get(phase, 0)
            assert actual == expected, \
                f"Expected {expected} sessions in phase '{phase}', got {actual}"

    return sessions


def verify_booking_enrollment_links(
    db_session: Session,
    tournament_id: int,
    expected_link_count: int
) -> List[Booking]:
    """
    Verify that bookings are correctly linked to enrollments

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID
        expected_link_count: Expected number of bookings with enrollment_id

    Returns:
        List of Booking objects

    Raises:
        AssertionError: If verification fails
    """
    bookings = db_session.query(Booking).join(
        SessionModel, Booking.session_id == SessionModel.id
    ).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    # Verify enrollment_id is set for all bookings
    linked_bookings = [b for b in bookings if b.enrollment_id is not None]

    assert len(linked_bookings) == expected_link_count, \
        f"Expected {expected_link_count} bookings with enrollment_id, got {len(linked_bookings)}"

    # Verify each booking's enrollment exists and matches user_id
    for booking in linked_bookings:
        enrollment = db_session.query(SemesterEnrollment).filter_by(
            id=booking.enrollment_id
        ).first()

        assert enrollment is not None, \
            f"Booking {booking.id} references non-existent enrollment {booking.enrollment_id}"
        assert enrollment.user_id == booking.user_id, \
            f"Booking {booking.id} user_id mismatch: booking.user_id={booking.user_id}, enrollment.user_id={enrollment.user_id}"

    return bookings


def verify_attendance_records(
    db_session: Session,
    tournament_id: int,
    expected_count: int,
    expected_status_distribution: Optional[Dict[str, int]] = None
) -> List[Attendance]:
    """
    Verify attendance records for tournament sessions

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID
        expected_count: Expected total attendance records
        expected_status_distribution: Optional dict mapping status to count
                                      Example: {"present": 50, "absent": 10}

    Returns:
        List of Attendance objects

    Raises:
        AssertionError: If verification fails
    """
    attendances = db_session.query(Attendance).join(
        SessionModel, Attendance.session_id == SessionModel.id
    ).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    assert len(attendances) == expected_count, \
        f"Expected {expected_count} attendance records, got {len(attendances)}"

    # Verify status distribution if specified
    if expected_status_distribution is not None:
        status_counts = {}
        for attendance in attendances:
            status = attendance.status.value if hasattr(attendance.status, 'value') else str(attendance.status)
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1

        for status, expected in expected_status_distribution.items():
            actual = status_counts.get(status, 0)
            assert actual == expected, \
                f"Expected {expected} attendance with status '{status}', got {actual}"

    return attendances


def verify_user_credit_balance(
    db_session: Session,
    user_id: int,
    expected_balance: int
) -> User:
    """
    Verify user credit balance

    Args:
        db_session: SQLAlchemy session
        user_id: User ID
        expected_balance: Expected credit balance

    Returns:
        User object

    Raises:
        AssertionError: If verification fails
    """
    user = db_session.query(User).filter_by(id=user_id).first()

    assert user is not None, f"User {user_id} not found"
    assert user.credits == expected_balance, \
        f"Expected user {user_id} to have {expected_balance} credits, got {user.credits}"

    return user


def print_tournament_summary(
    db_session: Session,
    tournament_id: int
) -> Dict[str, Any]:
    """
    Print comprehensive tournament summary for debugging

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID

    Returns:
        Dict with all tournament-related counts and states
    """
    tournament = db_session.query(Semester).filter_by(id=tournament_id).first()

    if tournament is None:
        print(f"❌ Tournament {tournament_id} not found")
        return {}

    enrollments = db_session.query(SemesterEnrollment).filter_by(
        semester_id=tournament_id,
        is_active=True
    ).all()

    sessions = db_session.query(SessionModel).filter_by(
        semester_id=tournament_id
    ).all()

    bookings = db_session.query(Booking).join(
        SessionModel, Booking.session_id == SessionModel.id
    ).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    attendances = db_session.query(Attendance).join(
        SessionModel, Attendance.session_id == SessionModel.id
    ).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    summary = {
        "tournament_id": tournament.id,
        "name": tournament.name,
        "status": str(tournament.tournament_status),
        "tournament_type_id": tournament.tournament_type_id,
        "sessions_generated": tournament.sessions_generated,
        "max_players": tournament.max_players,
        "enrollment_count": len(enrollments),
        "session_count": len(sessions),
        "booking_count": len(bookings),
        "attendance_count": len(attendances)
    }

    print("\n" + "="*70)
    print(f"TOURNAMENT SUMMARY - ID: {tournament_id}")
    print("="*70)
    print(f"Name: {tournament.name}")
    print(f"Status: {tournament.tournament_status}")
    print(f"Tournament Type ID: {tournament.tournament_type_id}")
    print(f"Sessions Generated: {tournament.sessions_generated}")
    print(f"Max Players: {tournament.max_players}")
    print(f"-"*70)
    print(f"Enrollments: {len(enrollments)}")
    print(f"Sessions: {len(sessions)}")
    print(f"Bookings: {len(bookings)}")
    print(f"Attendance: {len(attendances)}")
    print("="*70)

    return summary


def verify_complete_workflow_consistency(
    db_session: Session,
    tournament_id: int,
    expected_player_count: int,
    expected_session_count: int
) -> bool:
    """
    Comprehensive consistency check for complete tournament workflow

    Verifies:
    1. Tournament status is COMPLETED
    2. Correct number of enrollments
    3. Correct number of sessions
    4. All sessions have tournament metadata
    5. Attendance records exist

    Args:
        db_session: SQLAlchemy session
        tournament_id: Tournament ID
        expected_player_count: Expected number of enrolled players
        expected_session_count: Expected number of sessions

    Returns:
        True if all checks pass

    Raises:
        AssertionError: If any check fails
    """
    # 1. Verify tournament
    tournament_data = verify_tournament_state(
        db_session,
        tournament_id,
        expected_status="COMPLETED"
    )

    # 2. Verify enrollments
    enrollments = verify_enrollment_consistency(
        db_session,
        tournament_id,
        expected_count=expected_player_count
    )

    # 3. Verify sessions
    sessions = verify_session_structure(
        db_session,
        tournament_id,
        expected_count=expected_session_count,
        expected_auto_generated=True
    )

    # 4. Verify attendance exists
    attendances = db_session.query(Attendance).join(
        SessionModel, Attendance.session_id == SessionModel.id
    ).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    assert len(attendances) > 0, "No attendance records found for completed tournament"

    # 5. Print summary
    print_tournament_summary(db_session, tournament_id)

    print(f"\n✅ Complete workflow consistency verified!")
    print(f"   - Tournament: COMPLETED")
    print(f"   - Players: {len(enrollments)}")
    print(f"   - Sessions: {len(sessions)}")
    print(f"   - Attendance: {len(attendances)}")

    return True
