"""
Unit tests for app/api/web_routes/instructor.py

Covers:
  toggle_instructor_specialization — success, not_instructor, not_found
  start_session — success, not_instructor, not_found, wrong_type,
                  wrong_instructor, already_started
  stop_session — success, not_instructor, not_found, wrong_type,
                 wrong_instructor, not_started, already_stopped
  unlock_quiz — success, not_instructor, not_found, wrong_type,
                wrong_instructor, not_started
  take_quiz — not_found, no_session_success, session_not_linked, time_expired,
              existing_attempt_success, session_id_present_full_path
  submit_quiz — not_found, attempt_not_found, already_completed, success_no_pass,
                success_with_pass_creates_user_stats, success_with_pass_updates_stats,
                virtual_session_auto_attendance
  evaluate_student_performance — not_instructor, session_not_found, wrong_session,
                                  session_not_stopped, student_not_attended,
                                  invalid_scores, new_review_success,
                                  update_no_reason, update_with_reason
  evaluate_instructor_session — not_student, session_not_found, not_stopped,
                                 not_attended, invalid_scores, new_review, update_review

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
    unlock_quiz,
    take_quiz,
    submit_quiz,
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


# ──────────────────────────────────────────────────────────────────────────────
# unlock_quiz
# ──────────────────────────────────────────────────────────────────────────────

class TestUnlockQuiz:

    def test_not_instructor_redirects(self):
        user = _student()
        result = _run(unlock_quiz(request=_req(), session_id=1, db=_mock_db(), user=user))
        assert "unauthorized" in result.headers["location"]

    def test_session_not_found_redirects(self):
        user = _instructor()
        result = _run(unlock_quiz(request=_req(), session_id=1, db=_mock_db(None), user=user))
        assert "session_not_found" in result.headers["location"]

    def test_wrong_type_redirects(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.on_site)
        result = _run(unlock_quiz(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "unlock_only_hybrid" in result.headers["location"]

    def test_wrong_instructor_redirects(self):
        user = _instructor(uid=42)
        s = _session_mock(instructor_id=99, session_type=SessionType.hybrid)
        result = _run(unlock_quiz(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "not_your_session" in result.headers["location"]

    def test_not_started_redirects(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.hybrid, actual_start=None)
        result = _run(unlock_quiz(request=_req(), session_id=1, db=_mock_db(s), user=user))
        assert "session_not_started_unlock" in result.headers["location"]

    def test_success_unlocks_quiz(self):
        user = _instructor()
        s = _session_mock(session_type=SessionType.hybrid, actual_start=datetime.now(timezone.utc))
        db = _mock_db(s)
        result = _run(unlock_quiz(request=_req(), session_id=1, db=db, user=user))
        assert "quiz_unlocked" in result.headers["location"]
        assert s.quiz_unlocked is True
        db.commit.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# take_quiz
# ──────────────────────────────────────────────────────────────────────────────

class TestTakeQuiz:

    def test_quiz_not_found_raises_404(self):
        db = _mock_db(None)
        with pytest.raises(HTTPException) as exc_info:
            _run(take_quiz(request=_req(), quiz_id=1, session_id=None, db=db, user=_student()))
        assert exc_info.value.status_code == 404

    def test_no_session_no_active_attempt_creates_attempt(self):
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = [MagicMock(id=1), MagicMock(id=2)]
        quiz.time_limit_minutes = 30

        # First query (Quiz with options): quiz; second (QuizAttempt): None
        attempt = MagicMock()
        attempt.started_at = datetime.now(timezone.utc)
        attempt.id = 10

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.return_value = None  # No active attempt
        db.refresh.side_effect = lambda obj: setattr(obj, 'id', 10)

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(take_quiz(request=_req(), quiz_id=1, session_id=None, db=db, user=user))
        db.add.assert_called()
        db.commit.assert_called()

    def test_quiz_time_expired_returns_result_template(self):
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = [MagicMock()]
        quiz.time_limit_minutes = 0  # Zero minutes → immediately expired

        active_attempt = MagicMock()
        # started_at is far in the past so remaining_seconds = 0
        active_attempt.started_at = datetime.now(timezone.utc) - timedelta(hours=1)

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.return_value = active_attempt

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(take_quiz(request=_req(), quiz_id=1, session_id=None, db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "quiz_result.html"
        assert active_attempt.score == 0.0
        assert active_attempt.passed is False

    def test_quiz_within_time_returns_take_template(self):
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = [MagicMock()]
        quiz.time_limit_minutes = 60

        active_attempt = MagicMock()
        active_attempt.started_at = datetime.now(timezone.utc)  # just started
        active_attempt.id = 5

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.return_value = active_attempt

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(take_quiz(request=_req(), quiz_id=1, session_id=None, db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "quiz_take.html"

    def test_session_quiz_not_found_raises_404(self):
        """When session_id given but quiz not linked to session → 404."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.time_limit_minutes = 30

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        # SessionQuiz query returns None
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=user))
        assert exc_info.value.status_code == 404

    def test_take_quiz_session_id_session_not_found(self):
        """session_id given, SessionQuiz found, Session not found → 404."""
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.time_limit_minutes = 30
        session_quiz = MagicMock()
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.side_effect = [session_quiz, None]

        with pytest.raises(HTTPException) as exc_info:
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=_student()))
        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    def test_take_quiz_session_not_started_raises_403(self):
        """session_id given, session has future start → 403."""
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.time_limit_minutes = 30
        session_quiz = MagicMock()
        session_obj = MagicMock()
        future_naive = (datetime.now(ZoneInfo("Europe/Budapest")) + timedelta(hours=2)).replace(tzinfo=None)
        session_obj.date_start = future_naive
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.side_effect = [session_quiz, session_obj]

        with pytest.raises(HTTPException) as exc_info:
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=_student()))
        assert exc_info.value.status_code == 403

    def test_take_quiz_session_not_booked_raises_403(self):
        """session_id given, session started, booking=None → 403."""
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.time_limit_minutes = 30
        session_quiz = MagicMock()
        session_obj = MagicMock()
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_obj.date_start = past_naive
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.side_effect = [session_quiz, session_obj, None]

        with pytest.raises(HTTPException) as exc_info:
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=_student()))
        assert exc_info.value.status_code == 403
        assert "book this session" in exc_info.value.detail

    def test_take_quiz_session_id_booked_renders_take(self):
        """session_id given, all checks pass → quiz_take.html + line 369 session re-fetch."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = [MagicMock()]
        quiz.time_limit_minutes = 60
        session_quiz = MagicMock()
        session_obj = MagicMock()
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_obj.date_start = past_naive
        booking = MagicMock()
        active_attempt = MagicMock()
        active_attempt.started_at = datetime.now(timezone.utc)
        active_attempt.id = 10
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.side_effect = [
            session_quiz,    # SessionQuiz booking check
            session_obj,     # Session start-time check
            booking,         # Booking check
            active_attempt,  # QuizAttempt
            session_obj,     # Line 369: session re-fetch for template
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "quiz_take.html"

    def test_take_quiz_session_start_aware_datetime_skips_tz_replace(self):
        """date_start is tz-aware → 296→299 False branch (skip replace)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.time_limit_minutes = 60
        session_quiz = MagicMock()
        session_obj = MagicMock()
        bud = ZoneInfo("Europe/Budapest")
        session_obj.date_start = datetime.now(bud) - timedelta(hours=1)  # tz-aware, already past
        booking = MagicMock()
        active_attempt = MagicMock()
        active_attempt.started_at = datetime.now(timezone.utc)
        active_attempt.id = 10
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = quiz
        db.query.return_value.filter.return_value.first.side_effect = [
            session_quiz,   # SessionQuiz check
            session_obj,    # Session time check — tz-aware, skips replace
            booking,        # Booking check
            active_attempt, # QuizAttempt
            session_obj,    # line 369: session re-fetch for template
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(take_quiz(request=_req(), quiz_id=1, session_id=5, db=db, user=user))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "quiz_take.html"


# ──────────────────────────────────────────────────────────────────────────────
# submit_quiz
# ──────────────────────────────────────────────────────────────────────────────

class TestSubmitQuiz:
    """Tests for the submit_quiz endpoint.

    DB query order when session_id is provided (not None/"None"):
    ─────────────────────────────────────────────────────────────
    The endpoint always starts by fetching the Quiz object (options chain).
    When session_id is set, a *session validation block* runs BEFORE
    processing the QuizAttempt:

      filter().first() side_effect order:
        1. Quiz          — db.query(Quiz).options(...).filter(...).first()
        2. SessionQuiz   — db.query(SessionQuiz).filter(...).first()
        3. SessionModel  — time-check: date_start must be a real naive Budapest
                           datetime (< now → allowed; > now → 403)
                           Use: (datetime.now(ZoneInfo("Europe/Budapest")) ± delta).replace(tzinfo=None)
        4. Booking       — auth-check: must not be None, else 403
        5. QuizAttempt   — existing attempt lookup
        [questions loop — no DB calls]
        6. SessionModel  — re-fetch after commit (line ~523)
        7. Booking       — for auto-attendance when virtual + passed (line ~527)
        8. AttendanceRecord — existing attendance check (None → create new)

    When session_id is None/"None", steps 2–4 and 6–8 are skipped.
    """

    def _make_req_with_form(self, form_data=None):
        req = MagicMock()
        req.form = AsyncMock(return_value=form_data or {})
        return req

    def test_quiz_not_found_raises_404(self):
        db = _mock_db(None)
        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id=None,
                attempt_id=1,
                time_spent=5.0,
                db=db,
                user=_student(),
            ))
        assert exc_info.value.status_code == 404

    def test_attempt_not_found_raises_404(self):
        quiz = MagicMock()
        quiz.id = 1

        db = MagicMock()
        # First .first() = quiz, second = attempt (None)
        db.query.return_value.filter.return_value.first.side_effect = [quiz, None]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id=None,
                attempt_id=1,
                time_spent=5.0,
                db=db,
                user=_student(),
            ))
        assert exc_info.value.status_code == 404

    def test_already_completed_raises_400(self):
        quiz = MagicMock()
        quiz.id = 1
        attempt = MagicMock()
        attempt.completed_at = datetime.now(timezone.utc)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id=None,
                attempt_id=1,
                time_spent=5.0,
                db=db,
                user=_student(),
            ))
        assert exc_info.value.status_code == 400

    def test_submit_success_no_pass_returns_result_template(self):
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []  # No questions → score = 0
        quiz.passing_score = 0.70  # 70% to pass
        quiz.xp_reward = 50

        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id=None,
                attempt_id=1,
                time_spent=5.0,
                db=db,
                user=user,
            ))

        template_name = mock_tmpl.TemplateResponse.call_args.args[0]
        assert template_name == "quiz_result.html"
        assert attempt.passed is False
        assert attempt.xp_awarded == 0

    def test_submit_success_with_pass_creates_user_stats(self):
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []  # Simplified: no questions
        quiz.passing_score = 0.0  # Always pass with any score
        quiz.xp_reward = 100

        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1

        db = MagicMock()
        # quiz, attempt, then user_stats (None → create path)
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt, None]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id=None,
                attempt_id=1,
                time_spent=3.0,
                db=db,
                user=user,
            ))

        # UserStats created and added
        db.add.assert_called()
        assert attempt.xp_awarded == 100

    def test_submit_with_session_id_none_string_no_validation(self):
        """session_id='None' (string) → no session validation performed."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 1.0  # Never passes
        quiz.xp_reward = 0

        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1,
                session_id="None",
                attempt_id=1,
                time_spent=2.0,
                db=db,
                user=user,
            ))

        mock_tmpl.TemplateResponse.assert_called_once()

    def test_submit_session_quiz_link_not_found(self):
        """session_id given, SessionQuiz=None → 404."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [MagicMock(), None]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(), quiz_id=1, session_id="5",
                attempt_id=1, time_spent=5.0, db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 404
        assert "not found for this session" in exc_info.value.detail

    def test_submit_session_not_found(self):
        """session_id given, SessionQuiz found, Session not found → 404."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            MagicMock(),  # quiz
            MagicMock(),  # session_quiz
            None,         # session = None
        ]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(), quiz_id=1, session_id="5",
                attempt_id=1, time_spent=5.0, db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    def test_submit_session_not_started_403(self):
        """session_id given, session has future start → 403."""
        session_obj = MagicMock()
        future_naive = (datetime.now(ZoneInfo("Europe/Budapest")) + timedelta(hours=2)).replace(tzinfo=None)
        session_obj.date_start = future_naive

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            MagicMock(),  # quiz
            MagicMock(),  # session_quiz
            session_obj,  # session with future start
        ]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(), quiz_id=1, session_id="5",
                attempt_id=1, time_spent=5.0, db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 403

    def test_submit_session_not_booked_403(self):
        """session_id given, session started, booking=None → 403."""
        session_obj = MagicMock()
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_obj.date_start = past_naive

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            MagicMock(),  # quiz
            MagicMock(),  # session_quiz
            session_obj,  # session with past start
            None,         # booking = None
        ]

        with pytest.raises(HTTPException) as exc_info:
            _run(submit_quiz(
                request=self._make_req_with_form(), quiz_id=1, session_id="5",
                attempt_id=1, time_spent=5.0, db=db, user=_student(),
            ))
        assert exc_info.value.status_code == 403
        assert "book this session" in exc_info.value.detail

    def test_submit_unanswered_question_skips_scoring(self):
        """Question with no form answer → FALSE branch of line 469 (if selected_option_id)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        question = MagicMock()
        question.id = 7
        question.points = 10
        quiz.questions = [question]
        quiz.passing_score = 0.70
        quiz.xp_reward = 50
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt]

        req = MagicMock()
        req.form = AsyncMock(return_value={})  # No answer for question_7

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=req, quiz_id=1, session_id=None,
                attempt_id=1, time_spent=5.0, db=db, user=user,
            ))

        assert attempt.passed is False
        assert attempt.xp_awarded == 0

    def test_submit_incorrect_answer_no_points(self):
        """Selected answer is wrong → FALSE branch of line 473 (if option.is_correct)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        question = MagicMock()
        question.id = 7
        question.points = 10
        quiz.questions = [question]
        quiz.passing_score = 0.70
        quiz.xp_reward = 50
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        wrong_option = MagicMock()
        wrong_option.is_correct = False
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt, wrong_option]

        req = MagicMock()
        req.form = AsyncMock(return_value={"question_7": "42"})

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=req, quiz_id=1, session_id=None,
                attempt_id=1, time_spent=5.0, db=db, user=user,
            ))

        assert attempt.correct_answers == 0
        assert attempt.xp_awarded == 0

    def test_submit_existing_user_stats_updated(self):
        """Passed quiz with existing UserStats → update path (lines 513-515)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 0.0  # Always pass
        quiz.xp_reward = 100
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        existing_stats = MagicMock()
        existing_stats.total_xp = 500
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt, existing_stats]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id=None,
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        assert existing_stats.total_xp == 600  # 500 + 100

    def test_submit_virtual_session_auto_attendance(self):
        """Virtual session + quiz passed → auto-attendance created (lines 526-550)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 0.0  # Always pass
        quiz.xp_reward = 0        # Avoid UserStats query
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        # Validation session (lines 401-440): needs real date_start in the past
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_for_validation = MagicMock()
        session_for_validation.date_start = past_naive
        # Session for virtual attendance (line 523): needs session_type.value = 'virtual'
        session_for_attendance = MagicMock()
        session_for_attendance.id = 5
        session_for_attendance.session_type.value = 'virtual'
        booking_auth = MagicMock()    # booking for auth check (line 430-440)
        booking_attend = MagicMock()  # booking for auto-attendance (line 527)
        booking_attend.id = 10
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            quiz,                   # 1: Quiz
            MagicMock(),            # 2: SessionQuiz (validation)
            session_for_validation, # 3: SessionModel time-check
            booking_auth,           # 4: Booking auth-check
            attempt,                # 5: QuizAttempt
            session_for_attendance, # 6: SessionModel after commit (line 523)
            booking_attend,         # 7: Booking for auto-attendance (line 527)
            None,                   # 8: existing_attendance → create
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id="5",
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        db.add.assert_called()
        assert db.commit.call_count >= 2

    def test_submit_session_start_aware_skips_tz_replace(self):
        """date_start is tz-aware → 420→423 False branch (skip replace)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 1.0
        quiz.xp_reward = 0
        bud = ZoneInfo("Europe/Budapest")
        session_obj = MagicMock()
        session_obj.date_start = datetime.now(bud) - timedelta(hours=1)  # tz-aware
        session_obj.session_type.value = "on_site"
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            quiz,           # Quiz
            MagicMock(),    # SessionQuiz
            session_obj,    # Session (tz-aware, no replace)
            MagicMock(),    # Booking auth
            attempt,        # QuizAttempt
            session_obj,    # re-fetch after commit
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id="5",
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        mock_tmpl.TemplateResponse.assert_called_once()

    def test_submit_correct_answer_increments_score(self):
        """Correct answer → 474-475 covered (correct_count += 1, earned_points += question.points)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        question = MagicMock()
        question.id = 7
        question.points = 10
        quiz.questions = [question]
        quiz.passing_score = 0.5  # 50% threshold
        quiz.xp_reward = 0
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        correct_option = MagicMock()
        correct_option.is_correct = True
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [quiz, attempt, correct_option]

        req = MagicMock()
        req.form = AsyncMock(return_value={"question_7": "42"})

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=req, quiz_id=1, session_id=None,
                attempt_id=1, time_spent=5.0, db=db, user=user,
            ))

        assert attempt.correct_answers == 1
        assert attempt.score == 100.0

    def test_submit_non_virtual_session_skips_auto_attendance(self):
        """Non-virtual session + passed → 526→556 False branch (not virtual)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 0.0  # Always pass
        quiz.xp_reward = 0
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_obj = MagicMock()
        session_obj.date_start = past_naive
        session_obj.session_type.value = "on_site"  # NOT virtual → skip auto-attendance
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            quiz,           # Quiz
            MagicMock(),    # SessionQuiz validation
            session_obj,    # Session time check
            MagicMock(),    # Booking auth
            attempt,        # QuizAttempt
            session_obj,    # re-fetch after commit (line 523)
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id="5",
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        mock_tmpl.TemplateResponse.assert_called_once()

    def test_submit_virtual_no_booking_skips_auto_attendance(self):
        """Virtual + passed, booking=None → 532→556 False branch (no auto-attendance)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 0.0
        quiz.xp_reward = 0
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_for_validation = MagicMock()
        session_for_validation.date_start = past_naive
        session_for_attendance = MagicMock()
        session_for_attendance.id = 5
        session_for_attendance.session_type.value = "virtual"
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            quiz,                    # Quiz
            MagicMock(),             # SessionQuiz validation
            session_for_validation,  # Session time check
            MagicMock(),             # Booking auth
            attempt,                 # QuizAttempt
            session_for_attendance,  # re-fetch after commit
            None,                    # booking for auto-attendance = None → skip
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id="5",
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        mock_tmpl.TemplateResponse.assert_called_once()

    def test_submit_virtual_existing_attendance_skips_create(self):
        """Virtual + passed + booking found + existing_attendance → 539→556 False (no double-create)."""
        user = _student(uid=99)
        quiz = MagicMock()
        quiz.id = 1
        quiz.questions = []
        quiz.passing_score = 0.0
        quiz.xp_reward = 0
        past_naive = (datetime.now(ZoneInfo("Europe/Budapest")) - timedelta(hours=1)).replace(tzinfo=None)
        session_for_validation = MagicMock()
        session_for_validation.date_start = past_naive
        session_for_attendance = MagicMock()
        session_for_attendance.id = 5
        session_for_attendance.session_type.value = "virtual"
        booking_attend = MagicMock()
        booking_attend.id = 10
        existing_att = MagicMock()  # already exists → skip create
        attempt = MagicMock()
        attempt.completed_at = None
        attempt.id = 1
        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            quiz,                    # Quiz
            MagicMock(),             # SessionQuiz validation
            session_for_validation,  # Session time check
            MagicMock(),             # Booking auth
            attempt,                 # QuizAttempt
            session_for_attendance,  # re-fetch after commit
            booking_attend,          # booking for auto-attendance
            existing_att,            # existing_attendance found → don't create
        ]

        with patch(f"{_BASE}.templates") as mock_tmpl:
            mock_tmpl.TemplateResponse.return_value = MagicMock()
            _run(submit_quiz(
                request=self._make_req_with_form(),
                quiz_id=1, session_id="5",
                attempt_id=1, time_spent=3.0, db=db, user=user,
            ))

        mock_tmpl.TemplateResponse.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# evaluate_student_performance
# ──────────────────────────────────────────────────────────────────────────────

_PATCH_XP = f"{_BASE}._update_specialization_xp"

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
