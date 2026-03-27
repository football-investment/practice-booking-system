"""
Sport Director Enrollment Integration Tests — SD-01 through SD-07

Proves the Sport Director team enrollment flow end-to-end:

  SD-01  GET /sport-director/tournaments → only location-scoped tournaments shown
  SD-02  GET /sport-director/tournaments → tournament at different location NOT shown
  SD-03  GET /sport-director/tournaments/{id}/teams → enrolled + eligible teams shown
  SD-04  POST …/teams/{team_id}/enroll → TournamentTeamEnrollment(payment_verified=True)
  SD-05  POST …/teams/{team_id}/enroll wrong location → 303 with error
  SD-06  POST …/teams/{team_id}/remove → is_active=False
  SD-07  POST …/teams/{team_id}/remove when IN_PROGRESS → 303 with error
"""
import uuid
import pytest
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import (
    get_current_user_web,
    get_current_user,
    get_current_active_user,
    get_current_sport_director_user_web,
)
from app.models.campus import Campus
from app.models.instructor_assignment import SportDirectorAssignment
from app.models.location import Location, LocationType
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.tournament_enums import TeamMemberRole
from app.models.tournament_configuration import TournamentConfiguration
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from tests.factories.game_factory import TournamentFactory


# ── SAVEPOINT-isolated DB fixture ──────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSession()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, txn):
        if txn.nested and not txn._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _make_user(db: Session, role: UserRole = UserRole.SPORT_DIRECTOR) -> User:
    u = User(
        email=f"sd-test+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"SD User {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=role,
        is_active=True,
        onboarding_completed=True,
        credit_balance=0,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_location(db: Session) -> Location:
    loc = Location(
        name=f"SD Location {uuid.uuid4().hex[:4]}",
        city=f"SD City {uuid.uuid4().hex[:6]}",
        country="HU",
        location_type=LocationType.CENTER,
    )
    db.add(loc)
    db.flush()
    return loc


def _make_campus(db: Session, location: Location) -> Campus:
    c = Campus(
        location_id=location.id,
        name=f"SD Campus {uuid.uuid4().hex[:4]}",
        is_active=True,
    )
    db.add(c)
    db.flush()
    return c


def _make_sd_assignment(db: Session, user: User, location: Location) -> SportDirectorAssignment:
    sda = SportDirectorAssignment(
        user_id=user.id,
        location_id=location.id,
        is_active=True,
    )
    db.add(sda)
    db.flush()
    return sda


def _make_tournament(
    db: Session,
    *,
    campus: Campus | None = None,
    status: str = "ENROLLMENT_OPEN",
    participant_type: str = "TEAM",
) -> Semester:
    tt = TournamentFactory.ensure_tournament_type(db, code=f"tt-sd-{uuid.uuid4().hex[:6]}")
    t = Semester(
        code=f"SD-TOURN-{uuid.uuid4().hex[:8].upper()}",
        name=f"SD Tournament {uuid.uuid4().hex[:4]}",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        tournament_status=status,
        age_group="YOUTH",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 8),
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
        campus_id=campus.id if campus else None,
    )
    db.add(t)
    db.flush()
    cfg = TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id,
        participant_type=participant_type,
        max_players=32,
        parallel_fields=1,
        sessions_generated=False,
        team_enrollment_cost=0,
    )
    db.add(cfg)
    db.flush()
    return t


def _make_team(db: Session, captain: User) -> Team:
    team = Team(
        name=f"Team {uuid.uuid4().hex[:6]}",
        code=f"SD-{uuid.uuid4().hex[:8].upper()}",
        captain_user_id=captain.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(
        team_id=team.id,
        user_id=captain.id,
        role=TeamMemberRole.CAPTAIN.value,
        is_active=True,
    ))
    db.flush()
    return team


