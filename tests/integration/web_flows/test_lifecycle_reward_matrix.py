"""
Tournament Lifecycle + Reward Distribution Matrix Tests

SRL-01  INDIVIDUAL LEAGUE full pipeline:
        IN_PROGRESS → submit H2H results → calculate-rankings
        → COMPLETED transition → distribute-rewards-v2 → REWARDS_DISTRIBUTED
        → TournamentParticipation rows created with xp_awarded, placement

SRL-02  Reward idempotency:
        distribute-rewards-v2 called twice → TournamentParticipation count unchanged

SRL-03  TEAM reward expansion:
        TEAM tournament rankings → distribute-rewards-v2
        → each active TeamMember gets a TournamentParticipation row
        → team_id set on rows

SRL-04  Status guard — rewards require COMPLETED:
        IN_PROGRESS tournament → distribute-rewards-v2 → 400 Bad Request

SRL-05  Status machine guard — CHECK_IN_OPEN mandatory:
        ENROLLMENT_CLOSED → IN_PROGRESS direct transition → 400 Bad Request
        (CHECK_IN_OPEN phase is mandatory since 2026-03-27)

All tests use SAVEPOINT-isolated real DB (test_db) + TestClient (client) fixtures
from tests/integration/conftest.py. Admin Bearer token bypasses instructor-only checks.
"""
import json
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_type import TournamentType
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.session import Session as SessionModel, EventCategory, SessionType
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation
from app.models.license import UserLicense
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.core.security import get_password_hash


# ── Helpers ────────────────────────────────────────────────────────────────────

_PFX = "srl"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _user(db: Session, role=UserRole.STUDENT) -> User:
    u = User(
        email=f"{_PFX}-{_uid()}@lfa-test.com",
        name=f"SRL User {_uid()}",
        password_hash=get_password_hash("pw"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _preset(db: Session) -> GamePreset:
    existing = db.query(GamePreset).filter(GamePreset.code == "srl-default").first()
    if existing:
        return existing
    gp = GamePreset(
        code="srl-default",
        name="SRL Default",
        description="Auto-created for SRL tests",
        is_active=True,
        game_config={"metadata": {"min_players": 0}, "skills_tested": [], "skill_weights": {}},
    )
    db.add(gp)
    db.flush()
    return gp


def _tt(db: Session, code: str, fmt: str = "HEAD_TO_HEAD", min_players: int = 2) -> TournamentType:
    existing = db.query(TournamentType).filter(TournamentType.code == code).first()
    if existing:
        return existing
    tt = TournamentType(
        code=code,
        display_name=f"SRL {code}",
        description="Auto-created for SRL tests",
        format=fmt,
        min_players=min_players,
        max_players=64,
        requires_power_of_two=False,
        session_duration_minutes=60,
        break_between_sessions_minutes=10,
        config={"code": code},
    )
    db.add(tt)
    db.flush()
    return tt


def _tournament(
    db: Session,
    instructor: User,
    tt: TournamentType,
    participant_type: str = "INDIVIDUAL",
    tournament_status: str = "IN_PROGRESS",
) -> Semester:
    """Create a tournament Semester + TournamentConfiguration + GameConfiguration."""
    preset = _preset(db)
    t = Semester(
        name=f"SRL Cup {_uid()}",
        code=f"SRL-{_uid()}",
        master_instructor_id=instructor.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status=tournament_status,
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id,
        participant_type=participant_type,
        max_players=32,
        number_of_rounds=1,
        parallel_fields=1,
        ranking_direction="DESC",
    ))
    db.add(GameConfiguration(
        semester_id=t.id,
        game_preset_id=preset.id,
    ))
    db.flush()
    return t


def _session(db: Session, tournament: Semester) -> SessionModel:
    """Create a minimal MATCH session."""
    sess = SessionModel(
        title=f"SRL Match {_uid()}",
        date_start=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
        semester_id=tournament.id,
        event_category=EventCategory.MATCH,
        session_type=SessionType.on_site,
        is_tournament_game=True,
    )
    db.add(sess)
    db.flush()
    return sess


def _enroll(db: Session, tournament: Semester, user: User) -> SemesterEnrollment:
    lic = UserLicense(
        user_id=user.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        onboarding_completed=True,
        is_active=True,
    )
    db.add(lic)
    db.flush()
    enr = SemesterEnrollment(
        semester_id=tournament.id,
        user_id=user.id,
        user_license_id=lic.id,
        is_active=True,
        request_status=EnrollmentStatus.APPROVED,
    )
    db.add(enr)
    db.flush()
    return enr


def _make_team(db: Session) -> Team:
    captain = _user(db)
    team = Team(
        name=f"SRL Team {_uid()}",
        code=f"ST-{_uid()}",
        captain_user_id=captain.id,
        is_active=True,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=captain.id, role="CAPTAIN", is_active=True))
    db.flush()
    return team


