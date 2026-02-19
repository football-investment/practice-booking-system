"""
Integration test — Campus-scope guard (end-to-end HTTP layer)

Proves that `_assert_campus_scope` works at the HTTP boundary, not just
at the unit level.

Test scenario:
  I-01  Instructor logs in → POSTs generate-sessions with campus_ids=[101, 202]
        → Response: HTTP 403
        → DB: 0 sessions created (guard fires BEFORE any DB writes)

  I-02  Overrides variant — campus_schedule_overrides with 2 keys → HTTP 403
        → DB: 0 sessions created

  I-03  Admin with campus_ids=[101, 202] → guard does NOT raise 403
        (may still fail with 400 if tournament not ready, but NOT 403)

Setup:
  - PostgreSQL with transactional rollback (all changes undone after test)
  - FastAPI TestClient with the rolled-back session injected via get_db override
  - Users created in the rolled-back transaction (auto-cleaned)
  - JWT tokens minted directly (no login HTTP round-trip)

Why NOT a live-server test:
  Transactional rollback gives full isolation without manual cleanup.
  The point of this test is the HTTP 403 — not the session generation path.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel
from app.core.security import get_password_hash
from app.core.auth import create_access_token


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_instructor(db: Session) -> User:
    """Create a fresh instructor in the rolled-back transaction."""
    user = User(
        email=f"instructor+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Test Scope Instructor",
        password_hash=get_password_hash("test_pass"),
        role=UserRole.INSTRUCTOR,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_admin(db: Session) -> User:
    """Create a fresh admin in the rolled-back transaction."""
    user = User(
        email=f"admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Test Scope Admin",
        password_hash=get_password_hash("test_pass"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _token(user: User) -> str:
    return create_access_token(data={"sub": user.email})


def _make_client(db: Session) -> TestClient:
    """TestClient whose get_db dependency yields the rollback-wrapped session."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False)


GENERATE_URL = "/api/v1/tournaments/{tid}/generate-sessions"


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.tournament
class TestCampusScopeGuardHTTP:
    """
    HTTP-layer integration tests for the campus-scope guard.

    Uses postgres_db with transactional rollback (from tests/unit/conftest.py).
    """

    # ── I-01: instructor + campus_ids=[101,202] → 403 ─────────────────────────
    def test_instructor_two_campus_ids_returns_403(self, postgres_db: Session):
        """
        I-01: Instructor POSTs generate-sessions with 2 campus_ids.
        Expected: HTTP 403, no sessions in DB.
        """
        instructor = _make_instructor(postgres_db)
        token = _token(instructor)
        client = _make_client(postgres_db)

        try:
            # Count sessions before the request (any tournament ID)
            sessions_before = postgres_db.query(SessionModel).count()

            response = client.post(
                GENERATE_URL.format(tid=99999),  # non-existent tournament: irrelevant, guard fires first
                json={
                    "parallel_fields": 1,
                    "session_duration_minutes": 60,
                    "break_minutes": 10,
                    "number_of_rounds": 1,
                    "campus_ids": [101, 202],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            # ── Assertion 1: HTTP status ──
            assert response.status_code == 403, (
                f"Expected 403, got {response.status_code}. Body: {response.text}"
            )

            # ── Assertion 2: Error message references campus scope ──
            # Custom exception handler wraps error as {"error": {"message": "..."}}
            body = response.json()
            message = body.get("error", {}).get("message", body.get("detail", ""))
            assert "single campus" in message.lower(), (
                f"Expected 'single campus' in error message, got: {message!r} (full body: {body})"
            )

            # ── Assertion 3: No sessions written to DB ──
            sessions_after = postgres_db.query(SessionModel).count()
            assert sessions_after == sessions_before, (
                f"Guard should prevent DB writes. "
                f"Before={sessions_before}, After={sessions_after}"
            )

        finally:
            app.dependency_overrides.clear()

    # ── I-02: instructor + 2 campus_schedule_overrides keys → 403 ─────────────
    def test_instructor_two_override_keys_returns_403(self, postgres_db: Session):
        """
        I-02: Instructor POSTs with 2 campus_schedule_overrides keys (no campus_ids).
        Expected: HTTP 403, no sessions in DB.
        """
        instructor = _make_instructor(postgres_db)
        token = _token(instructor)
        client = _make_client(postgres_db)

        try:
            sessions_before = postgres_db.query(SessionModel).count()

            response = client.post(
                GENERATE_URL.format(tid=99999),
                json={
                    "parallel_fields": 1,
                    "session_duration_minutes": 60,
                    "break_minutes": 10,
                    "number_of_rounds": 1,
                    "campus_schedule_overrides": {
                        "101": {"parallel_fields": 2},
                        "202": {"parallel_fields": 3},
                    },
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 403, (
                f"Expected 403, got {response.status_code}. Body: {response.text}"
            )

            body = response.json()
            message = body.get("error", {}).get("message", body.get("detail", ""))
            assert "single campus" in message.lower(), (
                f"Expected 'single campus' in error message, got: {message!r} (full body: {body})"
            )

            sessions_after = postgres_db.query(SessionModel).count()
            assert sessions_after == sessions_before, (
                "No sessions must be written when guard raises 403"
            )

        finally:
            app.dependency_overrides.clear()

    # ── I-03: admin + campus_ids=[101,202] → NOT 403 ──────────────────────────
    def test_admin_two_campus_ids_not_403(self, postgres_db: Session):
        """
        I-03: Admin POSTs with 2 campus_ids — the campus-scope guard must pass
        (admin is unrestricted). The response may be 400 (tournament not found /
        not ready) but must NOT be 403.
        """
        admin = _make_admin(postgres_db)
        token = _token(admin)
        client = _make_client(postgres_db)

        try:
            response = client.post(
                GENERATE_URL.format(tid=99999),
                json={
                    "parallel_fields": 1,
                    "session_duration_minutes": 60,
                    "break_minutes": 10,
                    "number_of_rounds": 1,
                    "campus_ids": [101, 202],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            # Must NOT be 403 — guard should let admin through
            assert response.status_code != 403, (
                f"Admin must not be blocked by campus scope guard. "
                f"Got {response.status_code}: {response.text}"
            )

        finally:
            app.dependency_overrides.clear()

    # ── I-04: instructor + single campus_id → NOT 403 ─────────────────────────
    def test_instructor_single_campus_not_403(self, postgres_db: Session):
        """
        I-04: Instructor with campus_ids=[42] must NOT be rejected by the guard.
        Downstream may return 400 (tournament not found), but NOT 403.
        """
        instructor = _make_instructor(postgres_db)
        token = _token(instructor)
        client = _make_client(postgres_db)

        try:
            response = client.post(
                GENERATE_URL.format(tid=99999),
                json={
                    "parallel_fields": 1,
                    "session_duration_minutes": 60,
                    "break_minutes": 10,
                    "number_of_rounds": 1,
                    "campus_ids": [42],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code != 403, (
                f"Instructor with a single campus_id must pass the guard. "
                f"Got {response.status_code}: {response.text}"
            )

        finally:
            app.dependency_overrides.clear()
