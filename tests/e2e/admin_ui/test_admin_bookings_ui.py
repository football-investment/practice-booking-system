"""
Playwright E2E — Admin Bookings UI Tests
=========================================

Tests /admin/bookings page:
  UI-BK-01: Page loads with stat cards and filter bar (no bookings)
  UI-BK-02: Confirm action — confirm() dialog → booking status CONFIRMED in DB
  UI-BK-03: Cancel action — prompt() dialog → booking status CANCELLED in DB
  UI-BK-04: Mark attendance — select present → Attendance row created in DB
  UI-BK-05: Confirm button absent for already-confirmed booking
  UI-BK-06: Cancel button absent for already-cancelled booking
  UI-BK-07: Status filter PENDING shows only PENDING bookings

Run:
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=400 pytest tests/e2e/admin_ui/ -v -s \\
        --html=tests/e2e/admin_ui/report.html --self-contained-html
"""

import os
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus

# ── Config ─────────────────────────────────────────────────────────────────────

APP_URL = os.environ.get("API_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@lfa.com")
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def ss(page, name: str) -> None:
    """Save a timestamped screenshot."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOTS_DIR / f"{ts}_{name}.png"
    page.screenshot(path=str(path), full_page=True)


def admin_login(page) -> None:
    """Log in as admin and wait for redirect to dashboard."""
    page.goto(f"{APP_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", ADMIN_EMAIL)
    page.fill("input[name=password]", os.environ.get("ADMIN_PASSWORD", "admin123"))
    page.click("button[type=submit]")
    page.wait_for_url(f"{APP_URL}/dashboard*", timeout=8000)


# ── Fixtures ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def booking_setup(db_session, target_user):
    """
    Creates Semester → Session → PENDING Booking for target_user.
    Cleans up Attendance → Booking → Session → Semester on teardown
    (teardown runs BEFORE target_user teardown, so user_id FK is satisfied).
    """
    admin = db_session.query(User).filter(User.email == ADMIN_EMAIL).first()
    if admin is None:
        pytest.skip(f"Admin user {ADMIN_EMAIL!r} not found in DB — cannot create session")

    suffix = uuid.uuid4().hex[:6].upper()
    sem = Semester(
        code=f"E2EBK-{suffix}",
        name=f"E2E Booking Sem {suffix}",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=SemesterStatus.ONGOING,
        specialization_type="FOOTBALL_SKILLS",
    )
    db_session.add(sem)
    db_session.commit()
    db_session.refresh(sem)

    now = datetime.now(ZoneInfo("Europe/Budapest")).replace(tzinfo=None)
    sess = SessionModel(
        title=f"E2E Session {suffix}",
        semester_id=sem.id,
        session_type=SessionType.on_site,
        date_start=now + timedelta(hours=24),
        date_end=now + timedelta(hours=25),
        instructor_id=admin.id,
    )
    db_session.add(sess)
    db_session.commit()
    db_session.refresh(sess)

    booking = Booking(
        user_id=target_user.id,
        session_id=sess.id,
        status=BookingStatus.PENDING,
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    yield {"semester": sem, "session": sess, "booking": booking}

    # Teardown: delete Attendance → Booking → Session → Semester
    db_session.expire_all()
    db_session.query(Attendance).filter(
        Attendance.booking_id == booking.id
    ).delete(synchronize_session=False)
    db_session.query(Booking).filter(
        Booking.session_id == sess.id
    ).delete(synchronize_session=False)
    db_session.delete(sess)
    db_session.delete(sem)
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-01: Page loads
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingsPageLoad:
    """UI-BK-01: Bookings page renders with stat cards and filter controls."""

    def test_bk01_page_loads_with_stat_cards(self, page):
        """GET /admin/bookings → 200, stat cards and filter bar visible."""
        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")
        ss(page, "BK01_bookings_page")

        assert "Internal Server Error" not in page.content()
        assert "Booking Management" in page.content()

        # Stats row: 4 cards (Confirmed, Pending, Cancelled, Waitlisted)
        assert page.locator(".stat-card").count() >= 4

        # Filter bar: status select and session select
        assert page.locator("select[name=status_filter]").is_visible()
        assert page.locator("select[name=session_id]").is_visible()


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-02: Confirm action
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingConfirmAction:
    """UI-BK-02: Confirm button triggers confirm() dialog → booking CONFIRMED in DB."""

    def test_bk02_confirm_updates_status_in_db(self, page, booking_setup, db_session):
        """Click Confirm on PENDING booking → CONFIRMED in DB."""
        booking = booking_setup["booking"]

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")
        ss(page, "BK02a_bookings_before_confirm")

        # The confirm button is in the booking row
        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible(), f"Booking row #{booking.id} not visible on page"

        confirm_btn = row.locator("button:has-text('Confirm')")
        assert confirm_btn.is_visible(), "Confirm button not visible for PENDING booking"

        # Accept the confirm() dialog, then wait for page reload (location.reload after 1s)
        page.once("dialog", lambda d: d.accept())
        with page.expect_navigation(timeout=8000):
            confirm_btn.click()
        page.wait_for_load_state("networkidle")

        ss(page, "BK02b_after_confirm")

        # DB assertion
        db_session.expire_all()
        b = db_session.query(Booking).filter(Booking.id == booking.id).first()
        assert b.status == BookingStatus.CONFIRMED, (
            f"Expected CONFIRMED in DB, got {b.status}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-03: Cancel action
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingCancelAction:
    """UI-BK-03: Cancel button triggers prompt() → booking CANCELLED in DB."""

    def test_bk03_cancel_updates_status_in_db(self, page, booking_setup, db_session):
        """Click Cancel on PENDING booking → CANCELLED in DB, notes set."""
        booking = booking_setup["booking"]
        reason = "E2E cancel reason"

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")
        ss(page, "BK03a_before_cancel")

        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible(), f"Booking row #{booking.id} not visible"

        cancel_btn = row.locator("button:has-text('Cancel')")
        assert cancel_btn.is_visible(), "Cancel button not visible"

        # cancelBooking() uses prompt() — accept with reason text
        page.once("dialog", lambda d: d.accept(reason))
        with page.expect_navigation(timeout=8000):
            cancel_btn.click()
        page.wait_for_load_state("networkidle")

        ss(page, "BK03b_after_cancel")

        # DB assertion
        db_session.expire_all()
        b = db_session.query(Booking).filter(Booking.id == booking.id).first()
        assert b.status == BookingStatus.CANCELLED, (
            f"Expected CANCELLED in DB, got {b.status}"
        )
        assert b.notes == reason, f"Expected notes='{reason}', got '{b.notes}'"
        assert b.cancelled_at is not None, "cancelled_at not set after cancel"


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-04: Mark attendance
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingMarkAttendance:
    """UI-BK-04: Mark attendance creates Attendance row in DB."""

    def test_bk04_mark_attendance_creates_db_record(self, page, booking_setup, db_session):
        """Confirm booking first (required for attendance selector), then mark present."""
        booking = booking_setup["booking"]

        # Confirm first so attendance selector appears
        db_session.expire_all()
        b = db_session.query(Booking).filter(Booking.id == booking.id).first()
        b.status = BookingStatus.CONFIRMED
        db_session.commit()

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")
        ss(page, "BK04a_confirmed_booking_row")

        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible(), f"Booking row #{booking.id} not visible"

        # Select "present" from the attendance dropdown
        att_select = row.locator(f"#att-{booking.id}")
        assert att_select.is_visible(), "Attendance select not visible for CONFIRMED booking"
        att_select.select_option("present")

        # Click the save button (💾)
        save_btn = row.locator("button:has-text('💾')")
        with page.expect_navigation(timeout=8000):
            save_btn.click()
        page.wait_for_load_state("networkidle")

        ss(page, "BK04b_after_mark_attendance")

        # DB assertion
        db_session.expire_all()
        att = db_session.query(Attendance).filter(Attendance.booking_id == booking.id).first()
        assert att is not None, "Attendance record not created in DB"
        assert att.status == AttendanceStatus.present, (
            f"Expected present, got {att.status}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-05 & 06: Button visibility
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingButtonVisibility:
    """
    UI-BK-05: Confirm button absent for already-CONFIRMED booking.
    UI-BK-06: Cancel button absent for CANCELLED booking.
    """

    def test_bk05_no_confirm_button_for_confirmed_booking(
        self, page, booking_setup, db_session
    ):
        """CONFIRMED booking row has no Confirm button (only Cancel)."""
        booking = booking_setup["booking"]

        # Set booking to CONFIRMED in DB
        db_session.expire_all()
        b = db_session.query(Booking).filter(Booking.id == booking.id).first()
        b.status = BookingStatus.CONFIRMED
        db_session.commit()

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")

        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible()
        # Template: Confirm button only shown when status == PENDING
        assert not row.locator("button:has-text('Confirm')").is_visible(), (
            "Confirm button should NOT be visible for CONFIRMED booking"
        )
        # Cancel should still be visible (shown when status != CANCELLED)
        assert row.locator("button:has-text('Cancel')").is_visible()

    def test_bk06_no_cancel_button_for_cancelled_booking(
        self, page, booking_setup, db_session
    ):
        """CANCELLED booking row has no Cancel button."""
        booking = booking_setup["booking"]

        # Set booking to CANCELLED in DB
        db_session.expire_all()
        b = db_session.query(Booking).filter(Booking.id == booking.id).first()
        b.status = BookingStatus.CANCELLED
        db_session.commit()

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings")
        page.wait_for_load_state("networkidle")

        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible()
        # Template: Cancel button only shown when status != CANCELLED
        assert not row.locator("button:has-text('Cancel')").is_visible(), (
            "Cancel button should NOT be visible for CANCELLED booking"
        )


# ─────────────────────────────────────────────────────────────────────────────
# UI-BK-07: Status filter
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminBookingsFilter:
    """UI-BK-07: Status filter shows only matching bookings."""

    def test_bk07_pending_filter_shows_pending_booking(
        self, page, booking_setup, db_session
    ):
        """Filter status=PENDING → our PENDING booking row is visible."""
        booking = booking_setup["booking"]  # already PENDING

        admin_login(page)
        page.goto(f"{APP_URL}/admin/bookings?status_filter=PENDING")
        page.wait_for_load_state("networkidle")
        ss(page, "BK07_pending_filter")

        assert "Internal Server Error" not in page.content()
        # Our PENDING booking should appear
        row = page.locator(f"#booking-row-{booking.id}")
        assert row.is_visible(), (
            f"PENDING booking row #{booking.id} not found with status_filter=PENDING"
        )
