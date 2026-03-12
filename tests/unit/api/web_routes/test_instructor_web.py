"""
Unit tests for app/api/web_routes/instructor.py

Covers:
  toggle_instructor_specialization — success, not_instructor, not_found
  start_session — success, not_instructor, not_found, wrong_type,
                  wrong_instructor, already_started
  stop_session — success, not_instructor, not_found, wrong_type,
                 wrong_instructor, not_started, already_stopped
  evaluate_student_performance — not_instructor, session_not_found, wrong_session,
                                  session_not_stopped, student_not_attended,
                                  invalid_scores, new_review_success,
                                  update_no_reason, update_with_reason
  evaluate_instructor_session — not_student, session_not_found, not_stopped,
                                 not_attended, invalid_scores, new_review, update_review

Note: unlock_quiz, take_quiz, submit_quiz tests removed — canonical owner is quiz.py

Mock strategy:
  - db = MagicMock(); db.query(...).filter(...).first() returns configured mock objects
  - patch("app.api.web_routes.instructor.templates") for TemplateResponse
  - patch("app.api.web_routes.instructor._update_specialization_xp")  (imported from helpers, fixed Sprint 54 P1)
  - asyncio.run(endpoint(...)) calls async functions directly without FastAPI DI
"""
import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.api.web_routes.instructor import (
    toggle_instructor_specialization,
    start_session,
    stop_session,
    evaluate_student_performance,
    evaluate_instructor_session,
    ToggleSpecializationRequest,
)
from app.models.user import UserRole
from app.models.session import SessionType
from app.models.attendance import AttendanceStatus


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_BASE = "app.api.web_routes.instructor"
_PATCH_XP = f"{_BASE}._update_specialization_xp"


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    u.email = "instructor@test.com"
    u.specialization = None
    return u


def _student(uid=99):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.STUDENT
    u.email = "student@test.com"
    return u


def _session_mock(
    session_id=1,
    instructor_id=42,
    session_type=SessionType.on_site,
    actual_start=None,
    actual_end=None,
):
    s = MagicMock()
    s.id = session_id
    s.instructor_id = instructor_id
    s.session_type = session_type
    s.actual_start_time = actual_start
    s.actual_end_time = actual_end
    return s


