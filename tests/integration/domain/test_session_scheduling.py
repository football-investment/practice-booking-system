"""
Integration tests — Session scheduling patterns
================================================

Tests realistic session arrangements for academy seasons, tournaments, and camps.
Uses SAVEPOINT-isolated ``test_db`` + ``student_user`` from
``tests/integration/conftest.py``.

Tests
-----
  SCHED-01  Academy season: 5 weekly TRAINING sessions, stored chronologically
  SCHED-02  Tournament: 4 MATCH sessions (round-robin, non-overlapping slots)
  SCHED-03  Camp: multi-day structure (3 days × 2 sessions per day)
  SCHED-04  Mixed semester: TRAINING and MATCH co-exist; XP resolved per category
  SCHED-05  Per-session reward config overrides category default XP
  SCHED-06  Full academy schedule: each session generates a distinct EventRewardLog
  SCHED-07  XP accumulation across academy schedule (5 × 50 = 250)
  SCHED-08  Tournament schedule XP (4 × 100 = 400)
  SCHED-09  Camp: per-day custom XP via session_reward_config (200, 150, 100)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy.orm import Session

from app.models.semester import Semester, SemesterCategory
from app.models.session import Session as SessionModel, EventCategory
from app.models.event_reward_log import EventRewardLog
from app.models.user import User
from app.services.reward_service import award_session_completion
from tests.fixtures.builders import build_semester, build_session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _training_schedule(
    db: Session,
    semester_id: int,
    *,
    num_sessions: int = 5,
    weeks_offset: int = 1,
) -> List[SessionModel]:
    """Create ``num_sessions`` weekly TRAINING sessions."""
    now = _now()
    sessions = []
    for week in range(num_sessions):
        start = now + timedelta(weeks=weeks_offset + week)
        sess = build_session(
            db, semester_id,
            title=f"Training Week {week + 1}",
            event_category=EventCategory.TRAINING,
            date_start=start,
            date_end=start + timedelta(hours=1, minutes=30),
        )
        sessions.append(sess)
    return sessions


def _match_schedule(
    db: Session,
    semester_id: int,
    *,
    num_matches: int = 4,
    days_offset: int = 7,
) -> List[SessionModel]:
    """Create ``num_matches`` MATCH sessions, each 3 days apart."""
    now = _now()
    sessions = []
    for i in range(num_matches):
        start = now + timedelta(days=days_offset + i * 3)
        sess = build_session(
            db, semester_id,
            title=f"Round {i + 1} Match",
            event_category=EventCategory.MATCH,
            date_start=start,
            date_end=start + timedelta(hours=2),
        )
        sessions.append(sess)
    return sessions


# ── SCHED-01 to SCHED-03: Structure tests ─────────────────────────────────────

class TestAcademySeasonSchedule:
    """Academy season with weekly TRAINING sessions."""

    def test_sched01_weekly_training_schedule(self, test_db: Session, student_user: User):
        """SCHED-01: 5 weekly TRAINING sessions stored in chronological order."""
        sem = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        _training_schedule(test_db, sem.id, num_sessions=5)

        stored = (
            test_db.query(SessionModel)
            .filter(SessionModel.semester_id == sem.id)
            .order_by(SessionModel.date_start)
            .all()
        )

        assert len(stored) == 5
        assert all(s.event_category == EventCategory.TRAINING for s in stored)
        for i in range(len(stored) - 1):
            assert stored[i].date_start < stored[i + 1].date_start, (
                f"Session {i} starts after session {i+1}"
            )


class TestTournamentMatchSchedule:
    """Tournament semester with MATCH sessions."""

    def test_sched02_match_session_schedule(self, test_db: Session):
        """SCHED-02: 4 MATCH sessions with non-overlapping time slots."""
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        _match_schedule(test_db, sem.id, num_matches=4)

        stored = (
            test_db.query(SessionModel)
            .filter(SessionModel.semester_id == sem.id)
            .order_by(SessionModel.date_start)
            .all()
        )

        assert len(stored) == 4
        assert all(s.event_category == EventCategory.MATCH for s in stored)
        # Non-overlapping: each match ends before the next begins
        for i in range(len(stored) - 1):
            assert stored[i].date_end <= stored[i + 1].date_start, (
                f"Match {i} overlaps with match {i+1}"
            )


class TestCampSchedule:
    """Camp semester with multi-day sessions."""

    def test_sched03_multiday_camp_schedule(self, test_db: Session):
        """SCHED-03: 3-day camp with 2 sessions per day (6 sessions total)."""
        sem = build_semester(test_db, semester_category=SemesterCategory.CAMP)
        # Anchor to midnight so +9h and +14h slots always stay on the same
        # calendar date regardless of what time the test suite runs.
        base = datetime.combine(date.today() + timedelta(days=7), datetime.min.time())
        for day in range(3):
            for slot in range(2):  # morning (09:00) + afternoon (14:00)
                start = base + timedelta(days=day, hours=9 + slot * 5)
                build_session(
                    test_db, sem.id,
                    title=f"Day {day + 1} Session {slot + 1}",
                    event_category=EventCategory.TRAINING,
                    date_start=start,
                    date_end=start + timedelta(hours=2),
                )

        stored = (
            test_db.query(SessionModel)
            .filter(SessionModel.semester_id == sem.id)
            .order_by(SessionModel.date_start)
            .all()
        )

        assert len(stored) == 6

        # Day grouping: sessions 0+1 share a calendar date, 2+3 share the next, etc.
        assert stored[0].date_start.date() == stored[1].date_start.date(), "Day 1 pair must share date"
        assert stored[1].date_start.date() < stored[2].date_start.date(), "Day 1→Day 2 boundary"
        assert stored[2].date_start.date() == stored[3].date_start.date(), "Day 2 pair must share date"
        assert stored[3].date_start.date() < stored[4].date_start.date(), "Day 2→Day 3 boundary"

        # Within each day: morning before afternoon
        assert stored[0].date_start < stored[1].date_start
        assert stored[2].date_start < stored[3].date_start


# ── SCHED-04 to SCHED-05: Mixed / config overrides ────────────────────────────

class TestMixedSchedule:
    """Mixed session categories and per-session reward configs."""

    def test_sched04_training_and_match_coexist(self, test_db: Session, student_user: User):
        """SCHED-04: TRAINING (50 XP) and MATCH (100 XP) in the same semester."""
        sem = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        now = _now()

        training = build_session(
            test_db, sem.id,
            event_category=EventCategory.TRAINING,
            date_start=now + timedelta(days=7),
            date_end=now + timedelta(days=7, hours=1, minutes=30),
        )
        match = build_session(
            test_db, sem.id,
            event_category=EventCategory.MATCH,
            date_start=now + timedelta(days=14),
            date_end=now + timedelta(days=14, hours=2),
        )

        log_t = award_session_completion(test_db, user_id=student_user.id, session=training)
        log_m = award_session_completion(test_db, user_id=student_user.id, session=match)

        assert log_t.xp_earned == 50,  f"TRAINING XP: expected 50, got {log_t.xp_earned}"
        assert log_m.xp_earned == 100, f"MATCH XP: expected 100, got {log_m.xp_earned}"
        assert log_t.session_id != log_m.session_id

    def test_sched05_per_session_config_overrides_category(self, test_db: Session, student_user: User):
        """SCHED-05: session_reward_config.base_xp overrides event_category default."""
        sem = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        now = _now()

        # MATCH default would be 100 XP, but config raises it to 250
        sess = build_session(
            test_db, sem.id,
            event_category=EventCategory.MATCH,
            session_reward_config={"v": 1, "base_xp": 250, "skill_areas": ["leadership"]},
            date_start=now + timedelta(days=7),
            date_end=now + timedelta(days=7, hours=2),
        )

        log = award_session_completion(test_db, user_id=student_user.id, session=sess)
        assert log.xp_earned == 250, "Config base_xp (250) must override MATCH default (100)"
        # skill_areas must be passed explicitly to award_session_completion; config only governs XP


# ── SCHED-06 to SCHED-09: Full schedule rewards ───────────────────────────────

class TestFullScheduleRewards:
    """Full schedule reward generation and XP accumulation."""

    def test_sched06_all_sessions_generate_distinct_logs(self, test_db: Session, student_user: User):
        """SCHED-06: Each session in the academy schedule gets its own EventRewardLog."""
        sem = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        sessions = _training_schedule(test_db, sem.id, num_sessions=5)

        logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in sessions
        ]

        assert len(logs) == 5
        log_ids = {log.id for log in logs}
        assert len(log_ids) == 5, "Each session must produce a distinct EventRewardLog row"
        assert all(log.user_id == student_user.id for log in logs)

    def test_sched07_xp_accumulates_across_academy_schedule(self, test_db: Session, student_user: User):
        """SCHED-07: 5 TRAINING sessions × 50 XP = 250 XP total."""
        sem = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        sessions = _training_schedule(test_db, sem.id, num_sessions=5)

        logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in sessions
        ]

        total_xp = sum(log.xp_earned for log in logs)
        assert total_xp == 250, f"Expected 250 XP (5 × 50), got {total_xp}"

        # Confirm persisted total matches in-memory total
        test_db.expire_all()
        db_total = sum(
            r.xp_earned for r in test_db.query(EventRewardLog).filter(
                EventRewardLog.user_id == student_user.id,
                EventRewardLog.session_id.in_([s.id for s in sessions]),
            ).all()
        )
        assert db_total == 250

    def test_sched08_tournament_xp_total(self, test_db: Session, student_user: User):
        """SCHED-08: 4 MATCH sessions × 100 XP = 400 XP for a tournament participant."""
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        sessions = _match_schedule(test_db, sem.id, num_matches=4)

        logs = [
            award_session_completion(test_db, user_id=student_user.id, session=sess)
            for sess in sessions
        ]

        assert all(log.xp_earned == 100 for log in logs)
        assert sum(log.xp_earned for log in logs) == 400

    def test_sched09_camp_custom_xp_per_session(self, test_db: Session, student_user: User):
        """SCHED-09: Camp sessions with per-session reward config (200, 150, 100 XP)."""
        sem = build_semester(test_db, semester_category=SemesterCategory.CAMP)
        now = _now()

        configs_and_expected = [
            ({"v": 1, "base_xp": 200, "skill_areas": ["dribbling"]}, 200),
            ({"v": 1, "base_xp": 150, "skill_areas": ["passing"]},   150),
            ({"v": 1, "base_xp": 100, "skill_areas": ["shooting"]},  100),
        ]

        for day, (cfg, expected_xp) in enumerate(configs_and_expected):
            start = now + timedelta(days=7 + day)
            sess = build_session(
                test_db, sem.id,
                event_category=EventCategory.TRAINING,
                session_reward_config=cfg,
                date_start=start,
                date_end=start + timedelta(hours=2),
            )
            log = award_session_completion(
                test_db,
                user_id=student_user.id,
                session=sess,
                skill_areas=cfg["skill_areas"],  # passed explicitly; service doesn't auto-read from config
            )

            assert log.xp_earned == expected_xp, (
                f"Day {day + 1}: expected {expected_xp} XP, got {log.xp_earned}"
            )
            assert log.skill_areas_affected == cfg["skill_areas"]