def _make_client(db: Session, user: User) -> TestClient:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_web] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_sport_director_user_web] = lambda: user
    return TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"})


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSportDirectorEnrollment:

    def test_sd_01_tournament_list_shows_location_scoped(self, test_db: Session):
        """SD-01: GET /sport-director/tournaments → only tournaments at SD's location shown."""
        sd = _make_user(test_db)
        loc = _make_location(test_db)
        campus = _make_campus(test_db, loc)
        _make_sd_assignment(test_db, sd, loc)
        tournament = _make_tournament(test_db, campus=campus)
        client = _make_client(test_db, sd)

        try:
            resp = client.get("/sport-director/tournaments")
            assert resp.status_code == 200
            assert tournament.name in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_sd_02_tournament_list_excludes_other_locations(self, test_db: Session):
        """SD-02: Tournament at a different location is NOT shown to this SD."""
        sd = _make_user(test_db)
        my_loc = _make_location(test_db)
        my_campus = _make_campus(test_db, my_loc)
        other_loc = _make_location(test_db)
        other_campus = _make_campus(test_db, other_loc)
        _make_sd_assignment(test_db, sd, my_loc)

        # Tournament at SD's location (should appear)
        my_tournament = _make_tournament(test_db, campus=my_campus)
        # Tournament at another location (should NOT appear)
        other_tournament = _make_tournament(test_db, campus=other_campus)

        client = _make_client(test_db, sd)

        try:
            resp = client.get("/sport-director/tournaments")
            assert resp.status_code == 200
            assert my_tournament.name in resp.text
            assert other_tournament.name not in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_sd_03_tournament_teams_page_shows_enrolled_and_eligible(self, test_db: Session):
        """SD-03: GET .../teams shows enrolled teams and eligible teams."""
        sd = _make_user(test_db)
        captain = _make_user(test_db, role=UserRole.STUDENT)
        loc = _make_location(test_db)
        campus = _make_campus(test_db, loc)
        _make_sd_assignment(test_db, sd, loc)
        tournament = _make_tournament(test_db, campus=campus)
        enrolled_team = _make_team(test_db, captain)
        eligible_team = _make_team(test_db, captain)

        # Enroll one team already
        test_db.add(TournamentTeamEnrollment(
            semester_id=tournament.id,
            team_id=enrolled_team.id,
            is_active=True,
            payment_verified=True,
        ))
        test_db.flush()

        client = _make_client(test_db, sd)

        try:
            resp = client.get(f"/sport-director/tournaments/{tournament.id}/teams")
            assert resp.status_code == 200
            assert enrolled_team.name in resp.text
            assert eligible_team.name in resp.text
        finally:
            app.dependency_overrides.clear()

    def test_sd_04_enroll_team_creates_enrollment_payment_verified(self, test_db: Session):
        """SD-04: POST enroll → TournamentTeamEnrollment created with payment_verified=True."""
        sd = _make_user(test_db)
        captain = _make_user(test_db, role=UserRole.STUDENT)
        loc = _make_location(test_db)
        campus = _make_campus(test_db, loc)
        _make_sd_assignment(test_db, sd, loc)
        tournament = _make_tournament(test_db, campus=campus)
        team = _make_team(test_db, captain)
        client = _make_client(test_db, sd)

        try:
            resp = client.post(
                f"/sport-director/tournaments/{tournament.id}/teams/{team.id}/enroll",
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert "error" not in resp.headers["location"]

            enrollment = test_db.query(TournamentTeamEnrollment).filter(
                TournamentTeamEnrollment.semester_id == tournament.id,
                TournamentTeamEnrollment.team_id == team.id,
                TournamentTeamEnrollment.is_active == True,
            ).first()
            assert enrollment is not None
            assert enrollment.payment_verified is True
        finally:
            app.dependency_overrides.clear()

    def test_sd_05_enroll_wrong_location_returns_error(self, test_db: Session):
        """SD-05: SD tries to enroll into a tournament at a different location → 303 with error."""
        sd = _make_user(test_db)
        captain = _make_user(test_db, role=UserRole.STUDENT)
        my_loc = _make_location(test_db)
        other_loc = _make_location(test_db)
        other_campus = _make_campus(test_db, other_loc)
        _make_sd_assignment(test_db, sd, my_loc)  # Only assigned to my_loc
        tournament = _make_tournament(test_db, campus=other_campus)  # tournament at other_loc
        team = _make_team(test_db, captain)
        client = _make_client(test_db, sd)

        try:
            resp = client.post(
                f"/sport-director/tournaments/{tournament.id}/teams/{team.id}/enroll",
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert "error" in resp.headers["location"]

            # No enrollment created
            enrollment = test_db.query(TournamentTeamEnrollment).filter(
                TournamentTeamEnrollment.semester_id == tournament.id,
                TournamentTeamEnrollment.team_id == team.id,
            ).first()
            assert enrollment is None
        finally:
            app.dependency_overrides.clear()

    def test_sd_06_remove_team_sets_inactive(self, test_db: Session):
        """SD-06: POST remove → enrollment.is_active=False."""
        sd = _make_user(test_db)
        captain = _make_user(test_db, role=UserRole.STUDENT)
        loc = _make_location(test_db)
        campus = _make_campus(test_db, loc)
        _make_sd_assignment(test_db, sd, loc)
        tournament = _make_tournament(test_db, campus=campus)
        team = _make_team(test_db, captain)
        enrollment = TournamentTeamEnrollment(
            semester_id=tournament.id,
            team_id=team.id,
            is_active=True,
            payment_verified=True,
        )
        test_db.add(enrollment)
        test_db.flush()
        client = _make_client(test_db, sd)

        try:
            resp = client.post(
                f"/sport-director/tournaments/{tournament.id}/teams/{team.id}/remove",
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert "error" not in resp.headers["location"]

            test_db.refresh(enrollment)
            assert enrollment.is_active is False
        finally:
            app.dependency_overrides.clear()

    def test_sd_07_remove_when_in_progress_returns_error(self, test_db: Session):
        """SD-07: Tournament IN_PROGRESS → remove rejected with error, enrollment unchanged."""
        sd = _make_user(test_db)
        captain = _make_user(test_db, role=UserRole.STUDENT)
        loc = _make_location(test_db)
        campus = _make_campus(test_db, loc)
        _make_sd_assignment(test_db, sd, loc)
        tournament = _make_tournament(test_db, campus=campus, status="IN_PROGRESS")
        team = _make_team(test_db, captain)
        enrollment = TournamentTeamEnrollment(
            semester_id=tournament.id,
            team_id=team.id,
            is_active=True,
            payment_verified=True,
        )
        test_db.add(enrollment)
        test_db.flush()
        client = _make_client(test_db, sd)

        try:
            resp = client.post(
                f"/sport-director/tournaments/{tournament.id}/teams/{team.id}/remove",
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert "error" in resp.headers["location"]

            # Enrollment still active
            test_db.refresh(enrollment)
            assert enrollment.is_active is True
        finally:
            app.dependency_overrides.clear()
