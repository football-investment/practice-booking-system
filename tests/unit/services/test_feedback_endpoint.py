"""
Unit tests for app/api/api_v1/endpoints/feedback.py
Covers: get_all_feedback, create_feedback, get_my_feedback, update_feedback,
        delete_feedback, get_session_feedback, get_session_feedback_summary,
        get_instructor_feedback
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.api.api_v1.endpoints.feedback import (
    get_all_feedback, create_feedback, get_my_feedback,
    update_feedback, delete_feedback,
    get_session_feedback, get_session_feedback_summary,
    get_instructor_feedback,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.feedback"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.count.return_value = 0
    q.all.return_value = []
    q.first.return_value = None
    return q


def _seq_db(*vals):
    call_n = [0]
    db = MagicMock()
    def side(*args):
        n = call_n[0]; call_n[0] += 1
        v = vals[n] if n < len(vals) else None
        q = _q()
        if isinstance(v, list):
            q.all.return_value = v
        elif isinstance(v, int):
            q.count.return_value = v
        else:
            q.first.return_value = v
        return q
    db.query.side_effect = side
    return db


def _user(uid=42, role=UserRole.STUDENT):
    u = MagicMock()
    u.id = uid
    u.role = role
    return u


def _instructor():
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = 'instructor'
    return u


def _admin():
    return _user(uid=42, role=UserRole.ADMIN)


def _session_mock(date_end=None):
    s = MagicMock()
    s.id = 1
    s.date_end = date_end or datetime(2020, 6, 15, 10, 0, 0)  # tz-naive
    s.date_end.tzinfo = None  # ensure tz-naive; but date_end is already a real datetime
    return s


def _fb_mock(fid=1, uid=42, sid=1, rating=4, is_anon=False):
    fb = MagicMock()
    fb.id = fid
    fb.user_id = uid
    fb.session_id = sid
    fb.rating = rating
    fb.is_anonymous = is_anon
    fb.comment = "Good session"
    _ = fb.user   # pre-warm __getattr__ → goes to _mock_children, not __dict__
    _ = fb.session
    return fb


def _feedback_data(session_id=1, rating=4, comment="test"):
    fd = MagicMock()
    fd.session_id = session_id
    fd.rating = rating
    fd.comment = comment
    fd.model_dump.return_value = {"session_id": session_id, "rating": rating, "comment": comment}
    return fd


# ---------------------------------------------------------------------------
# get_all_feedback
# ---------------------------------------------------------------------------

class TestGetAllFeedback:
    def _call(self, db=None, current_user=None, page=1, size=50,
              session_id=None, user_id=None):
        return get_all_feedback(
            db=db or MagicMock(),
            current_user=current_user or _instructor(),
            page=page, size=size,
            session_id=session_id, user_id=user_id,
        )

    def test_no_filters_empty_list(self):
        """GAF-01: no filters, no feedback → empty list."""
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db)
        MockFL.assert_called_once_with(feedbacks=[], total=0, page=1, size=50)

    def test_with_session_filter(self):
        """GAF-02: session_id filter applied."""
        fb = _fb_mock()
        q = _q()
        q.all.return_value = [fb]
        q.count.return_value = 1
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations") as MockFWR:
            MockFWR.return_value = MagicMock()
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db, session_id=1)
        # Filter was called (at least once for session_id, once for basic)
        assert q.filter.called

    def test_with_user_filter(self):
        """GAF-03: user_id filter applied."""
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db, user_id=7)
        assert q.filter.called

    def test_pagination(self):
        """GAF-04: page/size → offset computed correctly."""
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db, page=3, size=10)
        q.offset.assert_called_once_with(20)  # (3-1)*10


# ---------------------------------------------------------------------------
# create_feedback
# ---------------------------------------------------------------------------

class TestCreateFeedback:
    _SESSION_END = datetime(2020, 6, 15, 10, 0, 0)

    def _call(self, feedback_data=None, db=None, current_user=None):
        return create_feedback(
            feedback_data=feedback_data or _feedback_data(),
            db=db or MagicMock(),
            current_user=current_user or _user(),
        )

    def _session(self):
        s = MagicMock()
        s.id = 1
        s.date_end = self._SESSION_END  # real tz-naive datetime → .tzinfo is None
        return s

    def test_session_not_found_404(self):
        """CF-01: session not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_before_session_ends_400(self):
        """CF-02: current_time < session end → 400."""
        from fastapi import HTTPException
        s = self._session()
        db = _seq_db(s)
        # current_time is 1 hour BEFORE session end
        before_end = datetime(2020, 6, 15, 9, 0, 0)
        with patch(f"{_BASE}.time_provider") as mock_tp:
            mock_tp.now.return_value.replace.return_value = before_end
            with pytest.raises(HTTPException) as exc:
                self._call(db=db)
        assert exc.value.status_code == 400
        assert "before" in exc.value.detail.lower()

    def test_after_window_400(self):
        """CF-03: current_time > session end + 24h → 400."""
        from fastapi import HTTPException
        s = self._session()
        db = _seq_db(s)
        # 25 hours after session end
        after_window = datetime(2020, 6, 16, 11, 0, 0)
        with patch(f"{_BASE}.time_provider") as mock_tp:
            mock_tp.now.return_value.replace.return_value = after_window
            with pytest.raises(HTTPException) as exc:
                self._call(db=db)
        assert exc.value.status_code == 400
        assert "closed" in exc.value.detail.lower()

    def test_no_confirmed_booking_400(self):
        """CF-04: no CONFIRMED booking → 400."""
        from fastapi import HTTPException
        s = self._session()
        # valid window: 5h after session end
        in_window = datetime(2020, 6, 15, 15, 0, 0)
        db = _seq_db(s, None)  # session found, no booking
        with patch(f"{_BASE}.time_provider") as mock_tp:
            mock_tp.now.return_value.replace.return_value = in_window
            with pytest.raises(HTTPException) as exc:
                self._call(db=db)
        assert exc.value.status_code == 400
        assert "attended" in exc.value.detail.lower()

    def test_duplicate_feedback_400(self):
        """CF-05: feedback already exists → 400."""
        from fastapi import HTTPException
        s = self._session()
        booking = MagicMock()
        existing_fb = MagicMock()
        in_window = datetime(2020, 6, 15, 15, 0, 0)
        db = _seq_db(s, booking, existing_fb)
        with patch(f"{_BASE}.time_provider") as mock_tp:
            mock_tp.now.return_value.replace.return_value = in_window
            with pytest.raises(HTTPException) as exc:
                self._call(db=db)
        assert exc.value.status_code == 400
        assert "already" in exc.value.detail.lower()

    def test_success_creates_feedback(self):
        """CF-06: all checks pass → feedback created and committed."""
        s = self._session()
        booking = MagicMock()
        in_window = datetime(2020, 6, 15, 15, 0, 0)
        db = _seq_db(s, booking, None)  # no existing feedback
        fd = _feedback_data()
        with patch(f"{_BASE}.time_provider") as mock_tp:
            mock_tp.now.return_value.replace.return_value = in_window
            with patch(f"{_BASE}.Feedback") as MockFeedback:
                mock_fb = MagicMock()
                MockFeedback.return_value = mock_fb
                result = self._call(feedback_data=fd, db=db)
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_my_feedback
# ---------------------------------------------------------------------------

