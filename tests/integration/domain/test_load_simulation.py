"""
Integration tests — Load simulation under concurrent traffic
=============================================================

Validates system correctness (not raw throughput) when reward and booking
operations run simultaneously across many threads.  These tests complement
the Locust performance baseline (``tests/performance/locustfile.py``) by
verifying that concurrent load produces **correct results** — no duplicates,
no lost writes, no deadlocks.

Architecture note
-----------------
Tests use real committed DB transactions (``SessionLocal()``) because OS
threads require separate DB connections.  Each test manages its own setup and
teardown via the ``_LoadEnv`` context manager.

Tests
-----
  LOAD-01  30 concurrent reward writes (3 sessions × 10 users) → 30 rows, no errors
  LOAD-02  50 threads all award the same (user, session) → exactly 1 row
  LOAD-03  10 concurrent reward writers + 10 concurrent booking-state readers
           → no deadlocks, all data consistent
  LOAD-04  20 concurrent re-awards with varying multipliers → final state is valid
           (1 row, xp between 50 and 200)
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus
from app.models.event_reward_log import EventRewardLog
from app.models.semester import Semester, SemesterCategory
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User, UserRole
from app.services.reward_service import award_session_completion


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class _LoadEnv:
    """
    Context manager that creates committed test data for load tests and
    cleans it up on exit regardless of test outcome.

    Usage::

        with _LoadEnv(n_users=10, n_sessions=3) as env:
            # env.user_ids: list of committed user IDs
            # env.session_ids: list of committed session IDs
            # env.semester_id: int
    """

    def __init__(self, n_users: int = 1, n_sessions: int = 1):
        self._n_users = n_users
        self._n_sessions = n_sessions
        self.user_ids: List[int] = []
        self.session_ids: List[int] = []
        self.semester_id: int = 0

    def __enter__(self) -> "_LoadEnv":
        db = SessionLocal()
        try:
            sem = Semester(
                code=f"LOAD-{uuid.uuid4().hex[:6]}",
                name="Load Test Semester",
                start_date=date.today() - timedelta(days=30),
                end_date=date.today() + timedelta(days=150),
                semester_category=SemesterCategory.ACADEMY_SEASON,
            )
            db.add(sem)
            db.flush()

            sessions = []
            for i in range(self._n_sessions):
                sess = SessionModel(
                    title=f"Load Session {i + 1} {uuid.uuid4().hex[:4]}",
                    semester_id=sem.id,
                    date_start=_now() + timedelta(days=7 + i),
                    date_end=_now() + timedelta(days=7 + i, hours=1),
                    event_category=EventCategory.TRAINING,
                    capacity=100,
                )
                db.add(sess)
                db.flush()
                sessions.append(sess.id)

            users = []
            for _ in range(self._n_users):
                u = User(
                    email=f"load+{uuid.uuid4().hex[:8]}@test.com",
                    name="Load Test User",
                    password_hash=get_password_hash("pw"),
                    role=UserRole.STUDENT,
                    is_active=True,
                )
                db.add(u)
                db.flush()
                users.append(u.id)

            db.commit()
            self.semester_id = sem.id
            self.session_ids = sessions
            self.user_ids = users
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return self

    def __exit__(self, *_) -> None:
        db = SessionLocal()
        try:
            # Delete in FK-safe order; EventRewardLog cascades on session delete
            if self.session_ids:
                db.query(EventRewardLog).filter(
                    EventRewardLog.session_id.in_(self.session_ids)
                ).delete(synchronize_session=False)
                db.query(Booking).filter(
                    Booking.session_id.in_(self.session_ids)
                ).delete(synchronize_session=False)
                db.query(SessionModel).filter(
                    SessionModel.id.in_(self.session_ids)
                ).delete(synchronize_session=False)
            if self.semester_id:
                db.query(Semester).filter(
                    Semester.id == self.semester_id
                ).delete(synchronize_session=False)
            if self.user_ids:
                db.query(User).filter(
                    User.id.in_(self.user_ids)
                ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


# ── Load simulation tests ─────────────────────────────────────────────────────

class TestLoadSimulation:
    """
    Correctness guarantees under concurrent load.

    Each test uses OS threads with separate DB sessions to exercise real
    concurrency — not simulated sequential calls.
    """

    def test_load01_30_concurrent_writers_produce_30_rows(self):
        """LOAD-01: 30 concurrent reward writes (3 sessions × 10 users) → exactly 30 rows."""
        with _LoadEnv(n_users=10, n_sessions=3) as env:
            errors: List[Exception] = []

            def worker(user_id: int, session_id: int) -> None:
                db = SessionLocal()
                try:
                    sess = db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(db, user_id=user_id, session=sess)
                except Exception as e:
                    errors.append(e)
                finally:
                    db.close()

            # Each user awards each session → 10 × 3 = 30 distinct pairs
            threads = [
                threading.Thread(target=worker, args=(uid, sid))
                for uid in env.user_ids
                for sid in env.session_ids
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Thread errors: {errors}"

            verify_db = SessionLocal()
            try:
                total = verify_db.query(EventRewardLog).filter(
                    EventRewardLog.session_id.in_(env.session_ids),
                    EventRewardLog.user_id.in_(env.user_ids),
                ).count()
                assert total == 30, f"Expected 30 reward rows, got {total}"

                # Each (user, session) pair has exactly 1 row
                rows = verify_db.query(
                    EventRewardLog.user_id,
                    EventRewardLog.session_id,
                ).filter(
                    EventRewardLog.session_id.in_(env.session_ids),
                    EventRewardLog.user_id.in_(env.user_ids),
                ).all()
                pairs = [(r.user_id, r.session_id) for r in rows]
                assert len(pairs) == len(set(pairs)), "Duplicate (user, session) pairs detected"
            finally:
                verify_db.close()

    def test_load02_50_concurrent_same_pair_produces_one_row(self):
        """LOAD-02: 50 threads award same (user, session) → exactly 1 row (ON CONFLICT DO UPDATE)."""
        with _LoadEnv(n_users=1, n_sessions=1) as env:
            user_id = env.user_ids[0]
            session_id = env.session_ids[0]
            errors: List[Exception] = []

            def worker() -> None:
                db = SessionLocal()
                try:
                    sess = db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(db, user_id=user_id, session=sess)
                except Exception as e:
                    errors.append(e)
                finally:
                    db.close()

            threads = [threading.Thread(target=worker) for _ in range(50)]
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
                    f"ON CONFLICT DO UPDATE must yield exactly 1 row under 50 concurrent "
                    f"writers, got {count}"
                )
            finally:
                verify_db.close()

    def test_load03_concurrent_readers_and_writers_no_deadlock(self):
        """LOAD-03: 10 reward writers + 10 booking-state readers → no deadlocks, consistent data."""
        with _LoadEnv(n_users=10, n_sessions=1) as env:
            session_id = env.session_ids[0]
            errors: List[Exception] = []
            confirmed_counts: List[int] = []

            def reward_worker(user_id: int) -> None:
                db = SessionLocal()
                try:
                    sess = db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(db, user_id=user_id, session=sess)
                except Exception as e:
                    errors.append(e)
                finally:
                    db.close()

            def reader_worker() -> None:
                """Read confirmed booking count — should never deadlock."""
                from sqlalchemy import func
                db = SessionLocal()
                try:
                    count = (
                        db.query(func.count(Booking.id))
                        .filter(
                            Booking.session_id == session_id,
                            Booking.status == BookingStatus.CONFIRMED,
                        )
                        .scalar()
                        or 0
                    )
                    confirmed_counts.append(count)
                except Exception as e:
                    errors.append(e)
                finally:
                    db.close()

            writers = [
                threading.Thread(target=reward_worker, args=(uid,))
                for uid in env.user_ids
            ]
            readers = [threading.Thread(target=reader_worker) for _ in range(10)]

            all_threads = writers + readers
            for t in all_threads:
                t.start()
            for t in all_threads:
                t.join()

            assert not errors, f"Thread errors (deadlock or exception): {errors}"

            # All reward rows were written
            verify_db = SessionLocal()
            try:
                reward_count = verify_db.query(EventRewardLog).filter(
                    EventRewardLog.session_id == session_id,
                    EventRewardLog.user_id.in_(env.user_ids),
                ).count()
                assert reward_count == 10, f"Expected 10 reward rows, got {reward_count}"

                # All readers succeeded and returned a non-negative count
                assert len(confirmed_counts) == 10, (
                    f"Expected 10 reader results, got {len(confirmed_counts)}"
                )
                assert all(c >= 0 for c in confirmed_counts), (
                    f"Reader returned invalid count: {confirmed_counts}"
                )
            finally:
                verify_db.close()

    def test_load04_20_concurrent_renames_converge_to_valid_state(self):
        """LOAD-04: 20 threads re-award same pair with varying multipliers → 1 row, valid XP."""
        # Each thread picks multiplier = 1.0 + thread_index * 0.1
        # Expected XP range: int(50 * 1.0) = 50 … int(50 * 2.9) = 145
        with _LoadEnv(n_users=1, n_sessions=1) as env:
            user_id = env.user_ids[0]
            session_id = env.session_ids[0]
            errors: List[Exception] = []

            def worker(idx: int) -> None:
                multiplier = round(1.0 + idx * 0.1, 1)
                db = SessionLocal()
                try:
                    sess = db.query(SessionModel).filter(
                        SessionModel.id == session_id
                    ).one()
                    award_session_completion(
                        db, user_id=user_id, session=sess, multiplier=multiplier
                    )
                except Exception as e:
                    errors.append(e)
                finally:
                    db.close()

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
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
                    f"Expected exactly 1 row after 20 concurrent re-awards, got {len(rows)}"
                )
                row = rows[0]
                # TRAINING base = 50; any multiplier between 1.0 and 2.9 is valid
                min_xp, max_xp = int(50 * 1.0), int(50 * 2.9)
                assert min_xp <= row.xp_earned <= max_xp, (
                    f"XP {row.xp_earned} outside valid range [{min_xp}, {max_xp}]"
                )
                assert 1.0 <= row.multiplier_applied <= 2.9, (
                    f"multiplier_applied {row.multiplier_applied} outside valid range"
                )
            finally:
                verify_db.close()
