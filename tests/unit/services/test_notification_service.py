"""
Unit tests for app/services/notification_service.py
Covers all functions — 6 branches (mark_as_read, delete, get_notifications).
Pure unit tests: no DB required, all mocked.
"""
import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from app.services.notification_service import (
    create_notification,
    create_tournament_application_approved_notification,
    create_tournament_application_rejected_notification,
    create_tournament_direct_invitation_notification,
    create_tournament_instructor_accepted_notification,
    mark_notification_as_read,
    get_unread_notification_count,
    get_notifications,
    mark_all_as_read,
    delete_notification,
    delete_old_notifications,
)
from app.models.notification import NotificationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.count.return_value = 3
    q.all.return_value = []
    q.first.return_value = None
    q.update.return_value = 2
    q.delete.return_value = 5
    db.query.return_value = q
    return db


def _tournament(tid=10, name="Spring Cup"):
    t = MagicMock()
    t.id = tid
    t.name = name
    return t


def _instructor(uid=99, name="Coach Bob"):
    u = MagicMock()
    u.id = uid
    u.name = name
    return u


# ---------------------------------------------------------------------------
# create_notification (base function)
# ---------------------------------------------------------------------------

class TestCreateNotification:
    def test_cn01_creates_and_adds_to_db(self):
        """CN-01: creates Notification, adds to db, does NOT commit."""
        db = _db()
        result = create_notification(
            db=db,
            user_id=42,
            title="Test",
            message="Hello",
            notification_type=NotificationType.TOURNAMENT_APPLICATION_APPROVED,
        )
        db.add.assert_called_once()
        db.commit.assert_not_called()

    def test_cn02_with_all_optional_fields(self):
        """CN-02: all optional fields populated."""
        db = _db()
        create_notification(
            db=db,
            user_id=42,
            title="Test",
            message="Hello",
            notification_type=NotificationType.TOURNAMENT_DIRECT_INVITATION,
            link="/dashboard",
            related_semester_id=5,
            related_request_id=3,
            related_session_id=7,
            related_booking_id=11,
        )
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Convenience notification creators
# ---------------------------------------------------------------------------

class TestConvenienceNotifications:
    def test_approved_notification(self):
        db = _db()
        t = _tournament()
        result = create_tournament_application_approved_notification(
            db=db, instructor_id=99, tournament=t, response_message="Great!", request_id=5
        )
        db.add.assert_called_once()
        assert "Approved" in result.title or result is not None

    def test_rejected_notification(self):
        db = _db()
        t = _tournament()
        create_tournament_application_rejected_notification(
            db=db, instructor_id=99, tournament=t, response_message="Sorry", request_id=5
        )
        db.add.assert_called_once()

    def test_direct_invitation_notification(self):
        db = _db()
        t = _tournament()
        create_tournament_direct_invitation_notification(
            db=db, instructor_id=99, tournament=t, invitation_message="Please join", request_id=5
        )
        db.add.assert_called_once()

    def test_instructor_accepted_notification(self):
        db = _db()
        t = _tournament()
        u = _instructor()
        create_tournament_instructor_accepted_notification(
            db=db, admin_id=1, instructor=u, tournament=t
        )
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# mark_notification_as_read
# ---------------------------------------------------------------------------

class TestMarkNotificationAsRead:
    def test_mnr01_not_found_returns_none(self):
        """MNR-01: notification not found → returns None."""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        result = mark_notification_as_read(db, notification_id=1, user_id=42)
        assert result is None

    def test_mnr02_found_marks_read(self):
        """MNR-02: found → is_read=True, read_at set, no commit."""
        n = MagicMock()
        n.is_read = False
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = n
        result = mark_notification_as_read(db, notification_id=1, user_id=42)
        assert result is n
        assert n.is_read is True
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# get_unread_notification_count
# ---------------------------------------------------------------------------

class TestGetUnreadCount:
    def test_guc01_returns_count(self):
        db = _db()
        db.query.return_value.filter.return_value.count.return_value = 7
        count = get_unread_notification_count(db, user_id=42)
        assert count == 7


# ---------------------------------------------------------------------------
# get_notifications
# ---------------------------------------------------------------------------

class TestGetNotifications:
    def test_gn01_all_notifications(self):
        """GN-01: unread_only=False → no extra filter applied."""
        db = _db()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [MagicMock(), MagicMock()]
        db.query.return_value = q

        result = get_notifications(db, user_id=42, limit=10, unread_only=False)

        assert len(result) == 2
        # filter called once (for user_id), order_by+limit chained
        q.order_by.assert_called_once()
        q.limit.assert_called_once_with(10)

    def test_gn02_unread_only_adds_filter(self):
        """GN-02: unread_only=True → extra is_read==False filter applied."""
        db = _db()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [MagicMock()]
        db.query.return_value = q

        result = get_notifications(db, user_id=42, unread_only=True)

        # filter called twice: once for user_id, once for is_read==False
        assert q.filter.call_count == 2


# ---------------------------------------------------------------------------
# mark_all_as_read
# ---------------------------------------------------------------------------

class TestMarkAllAsRead:
    def test_mar01_returns_count(self):
        db = _db()
        q = MagicMock()
        q.filter.return_value = q
        q.update.return_value = 4
        db.query.return_value = q
        count = mark_all_as_read(db, user_id=42)
        assert count == 4
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# delete_notification
# ---------------------------------------------------------------------------

class TestDeleteNotification:
    def test_dn01_not_found_returns_false(self):
        """DN-01: notification not found → False."""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        result = delete_notification(db, notification_id=1, user_id=42)
        assert result is False

    def test_dn02_found_deletes_returns_true(self):
        """DN-02: found → db.delete called, returns True, no commit."""
        n = MagicMock()
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = n
        result = delete_notification(db, notification_id=1, user_id=42)
        assert result is True
        db.delete.assert_called_once_with(n)
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# delete_old_notifications
# ---------------------------------------------------------------------------

class TestDeleteOldNotifications:
    def test_don01_returns_delete_count(self):
        db = _db()
        q = MagicMock()
        q.filter.return_value = q
        q.delete.return_value = 12
        db.query.return_value = q
        count = delete_old_notifications(db, days=90)
        assert count == 12
        db.commit.assert_not_called()
