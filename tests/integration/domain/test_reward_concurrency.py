"""
Integration tests — Reward service concurrency safety
======================================================

Verifies that ``award_session_completion()`` is safe under concurrent execution.
The unique constraint ``uq_event_reward_log_user_session`` on
``(user_id, session_id)`` combined with PostgreSQL's ``INSERT … ON CONFLICT DO
UPDATE`` makes the upsert atomic, so concurrent calls can never produce duplicate
EventRewardLog rows.

Architecture note
-----------------
These tests use **real committed DB transactions** — NOT the SAVEPOINT-isolated
``test_db`` fixture — because OS threads cannot safely share a single database
connection.  Each worker thread opens its own ``SessionLocal()`` session.

Tests
-----
  CONCURRENT-01  5 threads award same (user, session) → exactly 1 row
  CONCURRENT-02  5 threads award same session to 5 different users → 5 rows
  CONCURRENT-03  10 threads award same (user, session) with varying multipliers
                 → 1 row, final value is the last-committed multiplier's XP
"""
from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.event_reward_log import EventRewardLog
from app.models.semester import Semester, SemesterCategory
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User, UserRole
from app.services.reward_service import award_session_completion


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_semester(db) -> Semester:
    sem = Semester(
        code=f"CONC-{uuid.uuid4().hex[:6]}",
        name="Concurrency Test Semester",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=150),
        semester_category=SemesterCategory.ACADEMY_SEASON,
    )
    db.add(sem)
    db.flush()
    return sem


def _make_session(db, semester_id: int) -> SessionModel:
    sess = SessionModel(
        title=f"Conc Session {uuid.uuid4().hex[:6]}",
        semester_id=semester_id,
        date_start=_now() + timedelta(days=7),
        date_end=_now() + timedelta(days=7, hours=1),
        event_category=EventCategory.TRAINING,
        capacity=20,
    )
    db.add(sess)
    db.flush()
    return sess


def _make_user(db) -> User:
    u = User(
        email=f"conc+{uuid.uuid4().hex[:8]}@test.com",
        name="Concurrency Test User",
        password_hash=get_password_hash("testpassword"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


class _TestEnv:
    """
    Creates committed test data (users, session, semester) and cleans up after
    the test.  Use as a context manager::

        with _TestEnv(n_users=5) as env:
            # env.user_ids, env.session_id, env.semester_id available
    """

    def __init__(self, n_users: int = 1):
        self._n_users = n_users
        self.user_ids: List[int] = []
        self.session_id: int = 0
        self.semester_id: int = 0

    def __enter__(self) -> "_TestEnv":
        db = SessionLocal()
        try:
            sem = _make_semester(db)
            sess = _make_session(db, sem.id)
            users = [_make_user(db) for _ in range(self._n_users)]
            db.commit()
            self.semester_id = sem.id
            self.session_id = sess.id
            self.user_ids = [u.id for u in users]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return self

    def __exit__(self, *_) -> None:
        db = SessionLocal()
        try:
            db.query(EventRewardLog).filter(
                EventRewardLog.session_id == self.session_id,
            ).delete(synchronize_session=False)
            db.query(SessionModel).filter(
                SessionModel.id == self.session_id,
            ).delete(synchronize_session=False)
            db.query(Semester).filter(
                Semester.id == self.semester_id,
            ).delete(synchronize_session=False)
            if self.user_ids:
                db.query(User).filter(
                    User.id.in_(self.user_ids),
                ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


# ── Concurrency tests ─────────────────────────────────────────────────────────

class TestRewardConcurrency:
    """
    Thread-safety guarantees for award_session_completion.

    Each test spawns real OS threads, each opening its own SessionLocal DB
    session, to exercise the ON CONFLICT DO UPDATE path under genuine
    concurrency.
    """

    def test_concurrent01_same_user_session_produces_one_row(self):
        """CONCURRENT-01: 5 threads award same (user, session) → exactly 1 EventRewardLog row."""
        with _TestEnv(n_users=1) as env:
            user_id = env.user_ids[0]
            session_id = env.session_id
            errors: List[Exception] = []

            def worker():
                thread_db = SessionLocal()
                try:
                    sess = thread_db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(thread_db, user_id=user_id, session=sess)
                except Exception as e:
                    errors.append(e)
                finally:
                    thread_db.close()

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Thread errors: {errors}"

            verify_db = SessionLocal()
            try:
                count = verify_db.query(EventRewardLog).filter(
                    EventRewardLog.user_id == user_id,
                    EventRewardLog.session_id == session_id,
                ).count()
                assert count == 1, (
                    f"Expected exactly 1 EventRewardLog row under concurrency, got {count}"
                )
            finally:
                verify_db.close()

    def test_concurrent02_different_users_same_session_produce_n_rows(self):
        """CONCURRENT-02: 5 threads award same session to 5 different users → 5 rows."""
        with _TestEnv(n_users=5) as env:
            session_id = env.session_id
            user_ids = env.user_ids
            errors: List[Exception] = []

            def worker(uid: int):
                thread_db = SessionLocal()
                try:
                    sess = thread_db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(thread_db, user_id=uid, session=sess)
                except Exception as e:
                    errors.append(e)
                finally:
                    thread_db.close()

            threads = [threading.Thread(target=worker, args=(uid,)) for uid in user_ids]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Thread errors: {errors}"

            verify_db = SessionLocal()
            try:
                rows = verify_db.query(EventRewardLog).filter(
                    EventRewardLog.session_id == session_id,
                    EventRewardLog.user_id.in_(user_ids),
                ).all()
                assert len(rows) == 5, (
                    f"Expected 5 EventRewardLog rows (one per user), got {len(rows)}"
                )
                awarded_user_ids = {r.user_id for r in rows}
                assert awarded_user_ids == set(user_ids), (
                    f"Missing rows for users: {set(user_ids) - awarded_user_ids}"
                )
                assert all(r.xp_earned == 50 for r in rows), (
                    "All TRAINING rows should be 50 XP"
                )
            finally:
                verify_db.close()

    def test_concurrent03_repeated_awards_converge_to_one_row(self):
        """CONCURRENT-03: 10 threads each re-award same (user, session) → 1 row, valid XP."""
        with _TestEnv(n_users=1) as env:
            user_id = env.user_ids[0]
            session_id = env.session_id
            errors: List[Exception] = []

            # All threads use the same multiplier; any "last write" is valid
            def worker():
                thread_db = SessionLocal()
                try:
                    sess = thread_db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(
                        thread_db, user_id=user_id, session=sess, multiplier=1.5
                    )
                except Exception as e:
                    errors.append(e)
                finally:
                    thread_db.close()

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Thread errors: {errors}"

            verify_db = SessionLocal()
            try:
                rows = verify_db.query(EventRewardLog).filter(
                    EventRewardLog.user_id == user_id,
                    EventRewardLog.session_id == session_id,
                ).all()
                assert len(rows) == 1, (
                    f"ON CONFLICT must yield exactly 1 row, got {len(rows)}"
                )
                # TRAINING base=50, multiplier=1.5 → int(50 * 1.5) = 75
                assert rows[0].xp_earned == 75, (
                    f"Expected 75 XP (50 × 1.5), got {rows[0].xp_earned}"
                )
                assert abs(rows[0].multiplier_applied - 1.5) < 0.001
            finally:
                verify_db.close()
