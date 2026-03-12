"""
Communications Smoke Tests — Domain A (Sprint 2026-03-12)

Covers the Communications Hub end-to-end against a SAVEPOINT-isolated
real PostgreSQL database (no mocks):

  COM-01  GET /notifications returns 200 with notification list
  COM-02  GET /notifications shows unread badge count
  COM-03  POST /notifications/{id}/read marks notification read
  COM-04  POST /notifications/read-all marks all notifications read
  COM-05  POST /notifications/{id}/delete removes notification
  COM-06  GET /messages returns 200 (inbox tab default)
  COM-07  GET /messages?tab=sent shows sent messages
  COM-08  GET /messages?tab=compose shows compose form with recipients
  COM-09  POST /messages/send creates message and redirects
  COM-10  GET /messages/{id} auto-marks message read, shows detail
  COM-11  POST /messages/{id}/delete removes message
  COM-12  GET /unread-counts returns JSON with notification + message counts
  COM-13  GET /unread-counts when unauthenticated returns 0/0 (no redirect)

Auth: get_current_user_web overridden → student_user or admin_user injected.
CSRF: Authorization: Bearer bypass header skips CSRFProtectionMiddleware.
DB:   SAVEPOINT-isolated; all changes rolled back after each test.
"""

import uuid
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web, get_current_user_optional
from app.models.user import User, UserRole
from app.models.notification import Notification, NotificationType
from app.models.message import Message, MessagePriority
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


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def student_user(test_db: Session) -> User:
    u = User(
        email=f"comm-student+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Comm Student",
        password_hash=get_password_hash("pass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


@pytest.fixture(scope="function")
def other_user(test_db: Session) -> User:
    u = User(
        email=f"comm-other+{uuid.uuid4().hex[:8]}@lfa.com",
        name="Comm Other",
        password_hash=get_password_hash("pass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db.add(u)
    test_db.commit()
    test_db.refresh(u)
    return u


# ── Clients ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def student_client(test_db: Session, student_user: User) -> TestClient:
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_web] = lambda: student_user
    # Also override optional dep so /unread-counts uses the same test user
    app.dependency_overrides[get_current_user_optional] = lambda: student_user

    with TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"}) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def anon_client(test_db: Session) -> TestClient:
    """Unauthenticated client — get_current_user_optional returns None."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    # Return None from optional dep so unread-counts returns 0/0
    app.dependency_overrides[get_current_user_optional] = lambda: None

    with TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"}, follow_redirects=False) as c:
        yield c

    app.dependency_overrides.clear()


# ── Notification fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def unread_notification(test_db: Session, student_user: User) -> Notification:
    n = Notification(
        user_id=student_user.id,
        title="Test Notification",
        message="This is a test notification message.",
        type=NotificationType.GENERAL,
        is_read=False,
    )
    test_db.add(n)
    test_db.commit()
    test_db.refresh(n)
    return n


@pytest.fixture
def read_notification(test_db: Session, student_user: User) -> Notification:
    n = Notification(
        user_id=student_user.id,
        title="Read Notification",
        message="Already read notification.",
        type=NotificationType.BOOKING_CONFIRMED,
        is_read=True,
        read_at=datetime.now(timezone.utc),
    )
    test_db.add(n)
    test_db.commit()
    test_db.refresh(n)
    return n


# ── Message fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def inbox_message(test_db: Session, student_user: User, other_user: User) -> Message:
    m = Message(
        sender_id=other_user.id,
        recipient_id=student_user.id,
        subject="Hello from other",
        message="This is an inbox message body.",
        priority=MessagePriority.NORMAL,
        is_read=False,
    )
    test_db.add(m)
    test_db.commit()
    test_db.refresh(m)
    return m


@pytest.fixture
def sent_message(test_db: Session, student_user: User, other_user: User) -> Message:
    m = Message(
        sender_id=student_user.id,
        recipient_id=other_user.id,
        subject="Sent from student",
        message="This is a sent message body.",
        priority=MessagePriority.HIGH,
        is_read=False,
    )
    test_db.add(m)
    test_db.commit()
    test_db.refresh(m)
    return m


# ── COM-01 Notifications page loads ───────────────────────────────────────────

class TestNotificationsPage:
    def test_com01_notifications_page_loads(self, student_client: TestClient):
        r = student_client.get("/notifications")
        assert r.status_code == 200
        assert "Notifications" in r.text

    def test_com02_unread_badge_shown_when_unread(
        self, student_client: TestClient, unread_notification: Notification
    ):
        r = student_client.get("/notifications")
        assert r.status_code == 200
        assert "Unread" in r.text or "badge-count" in r.text

    def test_com02_empty_state_when_no_notifications(self, student_client: TestClient):
        r = student_client.get("/notifications")
        assert r.status_code == 200
        # No notifications → empty state
        assert "No notifications" in r.text or "all caught up" in r.text

    def test_com03_mark_notification_read(
        self, student_client: TestClient, unread_notification: Notification
    ):
        r = student_client.post(f"/notifications/{unread_notification.id}/read")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_com04_mark_all_notifications_read(
        self, student_client: TestClient, unread_notification: Notification, test_db: Session
    ):
        r = student_client.post("/notifications/read-all")
        # Redirects to /notifications?success=marked
        assert r.status_code in (200, 303)

    def test_com05_delete_notification(
        self, student_client: TestClient, unread_notification: Notification
    ):
        r = student_client.post(f"/notifications/{unread_notification.id}/delete")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_com03_mark_read_unknown_id_does_not_crash(self, student_client: TestClient):
        """Marking a non-existent notification read returns 200 (idempotent)."""
        r = student_client.post("/notifications/999999/read")
        assert r.status_code == 200

    def test_com05_delete_unknown_id_does_not_crash(self, student_client: TestClient):
        r = student_client.post("/notifications/999999/delete")
        assert r.status_code == 200


# ── COM-06..11 Messages ───────────────────────────────────────────────────────

class TestMessagesPage:
    def test_com06_inbox_tab_loads(self, student_client: TestClient, inbox_message: Message):
        r = student_client.get("/messages?tab=inbox")
        assert r.status_code == 200
        assert "Messages" in r.text
        assert inbox_message.subject in r.text

    def test_com07_sent_tab_shows_sent_messages(
        self, student_client: TestClient, sent_message: Message
    ):
        r = student_client.get("/messages?tab=sent")
        assert r.status_code == 200
        assert sent_message.subject in r.text

    def test_com08_compose_tab_shows_recipients(
        self, student_client: TestClient, other_user: User
    ):
        r = student_client.get("/messages?tab=compose")
        assert r.status_code == 200
        assert "compose-form" in r.text
        assert other_user.name in r.text

    def test_com08_default_tab_is_inbox(self, student_client: TestClient):
        r = student_client.get("/messages")
        assert r.status_code == 200
        assert "tab-inbox" in r.text

    def test_com09_send_message_creates_record(
        self, student_client: TestClient, other_user: User, test_db: Session
    ):
        r = student_client.post(
            "/messages/send",
            data={
                "recipient_id": other_user.id,
                "subject": "Smoke Test Subject",
                "message": "Smoke test message body.",
                "priority": "NORMAL",
            },
            follow_redirects=False,
        )
        # Should redirect after sending
        assert r.status_code in (200, 303)
        # Verify message was created
        msg = (
            test_db.query(Message)
            .filter(Message.subject == "Smoke Test Subject")
            .first()
        )
        assert msg is not None
        assert msg.sender_id == student_client.app.dependency_overrides[get_current_user_web]().id

    def test_com09_send_to_invalid_recipient_redirects_with_error(
        self, student_client: TestClient
    ):
        r = student_client.post(
            "/messages/send",
            data={
                "recipient_id": 999999,
                "subject": "Subject",
                "message": "Body",
                "priority": "NORMAL",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert "invalid_recipient" in str(r.url)

    def test_com10_message_detail_auto_marks_read(
        self, student_client: TestClient, inbox_message: Message, test_db: Session
    ):
        assert inbox_message.is_read is False
        r = student_client.get(f"/messages/{inbox_message.id}")
        assert r.status_code == 200
        assert inbox_message.subject in r.text
        # Verify auto-marked read in DB
        test_db.refresh(inbox_message)
        assert inbox_message.is_read is True

    def test_com10_message_detail_sent_message(
        self, student_client: TestClient, sent_message: Message
    ):
        r = student_client.get(f"/messages/{sent_message.id}")
        assert r.status_code == 200
        assert sent_message.subject in r.text

    def test_com10_message_detail_not_found_redirects(self, student_client: TestClient):
        r = student_client.get("/messages/999999", follow_redirects=True)
        assert r.status_code == 200
        assert "not_found" in str(r.url)

    def test_com11_delete_inbox_message(
        self, student_client: TestClient, inbox_message: Message, test_db: Session
    ):
        r = student_client.post(f"/messages/{inbox_message.id}/delete")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        deleted = test_db.query(Message).filter(Message.id == inbox_message.id).first()
        assert deleted is None

    def test_com11_delete_sent_message(
        self, student_client: TestClient, sent_message: Message, test_db: Session
    ):
        r = student_client.post(f"/messages/{sent_message.id}/delete")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_com11_delete_unknown_message_returns_ok(self, student_client: TestClient):
        r = student_client.post("/messages/999999/delete")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


# ── COM-12..13 Unread counts endpoint ────────────────────────────────────────

class TestUnreadCounts:
    def test_com12_authenticated_returns_counts(
        self,
        student_client: TestClient,
        unread_notification: Notification,
        inbox_message: Message,
    ):
        r = student_client.get("/unread-counts")
        assert r.status_code == 200
        data = r.json()
        assert "notifications" in data
        assert "messages" in data
        assert data["notifications"] >= 1
        assert data["messages"] >= 1

    def test_com12_authenticated_zero_when_all_read(self, student_client: TestClient):
        r = student_client.get("/unread-counts")
        assert r.status_code == 200
        data = r.json()
        assert data["notifications"] == 0
        assert data["messages"] == 0

    def test_com13_unauthenticated_returns_zero_not_redirect(self, anon_client: TestClient):
        r = anon_client.get("/unread-counts")
        assert r.status_code == 200
        data = r.json()
        assert data == {"notifications": 0, "messages": 0}
