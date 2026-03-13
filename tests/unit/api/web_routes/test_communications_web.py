"""
Unit tests for app/api/web_routes/communications.py

Covers (mock strategy: patch templates + service layer, call async functions directly):

  unread_counts()
    - unauthenticated user → {"notifications": 0, "messages": 0}
    - authenticated user with unread items → correct counts

  notifications_page()
    - calls notification_service, renders template with unread_count

  notification_mark_read()
    - delegates to notification_service.mark_notification_as_read, commits, returns {"ok": True}

  notification_delete()
    - delegates to notification_service.delete_notification, commits, returns {"ok": True}

  notifications_mark_all_read()
    - calls notification_service.mark_all_as_read, redirects 303

  messages_page()
    - queries inbox + sent + recipients, renders template

  message_detail()
    - not found → redirect to /messages?error=not_found
    - recipient opens unread → auto-marks is_read=True
    - sender views own message → no read update

  message_send()
    - invalid recipient → redirect error
    - empty fields → redirect error
    - valid → creates Message, redirects

  message_delete()
    - message found → deleted, returns {"ok": True}
    - message not found → still returns {"ok": True}
"""
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from fastapi.responses import JSONResponse, RedirectResponse

from app.api.web_routes.communications import (
    unread_counts,
    notifications_page,
    notification_mark_read,
    notification_delete,
    notifications_mark_all_read,
    messages_page,
    message_detail,
    message_send,
    message_delete,
)
from app.models.user import UserRole
from app.models.message import MessagePriority


_BASE = "app.api.web_routes.communications"


def _run(coro):
    return asyncio.run(coro)


def _user(uid=10, role=UserRole.STUDENT):
    u = MagicMock()
    u.id = uid
    u.name = "Test User"
    u.email = "test@lfa.com"
    u.role = role
    u.credit_balance = 100
    u.date_of_birth = None
    return u


def _req():
    return MagicMock()


def _db():
    return MagicMock()


# ── unread_counts ──────────────────────────────────────────────────────────────

class TestUnreadCounts:

    def test_unauthenticated_returns_zeros(self):
        req = _req()
        db = _db()
        result = _run(unread_counts(request=req, db=db, user=None))
        assert isinstance(result, JSONResponse)
        import json
        body = json.loads(result.body)
        assert body == {"notifications": 0, "messages": 0}

    def test_authenticated_returns_correct_counts(self):
        req = _req()
        db = _db()
        user = _user(uid=5)

        # notification_service.get_unread_notification_count returns 3
        # db.query(...).filter(...).count() returns 2
        with patch(f"{_BASE}.notification_service") as mock_svc:
            mock_svc.get_unread_notification_count.return_value = 3
            # Mock message count query chain
            db.query.return_value.filter.return_value.count.return_value = 2

            result = _run(unread_counts(request=req, db=db, user=user))

        import json
        body = json.loads(result.body)
        assert body == {"notifications": 3, "messages": 2}
        mock_svc.get_unread_notification_count.assert_called_once_with(db, 5)


# ── notifications_page ────────────────────────────────────────────────────────

class TestNotificationsPage:

    def test_renders_template_with_notifications(self):
        req = _req()
        db = _db()
        user = _user()
        mock_notifs = [MagicMock(), MagicMock()]

        with patch(f"{_BASE}.notification_service") as mock_svc, \
             patch(f"{_BASE}.templates") as mock_tmpl:
            mock_svc.get_notifications.return_value = mock_notifs
            mock_svc.get_unread_notification_count.return_value = 1
            mock_tmpl.TemplateResponse.return_value = MagicMock()

            _run(notifications_page(request=req, db=db, user=user))

        mock_tmpl.TemplateResponse.assert_called_once()
        call_kwargs = mock_tmpl.TemplateResponse.call_args
        ctx = call_kwargs[0][1] if call_kwargs[0] else call_kwargs[1]
        assert ctx["notifications"] == mock_notifs
        assert ctx["unread_count"] == 1
        assert ctx["user"] is user


# ── notification_mark_read / delete ───────────────────────────────────────────

class TestNotificationActions:

    def test_mark_read_delegates_to_service(self):
        db = _db()
        user = _user(uid=7)

        with patch(f"{_BASE}.notification_service") as mock_svc:
            result = _run(notification_mark_read(
                notification_id=42, db=db, user=user
            ))

        mock_svc.mark_notification_as_read.assert_called_once_with(db, 42, 7)
        db.commit.assert_called_once()
        import json
        assert json.loads(result.body) == {"ok": True}

    def test_delete_delegates_to_service(self):
        db = _db()
        user = _user(uid=7)

        with patch(f"{_BASE}.notification_service") as mock_svc:
            result = _run(notification_delete(
                notification_id=99, db=db, user=user
            ))

        mock_svc.delete_notification.assert_called_once_with(db, 99, 7)
        db.commit.assert_called_once()
        import json
        assert json.loads(result.body) == {"ok": True}


# ── notifications_mark_all_read ───────────────────────────────────────────────

class TestNotificationsMarkAllRead:

    def test_calls_service_and_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=3)

        with patch(f"{_BASE}.notification_service") as mock_svc:
            result = _run(notifications_mark_all_read(request=req, db=db, user=user))

        mock_svc.mark_all_as_read.assert_called_once_with(db, 3)
        db.commit.assert_called_once()
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303


# ── messages_page ─────────────────────────────────────────────────────────────

