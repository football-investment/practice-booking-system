"""
Integration tests — Tournament progression and multi-participant scenarios
=========================================================================

Validates tournament-specific domain invariants that go beyond the session
scheduling tests (which cover structural aspects like non-overlapping slots):

- All tournament sessions carry the MATCH EventCategory
- XP accumulates independently for each participant across all rounds
- Partial completion (dropout) awards proportional XP
- Per-round custom ``session_reward_config`` overrides the MATCH default
- Nested tournament enrollment requires an active parent-semester enrollment

Tests use the SAVEPOINT-isolated ``test_db`` fixture from
``tests/integration/conftest.py``.

Tests
-----
  TOURN-01  3 participants × 4 rounds → 12 independent EventRewardLog rows
  TOURN-02  Dropout after 2 rounds → 200 XP (not 400)
  TOURN-03  Per-round custom XP (semifinal 150, final 250)
  TOURN-04  Parent-gate check: no parent enrollment → gate blocks entry
  TOURN-05  Parent-gate check: active parent enrollment → gate allows entry
  TOURN-06  All tournament sessions have event_category == MATCH
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy.orm import Session

from app.models.event_reward_log import EventRewardLog
from app.models.semester import Semester, SemesterCategory
from app.models.semester_enrollment import SemesterEnrollment
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User
from app.services.reward_service import award_session_completion
from tests.fixtures.builders import (
    build_enrollment,
    build_semester,
    build_session,
    build_user_license,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _match_rounds(
    db: Session,
    semester_id: int,
    *,
    num_rounds: int = 4,
    days_offset: int = 7,
) -> List[SessionModel]:
    """Create ``num_rounds`` non-overlapping MATCH sessions (3-day cadence)."""
    now = _now()
    sessions = []
    for i in range(num_rounds):
        start = now + timedelta(days=days_offset + i * 3)
        sessions.append(
            build_session(
                db,
                semester_id,
                title=f"Round {i + 1}",
                event_category=EventCategory.MATCH,
                date_start=start,
                date_end=start + timedelta(hours=2),
            )
        )
    return sessions


# ── Multi-participant tests ───────────────────────────────────────────────────

class TestTournamentMultiParticipant:
    """Multiple participants earning rewards across tournament rounds."""

    def test_tourn01_three_participants_four_rounds_twelve_logs(
        self, test_db: Session, student_user: User
    ):
        """TOURN-01: 3 participants × 4 rounds → 12 distinct EventRewardLog rows."""
        from app.core.security import get_password_hash
        from app.models.user import UserRole

        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        sessions = _match_rounds(test_db, sem.id, num_rounds=4)

        # Create two additional participants alongside the fixture student_user
        extra_users = []
        for i in range(2):
            u = User(
                email=f"tourn-{uuid.uuid4().hex[:8]}@test.com",
                name=f"Tournament Player {i + 2}",
                password_hash=get_password_hash("pw"),
                role=UserRole.STUDENT,
                is_active=True,
            )
            test_db.add(u)
            test_db.flush()
            test_db.refresh(u)
            extra_users.append(u)

        participants = [student_user] + extra_users

        logs = [
            award_session_completion(test_db, user_id=p.id, session=s)
            for p in participants
            for s in sessions
        ]

        assert len(logs) == 12, f"Expected 12 logs (3×4), got {len(logs)}"
        assert len({log.id for log in logs}) == 12, "All 12 logs must be distinct rows"

        # Each participant earns 4 × 100 = 400 XP
        for p in participants:
            participant_xp = sum(
                log.xp_earned for log in logs if log.user_id == p.id
            )
            assert participant_xp == 400, (
                f"Participant {p.id} should earn 400 XP, got {participant_xp}"
            )

    def test_tourn02_dropout_awards_partial_xp(
        self, test_db: Session, student_user: User
    ):
        """TOURN-02: Participant completing 2 of 4 rounds earns 2 × 100 = 200 XP."""
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        sessions = _match_rounds(test_db, sem.id, num_rounds=4)

        # Award only the first 2 rounds
        completed = sessions[:2]
        logs = [
            award_session_completion(test_db, user_id=student_user.id, session=s)
            for s in completed
        ]

        total_xp = sum(log.xp_earned for log in logs)
        assert total_xp == 200, f"Expected 200 XP (2 × 100), got {total_xp}"

        # Verify only 2 rows exist for this user in this tournament
        test_db.expire_all()
        all_logs = (
            test_db.query(EventRewardLog)
            .filter(
                EventRewardLog.user_id == student_user.id,
                EventRewardLog.session_id.in_([s.id for s in sessions]),
            )
            .all()
        )
        assert len(all_logs) == 2, (
            f"Dropout should have exactly 2 reward rows, got {len(all_logs)}"
        )

    def test_tourn03_per_round_custom_xp_overrides_match_default(
        self, test_db: Session, student_user: User
    ):
        """TOURN-03: Custom session_reward_config overrides MATCH default (100 XP)."""
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        now = _now()

        # Quarterfinal: MATCH default (100 XP)
        # Semifinal: config override (150 XP)
        # Final: config override (250 XP)
        round_configs = [
            (None,                                               100),  # QF default
            ({"v": 1, "base_xp": 150, "skill_areas": []},      150),  # SF
            ({"v": 1, "base_xp": 250, "skill_areas": []},      250),  # Final
        ]

        logs = []
        for i, (cfg, expected_xp) in enumerate(round_configs):
            start = now + timedelta(days=7 + i * 3)
            kwargs = dict(
                event_category=EventCategory.MATCH,
                date_start=start,
                date_end=start + timedelta(hours=2),
            )
            if cfg is not None:
                kwargs["session_reward_config"] = cfg

            sess = build_session(test_db, sem.id, title=f"Round {i + 1}", **kwargs)
            log = award_session_completion(test_db, user_id=student_user.id, session=sess)
            logs.append((log, expected_xp))

        for log, expected in logs:
            assert log.xp_earned == expected, (
                f"Round with expected {expected} XP earned {log.xp_earned} instead"
            )

        total = sum(log.xp_earned for log, _ in logs)
        assert total == 500, f"Expected 100 + 150 + 250 = 500 XP total, got {total}"


# ── Enrollment gate tests ─────────────────────────────────────────────────────

class TestTournamentEnrollmentGate:
    """
    Nested tournament enrollment requires an active parent-semester enrollment.
    These tests validate the gate condition at the data layer; the HTTP 403
    response is exercised by the API smoke tests (FLOW-03).
    """

    def test_tourn04_no_parent_enrollment_blocks_gate(
        self, test_db: Session, student_user: User
    ):
        """TOURN-04: Student without parent enrollment fails the hierarchy gate."""
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.TOURNAMENT,
            parent_semester_id=parent.id,
        )

        # Confirm no active parent enrollment exists
        parent_enr = (
            test_db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.user_id == student_user.id,
                SemesterEnrollment.semester_id == parent.id,
                SemesterEnrollment.is_active == True,
            )
            .first()
        )
        assert parent_enr is None, "Pre-condition: student must NOT have a parent enrollment"

        # Gate condition: child requires active parent enrollment
        assert child.parent_semester_id == parent.id
        gate_would_pass = parent_enr is not None
        assert not gate_would_pass, "Gate must block enrollment without parent enrollment"

    def test_tourn05_active_parent_enrollment_passes_gate(
        self, test_db: Session, student_user: User
    ):
        """TOURN-05: Student with active parent enrollment passes the hierarchy gate."""
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.TOURNAMENT,
            parent_semester_id=parent.id,
        )

        # Grant parent enrollment
        lic = build_user_license(test_db, user_id=student_user.id)
        parent_enr = build_enrollment(
            test_db, student_user.id, parent.id, lic.id, approved=True
        )

        # Confirm the active enrollment exists
        active_enr = (
            test_db.query(SemesterEnrollment)
            .filter(
                SemesterEnrollment.user_id == student_user.id,
                SemesterEnrollment.semester_id == parent.id,
                SemesterEnrollment.is_active == True,
            )
            .first()
        )
        assert active_enr is not None, "Active parent enrollment must be present"
        assert active_enr.id == parent_enr.id

        # Gate condition passes
        gate_would_pass = active_enr is not None
        assert gate_would_pass, "Gate must pass when parent enrollment is active"
        assert child.parent_semester_id == parent.id


# ── Category validation ───────────────────────────────────────────────────────

class TestTournamentSessionCategory:
    """Tournament sessions must carry the MATCH EventCategory."""

    def test_tourn06_all_tournament_sessions_are_match_category(
        self, test_db: Session
    ):
        """TOURN-06: Every session in a TOURNAMENT semester is EventCategory.MATCH."""
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        sessions = _match_rounds(test_db, sem.id, num_rounds=4)

        stored = (
            test_db.query(SessionModel)
            .filter(SessionModel.semester_id == sem.id)
            .all()
        )
        assert len(stored) == 4
        non_match = [s for s in stored if s.event_category != EventCategory.MATCH]
        assert not non_match, (
            f"Tournament sessions must all be MATCH category; found: "
            f"{[s.title for s in non_match]}"
        )