def _mock_db(first_return=None):
    """DB where every query().filter().first() returns the given value."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = first_return
    db.query.return_value.options.return_value.filter.return_value.first.return_value = first_return
    return db


def _seq_db(*returns):
    """DB whose successive .first() calls return each value in order."""
    db = MagicMock()
    side_effects = list(returns) + [MagicMock()] * 20
    db.query.return_value.filter.return_value.first.side_effect = side_effects
    db.query.return_value.options.return_value.filter.return_value.first.side_effect = side_effects
    return db


def _req():
    return MagicMock()


def _run(coro):
    return asyncio.run(coro)


# ──────────────────────────────────────────────────────────────────────────────
# toggle_instructor_specialization
# ──────────────────────────────────────────────────────────────────────────────

class TestToggleInstructorSpecialization:

    def test_not_instructor_raises_403(self):
        user = _student()
        db = _mock_db()
        toggle = ToggleSpecializationRequest(specialization="football", is_active=True)
        with pytest.raises(HTTPException) as exc_info:
            _run(toggle_instructor_specialization(request=_req(), toggle_data=toggle, db=db, user=user))
        assert exc_info.value.status_code == 403

    def test_specialization_not_found_raises_404(self):
        user = _instructor()
        db = _mock_db(first_return=None)
        toggle = ToggleSpecializationRequest(specialization="football", is_active=True)
        with pytest.raises(HTTPException) as exc_info:
            _run(toggle_instructor_specialization(request=_req(), toggle_data=toggle, db=db, user=user))
        assert exc_info.value.status_code == 404

    def test_success_returns_json_response(self):
        user = _instructor()
        spec_record = MagicMock()
        db = _mock_db(first_return=spec_record)
        toggle = ToggleSpecializationRequest(specialization="football", is_active=False)
        result = _run(toggle_instructor_specialization(request=_req(), toggle_data=toggle, db=db, user=user))
        assert isinstance(result, JSONResponse)
        assert spec_record.is_active is False
        db.commit.assert_called_once()

    def test_success_activates_specialization(self):
        user = _instructor()
        spec_record = MagicMock()
        db = _mock_db(first_return=spec_record)
        toggle = ToggleSpecializationRequest(specialization="football", is_active=True)
        _run(toggle_instructor_specialization(request=_req(), toggle_data=toggle, db=db, user=user))
        assert spec_record.is_active is True


# ──────────────────────────────────────────────────────────────────────────────
# start_session
# ──────────────────────────────────────────────────────────────────────────────

class TestStartSession:

    def test_not_instructor_redirects(self):
        user = _student()
        result = _run(start_session(request=_req(), session_id=1, db=_mock_db(), user=user))
        assert isinstance(result, RedirectResponse)
        assert "unauthorized" in result.headers["location"]

    def test_session_not_found_redirects(self):
        user = _instructor()
        result = _run(start_session(request=_req(), session_id=1, db=_mock_db(None), user=user))
        assert isinstance(result, RedirectResponse)
        assert "session_not_found" in result.headers["location"]

    def test_wrong_session_type_redirects(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.virtual)
        result = _run(start_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "timer_only_onsite_hybrid" in result.headers["location"]

    def test_not_your_session_redirects(self):
        user = _instructor(uid=42)
        s = _session_mock(instructor_id=99, session_type=SessionType.on_site)
        result = _run(start_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "not_your_session" in result.headers["location"]

    def test_already_started_redirects(self):
        user = _instructor()
        s = _session_mock(actual_start=datetime.now(timezone.utc))
        result = _run(start_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "session_already_started" in result.headers["location"]

    def test_success_redirects_session_started(self):
        user = _instructor()
        s = _session_mock(actual_start=None)
        db = _mock_db(s)
        result = _run(start_session(request=_req(), session_id=1, db=db, user=user))
        assert "session_started" in result.headers["location"]
        db.commit.assert_called_once()
        assert s.session_status == "in_progress"

    def test_success_hybrid_session(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.hybrid, actual_start=None)
        db = _mock_db(s)
        result = _run(start_session(request=_req(), session_id=1, db=db, user=user))
        assert "session_started" in result.headers["location"]


# ──────────────────────────────────────────────────────────────────────────────
# stop_session
# ──────────────────────────────────────────────────────────────────────────────

class TestStopSession:

    def test_not_instructor_redirects(self):
        user = _student()
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(), user=user))
        assert "unauthorized" in result.headers["location"]

    def test_session_not_found_redirects(self):
        user = _instructor()
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(None), user=user))
        assert "session_not_found" in result.headers["location"]

    def test_wrong_type_redirects(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.virtual)
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "timer_only_onsite_hybrid" in result.headers["location"]

    def test_wrong_instructor_redirects(self):
        user = _instructor(uid=42)
        s = _session_mock(instructor_id=99, session_type=SessionType.on_site)
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "not_your_session" in result.headers["location"]

    def test_not_started_redirects(self):
        user = _instructor()
        s = _session_mock(actual_start=None, actual_end=None)
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "session_not_started" in result.headers["location"]

    def test_already_stopped_redirects(self):
        user = _instructor()
        s = _session_mock(
            actual_start=datetime.now(timezone.utc),
            actual_end=datetime.now(timezone.utc),
        )
        result = _run(stop_session(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "session_already_stopped" in result.headers["location"]

    def test_success_redirects_session_stopped(self):
        user = _instructor()
        s = _session_mock(
            actual_start=datetime.now(timezone.utc) - timedelta(hours=1),
            actual_end=None,
        )
        db = _mock_db(s)
        result = _run(stop_session(request=_req(), session_id=1, db=db, user=user))
        assert "session_stopped" in result.headers["location"]
        db.commit.assert_called_once()
        assert s.session_status == "completed"

_EVAL_SCORES = dict(
    punctuality=4, engagement=4, focus=4, collaboration=4, attitude=4,
    comments="Good", update_reason=None,
)


class TestEvaluateStudentPerformance:

    def test_not_instructor_redirects(self):
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=_mock_db(), user=_student(), **_EVAL_SCORES,
        ))
        assert "unauthorized" in result.headers["location"]

    def test_session_not_found_redirects(self):
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=_mock_db(None), user=_instructor(), **_EVAL_SCORES,
        ))
        assert "session_not_found" in result.headers["location"]

    def test_not_your_session_redirects(self):
        user = _instructor(uid=42)
        s = _session_mock(instructor_id=99)
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=_mock_db(s), user=user, **_EVAL_SCORES,
        ))
        assert "not_your_session" in result.headers["location"]

    def test_session_not_stopped_redirects(self):
        user = _instructor()
        s = _session_mock(actual_end=None)
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=_mock_db(s), user=user, **_EVAL_SCORES,
        ))
        assert "session_not_stopped" in result.headers["location"]

    def test_student_not_attended_redirects(self):
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.absent

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance]
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=db, user=user, **_EVAL_SCORES,
        ))
        assert "student_not_attended" in result.headers["location"]

    def test_invalid_scores_redirects(self):
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, None]
        bad_scores = dict(
            punctuality=6, engagement=4, focus=4, collaboration=4, attitude=4,
            comments=None, update_reason=None,
        )
        result = _run(evaluate_student_performance(
            request=_req(), session_id=1, student_id=2,
            db=db, user=user, **bad_scores,
        ))
        assert "invalid_scores" in result.headers["location"]

    def test_new_review_success(self):
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present
        student = MagicMock()
        student.specialization = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, None, student]

        with patch(_PATCH_XP) as mock_xp:
            result = _run(evaluate_student_performance(
                request=_req(), session_id=1, student_id=2,
                db=db, user=user, **_EVAL_SCORES,
            ))

        assert "student_evaluated" in result.headers["location"]
        db.add.assert_called()
        db.commit.assert_called()
        mock_xp.assert_called_once()

    def test_update_review_no_reason_redirects(self):
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present
        existing_review = MagicMock()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, existing_review]
        # update_reason=None (already in _EVAL_SCORES) → no reason provided → should redirect
        with patch(_PATCH_XP):
            result = _run(evaluate_student_performance(
                request=_req(), session_id=1, student_id=2,
                db=db, user=user,
                punctuality=4, engagement=4, focus=4, collaboration=4, attitude=4,
                comments="OK", update_reason=None,
            ))
        assert "update_reason_required" in result.headers["location"]

    def test_update_review_with_reason_success(self):
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present
        existing_review = MagicMock()
        existing_review.comments = "Old comment"
        student = MagicMock()
        student.specialization = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, existing_review, student]

        with patch(_PATCH_XP) as mock_xp:
            result = _run(evaluate_student_performance(
                request=_req(), session_id=1, student_id=2,
                db=db, user=user,
                punctuality=4, engagement=4, focus=4, collaboration=4, attitude=4,
                comments="Good", update_reason="Correction",
            ))

        assert "student_evaluated" in result.headers["location"]
        mock_xp.assert_called_once()

    def test_update_review_no_comments_path(self):
        """Updating review with update_reason but no comments → else branch (line 668-669)."""
        user = _instructor()
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present
        existing_review = MagicMock()
        existing_review.comments = "Previous comment"
        student = MagicMock()
        student.specialization = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, existing_review, student]

        with patch(_PATCH_XP):
            result = _run(evaluate_student_performance(
                request=_req(), session_id=1, student_id=2,
                db=db, user=user,
                punctuality=4, engagement=4, focus=4, collaboration=4, attitude=4,
                comments=None,             # No comments → else branch (line 668-669)
                update_reason="Correction needed",
            ))

        assert "student_evaluated" in result.headers["location"]
        # else branch: existing_review.comments = (existing_review.comments or "") + update_note
        assert existing_review.comments.startswith("Previous comment")


# ──────────────────────────────────────────────────────────────────────────────
# evaluate_instructor_session
# ──────────────────────────────────────────────────────────────────────────────

_INST_SCORES = dict(
    instructor_clarity=4, support_approachability=4, session_structure=4,
    relevance=4, environment=4, engagement_feeling=4, feedback_quality=4,
    satisfaction=4, comments="Great session",
)


class TestEvaluateInstructorSession:

    def test_not_student_redirects(self):
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=_mock_db(), user=_instructor(), **_INST_SCORES,
        ))
        assert "students_only" in result.headers["location"]

    def test_session_not_found_redirects(self):
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=_mock_db(None), user=_student(), **_INST_SCORES,
        ))
        assert "session_not_found" in result.headers["location"]

    def test_session_not_stopped_redirects(self):
        s = _session_mock(actual_end=None)
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=_mock_db(s), user=_student(), **_INST_SCORES,
        ))
        assert "session_not_stopped" in result.headers["location"]

    def test_student_not_attended_redirects(self):
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.absent

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance]
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=db, user=_student(), **_INST_SCORES,
        ))
        assert "must_attend_to_review" in result.headers["location"]

    def test_invalid_scores_redirects(self):
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, None]
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1, db=db, user=_student(),
            instructor_clarity=10,  # Invalid score > 5
            support_approachability=4, session_structure=4, relevance=4,
            environment=4, engagement_feeling=4, feedback_quality=4,
            satisfaction=4, comments=None,
        ))
        assert "invalid_scores" in result.headers["location"]

    def test_new_review_creates_and_redirects(self):
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        s.instructor_id = 42
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, None]
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=db, user=_student(), **_INST_SCORES,
        ))
        assert "instructor_evaluated" in result.headers["location"]
        db.add.assert_called()
        db.commit.assert_called()

    def test_update_review_updates_and_redirects(self):
        s = _session_mock(actual_end=datetime.now(timezone.utc))
        attendance = MagicMock()
        attendance.status = AttendanceStatus.present
        existing_review = MagicMock()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [s, attendance, existing_review]
        result = _run(evaluate_instructor_session(
            request=_req(), session_id=1,
            db=db, user=_student(), **_INST_SCORES,
        ))
        assert "instructor_evaluated" in result.headers["location"]
        assert existing_review.instructor_clarity == 4
        db.commit.assert_called()
