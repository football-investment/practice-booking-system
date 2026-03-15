"""
Integration tests — Reward service scale and isolation
=======================================================

Verifies that ``award_session_completion`` produces correct results across
high-volume and multi-user scenarios.  All tests use the SAVEPOINT-isolated
``test_db`` fixture from ``tests/integration/conftest.py`` so that every test
starts clean and rolls back automatically.

Tests
-----
  SCALE-01  20 sessions × 1 user → 20 distinct EventRewardLog rows
  SCALE-02  1 session × 10 users → 10 distinct rows (user isolation)
  SCALE-03  Idempotency under 10 sequential re-awards → 1 row, last value wins
  SCALE-04  Mixed categories at volume: 10 TRAINING + 10 MATCH → correct totals
  SCALE-05  Multiplier applied consistently across 10 MATCH sessions (1.5×)
"""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.event_reward_log import EventRewardLog
from app.models.session import EventCategory
from app.models.user import User, UserRole
from app.services.reward_service import award_session_completion
from tests.fixtures.builders import build_semester, build_session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_student(test_db: Session) -> User:
    """Create a fresh STUDENT user within the current SAVEPOINT transaction."""
    user = User(
        email=f"scale+{uuid.uuid4().hex[:8]}@test.com",
        name="Scale Test Student",
        password_hash=get_password_hash("password"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db.add(user)
    test_db.flush()
    test_db.refresh(user)
    return user


def _reward_count(test_db: Session, user_id: int, session_ids: List[int]) -> int:
    return (
        test_db.query(EventRewardLog)
        .filter(
            EventRewardLog.user_id == user_id,
            EventRewardLog.session_id.in_(session_ids),
        )
        .count()
    )


# ── Scale tests ───────────────────────────────────────────────────────────────

class TestRewardScale:
    """Scale and isolation guarantees for award_session_completion."""

    def test_scale01_many_sessions_one_user(self, test_db: Session, student_user: User):
        """SCALE-01: 20 TRAINING sessions → 20 distinct EventRewardLog rows, each 50 XP."""
        sem = build_semester(test_db)
        sessions = [
            build_session(test_db, sem.id, event_category=EventCategory.TRAINING)
            for _ in range(20)
        ]

        logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in sessions
        ]

        assert len(logs) == 20
        assert len({log.id for log in logs}) == 20, "Each session must have a distinct row"
        assert all(log.xp_earned == 50 for log in logs)
        assert all(log.user_id == student_user.id for log in logs)

        # Verify all 20 rows are persisted
        test_db.expire_all()
        count = _reward_count(test_db, student_user.id, [s.id for s in sessions])
        assert count == 20, f"Expected 20 EventRewardLog rows, found {count}"

    def test_scale02_one_session_many_users(self, test_db: Session):
        """SCALE-02: 10 users completing the same MATCH session → 10 distinct rows."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, event_category=EventCategory.MATCH)

        users = [_new_student(test_db) for _ in range(10)]
        logs = [
            award_session_completion(test_db, user_id=u.id, session=sess)
            for u in users
        ]

        assert len(logs) == 10
        assert len({log.id for log in logs}) == 10, "Each user must have their own row"
        assert len({log.user_id for log in logs}) == 10, "All user IDs must be distinct"
        assert all(log.xp_earned == 100 for log in logs)

        # Confirm count in DB
        test_db.expire_all()
        total = (
            test_db.query(EventRewardLog)
            .filter(EventRewardLog.session_id == sess.id)
            .count()
        )
        assert total == 10, f"Expected 10 EventRewardLog rows for the session, found {total}"

    def test_scale03_idempotency_under_repeated_awards(self, test_db: Session, student_user: User):
        """SCALE-03: 10 sequential award calls for same (user, session) → 1 row, last value wins."""
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, event_category=EventCategory.TRAINING)

        last_log = None
        for i in range(10):
            multiplier = round(1.0 + i * 0.1, 1)   # 1.0, 1.1, …, 1.9
            last_log = award_session_completion(
                test_db, user_id=student_user.id, session=sess, multiplier=multiplier
            )

        # Last call: multiplier=1.9, TRAINING base=50 → int(50 * 1.9) = 95
        assert last_log is not None
        expected_xp = int(50 * 1.9)
        assert last_log.xp_earned == expected_xp, (
            f"Expected {expected_xp} XP (50 × 1.9), got {last_log.xp_earned}"
        )
        assert abs(last_log.multiplier_applied - 1.9) < 0.001

        # Exactly 1 row in DB
        test_db.expire_all()
        count = _reward_count(test_db, student_user.id, [sess.id])
        assert count == 1, f"Expected exactly 1 EventRewardLog row, found {count}"

    def test_scale04_mixed_categories_xp_math(self, test_db: Session, student_user: User):
        """SCALE-04: 10 TRAINING + 10 MATCH → 10×50 + 10×100 = 1500 XP total."""
        sem = build_semester(test_db)
        training_sessions = [
            build_session(test_db, sem.id, event_category=EventCategory.TRAINING)
            for _ in range(10)
        ]
        match_sessions = [
            build_session(test_db, sem.id, event_category=EventCategory.MATCH)
            for _ in range(10)
        ]

        training_logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in training_sessions
        ]
        match_logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in match_sessions
        ]

        training_total = sum(log.xp_earned for log in training_logs)
        match_total    = sum(log.xp_earned for log in match_logs)

        assert training_total == 500,  f"Expected 500 XP from TRAINING (10×50), got {training_total}"
        assert match_total    == 1000, f"Expected 1000 XP from MATCH (10×100), got {match_total}"
        assert training_total + match_total == 1500

    def test_scale05_multiplier_at_scale(self, test_db: Session, student_user: User):
        """SCALE-05: 10 MATCH sessions × 1.5 multiplier → 150 XP each, 1500 XP total."""
        sem = build_semester(test_db)
        sessions = [
            build_session(test_db, sem.id, event_category=EventCategory.MATCH)
            for _ in range(10)
        ]

        logs = [
            award_session_completion(
                test_db, user_id=student_user.id, session=sess, multiplier=1.5
            )
            for sess in sessions
        ]

        wrong = [log.xp_earned for log in logs if log.xp_earned != 150]
        assert not wrong, f"Some sessions have wrong XP: {wrong} (expected 150 each)"
        assert sum(log.xp_earned for log in logs) == 1500
        assert all(log.multiplier_applied == 1.5 for log in logs)
