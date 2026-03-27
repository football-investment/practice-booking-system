"""
Session Generation — TEAM × tournament_type matrix tests

SGM-01  TEAM + LEAGUE    → sessions generated, participant_team_ids set
SGM-02  TEAM + KNOCKOUT  → sessions generated, participant_team_ids set (round 1)
SGM-03  TEAM + SWISS     → sessions generated, participant_team_ids set
SGM-04  TEAM + GROUP_KNOCKOUT → sessions generated, participant_team_ids set
SGM-05  INDIVIDUAL + LEAGUE → sessions generated, participant_user_ids set (regression guard)
SGM-06  TEAM + LEAGUE, 0 teams enrolled → generation fails with "teams" in error, not "players"

Every test uses TournamentSessionGenerator directly (no HTTP) with a real DB session.
"""
import uuid
import pytest
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_type import TournamentType
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense
from app.services.tournament_session_generator import TournamentSessionGenerator
from app.core.security import get_password_hash


# ── SAVEPOINT-isolated DB fixture ─────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    from app.database import engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import event

    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    db.begin_nested()  # SAVEPOINT

    @event.listens_for(db, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield db
    db.rollback()
    db.close()


# ── Factories ──────────────────────────────────────────────────────────────────

_PFX = "sgm"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _user(db: Session, role=UserRole.STUDENT) -> User:
    u = User(
        email=f"{_PFX}-{_uid()}@lfa-test.com",
        name=f"SGM User {_uid()}",
        password_hash=get_password_hash("pw"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _instructor(db: Session) -> User:
    return _user(db, role=UserRole.INSTRUCTOR)


def _tournament_type(db: Session, code: str, tt_format: str = "HEAD_TO_HEAD",
                     min_players: int = 2) -> TournamentType:
    existing = db.query(TournamentType).filter(TournamentType.code == code).first()
    if existing:
        return existing
    tt = TournamentType(
        code=code,
        display_name=f"SGM {code}",
        description="Auto-created for SGM tests",
        format=tt_format,
        min_players=min_players,
        max_players=64,
        requires_power_of_two=(code == "knockout"),
        session_duration_minutes=60,
        break_between_sessions_minutes=10,
        config={"code": code},
    )
    db.add(tt)
    db.flush()
    return tt


def _preset(db: Session) -> GamePreset:
    existing = db.query(GamePreset).filter(GamePreset.code == "sgm-default").first()
    if existing:
        return existing
    gp = GamePreset(
        code="sgm-default",
        name="SGM Default",
        description="Auto-created for SGM tests",
        is_active=True,
        game_config={"metadata": {"min_players": 0}, "skills_tested": [], "skill_weights": {}},
    )
    db.add(gp)
    db.flush()
    return gp


def _tournament(
    db: Session,
    tt: TournamentType,
    participant_type: str = "INDIVIDUAL",
    instructor: User = None,
) -> Semester:
    if instructor is None:
        instructor = _instructor(db)
    preset = _preset(db)

    t = Semester(
        name=f"SGM Cup {_uid()}",
        code=f"SGM-{_uid()}",
        master_instructor_id=instructor.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="IN_PROGRESS",
    )
    db.add(t)
    db.flush()

    cfg = TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id,
        participant_type=participant_type,
        max_players=32,
        number_of_rounds=1,
        parallel_fields=1,
    )
    db.add(cfg)

    game_cfg = GameConfiguration(
        semester_id=t.id,
        game_preset_id=preset.id,
    )
    db.add(game_cfg)
    db.flush()
    return t


def _make_team(db: Session, tournament: Semester) -> Team:
    captain = _user(db)
    team = Team(
        name=f"Team {_uid()}",
        code=f"T-{_uid()}",
        captain_user_id=captain.id,
        is_active=True,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=captain.id, role="CAPTAIN", is_active=True))
    db.add(TournamentTeamEnrollment(
        semester_id=tournament.id,
        team_id=team.id,
        payment_verified=True,
        is_active=True,
    ))
    db.flush()
    return team


def _enroll_player(db: Session, tournament: Semester) -> User:
    u = _user(db)
    lic = UserLicense(
        user_id=u.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        onboarding_completed=True,
        is_active=True,
    )
    db.add(lic)
    db.flush()
    db.add(SemesterEnrollment(
        semester_id=tournament.id,
        user_id=u.id,
        user_license_id=lic.id,
        is_active=True,
        request_status=EnrollmentStatus.APPROVED,
    ))
    db.flush()
    return u


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSessionGenTeamMatrix:
    """
    Parametrized cross-product: participant_type × tournament_type_code.
    All TEAM + HEAD_TO_HEAD combinations must correctly use TournamentTeamEnrollment.
    """

    def _run_gen(self, db: Session, tournament: Semester) -> tuple:
        """Run TournamentSessionGenerator and return (success, msg, sessions)."""
        gen = TournamentSessionGenerator(db)
        result = gen.generate_sessions(
            tournament_id=tournament.id,
            parallel_fields=1,
            session_duration_minutes=60,
            break_minutes=10,
            number_of_rounds=1,
        )
        db.rollback()  # don't persist generated sessions between tests
        return result

    # ── SGM-01: TEAM + LEAGUE ────────────────────────────────────────────────
    def test_SGM_01_team_league_generates_sessions(self, test_db: Session):
        """TEAM LEAGUE with 2 enrolled teams → sessions with participant_team_ids."""
        tt = _tournament_type(test_db, "league", min_players=2)
        t = _tournament(test_db, tt, participant_type="TEAM")
        _make_team(test_db, t)
        _make_team(test_db, t)

        success, msg, sessions = self._run_gen(test_db, t)

        assert success, f"Expected success, got: {msg}"
        assert len(sessions) >= 1, "Expected at least 1 session"
        # Round 1 matches must have participant_team_ids, not participant_user_ids
        first_match = sessions[0]
        team_ids_field = first_match.get("participant_team_ids")
        user_ids_field = first_match.get("participant_user_ids")
        assert team_ids_field, f"Expected participant_team_ids, got: {first_match}"
        assert not user_ids_field, f"participant_user_ids should be None for TEAM, got: {user_ids_field}"

    # ── SGM-02: TEAM + KNOCKOUT ──────────────────────────────────────────────
    def test_SGM_02_team_knockout_generates_sessions(self, test_db: Session):
        """TEAM KNOCKOUT with 4 enrolled teams → sessions with participant_team_ids in R1."""
        tt = _tournament_type(test_db, "knockout", min_players=4)
        t = _tournament(test_db, tt, participant_type="TEAM")
        for _ in range(4):
            _make_team(test_db, t)

        success, msg, sessions = self._run_gen(test_db, t)

        assert success, f"Expected success, got: {msg}"
        assert len(sessions) >= 1
        round1_sessions = [s for s in sessions if s.get("tournament_round") == 1]
        for s in round1_sessions:
            assert s.get("participant_team_ids"), \
                f"R1 session missing participant_team_ids: {s}"

    # ── SGM-03: TEAM + SWISS ─────────────────────────────────────────────────
    def test_SGM_03_team_swiss_generates_sessions(self, test_db: Session):
        """TEAM SWISS with 4 enrolled teams → sessions with participant_team_ids."""
        tt = _tournament_type(test_db, "swiss", min_players=4)
        t = _tournament(test_db, tt, participant_type="TEAM")
        for _ in range(4):
            _make_team(test_db, t)

        success, msg, sessions = self._run_gen(test_db, t)

        assert success, f"Expected success, got: {msg}"
        assert len(sessions) >= 1
        h2h_sessions = [s for s in sessions if s.get("participant_team_ids")]
        assert h2h_sessions, "Expected sessions with participant_team_ids"

    # ── SGM-04: TEAM + GROUP_KNOCKOUT ────────────────────────────────────────
    def test_SGM_04_team_group_knockout_generates_sessions(self, test_db: Session):
        """TEAM GROUP_KNOCKOUT with 8 enrolled teams → group stage sessions."""
        tt = _tournament_type(test_db, "group_knockout", min_players=8)
        t = _tournament(test_db, tt, participant_type="TEAM")
        for _ in range(8):
            _make_team(test_db, t)

        success, msg, sessions = self._run_gen(test_db, t)

        assert success, f"Expected success, got: {msg}"
        assert len(sessions) >= 1

    # ── SGM-05: INDIVIDUAL + LEAGUE (regression guard) ──────────────────────
    def test_SGM_05_individual_league_unchanged(self, test_db: Session):
        """INDIVIDUAL LEAGUE still uses participant_user_ids (regression guard)."""
        tt = _tournament_type(test_db, "league", min_players=2)
        t = _tournament(test_db, tt, participant_type="INDIVIDUAL")
        _enroll_player(test_db, t)
        _enroll_player(test_db, t)

        success, msg, sessions = self._run_gen(test_db, t)

        assert success, f"Expected success, got: {msg}"
        assert len(sessions) >= 1
        first_match = sessions[0]
        user_ids_field = first_match.get("participant_user_ids")
        team_ids_field = first_match.get("participant_team_ids")
        assert user_ids_field, f"Expected participant_user_ids for INDIVIDUAL, got: {first_match}"
        assert not team_ids_field, f"participant_team_ids should be None for INDIVIDUAL"

    # ── SGM-06: TEAM + LEAGUE, no teams enrolled → error uses "teams" ────────
    def test_SGM_06_team_no_teams_enrolled_error_says_teams(self, test_db: Session):
        """TEAM LEAGUE with 0 teams → error message says 'teams', not 'players'."""
        tt = _tournament_type(test_db, "league", min_players=2)
        t = _tournament(test_db, tt, participant_type="TEAM")
        # No teams enrolled

        success, msg, sessions = self._run_gen(test_db, t)

        assert not success, "Expected failure with 0 teams"
        assert "teams" in msg.lower(), \
            f"Error should mention 'teams', not 'players'. Got: {msg!r}"
        assert "players" not in msg.lower(), \
            f"Error must NOT say 'players' for a TEAM tournament. Got: {msg!r}"
