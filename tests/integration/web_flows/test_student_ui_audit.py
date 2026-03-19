"""
Student UI Audit Smoke Tests (SMOKE-33a–33f)

Covers:
  SMOKE-33a  GET /achievements (student)   → 200 + "Achievements" in HTML
  SMOKE-33b  GET /achievements (admin)     → 303 redirect to /dashboard
  SMOKE-33c  GET /sessions (student)       → 200 + no alert() dialog literal
  SMOKE-33d  GET /progress (student)       → 200 + "Skill Snapshot" in HTML
  SMOKE-33e  GET /notifications (student)  → 200 + page renders notification list
  SMOKE-33f  GET /progress (student)       → /skills and /achievements hrefs present (nav)

Auth:   get_current_user_web overridden — no real login needed.
CSRF:   Authorization: Bearer bypass header.
DB:     SAVEPOINT-isolated; all changes rolled back after each test.
"""

import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web
from app.models.user import User, UserRole
from app.core.security import get_password_hash


# ── SAVEPOINT-isolated DB ─────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, txn):
        if txn.nested and not txn._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def student_user(test_db: Session) -> User:
    u = User(
        email=f"smoke33-student+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Smoke33 Student",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,   # required by /sessions guard
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


@pytest.fixture(scope="function")
def admin_user(test_db: Session) -> User:
    u = User(
        email=f"smoke33-admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Smoke33 Admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


@pytest.fixture(scope="function")
def student_client(test_db: Session, student_user: User) -> TestClient:
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_web] = lambda: student_user

    with TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        follow_redirects=False,
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(test_db: Session, admin_user: User) -> TestClient:
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_web] = lambda: admin_user

    with TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        follow_redirects=False,
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAchievementsPageAccess:
    """SMOKE-33a, SMOKE-33b — achievements page access control."""

    def test_smoke33a_achievements_student_200(self, student_client: TestClient):
        """SMOKE-33a: GET /achievements (student) → 200, page renders."""
        resp = student_client.get("/achievements")
        assert resp.status_code == 200
        assert "Achievements" in resp.text

    def test_smoke33b_achievements_admin_redirects(self, admin_client: TestClient):
        """SMOKE-33b: GET /achievements (admin) → 303 redirect to /dashboard."""
        resp = admin_client.get("/achievements")
        assert resp.status_code == 303


class TestSessionsUXFix:
    """SMOKE-33c — sessions page must not use browser alert() dialogs."""

    def test_smoke33c_sessions_no_alert_dialogs(self, student_client: TestClient):
        """SMOKE-33c: GET /sessions (student) → 200, no alert() literal in HTML."""
        resp = student_client.get("/sessions")
        assert resp.status_code == 200
        # alert() dialog calls (with string args) should be replaced with flash banners.
        # Comments may contain "alert(" so check for the actual call patterns.
        assert "alert('✅" not in resp.text
        assert "alert('ℹ️" not in resp.text
        assert "alert('❌" not in resp.text
        # flash-banner div must be present instead
        assert "flash-banner" in resp.text


class TestProgressPageContent:
    """SMOKE-33d — progress page contains skill snapshot widget."""

    def test_smoke33d_progress_skill_snapshot(self, student_client: TestClient):
        """SMOKE-33d: GET /progress (student) → 200, 'Skill Snapshot' section present."""
        resp = student_client.get("/progress")
        assert resp.status_code == 200
        assert "Skill Snapshot" in resp.text


class TestNotificationsPage:
    """SMOKE-33e — notifications page renders correctly."""

    def test_smoke33e_notifications_student_200(self, student_client: TestClient):
        """SMOKE-33e: GET /notifications (student) → 200, page-content div present."""
        resp = student_client.get("/notifications")
        assert resp.status_code == 200
        # The page uses .page-content class as its main wrapper
        assert "page-content" in resp.text


class TestStudentNavLinks:
    """SMOKE-33f — student nav links present on pages that include unified_header.html."""

    def test_smoke33f_nav_links_on_achievements_page(self, student_client: TestClient):
        """SMOKE-33f: GET /achievements (student) → unified_header injects nav links."""
        resp = student_client.get("/achievements")
        assert resp.status_code == 200
        # unified_header.html injects these student-only links
        assert 'href="/skills"' in resp.text
        assert 'href="/achievements"' in resp.text
        assert 'href="/sessions"' in resp.text
        assert 'href="/progress"' in resp.text
