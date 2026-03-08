"""
Unit tests for app/api/api_v1/endpoints/messages.py

Covers all endpoint functions:
  get_inbox_messages:
    unread_only=False → all messages returned with counts
    unread_only=True  → adds is_read filter, counts still correct
    pagination: page/size applied via offset/limit
    empty inbox → zero counts

  get_sent_messages:
    basic pagination + counts
    empty sent box

  get_message:
    not found → 404
    found, not sender and not recipient → 403
    found, recipient, unread → marks read, commits, refreshes
    found, recipient, already read → no commit
    found, sender (not recipient) → returns without marking read

  create_message:
    recipient not found → 404
    success → new Message created, committed, refreshed, re-queried

  create_message_by_nickname:
    recipient nickname not found → 404
    success → message created and returned
    unexpected exception → 500 + rollback

  update_message:
    not found → 404
    message.message update, not sender → 403
    message.message update, sender → success, edits attrs
    is_read update, not recipient → 403
    is_read=True update, recipient → read_at set
    is_read=False update, recipient → read_at cleared
    no update fields → 400

  get_available_users:
    returns active users with nicknames
    empty list

  delete_message:
    not found → 404
    not sender and not recipient → 403
    authorized (sender) → deleted, commit
    authorized (recipient) → deleted, commit

  delete_conversation:
    other user not found → 404
    no messages → deleted_count=0, commit
    multiple messages → all deleted, count matches
    response includes other_user name
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
from fastapi import HTTPException

from app.api.api_v1.endpoints.messages import (
    get_inbox_messages,
    get_sent_messages,
    get_message,
    create_message,
    create_message_by_nickname,
    update_message,
    get_available_users,
    delete_message,
    delete_conversation,
)
from app.schemas.message import (
    MessageCreate,
    MessageCreateByNickname,
    MessageUpdate,
    MessagePriority,
)

_BASE = "app.api.api_v1.endpoints.messages"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = 42
OTHER_ID = 7


def _user(uid=USER_ID, name="Alice"):
    u = MagicMock()
    u.id = uid
    u.name = name
    u.email = f"user{uid}@test.com"
    u.nickname = f"nick_{uid}"
    return u


def _message(
    mid=1,
    sender_id=USER_ID,
    recipient_id=OTHER_ID,
    is_read=False,
    is_edited=False,
):
    m = MagicMock()
    m.id = mid
    m.sender_id = sender_id
    m.recipient_id = recipient_id
    m.subject = "Test Subject"
    m.message = "Test message body"
    m.priority = "NORMAL"
    m.is_read = is_read
    m.is_edited = is_edited
    m.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    m.read_at = None
    m.edited_at = None
    return m


def _q(first=None, all_=None, count_val=0):
    """Fluent query mock: every chainable method returns self."""
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.group_by.return_value = q
    q.with_for_update.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count_val
    return q


def _seq_db(*vals):
    """
    Build a db mock whose n-th db.query() call returns vals[n].
    Each val can be:
      list  → .all() returns it
      int   → .count() returns it (as a single mock, not used here)
      else  → .first() returns it
    """
    mocks = []
    for v in vals:
        if isinstance(v, list):
            mocks.append(_q(all_=v))
        else:
            mocks.append(_q(first=v))

    idx = [0]

    def _side(*args, **kwargs):
        i = idx[0]
        idx[0] += 1
        if i < len(mocks):
            return mocks[i]
        return _q()

    db = MagicMock()
    db.query.side_effect = _side
    return db


# ===========================================================================
# get_inbox_messages
# ===========================================================================

class TestGetInboxMessages:
    """Tests for the /inbox endpoint."""

    @patch(f"{_BASE}.MessageList")
    def test_unread_only_false_returns_all(self, MockMessageList):
        """unread_only=False: no extra is_read filter; counts and messages returned."""
        msg = _message()
        main_q = _q(all_=[msg])
        total_q = _q(count_val=0)
        total_q.count.side_effect = [3, 1]

        db = MagicMock()
        db.query.side_effect = [main_q, total_q]

        cu = _user()
        mock_list_instance = MagicMock()
        MockMessageList.return_value = mock_list_instance

        result = get_inbox_messages(page=1, size=50, unread_only=False, db=db, current_user=cu)

        MockMessageList.assert_called_once_with(
            messages=[msg],
            total_count=3,
            unread_count=1,
        )
        assert result == mock_list_instance

    @patch(f"{_BASE}.MessageList")
    def test_unread_only_true_adds_filter(self, MockMessageList):
        """unread_only=True: filter(Message.is_read == False) called on main query."""
        msg = _message(is_read=False)
        main_q = _q(all_=[msg])
        total_q = _q(count_val=0)
        total_q.count.side_effect = [5, 2]

        db = MagicMock()
        db.query.side_effect = [main_q, total_q]

        cu = _user()
        MockMessageList.return_value = MagicMock()

        get_inbox_messages(page=1, size=50, unread_only=True, db=db, current_user=cu)

        # Main query should have had filter called twice (recipient_id + is_read==False)
        assert main_q.filter.call_count == 2

        MockMessageList.assert_called_once_with(
            messages=[msg],
            total_count=5,
            unread_count=2,
        )

    @patch(f"{_BASE}.MessageList")
    def test_pagination_applies_offset_and_limit(self, MockMessageList):
        """Page 3, size 10 → offset=20, limit=10."""
        main_q = _q(all_=[])
        total_q = _q(count_val=0)
        total_q.count.side_effect = [0, 0]

        db = MagicMock()
        db.query.side_effect = [main_q, total_q]

        cu = _user()
        MockMessageList.return_value = MagicMock()

        get_inbox_messages(page=3, size=10, unread_only=False, db=db, current_user=cu)

        main_q.offset.assert_called_once_with(20)
        main_q.limit.assert_called_once_with(10)

    @patch(f"{_BASE}.MessageList")
    def test_empty_inbox(self, MockMessageList):
        """Empty message list returns zeros."""
        main_q = _q(all_=[])
        total_q = _q(count_val=0)
        total_q.count.side_effect = [0, 0]

        db = MagicMock()
        db.query.side_effect = [main_q, total_q]

        cu = _user()
        MockMessageList.return_value = MagicMock()

        get_inbox_messages(page=1, size=50, unread_only=False, db=db, current_user=cu)

        MockMessageList.assert_called_once_with(
            messages=[],
            total_count=0,
            unread_count=0,
        )


# ===========================================================================
# get_sent_messages
# ===========================================================================

class TestGetSentMessages:
    """Tests for the /sent endpoint."""

    @patch(f"{_BASE}.MessageList")
    def test_returns_sent_messages_with_count(self, MockMessageList):
        """Returns paginated sent messages; unread_count always 0."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)
        main_q = _q(all_=[msg])
        count_q = _q(count_val=4)

        db = MagicMock()
        db.query.side_effect = [main_q, count_q]

        cu = _user()
        mock_list = MagicMock()
        MockMessageList.return_value = mock_list

        result = get_sent_messages(page=1, size=50, db=db, current_user=cu)

        MockMessageList.assert_called_once_with(
            messages=[msg],
            total_count=4,
            unread_count=0,
        )
        assert result == mock_list

    @patch(f"{_BASE}.MessageList")
    def test_pagination_applied(self, MockMessageList):
        """Page 2, size 5 → offset=5."""
        main_q = _q(all_=[])
        count_q = _q(count_val=0)

        db = MagicMock()
        db.query.side_effect = [main_q, count_q]

        cu = _user()
        MockMessageList.return_value = MagicMock()

        get_sent_messages(page=2, size=5, db=db, current_user=cu)

        main_q.offset.assert_called_once_with(5)
        main_q.limit.assert_called_once_with(5)

    @patch(f"{_BASE}.MessageList")
    def test_empty_sent(self, MockMessageList):
        """Empty sent box."""
        main_q = _q(all_=[])
        count_q = _q(count_val=0)

        db = MagicMock()
        db.query.side_effect = [main_q, count_q]

        cu = _user()
        MockMessageList.return_value = MagicMock()

        get_sent_messages(page=1, size=50, db=db, current_user=cu)

        MockMessageList.assert_called_once_with(
            messages=[],
            total_count=0,
            unread_count=0,
        )


