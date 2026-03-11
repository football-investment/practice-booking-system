"""
Integration test: XP grant lifecycle (service-layer)

Tests the gamification XP service using a SAVEPOINT-isolated real DB session.
All writes are rolled back at teardown — no data persists.

Covers:
  1. award_attendance_xp grants base XP (50) for an Attendance record
  2. award_attendance_xp is idempotent — second call returns same amount, no double-grant
  3. award_xp updates UserStats.total_xp and User.xp_balance
  4. No XP awarded when attendance_id is not found (graceful return 0)
"""
import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.attendance import Attendance, AttendanceStatus, ConfirmationStatus
from app.models.gamification import UserStats
from app.models.session import Session as SessionModel, SessionType
from app.models.semester import Semester, SemesterStatus
from app.models.booking import Booking, BookingStatus
from app.services.gamification.xp_service import award_attendance_xp, award_xp
from app.services.gamification.utils import get_or_create_user_stats


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_bp() -> datetime:
    return datetime.now(ZoneInfo("Europe/Budapest")).replace(tzinfo=None)


def _make_session(test_db, semester_id: int, instructor_id: int) -> SessionModel:
    """Create a minimal on-site session."""
    now = _now_bp()
    s = SessionModel(
        title="XP Test Session",
        semester_id=semester_id,
        session_type=SessionType.on_site,
        date_start=now - timedelta(minutes=30),
        date_end=now + timedelta(minutes=30),
        instructor_id=instructor_id,
    )
    test_db.add(s)
    test_db.commit()
    test_db.refresh(s)
    return s


def _make_semester(test_db) -> Semester:
    import uuid
    sem = Semester(
        code=f"XP-{uuid.uuid4().hex[:6].upper()}",
        name="XP Test Semester",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=SemesterStatus.ONGOING,
    )
    test_db.add(sem)
    test_db.commit()
    test_db.refresh(sem)
    return sem


def _make_attendance(test_db, user_id: int, session_id: int,
                     status: AttendanceStatus = AttendanceStatus.present) -> Attendance:
    att = Attendance(
        user_id=user_id,
        session_id=session_id,
        status=status,
        xp_earned=0,
    )
    test_db.add(att)
    test_db.commit()
    test_db.refresh(att)
    return att


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAwardAttendanceXp:

    def test_awards_base_xp_for_present_attendance(
        self, test_db, student_user, instructor_user
    ):
        """award_attendance_xp on a new Attendance record → xp_earned=50 (base XP)."""
        sem = _make_semester(test_db)
        session = _make_session(test_db, sem.id, instructor_user.id)
        att = _make_attendance(test_db, student_user.id, session.id, AttendanceStatus.present)

        xp = award_attendance_xp(test_db, att.id)

        assert xp == 50

        test_db.expire_all()
        updated_att = test_db.query(Attendance).filter(Attendance.id == att.id).first()
        assert updated_att.xp_earned == 50

    def test_updates_user_stats_total_xp(
        self, test_db, student_user, instructor_user
    ):
        """award_attendance_xp creates or updates UserStats.total_xp."""
        sem = _make_semester(test_db)
        session = _make_session(test_db, sem.id, instructor_user.id)
        att = _make_attendance(test_db, student_user.id, session.id, AttendanceStatus.present)

        # Ensure stats start from 0
        stats_before = get_or_create_user_stats(test_db, student_user.id)
        xp_before = stats_before.total_xp or 0

        award_attendance_xp(test_db, att.id)

        test_db.expire_all()
        stats_after = test_db.query(UserStats).filter(
            UserStats.user_id == student_user.id
        ).first()
        assert stats_after.total_xp == xp_before + 50

    def test_idempotent_second_call_returns_same_xp(
        self, test_db, student_user, instructor_user
    ):
        """Calling award_attendance_xp twice does NOT double-grant XP."""
        sem = _make_semester(test_db)
        session = _make_session(test_db, sem.id, instructor_user.id)
        att = _make_attendance(test_db, student_user.id, session.id, AttendanceStatus.present)

        xp1 = award_attendance_xp(test_db, att.id)

        # Capture total_xp after first grant
        test_db.expire_all()
        stats_mid = test_db.query(UserStats).filter(
            UserStats.user_id == student_user.id
        ).first()
        total_after_first = stats_mid.total_xp

        # Second call — must NOT add more XP
        xp2 = award_attendance_xp(test_db, att.id)

        assert xp1 == xp2  # Same amount returned

        test_db.expire_all()
        stats_final = test_db.query(UserStats).filter(
            UserStats.user_id == student_user.id
        ).first()
        assert stats_final.total_xp == total_after_first  # No change

    def test_nonexistent_attendance_id_returns_zero(self, test_db):
        """award_attendance_xp with invalid attendance_id returns 0, no crash."""
        xp = award_attendance_xp(test_db, attendance_id=999999)
        assert xp == 0


class TestAwardXp:

    def test_award_xp_updates_user_stats_and_balance(
        self, test_db, student_user
    ):
        """award_xp grants XP, updates UserStats.total_xp and User.xp_balance."""
        from app.models.user import User

        stats_before = get_or_create_user_stats(test_db, student_user.id)
        xp_before = stats_before.total_xp or 0

        award_xp(test_db, student_user.id, 100, "Integration test reward")

        test_db.expire_all()
        stats_after = test_db.query(UserStats).filter(
            UserStats.user_id == student_user.id
        ).first()
        assert stats_after.total_xp == xp_before + 100

        user_after = test_db.query(User).filter(User.id == student_user.id).first()
        assert (user_after.xp_balance or 0) >= 100

    def test_award_xp_cumulative_multiple_calls(
        self, test_db, student_user
    ):
        """award_xp called twice accumulates XP (not idempotent by design)."""
        stats_before = get_or_create_user_stats(test_db, student_user.id)
        xp_before = stats_before.total_xp or 0

        award_xp(test_db, student_user.id, 50, "First award")
        award_xp(test_db, student_user.id, 75, "Second award")

        test_db.expire_all()
        stats_after = test_db.query(UserStats).filter(
            UserStats.user_id == student_user.id
        ).first()
        assert stats_after.total_xp == xp_before + 125
