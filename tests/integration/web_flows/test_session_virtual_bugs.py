"""
Virtual Session Page — Bug Fix Tests (SBF-01..04)

SBF-01  passing_score=0.60 → template shows "60%" (not "6000%")
SBF-02  Tournament-enrolled student (SemesterEnrollment only, no Booking)
        → is_enrolled=True, quiz section visible (no "Enrollment Required")
SBF-03  Virtual session with meeting_link → "💻 Meeting Link" shown (not "📍 Location: TBA")
SBF-04  Virtual session without meeting_link → "TBA" shown under "💻 Meeting Link"
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.dependencies import get_current_user_web
from app.models.session import Session as SessionModel, SessionType
from app.models.quiz import (
    Quiz, QuizCategory, QuizDifficulty,
    QuizQuestion, QuestionType, QuizAnswerOption, SessionQuiz,
)
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _override_get_db(test_db):
    def override():
        try:
            yield test_db
        finally:
            pass
    return override


@contextmanager
def _web_client(test_db, user):
    app.dependency_overrides[get_db] = _override_get_db(test_db)
    app.dependency_overrides[get_current_user_web] = lambda: user
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _make_quiz(test_db, passing_score: float) -> Quiz:
    """Create an active quiz with one MC question."""
    quiz = Quiz(
        title=f"SBF Quiz {uuid.uuid4().hex[:6]}",
        category=QuizCategory.GENERAL,
        difficulty=QuizDifficulty.EASY,
        time_limit_minutes=10,
        xp_reward=50,
        passing_score=passing_score,
        is_active=True,
    )
    test_db.add(quiz)
    test_db.flush()

    q = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Test question?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        points=1,
        order_index=0,
    )
    test_db.add(q)
    test_db.flush()

    test_db.add(QuizAnswerOption(question_id=q.id, option_text="Yes", is_correct=True, order_index=0))
    test_db.add(QuizAnswerOption(question_id=q.id, option_text="No", is_correct=False, order_index=1))
    test_db.commit()
    test_db.refresh(quiz)
    return quiz


def _make_virtual_session(test_db, semester_id, instructor_id, meeting_link=None) -> SessionModel:
    """Create a future virtual session linked to a semester (well within booking window)."""
    now = datetime.now()
    s = SessionModel(
        title=f"Virtual SBF Session {uuid.uuid4().hex[:6]}",
        session_type=SessionType.virtual,
        semester_id=semester_id,
        instructor_id=instructor_id,
        date_start=now + timedelta(days=3),
        date_end=now + timedelta(days=3, hours=2),
        capacity=10,
        meeting_link=meeting_link,
    )
    test_db.add(s)
    test_db.commit()
    test_db.refresh(s)
    return s


def _enroll(test_db, user_id, semester_id) -> SemesterEnrollment:
    """Enroll a student via SemesterEnrollment (tournament-style, no Booking).

    SemesterEnrollment requires a UserLicense FK (NOT NULL). Create one if absent.
    """
    lic = test_db.query(UserLicense).filter(UserLicense.user_id == user_id).first()
    if not lic:
        lic = UserLicense(
            user_id=user_id,
            specialization_type="LFA_FOOTBALL_PLAYER",
            current_level=1,
            max_achieved_level=1,
            started_at=datetime.now(timezone.utc),
            is_active=True,
        )
        test_db.add(lic)
        test_db.flush()

    enr = SemesterEnrollment(
        user_id=user_id,
        semester_id=semester_id,
        user_license_id=lic.id,
        is_active=True,
        request_status=EnrollmentStatus.APPROVED,
        enrolled_at=datetime.now(timezone.utc),
    )
    test_db.add(enr)
    test_db.commit()
    test_db.refresh(enr)
    return enr


# ─────────────────────────────────────────────────────────────────────────────
# Tests — use `semester` fixture from web_flows/conftest.py (fresh per test)
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionVirtualBugs:

    def test_SBF_01_passing_score_0_60_displays_60_percent(
        self, test_db, semester, student_user, instructor_user
    ):
        """SBF-01: passing_score=0.60 → template shows '60%', NOT '6000%'."""
        quiz = _make_quiz(test_db, passing_score=0.60)
        session = _make_virtual_session(test_db, semester.id, instructor_user.id)
        sq = SessionQuiz(session_id=session.id, quiz_id=quiz.id, max_attempts=2)
        test_db.add(sq)
        test_db.commit()

        _enroll(test_db, student_user.id, semester.id)

        with _web_client(test_db, student_user) as client:
            resp = client.get(f"/sessions/{session.id}")

        assert resp.status_code == 200
        html = resp.text
        assert "6000%" not in html, "passing_score=0.60 must NOT display as 6000%"
        assert "60%" in html, "passing_score=0.60 must display as '60%'"

    def test_SBF_02_semester_enrolled_student_sees_quiz_not_enrollment_required(
        self, test_db, semester, student_user, instructor_user
    ):
        """SBF-02: SemesterEnrollment (no Booking) → quiz visible, not 'Enrollment Required'."""
        quiz = _make_quiz(test_db, passing_score=0.60)
        session = _make_virtual_session(test_db, semester.id, instructor_user.id)
        sq = SessionQuiz(session_id=session.id, quiz_id=quiz.id, max_attempts=2)
        test_db.add(sq)
        test_db.commit()

        # Only SemesterEnrollment — NO Booking created
        _enroll(test_db, student_user.id, semester.id)

        with _web_client(test_db, student_user) as client:
            resp = client.get(f"/sessions/{session.id}")

        assert resp.status_code == 200
        html = resp.text
        assert "Enrollment Required" not in html, \
            "SemesterEnrollment must grant quiz access — no 'Enrollment Required'"
        assert "You must book this session before you can take the quiz" not in html
        assert quiz.title in html, "Quiz title must appear when student is enrolled"

    def test_SBF_03_virtual_session_shows_meeting_link(
        self, test_db, semester, student_user, instructor_user
    ):
        """SBF-03: Virtual session with meeting_link → '💻 Meeting Link' shown."""
        meeting_url = "https://meet.example.com/lfa-virtual-abc"
        session = _make_virtual_session(
            test_db, semester.id, instructor_user.id, meeting_link=meeting_url
        )
        _enroll(test_db, student_user.id, semester.id)

        with _web_client(test_db, student_user) as client:
            resp = client.get(f"/sessions/{session.id}")

        assert resp.status_code == 200
        html = resp.text
        assert "Meeting Link" in html, "Virtual session must show '💻 Meeting Link'"
        assert meeting_url in html, "The actual meeting URL must appear in the page"
        assert "📍 Location:" not in html, \
            "Virtual session must NOT show '📍 Location:'"

    def test_SBF_04_virtual_session_without_meeting_link_shows_tba(
        self, test_db, semester, student_user, instructor_user
    ):
        """SBF-04: Virtual session with no meeting_link → 'TBA' under '💻 Meeting Link'."""
        session = _make_virtual_session(
            test_db, semester.id, instructor_user.id, meeting_link=None
        )
        _enroll(test_db, student_user.id, semester.id)

        with _web_client(test_db, student_user) as client:
            resp = client.get(f"/sessions/{session.id}")

        assert resp.status_code == 200
        html = resp.text
        assert "Meeting Link" in html
        assert "TBA" in html
        assert "📍 Location:" not in html