def _enroll_team(db: Session, tournament: Semester, team: Team) -> TournamentTeamEnrollment:
    enr = TournamentTeamEnrollment(
        semester_id=tournament.id,
        team_id=team.id,
        payment_verified=True,
        is_active=True,
    )
    db.add(enr)
    db.flush()
    return enr


# ── SRL Tests ──────────────────────────────────────────────────────────────────

class TestLifecycleRewardMatrix:
    """
    SRL-01..05 — Full tournament lifecycle + reward distribution matrix.
    Proves CI-level guarantee that the pipeline runs end-to-end correctly.
    """

    def test_SRL_01_individual_league_full_lifecycle(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """
        SRL-01: INDIVIDUAL + LEAGUE full lifecycle:
        IN_PROGRESS → H2H results → calculate-rankings → COMPLETED → distribute-rewards-v2
        → REWARDS_DISTRIBUTED + TournamentParticipation rows created.
        """
        # Use existing "league" code — RankingStrategyFactory matches on code
        tt = _tt(test_db, "league", min_players=2)
        t = _tournament(test_db, admin_user, tt)
        p1 = _user(test_db)
        p2 = _user(test_db)
        _enroll(test_db, t, p1)
        _enroll(test_db, t, p2)
        sess = _session(test_db, t)

        hdrs = {"Authorization": f"Bearer {admin_token}"}

        # Step 1: Submit H2H results (p1 wins 3-1)
        resp = client.patch(
            f"/api/v1/sessions/{sess.id}/head-to-head-results",
            json={"results": [{"user_id": p1.id, "score": 3}, {"user_id": p2.id, "score": 1}]},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"H2H results failed: {resp.text[:300]}"
        assert resp.json()["winner_user_id"] == p1.id

        # Step 2: Calculate rankings
        resp = client.post(f"/api/v1/tournaments/{t.id}/calculate-rankings", headers=hdrs)
        assert resp.status_code == 200, f"calculate-rankings failed: {resp.text[:300]}"

        rankings = test_db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == t.id
        ).all()
        assert len(rankings) == 2
        winner = next(r for r in rankings if r.user_id == p1.id)
        assert winner.rank == 1

        # Step 3: Transition IN_PROGRESS → COMPLETED
        resp = client.patch(
            f"/api/v1/tournaments/{t.id}/status",
            json={"new_status": "COMPLETED", "reason": "SRL-01 test"},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"Status → COMPLETED failed: {resp.text[:300]}"

        test_db.expire_all()
        t_refreshed = test_db.query(Semester).filter(Semester.id == t.id).first()
        assert t_refreshed.tournament_status == "COMPLETED"

        # Step 4: Distribute rewards
        resp = client.post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            json={"tournament_id": t.id, "force_redistribution": False},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"distribute-rewards-v2 failed: {resp.text[:400]}"

        test_db.expire_all()

        # Verify: tournament status → REWARDS_DISTRIBUTED
        t_final = test_db.query(Semester).filter(Semester.id == t.id).first()
        assert t_final.tournament_status == "REWARDS_DISTRIBUTED", (
            f"Expected REWARDS_DISTRIBUTED, got {t_final.tournament_status}"
        )

        # Verify: TournamentParticipation rows created for both players
        parts = test_db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == t.id
        ).all()
        assert len(parts) == 2, f"Expected 2 TournamentParticipation rows, got {len(parts)}"

        p1_part = next(p for p in parts if p.user_id == p1.id)
        assert p1_part.placement == 1
        assert p1_part.xp_awarded >= 0

        p2_part = next(p for p in parts if p.user_id == p2.id)
        assert p2_part.placement == 2

    def test_SRL_02_reward_distribution_idempotent(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """
        SRL-02: distribute-rewards-v2 called twice → TournamentParticipation count unchanged.
        Idempotency: second call skips already-distributed rows.
        """
        tt = _tt(test_db, f"srl-idem-{_uid()}", min_players=2)
        t = _tournament(test_db, admin_user, tt, tournament_status="COMPLETED")

        # Insert rankings directly (pipeline already proved in SRL-01)
        p1 = _user(test_db)
        p2 = _user(test_db)
        test_db.add(TournamentRanking(
            tournament_id=t.id,
            user_id=p1.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100,
        ))
        test_db.add(TournamentRanking(
            tournament_id=t.id,
            user_id=p2.id,
            participant_type="INDIVIDUAL",
            rank=2,
            points=50,
        ))
        test_db.flush()

        hdrs = {"Authorization": f"Bearer {admin_token}"}

        # First call
        resp = client.post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            json={"tournament_id": t.id, "force_redistribution": False},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"First distribute-rewards-v2 failed: {resp.text[:300]}"

        test_db.expire_all()
        count_after_first = test_db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == t.id
        ).count()
        assert count_after_first == 2

        # Reset tournament status to COMPLETED for second call
        t_obj = test_db.query(Semester).filter(Semester.id == t.id).first()
        t_obj.tournament_status = "COMPLETED"
        test_db.flush()

        # Second call (no force_redistribution)
        resp = client.post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            json={"tournament_id": t.id, "force_redistribution": False},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"Second distribute-rewards-v2 failed: {resp.text[:300]}"

        test_db.expire_all()
        count_after_second = test_db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == t.id
        ).count()
        assert count_after_second == count_after_first, (
            f"Idempotency broken: count changed from {count_after_first} to {count_after_second}"
        )

    def test_SRL_03_team_reward_expansion(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """
        SRL-03: TEAM tournament → distribute-rewards-v2 expands team ranking
        → one TournamentParticipation per active TeamMember, with team_id set.
        """
        tt = _tt(test_db, f"srl-team-{_uid()}", min_players=2)
        t = _tournament(test_db, admin_user, tt, participant_type="TEAM", tournament_status="COMPLETED")

        # Create team with 2 active members
        team = _make_team(test_db)
        extra_member = _user(test_db)
        test_db.add(TeamMember(
            team_id=team.id, user_id=extra_member.id, role="PLAYER", is_active=True
        ))
        test_db.flush()
        _enroll_team(test_db, t, team)

        # Insert team ranking
        test_db.add(TournamentRanking(
            tournament_id=t.id,
            team_id=team.id,
            participant_type="TEAM",
            rank=1,
            points=100,
        ))
        test_db.flush()

        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            json={"tournament_id": t.id, "force_redistribution": False},
            headers=hdrs,
        )
        assert resp.status_code == 200, f"distribute-rewards-v2 TEAM failed: {resp.text[:400]}"

        test_db.expire_all()

        parts = test_db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == t.id
        ).all()

        # 2 active members → 2 TournamentParticipation rows
        assert len(parts) == 2, f"Expected 2 rows (per active member), got {len(parts)}"
        for part in parts:
            assert part.team_id == team.id, "team_id must be set on TEAM participation rows"
            assert part.user_id is not None
            assert part.placement == 1

    def test_SRL_04_rewards_require_completed_status(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """
        SRL-04: distribute-rewards-v2 on IN_PROGRESS tournament → 400 Bad Request.
        Rewards endpoint enforces COMPLETED prerequisite.
        """
        tt = _tt(test_db, f"srl-guard-{_uid()}", min_players=2)
        t = _tournament(test_db, admin_user, tt, tournament_status="IN_PROGRESS")

        # Insert rankings (so the guard is purely status-based, not rankings-based)
        p1 = _user(test_db)
        test_db.add(TournamentRanking(
            tournament_id=t.id,
            user_id=p1.id,
            participant_type="INDIVIDUAL",
            rank=1,
            points=100,
        ))
        test_db.flush()

        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.post(
            f"/api/v1/tournaments/{t.id}/distribute-rewards-v2",
            json={"tournament_id": t.id, "force_redistribution": False},
            headers=hdrs,
        )
        assert resp.status_code == 400, (
            f"Expected 400 for IN_PROGRESS tournament, got {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        detail = (body.get("error") or body).get("message") or body.get("detail", "")
        assert "COMPLETED" in detail or "completed" in detail.lower(), (
            f"Error message should mention COMPLETED: {detail}"
        )

    def test_SRL_05_enrollment_closed_to_in_progress_rejected(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """
        SRL-05: ENROLLMENT_CLOSED → IN_PROGRESS direct transition now invalid.
        CHECK_IN_OPEN phase is mandatory since 2026-03-27.
        """
        tt = _tt(test_db, f"srl-sm-{_uid()}", min_players=2)
        t = _tournament(
            test_db, admin_user, tt, tournament_status="ENROLLMENT_CLOSED"
        )

        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}/status",
            json={"new_status": "IN_PROGRESS", "reason": "SRL-05 skip check-in"},
            headers=hdrs,
        )
        assert resp.status_code == 400, (
            f"Expected 400 for ENROLLMENT_CLOSED → IN_PROGRESS, got {resp.status_code}: {resp.text[:300]}"
        )
        # Confirm tournament status unchanged
        test_db.expire_all()
        t_obj = test_db.query(Semester).filter(Semester.id == t.id).first()
        assert t_obj.tournament_status == "ENROLLMENT_CLOSED", (
            "Tournament status must remain ENROLLMENT_CLOSED after rejected transition"
        )
