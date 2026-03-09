"""
Integration test: Hybrid session quiz-unlock flow

Positive flow:
  Instructor POSTs /sessions/{id}/unlock-quiz
    → 303 + session.quiz_unlocked=True persisted in DB

Negative flows:
  - Non-instructor (student) tries to unlock            → 303 error=unauthorized
  - Unlock on non-HYBRID (on_site) session              → 303 error=unlock_only_hybrid
  - Unlock on hybrid session not yet started            → 303 error=session_not_started_unlock

DB validation:
  - session.quiz_unlocked transitions False → True on success
  - quiz_unlocked remains False on all error paths
"""

from app.models.session import Session as SessionModel


class TestHybridSessionQuizUnlock:

    def test_unlock_quiz_sets_db_flag_true(
        self,
        instructor_client,
        hybrid_session,
        test_db,
    ):
        """Instructor unlocks quiz → session.quiz_unlocked=True in DB."""
        # Precondition: quiz is not yet unlocked
        assert not hybrid_session.quiz_unlocked

        resp = instructor_client.post(
            f"/sessions/{hybrid_session.id}/unlock-quiz",
            follow_redirects=False,
        )

        assert resp.status_code == 303
        assert "quiz_unlocked" in resp.headers["location"]

        # Verify DB state
        test_db.expire_all()
        session = (
            test_db.query(SessionModel)
            .filter(SessionModel.id == hybrid_session.id)
            .first()
        )
        assert session.quiz_unlocked is True

    def test_non_instructor_cannot_unlock_quiz(
        self,
        student_client,
        hybrid_session,
        test_db,
    ):
        """Student (non-instructor) POSTing unlock → 303 with error=unauthorized."""
        resp = student_client.post(
            f"/sessions/{hybrid_session.id}/unlock-quiz",
            follow_redirects=False,
        )

        assert resp.status_code == 303
        assert "unauthorized" in resp.headers["location"]

        # Verify DB state is unchanged
        test_db.expire_all()
        session = (
            test_db.query(SessionModel)
            .filter(SessionModel.id == hybrid_session.id)
            .first()
        )
        assert not session.quiz_unlocked

    def test_unlock_on_non_hybrid_session_returns_error(
        self,
        instructor_client,
        active_session,
        test_db,
    ):
        """Unlocking quiz on non-HYBRID (on_site) session → 303 error redirect."""
        resp = instructor_client.post(
            f"/sessions/{active_session.id}/unlock-quiz",
            follow_redirects=False,
        )

        assert resp.status_code == 303
        assert "unlock_only_hybrid" in resp.headers["location"]

    def test_unlock_quiz_on_unstarted_session_returns_error(
        self,
        instructor_client,
        unstarted_hybrid_session,
        test_db,
    ):
        """Hybrid session with actual_start_time=None → 303 error=session_not_started_unlock.

        DB must remain unchanged (quiz_unlocked stays False/None).
        """
        resp = instructor_client.post(
            f"/sessions/{unstarted_hybrid_session.id}/unlock-quiz",
            follow_redirects=False,
        )

        assert resp.status_code == 303
        assert "session_not_started_unlock" in resp.headers["location"]

        # DB unchanged — still not unlocked
        test_db.expire_all()
        session = (
            test_db.query(SessionModel)
            .filter(SessionModel.id == unstarted_hybrid_session.id)
            .first()
        )
        assert not session.quiz_unlocked