class TestMessagesPage:

    def test_renders_inbox_tab(self):
        req = _req()
        db = _db()
        user = _user(uid=20)

        # All three query chains (inbox, sent, unread count, recipients)
        mock_inbox = [MagicMock()]
        mock_sent = []
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_inbox
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(messages_page(request=req, tab="inbox", db=db, user=user))

        mock_tmpl.TemplateResponse.assert_called_once()
        call_kwargs = mock_tmpl.TemplateResponse.call_args
        ctx = call_kwargs[0][1] if call_kwargs[0] else call_kwargs[1]
        assert ctx["active_tab"] == "inbox"
        assert ctx["user"] is user


# ── message_detail ────────────────────────────────────────────────────────────

class TestMessageDetail:

    def test_not_found_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        db.query.return_value.filter.return_value.first.return_value = None

        result = _run(message_detail(message_id=999, request=req, db=db, user=user))

        assert isinstance(result, RedirectResponse)
        assert "not_found" in result.headers["location"]

    def test_recipient_opens_unread_marks_read(self):
        req = _req()
        db = _db()
        user = _user(uid=5)

        mock_msg = MagicMock()
        mock_msg.recipient_id = 5
        mock_msg.is_read = False
        db.query.return_value.filter.return_value.first.return_value = mock_msg

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(message_detail(message_id=1, request=req, db=db, user=user))

        assert mock_msg.is_read is True
        assert mock_msg.read_at is not None
        db.commit.assert_called_once()

    def test_sender_views_own_message_no_read_update(self):
        req = _req()
        db = _db()
        user = _user(uid=5)

        mock_msg = MagicMock()
        mock_msg.recipient_id = 99  # different user is recipient
        mock_msg.is_read = False
        db.query.return_value.filter.return_value.first.return_value = mock_msg

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(message_detail(message_id=1, request=req, db=db, user=user))

        # is_read must not be set to True by sender viewing
        assert mock_msg.is_read is False
        db.commit.assert_not_called()

    def test_recipient_views_already_read_no_commit(self):
        req = _req()
        db = _db()
        user = _user(uid=5)

        mock_msg = MagicMock()
        mock_msg.recipient_id = 5
        mock_msg.is_read = True  # already read
        db.query.return_value.filter.return_value.first.return_value = mock_msg

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(message_detail(message_id=1, request=req, db=db, user=user))

        db.commit.assert_not_called()


# ── message_send ──────────────────────────────────────────────────────────────

class TestMessageSend:

    def test_invalid_recipient_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        db.query.return_value.filter.return_value.first.return_value = None  # no recipient

        result = _run(message_send(
            request=req,
            recipient_id=999,
            subject="Hello",
            message="Body",
            priority="NORMAL",
            db=db,
            user=user,
        ))

        assert isinstance(result, RedirectResponse)
        assert "invalid_recipient" in result.headers["location"]

    def test_empty_subject_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        recipient = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = recipient

        result = _run(message_send(
            request=req,
            recipient_id=2,
            subject="   ",  # blank
            message="Body",
            priority="NORMAL",
            db=db,
            user=user,
        ))

        assert isinstance(result, RedirectResponse)
        assert "empty_fields" in result.headers["location"]

    def test_empty_message_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        recipient = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = recipient

        result = _run(message_send(
            request=req,
            recipient_id=2,
            subject="Subject",
            message="",
            priority="NORMAL",
            db=db,
            user=user,
        ))

        assert isinstance(result, RedirectResponse)
        assert "empty_fields" in result.headers["location"]

    def test_valid_send_creates_message_and_redirects(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        recipient = MagicMock()
        recipient.id = 2
        db.query.return_value.filter.return_value.first.return_value = recipient

        result = _run(message_send(
            request=req,
            recipient_id=2,
            subject="Hello",
            message="How are you?",
            priority="HIGH",
            db=db,
            user=user,
        ))

        db.add.assert_called_once()
        added_msg = db.add.call_args[0][0]
        from app.models.message import Message
        assert isinstance(added_msg, Message)
        assert added_msg.subject == "Hello"
        assert added_msg.message == "How are you?"
        assert added_msg.priority == MessagePriority.HIGH
        assert added_msg.sender_id == 1
        assert added_msg.recipient_id == 2
        db.commit.assert_called_once()

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303
        assert "success=sent" in result.headers["location"]

    def test_invalid_priority_defaults_to_normal(self):
        req = _req()
        db = _db()
        user = _user(uid=1)
        recipient = MagicMock()
        recipient.id = 2
        db.query.return_value.filter.return_value.first.return_value = recipient

        _run(message_send(
            request=req,
            recipient_id=2,
            subject="Sub",
            message="Msg",
            priority="INVALID_VALUE",
            db=db,
            user=user,
        ))

        added_msg = db.add.call_args[0][0]
        assert added_msg.priority == MessagePriority.NORMAL


# ── message_delete ────────────────────────────────────────────────────────────

class TestMessageDelete:

    def test_found_message_is_deleted(self):
        db = _db()
        user = _user(uid=5)
        mock_msg = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_msg

        result = _run(message_delete(message_id=1, db=db, user=user))

        db.delete.assert_called_once_with(mock_msg)
        db.commit.assert_called_once()
        import json
        assert json.loads(result.body) == {"ok": True}

    def test_not_found_still_returns_ok(self):
        db = _db()
        user = _user(uid=5)
        db.query.return_value.filter.return_value.first.return_value = None

        result = _run(message_delete(message_id=999, db=db, user=user))

        db.delete.assert_not_called()
        import json
        assert json.loads(result.body) == {"ok": True}