# ===========================================================================
# get_message
# ===========================================================================

class TestGetMessage:
    """Tests for GET /{message_id}."""

    def test_not_found_raises_404(self):
        """Message doesn't exist → 404."""
        db = MagicMock()
        db.query.return_value = _q(first=None)

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            get_message(message_id=99, db=db, current_user=cu)

        assert exc.value.status_code == 404
        assert "not found" in exc.value.detail.lower()

    def test_not_sender_not_recipient_raises_403(self):
        """Message exists but current user is neither sender nor recipient → 403."""
        msg = _message(sender_id=OTHER_ID, recipient_id=99)  # cu=42 has no access
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        with pytest.raises(HTTPException) as exc:
            get_message(message_id=1, db=db, current_user=cu)

        assert exc.value.status_code == 403
        assert "access denied" in exc.value.detail.lower()

    def test_recipient_unread_marks_as_read(self):
        """Recipient viewing unread message → is_read=True, commit, refresh."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID, is_read=False)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        result = get_message(message_id=1, db=db, current_user=cu)

        assert msg.is_read is True
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(msg)
        assert result == msg

    def test_recipient_already_read_no_commit(self):
        """Recipient viewing already-read message → no commit."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID, is_read=True)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        result = get_message(message_id=1, db=db, current_user=cu)

        db.commit.assert_not_called()
        assert result == msg

    def test_sender_viewing_own_message_no_commit(self):
        """Sender viewing their own message (not recipient) → no commit."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID, is_read=False)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        result = get_message(message_id=1, db=db, current_user=cu)

        db.commit.assert_not_called()
        assert result == msg


# ===========================================================================
# create_message
# ===========================================================================

class TestCreateMessage:
    """Tests for POST /."""

    def _make_data(self, recipient_id=OTHER_ID):
        return MessageCreate(
            recipient_id=recipient_id,
            subject="Hello",
            message="How are you?",
            priority=MessagePriority.NORMAL,
        )

    def test_recipient_not_found_raises_404(self):
        """Recipient doesn't exist → 404."""
        recipient_q = _q(first=None)
        db = MagicMock()
        db.query.return_value = recipient_q

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            create_message(message_data=self._make_data(), db=db, current_user=cu)

        assert exc.value.status_code == 404
        assert "recipient" in exc.value.detail.lower()

    @patch(f"{_BASE}.timezone", create=True)
    @patch(f"{_BASE}.datetime", create=True)
    def test_success_creates_and_returns(self, mock_dt, mock_tz):
        """Valid recipient → message created, added, committed, re-queried."""
        recipient = _user(uid=OTHER_ID, name="Bob")

        mock_dt.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

        msg_with_relations = _message(mid=55)
        recipient_q = _q(first=recipient)
        # The reload query (with joinedload) returns the full message
        reload_q = _q(first=msg_with_relations)

        db = MagicMock()
        db.query.side_effect = [recipient_q, reload_q]

        cu = _user()
        result = create_message(message_data=self._make_data(), db=db, current_user=cu)

        db.add.assert_called_once()
        db.commit.assert_called()
        assert result == msg_with_relations


