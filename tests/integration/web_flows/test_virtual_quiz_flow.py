"""
Integration test: Virtual session quiz submission flow

Positive flows:
  Student POSTs /quizzes/{quiz_id}/submit (without session_id)
    → 200 TemplateResponse (quiz_result.html)
    → QuizAttempt.completed_at set in DB

Negative flows:
  - Submit already-completed attempt                    → 400
  - Submit with nonexistent attempt_id                 → 404
  - Submit with session_id but no booking              → 403 (not booked for session)

Design notes:
  - session_id omitted → skips session/booking validation entirely
  - Quiz has no questions → correct_count=0, total_points=0, score=0, passed=False
  - xp_awarded=0 → no UserStats update triggered
  - Response is a rendered HTML page (TemplateResponse), NOT a redirect

DB validation:
  - attempt.completed_at transitions None → datetime
  - attempt.passed == False (0% < 60% passing_score)
  - attempt.score == 0.0
  - Failed submissions do NOT modify the attempt row
"""

import pytest
from app.models.quiz import QuizAttempt


class TestVirtualQuizSubmission:

    def test_submit_quiz_marks_attempt_completed(
        self,
        student_client,
        simple_quiz,
        student_user,
        test_db,
    ):
        """POST /quizzes/{id}/submit → 200 HTML + QuizAttempt.completed_at set in DB."""
        # Create an active (incomplete) attempt
        attempt = QuizAttempt(
            user_id=student_user.id,
            quiz_id=simple_quiz.id,
            total_questions=0,
        )
        test_db.add(attempt)
        test_db.commit()
        test_db.refresh(attempt)
        assert attempt.completed_at is None

        resp = student_client.post(
            f"/quizzes/{simple_quiz.id}/submit",
            data={
                "attempt_id": str(attempt.id),
                "time_spent": "30.0",
                # session_id intentionally omitted → skip session/booking checks
            },
        )

        # submit_quiz renders quiz_result.html (TemplateResponse), not a redirect
        assert resp.status_code == 200

        # Verify DB state
        test_db.expire_all()
        updated = test_db.query(QuizAttempt).filter(QuizAttempt.id == attempt.id).first()
        assert updated.completed_at is not None
        assert updated.score == 0.0        # 0 questions → 0%
        assert updated.passed is False     # 0% < 60% threshold
        assert updated.xp_awarded == 0    # xp only if passed

    def test_submit_already_completed_attempt_returns_400(
        self,
        student_client,
        simple_quiz,
        student_user,
        test_db,
    ):
        """Submitting an already-completed attempt raises 400."""
        from datetime import datetime, timezone

        attempt = QuizAttempt(
            user_id=student_user.id,
            quiz_id=simple_quiz.id,
            total_questions=0,
            completed_at=datetime.now(timezone.utc),  # already done
        )
        test_db.add(attempt)
        test_db.commit()
        test_db.refresh(attempt)

        resp = student_client.post(
            f"/quizzes/{simple_quiz.id}/submit",
            data={
                "attempt_id": str(attempt.id),
                "time_spent": "10.0",
            },
        )

        assert resp.status_code == 400

    def test_submit_nonexistent_attempt_returns_404(
        self,
        student_client,
        simple_quiz,
    ):
        """Submitting with an attempt_id that doesn't exist → 404."""
        resp = student_client.post(
            f"/quizzes/{simple_quiz.id}/submit",
            data={
                "attempt_id": "99999",
                "time_spent": "5.0",
            },
        )

        assert resp.status_code == 404

    def test_submit_quiz_with_session_id_but_no_booking_returns_403(
        self,
        student_client,
        simple_quiz,
        active_session,
        student_user,
        test_db,
    ):
        """Submit with session_id but no Booking → 403 'You must book this session'.

        Setup: SessionQuiz links active_session ↔ simple_quiz.
               QuizAttempt exists for student.
               No Booking row exists for student on active_session.

        Expected: 403 (route raises HTTPException before rendering template).
        DB: QuizAttempt.completed_at remains None.
        """
        from app.models.quiz import SessionQuiz, QuizAttempt

        # Link quiz to session
        sq = SessionQuiz(session_id=active_session.id, quiz_id=simple_quiz.id)
        test_db.add(sq)

        # Create an incomplete attempt
        attempt = QuizAttempt(
            user_id=student_user.id,
            quiz_id=simple_quiz.id,
            total_questions=0,
        )
        test_db.add(attempt)
        test_db.commit()
        test_db.refresh(attempt)
        # No Booking → submit should fail with 403

        resp = student_client.post(
            f"/quizzes/{simple_quiz.id}/submit",
            data={
                "attempt_id": str(attempt.id),
                "time_spent": "10.0",
                "session_id": str(active_session.id),  # triggers booking check
            },
        )

        assert resp.status_code == 403

        # DB unchanged — attempt NOT completed
        test_db.expire_all()
        unchanged = test_db.query(QuizAttempt).filter(QuizAttempt.id == attempt.id).first()
        assert unchanged.completed_at is None
