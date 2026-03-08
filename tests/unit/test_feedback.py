"""
Unit tests for app/api/api_v1/endpoints/feedback.py

Coverage targets:
  get_all_feedback()              — GET /
    - no filters: basic call
    - session_id filter applied
    - user_id filter applied
    - items present → FeedbackWithRelations called

  create_feedback()               — POST /
    - 404: session not found
    - 400: current_time < session_end (before window)
    - 400: current_time > session_end + 24h (window closed)
    - 400: no confirmed booking
    - 400: duplicate feedback
    - happy path

  get_my_feedback()               — GET /me
    - basic: no filters
    - semester_id filter applied (join)
    - anonymous → user=None
    - non-anonymous → user set

  update_feedback()               — PATCH /{feedback_id}
    - 404
    - 403: not owner
    - happy path: fields updated

  delete_feedback()               — DELETE /{feedback_id}
    - 404
    - 403: not owner
    - happy path

  get_session_feedback()          — GET /sessions/{session_id}
    - 404: session not found
    - happy path

  get_session_feedback_summary()  — GET /sessions/{session_id}/summary
    - 404: session not found
    - empty feedbacks → FeedbackSummary(0)
    - avg + distribution calculated
    - anonymous comments excluded
    - recent_comments capped at 5

  get_instructor_feedback()       — GET /instructor/my
    - 403: non-instructor role
    - happy path: returns dict
    - anonymous → user/user_id None
    - session=None → session key is None
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from app.api.api_v1.endpoints.feedback import (
    get_all_feedback,
    create_feedback,
    get_my_feedback,
    update_feedback,
    delete_feedback,
    get_session_feedback,
    get_session_feedback_summary,
    get_instructor_feedback,
)
from app.models.user import UserRole

_FB  = "app.api.api_v1.endpoints.feedback"
_FWR = f"{_FB}.FeedbackWithRelations"
_FBL = f"{_FB}.FeedbackList"
_FBS = f"{_FB}.FeedbackSummary"
_NOW = f"{_FB}.time_provider.now"

# Fixed datetime used across time-window tests: session ends at 10:00 UTC on 2026-03-05
SESSION_END = datetime(2026, 3, 5, 10, 0)   # naive


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role=UserRole.STUDENT, user_id=42):
    u = MagicMock()
    u.role = role
    u.id = user_id
    return u


def _instructor(user_id=42):
    u = MagicMock()
    u.role.value = "instructor"     # matches `role.value != 'instructor'` check
    u.id = user_id
    return u


def _q(first=None, all_=None, count_=0, scalar_=0):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.join.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.first.return_value = first
    q.count.return_value = count_
    q.scalar.return_value = scalar_
    q.all.return_value = all_ or []
    q.delete.return_value = 0
    return q


def _db_seq(*qs):
    db = MagicMock()
    db.query.side_effect = list(qs) + [MagicMock()] * 8
    return db


def _session_mock():
    s = MagicMock()
    s.id = 10
    s.date_end = SESSION_END        # naive → tzinfo is None → session_end_naive = date_end
    return s


def _feedback_data(session_id=10):
    fd = MagicMock()
    fd.session_id = session_id
    fd.model_dump.return_value = {"session_id": session_id, "rating": 4, "comment": "Good"}
    return fd


# ── get_all_feedback ────────────────────────────────────────────────────────────

class TestGetAllFeedback:

    def test_no_items_returns_empty_feedbacklist(self):
        db = _db_seq(_q(count_=0, all_=[]))
        with patch(_FWR), patch(_FBL) as MockFBL:
            MockFBL.return_value = MagicMock()
            get_all_feedback(db=db, current_user=_user(), page=1, size=50)
        MockFBL.assert_called_once()

    def test_session_id_filter_applied(self):
        db = _db_seq(_q(count_=0, all_=[]))
        with patch(_FWR), patch(_FBL) as MockFBL:
            MockFBL.return_value = MagicMock()
            get_all_feedback(db=db, current_user=_user(), page=1, size=50, session_id=5)
        MockFBL.assert_called_once()

    def test_user_id_filter_applied(self):
        db = _db_seq(_q(count_=0, all_=[]))
        with patch(_FWR), patch(_FBL) as MockFBL:
            MockFBL.return_value = MagicMock()
            get_all_feedback(db=db, current_user=_user(), page=1, size=50, user_id=42)
        MockFBL.assert_called_once()

    def test_items_present_calls_feedback_with_relations(self):
        fb = MagicMock()
        # NOTE: do NOT set fb.user/fb.session via assignment — that lands them in
        # fb.__dict__, causing "multiple values for keyword argument" when the code
        # does FeedbackWithRelations(**feedback.__dict__, user=..., session=...)
        db = _db_seq(_q(count_=1, all_=[fb]))
        with patch(_FWR) as MockFWR, patch(_FBL) as MockFBL:
            MockFWR.return_value = MagicMock()
            MockFBL.return_value = MagicMock()
            get_all_feedback(db=db, current_user=_user(), page=1, size=50)
        assert MockFWR.call_count == 1


# ── create_feedback ─────────────────────────────────────────────────────────────

class TestCreateFeedback:

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            create_feedback(_feedback_data(), db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_400_before_session_ends(self):
        db = _db_seq(_q(first=_session_mock()))
        with patch(_NOW, return_value=datetime(2026, 3, 5, 8, 0)):
            with pytest.raises(HTTPException) as exc:
                create_feedback(_feedback_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "before session ends" in exc.value.detail.lower()

    def test_400_after_24h_window_closed(self):
        db = _db_seq(_q(first=_session_mock()))
        # SESSION_END = 10:00 → window closes 2026-03-06 10:00; now = 20:00 → past window
        with patch(_NOW, return_value=datetime(2026, 3, 6, 20, 0)):
            with pytest.raises(HTTPException) as exc:
                create_feedback(_feedback_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "window closed" in exc.value.detail.lower()

    def test_400_no_confirmed_booking(self):
        db = _db_seq(
            _q(first=_session_mock()),  # q1: session found
            _q(first=None),             # q2: Booking → not found
        )
        with patch(_NOW, return_value=datetime(2026, 3, 5, 18, 0)):
            with pytest.raises(HTTPException) as exc:
                create_feedback(_feedback_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "attended" in exc.value.detail.lower()

    def test_400_duplicate_feedback(self):
        db = _db_seq(
            _q(first=_session_mock()),      # q1: session
            _q(first=MagicMock()),          # q2: booking found
            _q(first=MagicMock()),          # q3: existing feedback found
        )
        with patch(_NOW, return_value=datetime(2026, 3, 5, 18, 0)):
            with pytest.raises(HTTPException) as exc:
                create_feedback(_feedback_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "already provided" in exc.value.detail.lower()

    def test_happy_path_creates_feedback(self):
        db = _db_seq(
            _q(first=_session_mock()),  # q1: session
            _q(first=MagicMock()),      # q2: booking confirmed
            _q(first=None),             # q3: no existing feedback
        )
        with patch(_NOW, return_value=datetime(2026, 3, 5, 18, 0)):
            create_feedback(_feedback_data(), db=db, current_user=_user())
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


# ── get_my_feedback ─────────────────────────────────────────────────────────────

class TestGetMyFeedback:

    def test_basic_no_filters(self):
        db = _db_seq(_q(count_=0, all_=[]))
        with patch(_FWR), patch(_FBL) as MockFBL:
            MockFBL.return_value = MagicMock()
            get_my_feedback(db=db, current_user=_user(), page=1, size=50)
        MockFBL.assert_called_once()

    def test_semester_filter_adds_join(self):
        db = _db_seq(_q(count_=0, all_=[]))
        with patch(_FWR), patch(_FBL) as MockFBL:
            MockFBL.return_value = MagicMock()
            get_my_feedback(db=db, current_user=_user(), page=1, size=50, semester_id=3)
        MockFBL.assert_called_once()

    def test_anonymous_feedback_user_is_none(self):
        fb = MagicMock()
        fb.is_anonymous = True
        # fb.session auto-created via __getattr__ (not in __dict__)
        db = _db_seq(_q(count_=1, all_=[fb]))
        with patch(_FWR) as MockFWR, patch(_FBL) as MockFBL:
            MockFWR.return_value = MagicMock()
            MockFBL.return_value = MagicMock()
            get_my_feedback(db=db, current_user=_user(), page=1, size=50)
        kw = MockFWR.call_args[1]
        assert kw["user"] is None

    def test_non_anonymous_feedback_user_set(self):
        fb = MagicMock()
        fb.is_anonymous = False
        # Access fb.user via __getattr__ (stored in _mock_children, NOT __dict__)
        _ = fb.user.name   # pre-warm child mock without landing in __dict__
        db = _db_seq(_q(count_=1, all_=[fb]))
        with patch(_FWR) as MockFWR, patch(_FBL) as MockFBL:
            MockFWR.return_value = MagicMock()
            MockFBL.return_value = MagicMock()
            get_my_feedback(db=db, current_user=_user(), page=1, size=50)
        kw = MockFWR.call_args[1]
        assert kw["user"] is fb.user


# ── update_feedback ─────────────────────────────────────────────────────────────

class TestUpdateFeedback:

    def test_404_feedback_not_found(self):
        db = _db_seq(_q(first=None))
        fu = MagicMock()
        fu.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_feedback(1, fu, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_owner(self):
        fb = MagicMock()
        fb.user_id = 99     # different from current_user.id = 42
        db = _db_seq(_q(first=fb))
        fu = MagicMock()
        fu.model_dump.return_value = {}
        with pytest.raises(HTTPException) as exc:
            update_feedback(1, fu, db=db, current_user=_user(user_id=42))
        assert exc.value.status_code == 403

    def test_happy_path_updates_and_commits(self):
        fb = MagicMock()
        fb.user_id = 42
        db = _db_seq(_q(first=fb))
        fu = MagicMock()
        fu.model_dump.return_value = {"rating": 5, "comment": "Updated"}
        update_feedback(1, fu, db=db, current_user=_user(user_id=42))
        assert fb.rating == 5
        assert fb.comment == "Updated"
        db.commit.assert_called_once()


# ── delete_feedback ─────────────────────────────────────────────────────────────

class TestDeleteFeedback:

    def test_404_feedback_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            delete_feedback(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_owner(self):
        fb = MagicMock()
        fb.user_id = 99
        db = _db_seq(_q(first=fb))
        with pytest.raises(HTTPException) as exc:
            delete_feedback(1, db=db, current_user=_user(user_id=42))
        assert exc.value.status_code == 403

    def test_happy_path_deletes_and_commits(self):
        fb = MagicMock()
        fb.user_id = 42
        db = _db_seq(_q(first=fb))
        result = delete_feedback(1, db=db, current_user=_user(user_id=42))
        db.delete.assert_called_once_with(fb)
        db.commit.assert_called_once()
        assert result["message"] == "Feedback deleted successfully"


# ── get_session_feedback ────────────────────────────────────────────────────────

class TestGetSessionFeedback:

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_session_feedback(session_id=1, db=db, current_user=_user(), page=1, size=50)
        assert exc.value.status_code == 404

    def test_happy_path_returns_feedback_list(self):
        fb = MagicMock()
        fb.is_anonymous = False
        # fb.user and fb.session auto-created (not in __dict__)
        db = _db_seq(
            _q(first=MagicMock()),          # q1: session found
            _q(count_=1, all_=[fb]),        # q2: feedbacks
        )
        with patch(_FWR) as MockFWR, patch(_FBL) as MockFBL:
            MockFWR.return_value = MagicMock()
            MockFBL.return_value = MagicMock()
            get_session_feedback(session_id=1, db=db, current_user=_user(), page=1, size=50)
        assert MockFWR.call_count == 1


# ── get_session_feedback_summary ─────────────────────────────────────────────────

class TestGetSessionFeedbackSummary:

    def test_404_session_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_session_feedback_summary(session_id=1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_empty_feedbacks_returns_zero_summary(self):
        db = _db_seq(
            _q(first=MagicMock()),  # q1: session found
            _q(all_=[]),            # q2: no feedbacks
        )
        with patch(_FBS) as MockFBS:
            MockFBS.return_value = MagicMock()
            get_session_feedback_summary(session_id=1, db=db, current_user=_user())
        kw = MockFBS.call_args[1]
        assert kw["average_rating"] == 0.0
        assert kw["total_feedback"] == 0
        assert kw["rating_distribution"] == {}

    def test_average_and_distribution_calculated(self):
        fb1 = MagicMock(); fb1.rating = 4; fb1.comment = "Great"; fb1.is_anonymous = False
        fb2 = MagicMock(); fb2.rating = 2; fb2.comment = None;    fb2.is_anonymous = False
        db = _db_seq(
            _q(first=MagicMock()),
            _q(all_=[fb1, fb2]),
        )
        with patch(_FBS) as MockFBS:
            MockFBS.return_value = MagicMock()
            get_session_feedback_summary(session_id=1, db=db, current_user=_user())
        kw = MockFBS.call_args[1]
        assert abs(kw["average_rating"] - 3.0) < 0.01
        assert kw["total_feedback"] == 2
        assert kw["rating_distribution"]["4"] == 1
        assert kw["rating_distribution"]["2"] == 1
        assert kw["rating_distribution"]["1"] == 0

    def test_anonymous_comments_excluded(self):
        fb1 = MagicMock(); fb1.rating = 5; fb1.comment = "Visible"; fb1.is_anonymous = False
        fb2 = MagicMock(); fb2.rating = 5; fb2.comment = "Hidden";  fb2.is_anonymous = True
        db = _db_seq(
            _q(first=MagicMock()),
            _q(all_=[fb1, fb2]),
        )
        with patch(_FBS) as MockFBS:
            MockFBS.return_value = MagicMock()
            get_session_feedback_summary(session_id=1, db=db, current_user=_user())
        kw = MockFBS.call_args[1]
        assert kw["recent_comments"] == ["Visible"]

    def test_recent_comments_capped_at_5(self):
        fbs = []
        for i in range(7):
            fb = MagicMock()
            fb.rating = 5
            fb.comment = f"Comment {i}"
            fb.is_anonymous = False
            fbs.append(fb)
        db = _db_seq(
            _q(first=MagicMock()),
            _q(all_=fbs),
        )
        with patch(_FBS) as MockFBS:
            MockFBS.return_value = MagicMock()
            get_session_feedback_summary(session_id=1, db=db, current_user=_user())
        kw = MockFBS.call_args[1]
        assert len(kw["recent_comments"]) == 5


# ── get_instructor_feedback ─────────────────────────────────────────────────────

class TestGetInstructorFeedback:

    def test_403_non_instructor_role(self):
        u = MagicMock()
        u.role.value = "student"    # != 'instructor' → 403
        db = _db_seq(_q())
        with pytest.raises(HTTPException) as exc:
            get_instructor_feedback(db=db, current_user=u, page=1, size=50)
        assert exc.value.status_code == 403

    def test_happy_path_returns_feedback_dict(self):
        fb = MagicMock()
        fb.is_anonymous = False
        fb.user = MagicMock()
        fb.user.id = 42
        fb.user.name = "Player"
        fb.session = MagicMock()
        fb.session.id = 10
        fb.session.title = "Training"
        fb.session.date_start = datetime(2026, 3, 5, 9, 0)
        fb.created_at = datetime(2026, 3, 5, 12, 0)
        db = _db_seq(_q(count_=1, all_=[fb]))
        result = get_instructor_feedback(db=db, current_user=_instructor(), page=1, size=50)
        assert result["total"] == 1
        assert len(result["feedback"]) == 1
        assert result["feedback"][0]["user"]["name"] == "Player"

    def test_anonymous_feedback_hides_user_and_id(self):
        fb = MagicMock()
        fb.is_anonymous = True
        fb.user = MagicMock()
        fb.session = MagicMock()
        fb.session.id = 10
        fb.session.title = "Training"
        fb.session.date_start = datetime(2026, 3, 5, 9, 0)
        fb.created_at = datetime(2026, 3, 5, 12, 0)
        db = _db_seq(_q(count_=1, all_=[fb]))
        result = get_instructor_feedback(db=db, current_user=_instructor(), page=1, size=50)
        assert result["feedback"][0]["user"] is None
        assert result["feedback"][0]["user_id"] is None

    def test_session_none_yields_none_in_dict(self):
        fb = MagicMock()
        fb.is_anonymous = False
        fb.session = None           # no session attached
        fb.user = MagicMock()
        fb.user.id = 42
        fb.user.name = "Player"
        fb.created_at = datetime(2026, 3, 5, 12, 0)
        db = _db_seq(_q(count_=1, all_=[fb]))
        result = get_instructor_feedback(db=db, current_user=_instructor(), page=1, size=50)
        assert result["feedback"][0]["session"] is None
