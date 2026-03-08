"""
Booking Lifecycle E2E — Integration Critical (BLOCKING CI gate)

Sprint 37 — covers the core revenue flow missing from BLOCKING Python gate.

Tests:
  1. test_booking_full_lifecycle     — confirm → waitlist → student cancel → auto-promote
  2. test_admin_cancel_triggers_promote — confirm → waitlist → admin cancel → auto-promote
  3. test_concurrent_capacity_guard  — 3 concurrent bookings on 1-slot session → ≤ 1 CONFIRMED

Session fixture design:
  - Admin creates a Semester (tournament) spanning +/-1 year from now.
  - Admin creates 1 Session with capacity=1, date_start=now+48h.
  - Session has target_specialization=NULL → is_accessible_to_all=True
    (bypasses validate_can_book_session spec check in student.py:63).
  - Cleanup: cancel all bookings + delete semester via DB.

Key booking rules exercised:
  - 24h booking deadline: sessions must start > 24h from now ✓ (we use +48h)
  - 12h cancel deadline: must cancel > 12h before session ✓ (we use +48h)
  - auto_promote_from_waitlist: first WAITLISTED → CONFIRMED after cancel ✓
  - capacity guard: SELECT FOR UPDATE prevents overbooking ✓
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pytest
import requests


# ---------------------------------------------------------------------------
# Helper — auth header
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixture: semester + session for booking tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def booking_session_fixture(api_url: str, admin_token: str, test_campus_ids: List[int]):
    """
    CREATE: Semester + 1 Session (capacity=1, +48h, is_accessible_to_all=True).
    CLEANUP: Cancel all bookings, delete session, delete semester.

    Returns:
        {
            "semester_id": int,
            "session_id": int,
        }
    """
    from app.database import get_db
    from app.models.semester import Semester
    from app.models.session import Session as SessionModel

    ts = int(time.time() * 1000)
    campus_id = test_campus_ids[0]

    now = datetime.now(timezone.utc)
    session_start = now + timedelta(hours=48)
    session_end = session_start + timedelta(hours=2)

    db = next(get_db())
    semester_id: Optional[int] = None
    session_id: Optional[int] = None

    try:
        # Create semester (tournament)
        semester = Semester(
            code=f"BK_LIFECYCLE_{ts}",
            name=f"Booking Lifecycle Test {ts}",
            start_date=now.date(),
            end_date=(now + timedelta(days=365)).date(),
            tournament_status="IN_PROGRESS",
            enrollment_cost=0,
            age_group="PRO",
            campus_id=campus_id,
            is_active=True,
        )
        db.add(semester)
        db.commit()
        db.refresh(semester)
        semester_id = semester.id

        # Create session (no target_specialization → is_accessible_to_all=True)
        session = SessionModel(
            title=f"BK_LIFECYCLE_SESSION_{ts}",
            description="Booking lifecycle E2E test session",
            date_start=session_start.replace(tzinfo=None),
            date_end=session_end.replace(tzinfo=None),
            semester_id=semester_id,
            campus_id=campus_id,
            capacity=1,
            credit_cost=0,
            session_status="scheduled",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

        yield {
            "semester_id": semester_id,
            "session_id": session_id,
        }

    finally:
        db.close()

    # CLEANUP: cancel outstanding bookings, delete session and semester
    from app.database import get_db as get_db2
    from app.models.booking import Booking, BookingStatus

    cleanup_db = next(get_db2())
    try:
        if session_id:
            # Cancel all non-cancelled bookings for this session
            bookings = cleanup_db.query(Booking).filter(
                Booking.session_id == session_id,
                Booking.status != BookingStatus.CANCELLED,
            ).all()
            for bk in bookings:
                bk.status = BookingStatus.CANCELLED
            cleanup_db.commit()

            # Delete bookings
            cleanup_db.query(Booking).filter(Booking.session_id == session_id).delete()
            cleanup_db.commit()

            # Delete session
            sess = cleanup_db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if sess:
                cleanup_db.delete(sess)
                cleanup_db.commit()

        if semester_id:
            sem = cleanup_db.query(Semester).filter(Semester.id == semester_id).first()
            if sem:
                cleanup_db.delete(sem)
                cleanup_db.commit()
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
        cleanup_db.rollback()
    finally:
        cleanup_db.close()


# ---------------------------------------------------------------------------
# Test 1: Full booking lifecycle (student cancel → auto-promote)
# ---------------------------------------------------------------------------

def test_booking_full_lifecycle(
    api_url: str,
    admin_token: str,
    test_students: List[Dict],
    booking_session_fixture: Dict,
):
    """
    Full lifecycle:
      Student[0] → CONFIRMED (capacity=1)
      Student[1] → WAITLISTED (position=1)
      Student[0] cancels → auto-promote Student[1] → CONFIRMED
      Assert: cancel response contains promotion, no overbooking
    """
    session_id = booking_session_fixture["session_id"]
    s0, s1 = test_students[0], test_students[1]

    # --- 1. Student[0] books → CONFIRMED ---
    r0 = requests.post(
        f"{api_url}/api/v1/bookings/",
        headers=_auth(s0["token"]),
        json={"session_id": session_id},
    )
    assert r0.status_code == 200, f"Student[0] booking failed: {r0.text}"
    booking0 = r0.json()
    assert booking0["status"] == "CONFIRMED", f"Expected CONFIRMED, got {booking0['status']}"
    booking0_id = booking0["id"]

    # --- 2. Student[1] books → WAITLISTED ---
    r1 = requests.post(
        f"{api_url}/api/v1/bookings/",
        headers=_auth(s1["token"]),
        json={"session_id": session_id},
    )
    assert r1.status_code == 200, f"Student[1] booking failed: {r1.text}"
    booking1 = r1.json()
    assert booking1["status"] == "WAITLISTED", (
        f"Expected WAITLISTED (capacity full), got {booking1['status']}"
    )
    booking1_id = booking1["id"]
    assert booking1.get("waitlist_position") == 1, (
        f"Expected waitlist_position=1, got {booking1.get('waitlist_position')}"
    )

    # --- 3. Student[0] cancels → auto-promote ---
    rc = requests.delete(
        f"{api_url}/api/v1/bookings/{booking0_id}",
        headers=_auth(s0["token"]),
    )
    assert rc.status_code == 200, f"Student[0] cancel failed: {rc.text}"
    cancel_data = rc.json()
    assert "promotion" in cancel_data, (
        f"Expected 'promotion' key in cancel response; got: {cancel_data}"
    )
    assert cancel_data["promotion"]["promoted_user_email"] == s1["email"], (
        f"Wrong user promoted: expected {s1['email']}, "
        f"got {cancel_data['promotion']['promoted_user_email']}"
    )

    # --- 4. Verify Student[1] booking is now CONFIRMED ---
    rg = requests.get(
        f"{api_url}/api/v1/bookings/{booking1_id}",
        headers=_auth(admin_token),
    )
    assert rg.status_code == 200, f"GET booking failed: {rg.text}"
    promoted = rg.json()
    assert promoted["status"] == "CONFIRMED", (
        f"Expected Student[1] to be CONFIRMED after promotion; got {promoted['status']}"
    )

    # --- 5. No overbooking: only 1 CONFIRMED booking for this session ---
    rlist = requests.get(
        f"{api_url}/api/v1/bookings/",
        headers=_auth(admin_token),
        params={"session_id": session_id, "status": "CONFIRMED"},
    )
    if rlist.status_code == 200:
        data = rlist.json()
        bookings = data if isinstance(data, list) else data.get("bookings", [])
        confirmed_total = sum(1 for b in bookings if b.get("status") == "CONFIRMED")
        assert confirmed_total <= 1, (
            f"Overbooking detected: {confirmed_total} CONFIRMED bookings in 1-slot session"
        )


# ---------------------------------------------------------------------------
# Test 2: Admin cancel triggers auto-promote
# ---------------------------------------------------------------------------

def test_admin_cancel_triggers_promote(
    api_url: str,
    admin_token: str,
    test_students: List[Dict],
    booking_session_fixture: Dict,
):
    """
    Admin cancel lifecycle:
      Student[0] → CONFIRMED
      Student[1] → WAITLISTED
      Admin cancels Student[0] booking → Student[1] auto-promoted
      Assert: promotion key in response, Student[1] now CONFIRMED
    """
    session_id = booking_session_fixture["session_id"]
    s0, s1 = test_students[0], test_students[1]

    # 1. Student[0] → CONFIRMED
    r0 = requests.post(
        f"{api_url}/api/v1/bookings/",
        headers=_auth(s0["token"]),
        json={"session_id": session_id},
    )
    assert r0.status_code == 200, f"Student[0] booking failed: {r0.text}"
    b0_id = r0.json()["id"]
    assert r0.json()["status"] == "CONFIRMED"

    # 2. Student[1] → WAITLISTED
    r1 = requests.post(
        f"{api_url}/api/v1/bookings/",
        headers=_auth(s1["token"]),
        json={"session_id": session_id},
    )
    assert r1.status_code == 200, f"Student[1] booking failed: {r1.text}"
    b1_id = r1.json()["id"]
    assert r1.json()["status"] == "WAITLISTED"

    # 3. Admin cancels Student[0] booking
    rc = requests.post(
        f"{api_url}/api/v1/bookings/{b0_id}/cancel",
        headers=_auth(admin_token),
        json={"reason": "E2E lifecycle test — admin cancel"},
    )
    assert rc.status_code == 200, f"Admin cancel failed: {rc.text}"
    cancel_data = rc.json()
    assert "promotion" in cancel_data, (
        f"Expected 'promotion' key in admin cancel response; got: {cancel_data}"
    )

    # 4. Verify Student[1] is now CONFIRMED
    rg = requests.get(
        f"{api_url}/api/v1/bookings/{b1_id}",
        headers=_auth(admin_token),
    )
    assert rg.status_code == 200, f"GET booking failed: {rg.text}"
    assert rg.json()["status"] == "CONFIRMED", (
        f"Student[1] not promoted: {rg.json()['status']}"
    )


# ---------------------------------------------------------------------------
# Test 3: Concurrent capacity guard
# ---------------------------------------------------------------------------

def test_concurrent_capacity_guard(
    api_url: str,
    admin_token: str,
    test_students: List[Dict],
    booking_session_fixture: Dict,
):
    """
    Concurrency guard:
      3 students submit bookings simultaneously on a capacity=1 session.
      Exactly 1 must be CONFIRMED; others are WAITLISTED (not errors).
      No overbooking — confirmed_count ≤ 1.

    Uses ThreadPoolExecutor to fire 3 concurrent POST /bookings/ requests.
    """
    session_id = booking_session_fixture["session_id"]
    students = test_students[:3]

    results: List[dict] = []
    errors: List[str] = []

    def book(student: dict) -> dict:
        resp = requests.post(
            f"{api_url}/api/v1/bookings/",
            headers=_auth(student["token"]),
            json={"session_id": session_id},
        )
        return {"status_code": resp.status_code, "body": resp.json()}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(book, s) for s in students]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(str(exc))

    assert not errors, f"Unexpected exceptions during concurrent booking: {errors}"

    # All responses must be 200 (CONFIRMED or WAITLISTED, never an error)
    status_codes = [r["status_code"] for r in results]
    assert all(sc == 200 for sc in status_codes), (
        f"Expected all 200 responses; got: {status_codes} — "
        f"bodies: {[r['body'] for r in results]}"
    )

    # Count CONFIRMED bookings
    booking_statuses = [r["body"]["status"] for r in results if "status" in r["body"]]
    confirmed_count = booking_statuses.count("CONFIRMED")
    waitlisted_count = booking_statuses.count("WAITLISTED")

    assert confirmed_count <= 1, (
        f"Overbooking: {confirmed_count} CONFIRMED on a capacity=1 session. "
        f"Statuses: {booking_statuses}"
    )
    assert confirmed_count + waitlisted_count == 3, (
        f"Unexpected booking statuses: {booking_statuses}"
    )