# ===========================================================================
# create_message_by_nickname
# ===========================================================================

class TestCreateMessageByNickname:
    """Tests for POST /by-nickname."""

    def _make_data(self, nickname="bob_nick"):
        return MessageCreateByNickname(
            recipient_nickname=nickname,
            subject="Hey",
            message="Whats up?",
            priority=MessagePriority.NORMAL,
        )

    def test_nickname_not_found_raises_404(self):
        """Nickname not found → 404."""
        recipient_q = _q(first=None)
        db = MagicMock()
        db.query.return_value = recipient_q

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            create_message_by_nickname(
                message_data=self._make_data("ghost"),
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 404
        assert "ghost" in exc.value.detail

    @patch(f"{_BASE}.timezone", create=True)
    @patch(f"{_BASE}.datetime", create=True)
    def test_success_creates_and_returns(self, mock_dt, mock_tz):
        """Valid nickname → message created and returned with relations."""
        recipient = _user(uid=OTHER_ID, name="Bob")
        recipient.nickname = "bob_nick"

        mock_dt.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

        msg_with_relations = _message(mid=77)
        recipient_q = _q(first=recipient)
        reload_q = _q(first=msg_with_relations)

        db = MagicMock()
        db.query.side_effect = [recipient_q, reload_q]

        cu = _user()
        result = create_message_by_nickname(
            message_data=self._make_data("bob_nick"),
            db=db,
            current_user=cu,
        )

        db.add.assert_called_once()
        db.commit.assert_called()
        assert result == msg_with_relations

    @patch(f"{_BASE}.traceback", create=True)
    @patch(f"{_BASE}.timezone", create=True)
    @patch(f"{_BASE}.datetime", create=True)
    def test_unexpected_exception_rolls_back_and_raises_500(self, mock_dt, mock_tz, mock_tb):
        """Unexpected exception (not HTTPException) → rollback + 500."""
        recipient = _user(uid=OTHER_ID, name="Bob")
        recipient.nickname = "bob_nick"

        db = MagicMock()
        recipient_q = _q(first=recipient)

        # Make db.add raise an unexpected error
        db.query.return_value = recipient_q
        db.add.side_effect = RuntimeError("DB exploded")

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            create_message_by_nickname(
                message_data=self._make_data("bob_nick"),
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 500
        db.rollback.assert_called_once()


# ===========================================================================
# update_message
# ===========================================================================

class TestUpdateMessage:
    """Tests for PUT /{message_id}."""

    def test_not_found_raises_404(self):
        """Message doesn't exist → 404."""
        db = MagicMock()
        db.query.return_value = _q(first=None)

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            update_message(
                message_id=99,
                message_update=MessageUpdate(message="new content"),
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 404

    def test_edit_content_not_sender_raises_403(self):
        """Editing message.message, but user is not the sender → 403."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        with pytest.raises(HTTPException) as exc:
            update_message(
                message_id=1,
                message_update=MessageUpdate(message="new content"),
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 403
        assert "sender" in exc.value.detail.lower()

    @patch(f"{_BASE}.timezone", create=True)
    @patch(f"{_BASE}.datetime", create=True)
    def test_edit_content_success(self, mock_dt, mock_tz):
        """Sender edits message content → message updated, is_edited=True."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)
        reload_msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)

        main_q = _q(first=msg)
        reload_q = _q(first=reload_msg)

        db = MagicMock()
        db.query.side_effect = [main_q, reload_q]

        mock_dt.now.return_value = datetime(2026, 2, 1, tzinfo=timezone.utc)

        cu = _user(uid=USER_ID)
        result = update_message(
            message_id=1,
            message_update=MessageUpdate(message="Updated body"),
            db=db,
            current_user=cu,
        )

        assert msg.message == "Updated body"
        assert msg.is_edited is True
        db.commit.assert_called_once()
        assert result == reload_msg

    def test_mark_read_not_recipient_raises_403(self):
        """Marking is_read, but user is not recipient → 403."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)  # sender, not recipient
        with pytest.raises(HTTPException) as exc:
            update_message(
                message_id=1,
                message_update=MessageUpdate(is_read=True),
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 403
        assert "recipient" in exc.value.detail.lower()

    def test_mark_read_true_sets_read_at(self):
        """Recipient marks is_read=True → read_at set via func.now()."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID)
        reload_msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID)

        main_q = _q(first=msg)
        reload_q = _q(first=reload_msg)

        db = MagicMock()
        db.query.side_effect = [main_q, reload_q]

        cu = _user(uid=USER_ID)
        update_message(
            message_id=1,
            message_update=MessageUpdate(is_read=True),
            db=db,
            current_user=cu,
        )

        assert msg.is_read is True
        # read_at is set to func.now() — verify it was assigned (not None)
        assert msg.read_at is not None
        db.commit.assert_called_once()

    def test_mark_read_false_clears_read_at(self):
        """Recipient marks is_read=False → read_at cleared to None."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID, is_read=True)
        reload_msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID)

        main_q = _q(first=msg)
        reload_q = _q(first=reload_msg)

        db = MagicMock()
        db.query.side_effect = [main_q, reload_q]

        cu = _user(uid=USER_ID)
        update_message(
            message_id=1,
            message_update=MessageUpdate(is_read=False),
            db=db,
            current_user=cu,
        )

        assert msg.is_read is False
        assert msg.read_at is None
        db.commit.assert_called_once()

    def test_no_fields_raises_400(self):
        """MessageUpdate with neither message nor is_read → 400."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        with pytest.raises(HTTPException) as exc:
            update_message(
                message_id=1,
                message_update=MessageUpdate(),  # both fields None
                db=db,
                current_user=cu,
            )

        assert exc.value.status_code == 400
        assert "no valid" in exc.value.detail.lower()


# ===========================================================================
# get_available_users
# ===========================================================================

class TestGetAvailableUsers:
    """Tests for GET /users/available."""

    def test_returns_active_users_with_nicknames(self):
        """Returns all users that are active and have nicknames, excluding current user."""
        other1 = _user(uid=OTHER_ID, name="Bob")
        other2 = _user(uid=8, name="Carol")

        q = _q(all_=[other1, other2])
        db = MagicMock()
        db.query.return_value = q

        cu = _user(uid=USER_ID)
        result = get_available_users(db=db, current_user=cu)

        assert result == [other1, other2]
        q.filter.assert_called_once()
        q.order_by.assert_called_once()

    def test_empty_user_list(self):
        """No available users → empty list."""
        q = _q(all_=[])
        db = MagicMock()
        db.query.return_value = q

        cu = _user(uid=USER_ID)
        result = get_available_users(db=db, current_user=cu)

        assert result == []


# ===========================================================================
# delete_message
# ===========================================================================

class TestDeleteMessage:
    """Tests for DELETE /{message_id}."""

    def test_not_found_raises_404(self):
        """Message doesn't exist → 404."""
        db = MagicMock()
        db.query.return_value = _q(first=None)

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            delete_message(message_id=99, db=db, current_user=cu)

        assert exc.value.status_code == 404

    def test_not_sender_not_recipient_raises_403(self):
        """User is neither sender nor recipient → 403."""
        msg = _message(sender_id=OTHER_ID, recipient_id=99)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        with pytest.raises(HTTPException) as exc:
            delete_message(message_id=1, db=db, current_user=cu)

        assert exc.value.status_code == 403
        assert "access denied" in exc.value.detail.lower()

    def test_sender_can_delete(self):
        """Sender deletes their own message → commit called."""
        msg = _message(sender_id=USER_ID, recipient_id=OTHER_ID)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        result = delete_message(message_id=1, db=db, current_user=cu)

        db.delete.assert_called_once_with(msg)
        db.commit.assert_called_once()
        assert result["message"] == "Message deleted successfully"

    def test_recipient_can_delete(self):
        """Recipient deletes a message they received → commit called."""
        msg = _message(sender_id=OTHER_ID, recipient_id=USER_ID)
        db = MagicMock()
        db.query.return_value = _q(first=msg)

        cu = _user(uid=USER_ID)
        result = delete_message(message_id=1, db=db, current_user=cu)

        db.delete.assert_called_once_with(msg)
        db.commit.assert_called_once()
        assert result["message"] == "Message deleted successfully"


# ===========================================================================
# delete_conversation
# ===========================================================================

class TestDeleteConversation:
    """Tests for DELETE /conversation/{user_id}."""

    def test_other_user_not_found_raises_404(self):
        """Other user doesn't exist → 404."""
        user_q = _q(first=None)
        db = MagicMock()
        db.query.return_value = user_q

        cu = _user()
        with pytest.raises(HTTPException) as exc:
            delete_conversation(user_id=999, db=db, current_user=cu)

        assert exc.value.status_code == 404
        assert "user not found" in exc.value.detail.lower()

    def test_deletes_all_messages_in_conversation(self):
        """Deletes all messages in both directions between the two users."""
        other = _user(uid=OTHER_ID, name="Bob")
        msg1 = _message(mid=10, sender_id=USER_ID, recipient_id=OTHER_ID)
        msg2 = _message(mid=11, sender_id=OTHER_ID, recipient_id=USER_ID)

        user_q = _q(first=other)
        msgs_q = _q(all_=[msg1, msg2])

        db = MagicMock()
        db.query.side_effect = [user_q, msgs_q]

        cu = _user(uid=USER_ID)
        result = delete_conversation(user_id=OTHER_ID, db=db, current_user=cu)

        assert db.delete.call_count == 2
        db.commit.assert_called_once()
        assert result["deleted_messages"] == 2
        assert result["other_user"] == other.name

    def test_empty_conversation_zero_deleted(self):
        """No messages between users → deleted_count=0."""
        other = _user(uid=OTHER_ID, name="Bob")

        user_q = _q(first=other)
        msgs_q = _q(all_=[])

        db = MagicMock()
        db.query.side_effect = [user_q, msgs_q]

        cu = _user(uid=USER_ID)
        result = delete_conversation(user_id=OTHER_ID, db=db, current_user=cu)

        db.delete.assert_not_called()
        db.commit.assert_called_once()
        assert result["deleted_messages"] == 0

    def test_returns_other_user_name(self):
        """Response includes other_user name."""
        other = _user(uid=OTHER_ID, name="Charlie")

        user_q = _q(first=other)
        msgs_q = _q(all_=[])

        db = MagicMock()
        db.query.side_effect = [user_q, msgs_q]

        cu = _user(uid=USER_ID)
        result = delete_conversation(user_id=OTHER_ID, db=db, current_user=cu)

        assert result["other_user"] == "Charlie"
        assert "message" in result

    def test_returns_success_message(self):
        """Response contains a success message string."""
        other = _user(uid=OTHER_ID, name="Dave")

        user_q = _q(first=other)
        msgs_q = _q(all_=[])

        db = MagicMock()
        db.query.side_effect = [user_q, msgs_q]

        cu = _user(uid=USER_ID)
        result = delete_conversation(user_id=OTHER_ID, db=db, current_user=cu)

        assert "deleted" in result["message"].lower()