class TestGetMyFeedback:
    def _call(self, db=None, current_user=None, page=1, size=50, semester_id=None):
        return get_my_feedback(
            db=db or MagicMock(),
            current_user=current_user or _user(),
            page=page, size=size, semester_id=semester_id,
        )

    def test_no_semester_filter(self):
        """GMF-01: no semester_id → no join applied."""
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db)
        q.join.assert_not_called()

    def test_with_semester_filter(self):
        """GMF-02: semester_id → join applied."""
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db, semester_id=5)
        q.join.assert_called_once()

    def test_anonymous_feedback_hides_user(self):
        """GMF-03: is_anonymous=True → user=None in FeedbackWithRelations."""
        fb = _fb_mock(is_anon=True)
        q = _q()
        q.all.return_value = [fb]
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.FeedbackWithRelations") as MockFWR:
            MockFWR.return_value = MagicMock()
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db)
        # FeedbackWithRelations called with user=None (is_anonymous=True)
        call_kwargs = MockFWR.call_args[1]
        assert call_kwargs.get("user") is None


# ---------------------------------------------------------------------------
# update_feedback
# ---------------------------------------------------------------------------

class TestUpdateFeedback:
    def _call(self, feedback_id=1, update=None, db=None, current_user=None):
        update = update or MagicMock(model_dump=lambda exclude_unset=False: {"comment": "updated"})
        return update_feedback(
            feedback_id=feedback_id,
            feedback_update=update,
            db=db or MagicMock(),
            current_user=current_user or _user(),
        )

    def test_not_found_404(self):
        """UF-01: feedback not found → 404."""
        from fastapi import HTTPException
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_wrong_user_403(self):
        """UF-02: feedback belongs to other user → 403."""
        from fastapi import HTTPException
        fb = MagicMock()
        fb.user_id = 99  # different user
        q = _q()
        q.first.return_value = fb
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            self._call(db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403

    def test_success_updates_fields(self):
        """UF-03: owner updates → fields set, commit called."""
        fb = MagicMock()
        fb.user_id = 42
        q = _q()
        q.first.return_value = fb
        db = MagicMock()
        db.query.return_value = q
        update = MagicMock()
        update.model_dump.return_value = {"comment": "new comment", "rating": 5}
        result = self._call(db=db, update=update, current_user=_user(uid=42))
        assert fb.comment == "new comment"
        assert fb.rating == 5
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# delete_feedback
# ---------------------------------------------------------------------------

class TestDeleteFeedback:
    def _call(self, feedback_id=1, db=None, current_user=None):
        return delete_feedback(
            feedback_id=feedback_id,
            db=db or MagicMock(),
            current_user=current_user or _user(),
        )

    def test_not_found_404(self):
        """DF-01: feedback not found → 404."""
        from fastapi import HTTPException
        q = _q()
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_wrong_user_403(self):
        """DF-02: feedback belongs to other → 403."""
        from fastapi import HTTPException
        fb = MagicMock()
        fb.user_id = 99
        q = _q()
        q.first.return_value = fb
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            self._call(db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403

    def test_success_deletes(self):
        """DF-03: owner deletes → db.delete + commit."""
        fb = MagicMock()
        fb.user_id = 42
        q = _q()
        q.first.return_value = fb
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db, current_user=_user(uid=42))
        db.delete.assert_called_once_with(fb)
        db.commit.assert_called_once()
        assert "deleted" in result["message"].lower()


# ---------------------------------------------------------------------------
# get_session_feedback
# ---------------------------------------------------------------------------

class TestGetSessionFeedback:
    def _call(self, session_id=1, db=None, current_user=None, page=1, size=50):
        return get_session_feedback(
            session_id=session_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
            page=page, size=size,
        )

    def test_session_not_found_404(self):
        """GSF-01: session not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_no_feedback_empty_list(self):
        """GSF-02: session found, no feedback → FeedbackList(total=0)."""
        s = MagicMock()
        s.id = 1
        q = _q()
        call_n = [0]
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            r = _q()
            r.first.return_value = s if n == 0 else None
            return r
        db = MagicMock()
        db.query.side_effect = side
        with patch(f"{_BASE}.FeedbackWithRelations"):
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db)
        MockFL.assert_called_once_with(feedbacks=[], total=0, page=1, size=50)

    def test_feedback_returned(self):
        """GSF-03: feedback found → FeedbackWithRelations built."""
        s = MagicMock()
        fb = _fb_mock()
        call_n = [0]
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = s
            else:
                q.all.return_value = [fb]
                q.count.return_value = 1
            return q
        db = MagicMock()
        db.query.side_effect = side
        with patch(f"{_BASE}.FeedbackWithRelations") as MockFWR:
            MockFWR.return_value = MagicMock()
            with patch(f"{_BASE}.FeedbackList") as MockFL:
                MockFL.return_value = MagicMock()
                result = self._call(db=db)
        MockFWR.assert_called_once()


# ---------------------------------------------------------------------------
# get_session_feedback_summary
# ---------------------------------------------------------------------------

class TestGetSessionFeedbackSummary:
    def _call(self, session_id=1, db=None, current_user=None):
        return get_session_feedback_summary(
            session_id=session_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_session_not_found_404(self):
        """GSFS-01: session not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_no_feedback_returns_zeroed_summary(self):
        """GSFS-02: no feedback → FeedbackSummary(average_rating=0.0, total=0)."""
        s = MagicMock()
        call_n = [0]
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = s
            else:
                q.all.return_value = []
            return q
        db = MagicMock()
        db.query.side_effect = side
        with patch(f"{_BASE}.FeedbackSummary") as MockFS:
            MockFS.return_value = MagicMock()
            result = self._call(db=db)
        MockFS.assert_called_once_with(
            session_id=1, average_rating=0.0, total_feedback=0,
            rating_distribution={}, recent_comments=[]
        )

    def test_with_feedback_calculates_averages(self):
        """GSFS-03: feedback present → averages and distribution computed."""
        s = MagicMock()
        fb1 = MagicMock(); fb1.rating = 5; fb1.is_anonymous = False; fb1.comment = "Excellent"
        fb2 = MagicMock(); fb2.rating = 3; fb2.is_anonymous = False; fb2.comment = "OK"
        call_n = [0]
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = s
            else:
                q.all.return_value = [fb1, fb2]
            return q
        db = MagicMock()
        db.query.side_effect = side
        with patch(f"{_BASE}.FeedbackSummary") as MockFS:
            MockFS.return_value = MagicMock()
            result = self._call(db=db)
        # average = (5+3)/2 = 4.0
        call_kwargs = MockFS.call_args[1]
        assert call_kwargs["average_rating"] == 4.0
        assert call_kwargs["total_feedback"] == 2


# ---------------------------------------------------------------------------
# get_instructor_feedback
# ---------------------------------------------------------------------------

class TestGetInstructorFeedback:
    def _call(self, db=None, current_user=None, page=1, size=50):
        return get_instructor_feedback(
            db=db or MagicMock(),
            current_user=current_user or _instructor(),
            page=page, size=size,
        )

    def test_non_instructor_403(self):
        """GIF-01: non-instructor role → 403."""
        from fastapi import HTTPException
        admin = MagicMock()
        admin.id = 42
        admin.role = MagicMock()
        admin.role.value = 'admin'
        with pytest.raises(HTTPException) as exc:
            self._call(current_user=admin)
        assert exc.value.status_code == 403

    def test_instructor_returns_feedback(self):
        """GIF-02: instructor role → feedback returned."""
        fb = _fb_mock(is_anon=False)
        fb.is_anonymous = False
        fb.session.date_start.isoformat.return_value = "2020-06-15T10:00:00"
        fb.created_at.isoformat.return_value = "2020-06-15T15:00:00"
        q = _q()
        q.all.return_value = [fb]
        q.count.return_value = 1
        db = MagicMock()
        db.query.return_value = q
        instr = _instructor()
        result = self._call(db=db, current_user=instr)
        assert result["total"] == 1
        assert len(result["feedback"]) == 1
