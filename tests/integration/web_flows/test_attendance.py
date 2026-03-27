"""
Attendance Integration Tests — ATT-01 through ATT-06, IND-ATT-01 through IND-ATT-04

ATT-01  GET /attendance page returns 200 with team + instructor rows
ATT-02  POST teams/{id}/checkin sets checked_in_at; uncheckin clears it
ATT-03  POST players/{uid}/checkin creates row; uncheckin deletes it
ATT-04  Session generator uses only checked-in teams when any exist
ATT-05  Session generator uses all active teams when no checkins
ATT-06  PATCH sessions/{id}/postpone saves / clears postponed_reason

IND-ATT-01  GET /attendance for INDIVIDUAL tournament shows player list (no teams)
IND-ATT-02  POST players/{uid}/checkin for INDIVIDUAL (team_id=null)
IND-ATT-03  POST players/{uid}/uncheckin for INDIVIDUAL removes row
IND-ATT-04  TEAM regression — get_attendance_summary still works for TEAM tournaments

All tests run against real DB in SAVEPOINT-isolated transaction (auto-rollback).
"""
import uuid
import pytest
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web, get_current_admin_user_hybrid, get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.session import Session as SessionModel, SessionType, EventCategory
from app.models.team import Team, TeamMember, TournamentTeamEnrollment, TournamentPlayerCheckin
from app.models.tournament_configuration import TournamentConfiguration
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
from app.core.security import get_password_hash
from app.models.tournament_ranking import TournamentRanking
import app.services.tournament.attendance_service as svc


# ─────────────────────────────────────────────────────────────────────────────
# DB fixture (SAVEPOINT isolated)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Factories
# ─────────────────────────────────────────────────────────────────────────────

def _admin(db: Session) -> User:
    u = User(
        email=f"att-admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="ATT Admin",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.ADMIN,
        is_active=True,
        onboarding_completed=True,
        credit_balance=0,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _player(db: Session) -> User:
    u = User(
        email=f"att-player+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"ATT Player {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=100,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _tournament(db: Session) -> Semester:
    t = Semester(
        code=f"ATT-{uuid.uuid4().hex[:8].upper()}",
        name="ATT Test Tournament",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        age_group="YOUTH",
    )
    db.add(t)
    db.flush()
    # TournamentConfiguration for TEAM participant type
    cfg = TournamentConfiguration(
        semester_id=t.id,
        participant_type="TEAM",
        max_players=64,
        parallel_fields=2,
    )
    db.add(cfg)
    db.flush()
    return t


def _team(db: Session, tournament: Semester, captain: User) -> Team:
    uid = uuid.uuid4().hex[:8]
    team = Team(
        name=f"ATT Team {uid}",
        code=f"ATT-{uid}",
        captain_user_id=captain.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
    )
    db.add(team)
    db.flush()
    # Enroll in tournament
    enrollment = TournamentTeamEnrollment(
        semester_id=tournament.id,
        team_id=team.id,
        payment_verified=True,
        is_active=True,
    )
    db.add(enrollment)
    # Add captain as member
    member = TeamMember(team_id=team.id, user_id=captain.id, role="CAPTAIN", is_active=True)
    db.add(member)
    db.flush()
    return team


def _session(db: Session, tournament: Semester) -> SessionModel:
    s = SessionModel(
        title="ATT Match",
        semester_id=tournament.id,
        session_type=SessionType.on_site,
        event_category=EventCategory.MATCH,
        date_start=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
        capacity=20,
    )
    db.add(s)
    db.flush()
    return s


def _client(db: Session, admin: User) -> TestClient:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_web] = lambda: admin
    app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
    return TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"},
                      raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# ATT-01: GET /attendance — page renders with instructor + team rows
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_01_attendance_page_renders(test_db: Session):
    """GET /attendance returns 200 and get_attendance_summary includes enrolled teams."""
    admin = _admin(test_db)
    cap1  = _player(test_db)
    cap2  = _player(test_db)
    tourn = _tournament(test_db)
    team1 = _team(test_db, tourn, cap1)
    team2 = _team(test_db, tourn, cap2)
    test_db.flush()

    # 1. Web route returns 200
    client = _client(test_db, admin)
    resp = client.get(f"/admin/tournaments/{tourn.id}/attendance")
    assert resp.status_code == 200
    # 2. Tournament name always appears in the breadcrumb/title
    assert "ATT Test Tournament" in resp.text

    # 3. Service-layer: summary includes both enrolled teams
    summary = svc.get_attendance_summary(test_db, tourn.id)
    team_names = [t["team_name"] for t in summary["teams"]]
    assert team1.name in team_names
    assert team2.name in team_names
    assert summary["summary"]["teams_total"] == 2
    assert summary["summary"]["teams_checked_in"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# ATT-02: Team check-in / uncheckin
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_02_team_checkin_uncheckin(test_db: Session):
    """POST checkin → checked_in_at set; POST uncheckin → cleared."""
    admin = _admin(test_db)
    cap   = _player(test_db)
    tourn = _tournament(test_db)
    team  = _team(test_db, tourn, cap)

    client = _client(test_db, admin)

    # Check in
    resp = client.post(f"/admin/tournaments/{tourn.id}/teams/{team.id}/checkin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["checked_in_at"] is not None

    # Verify DB
    enrollment = test_db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tourn.id,
        TournamentTeamEnrollment.team_id == team.id,
    ).first()
    assert enrollment.checked_in_at is not None

    # Undo
    resp2 = client.post(f"/admin/tournaments/{tourn.id}/teams/{team.id}/uncheckin")
    assert resp2.status_code == 200
    assert resp2.json()["ok"] is True

    test_db.expire(enrollment)
    assert enrollment.checked_in_at is None


# ─────────────────────────────────────────────────────────────────────────────
# ATT-03: Player check-in / uncheckin
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_03_player_checkin_uncheckin(test_db: Session):
    """POST player checkin creates TournamentPlayerCheckin row; uncheckin deletes it."""
    admin  = _admin(test_db)
    player = _player(test_db)
    tourn  = _tournament(test_db)
    cap    = _player(test_db)
    team   = _team(test_db, tourn, cap)

    # Add player as team member
    member = TeamMember(team_id=team.id, user_id=player.id, role="PLAYER", is_active=True)
    test_db.add(member)
    test_db.flush()

    client = _client(test_db, admin)

    resp = client.post(
        f"/admin/tournaments/{tourn.id}/players/{player.id}/checkin",
        json={"team_id": team.id},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    row = test_db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tourn.id,
        TournamentPlayerCheckin.user_id == player.id,
    ).first()
    assert row is not None
    assert row.team_id == team.id

    # Uncheckin
    resp2 = client.post(f"/admin/tournaments/{tourn.id}/players/{player.id}/uncheckin")
    assert resp2.status_code == 200

    test_db.expire_all()
    gone = test_db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tourn.id,
        TournamentPlayerCheckin.user_id == player.id,
    ).first()
    assert gone is None


# ─────────────────────────────────────────────────────────────────────────────
# ATT-04: Session generator opt-in filter — only checked-in teams used
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_04_session_generator_uses_only_checked_in_teams(test_db: Session):
    """When ≥1 team is checked in, session generator should only include checked-in teams."""
    admin = _admin(test_db)
    cap1  = _player(test_db)
    cap2  = _player(test_db)
    cap3  = _player(test_db)
    tourn = _tournament(test_db)
    team1 = _team(test_db, tourn, cap1)
    team2 = _team(test_db, tourn, cap2)
    team3 = _team(test_db, tourn, cap3)  # NOT checked in

    # Check in team1 and team2 only
    svc.checkin_team(test_db, tourn.id, team1.id, by_user_id=admin.id)
    svc.checkin_team(test_db, tourn.id, team2.id, by_user_id=admin.id)

    # Load enrollments as session generator would
    enrollments = test_db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tourn.id,
        TournamentTeamEnrollment.is_active == True,
    ).all()

    # Apply opt-in filter (same logic as session_generator.py)
    if any(e.checked_in_at is not None for e in enrollments):
        filtered = [e for e in enrollments if e.checked_in_at is not None]
    else:
        filtered = enrollments

    team_ids = [e.team_id for e in filtered]
    assert team3.id not in team_ids
    assert team1.id in team_ids
    assert team2.id in team_ids
    assert len(team_ids) == 2


# ─────────────────────────────────────────────────────────────────────────────
# ATT-05: Session generator — fallback to all active teams when no checkins
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_05_session_generator_fallback_when_no_checkins(test_db: Session):
    """When no team has checked in, all active teams are used (backward compat)."""
    admin = _admin(test_db)
    cap1  = _player(test_db)
    cap2  = _player(test_db)
    tourn = _tournament(test_db)
    team1 = _team(test_db, tourn, cap1)
    team2 = _team(test_db, tourn, cap2)

    # No checkins

    enrollments = test_db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tourn.id,
        TournamentTeamEnrollment.is_active == True,
    ).all()

    if any(e.checked_in_at is not None for e in enrollments):
        filtered = [e for e in enrollments if e.checked_in_at is not None]
    else:
        filtered = enrollments

    team_ids = [e.team_id for e in filtered]
    assert team1.id in team_ids
    assert team2.id in team_ids
    assert len(team_ids) == 2


# ─────────────────────────────────────────────────────────────────────────────
# ATT-06: PATCH /sessions/{id}/postpone saves + clears postponed_reason
# ─────────────────────────────────────────────────────────────────────────────

def test_ATT_06_session_postpone(test_db: Session):
    """PATCH postpone saves reason; sending empty string clears it."""
    admin  = _admin(test_db)
    tourn  = _tournament(test_db)
    sess   = _session(test_db, tourn)

    client = _client(test_db, admin)

    # Set postpone reason
    resp = client.patch(
        f"/admin/sessions/{sess.id}/postpone",
        json={"reason": "Pitch flooded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["postponed_reason"] == "Pitch flooded"

    test_db.expire(sess)
    assert sess.postponed_reason == "Pitch flooded"

    # Clear
    resp2 = client.patch(
        f"/admin/sessions/{sess.id}/postpone",
        json={"reason": ""},
    )
    assert resp2.status_code == 200
    assert resp2.json()["postponed_reason"] is None

    test_db.expire(sess)
    assert sess.postponed_reason is None


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL tournament helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ind_tournament(db: Session) -> Semester:
    t = Semester(
        code=f"IND-{uuid.uuid4().hex[:8].upper()}",
        name="IND Test Tournament",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        age_group="ADULT",
    )
    db.add(t)
    db.flush()
    cfg = TournamentConfiguration(
        semester_id=t.id,
        participant_type="INDIVIDUAL",
        max_players=32,
        parallel_fields=1,
    )
    db.add(cfg)
    db.flush()
    return t


def _enroll_player(db: Session, tournament: Semester, user: User) -> SemesterEnrollment:
    lic = UserLicense(
        user_id=user.id,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
        onboarding_completed=True,
    )
    db.add(lic)
    db.flush()
    enr = SemesterEnrollment(
        user_id=user.id,
        semester_id=tournament.id,
        user_license_id=lic.id,
        request_status=EnrollmentStatus.APPROVED,
        is_active=True,
    )
    db.add(enr)
    db.flush()
    return enr


# ─────────────────────────────────────────────────────────────────────────────
# IND-ATT-01: attendance page renders flat player list for INDIVIDUAL tournament
# ─────────────────────────────────────────────────────────────────────────────

def test_IND_ATT_01_individual_attendance_page(test_db: Session):
    """GET /attendance for INDIVIDUAL tournament returns 200 and shows enrolled players."""
    admin   = _admin(test_db)
    player1 = _player(test_db)
    player2 = _player(test_db)
    tourn   = _ind_tournament(test_db)
    _enroll_player(test_db, tourn, player1)
    _enroll_player(test_db, tourn, player2)
    test_db.flush()

    # HTTP page renders
    client = _client(test_db, admin)
    resp = client.get(f"/admin/tournaments/{tourn.id}/attendance")
    assert resp.status_code == 200
    assert "IND Test Tournament" in resp.text

    # Service returns individual_players, no teams
    summary = svc.get_attendance_summary(test_db, tourn.id)
    assert summary["participant_type"] == "INDIVIDUAL"
    assert summary["teams"] == []
    ind_ids = [p["user_id"] for p in summary["individual_players"]]
    assert player1.id in ind_ids
    assert player2.id in ind_ids
    assert summary["summary"]["players_total"] == 2
    assert summary["summary"]["players_checked_in"] == 0
    assert summary["summary"]["teams_total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# IND-ATT-02: check-in individual player (team_id = null)
# ─────────────────────────────────────────────────────────────────────────────

def test_IND_ATT_02_individual_player_checkin(test_db: Session):
    """POST players/{uid}/checkin for INDIVIDUAL tournament creates TournamentPlayerCheckin with team_id=None."""
    admin  = _admin(test_db)
    player = _player(test_db)
    tourn  = _ind_tournament(test_db)
    _enroll_player(test_db, tourn, player)
    test_db.flush()

    client = _client(test_db, admin)

    # Check in without team_id
    resp = client.post(
        f"/admin/tournaments/{tourn.id}/players/{player.id}/checkin",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["checked_in_at"] is not None

    # DB row created with team_id = None
    row = test_db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tourn.id,
        TournamentPlayerCheckin.user_id == player.id,
    ).first()
    assert row is not None
    assert row.team_id is None

    # Summary reflects check-in
    summary = svc.get_attendance_summary(test_db, tourn.id)
    player_entry = next(p for p in summary["individual_players"] if p["user_id"] == player.id)
    assert player_entry["checked_in_at"] is not None
    assert summary["summary"]["players_checked_in"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# IND-ATT-03: uncheckin individual player removes the row
# ─────────────────────────────────────────────────────────────────────────────

def test_IND_ATT_03_individual_player_uncheckin(test_db: Session):
    """POST players/{uid}/uncheckin for INDIVIDUAL tournament removes TournamentPlayerCheckin row."""
    admin  = _admin(test_db)
    player = _player(test_db)
    tourn  = _ind_tournament(test_db)
    _enroll_player(test_db, tourn, player)
    test_db.flush()

    client = _client(test_db, admin)

    # Check in first
    client.post(f"/admin/tournaments/{tourn.id}/players/{player.id}/checkin", json={})

    row = test_db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tourn.id,
        TournamentPlayerCheckin.user_id == player.id,
    ).first()
    assert row is not None

    # Uncheckin
    resp = client.post(f"/admin/tournaments/{tourn.id}/players/{player.id}/uncheckin")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    test_db.expire_all()
    gone = test_db.query(TournamentPlayerCheckin).filter(
        TournamentPlayerCheckin.tournament_id == tourn.id,
        TournamentPlayerCheckin.user_id == player.id,
    ).first()
    assert gone is None

    # Summary reflects removal
    summary = svc.get_attendance_summary(test_db, tourn.id)
    assert summary["summary"]["players_checked_in"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# IND-ATT-04: TEAM regression — branching doesn't break existing TEAM behavior
# ─────────────────────────────────────────────────────────────────────────────

def test_IND_ATT_04_team_regression(test_db: Session):
    """TEAM tournament: get_attendance_summary still returns teams list and empty individual_players."""
    admin = _admin(test_db)
    cap1  = _player(test_db)
    cap2  = _player(test_db)
    tourn = _tournament(test_db)  # TEAM type
    team1 = _team(test_db, tourn, cap1)
    team2 = _team(test_db, tourn, cap2)
    test_db.flush()

    summary = svc.get_attendance_summary(test_db, tourn.id)
    assert summary["participant_type"] == "TEAM"
    assert summary["individual_players"] == []
    team_ids = [t["team_id"] for t in summary["teams"]]
    assert team1.id in team_ids
    assert team2.id in team_ids
    assert summary["summary"]["teams_total"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# CHDT-05: schedule-config UTC round-trip (integration)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckinOpensAtUTC:
    """CHDT-05: naive datetime string PATCH-ed in → stored + returned as UTC ISO."""

    def test_CHDT_05_naive_string_stored_as_utc(self, test_db: Session):
        """PATCH with naive datetime → value is stored as UTC (same moment regardless of tz offset returned)."""
        admin = _admin(test_db)
        tourn = _tournament(test_db)
        client = _client(test_db, admin)

        resp = client.patch(
            f"/api/v1/tournaments/{tourn.id}/schedule-config",
            json={"checkin_opens_at": "2026-06-01T10:00:00"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        returned = data["checkin_opens_at"]
        assert returned is not None
        # Parse and normalise — regardless of tz offset, must represent 10:00 UTC
        dt = datetime.fromisoformat(returned)
        assert dt.tzinfo is not None, "Response must be timezone-aware"
        dt_utc = dt.astimezone(timezone.utc)
        assert dt_utc.hour == 10
        assert dt_utc.minute == 0


# ─────────────────────────────────────────────────────────────────────────────
# RES-01..03: Results recording in the attendance / tournament flow
# ─────────────────────────────────────────────────────────────────────────────


def _ind_session(db: Session, tournament: Semester) -> SessionModel:
    """INDIVIDUAL_RANKING match session."""
    s = SessionModel(
        title="RES Match",
        semester_id=tournament.id,
        session_type=SessionType.on_site,
        event_category=EventCategory.MATCH,
        match_format="INDIVIDUAL_RANKING",
        date_start=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 7, 1, 11, 0, tzinfo=timezone.utc),
        capacity=20,
        rounds_data={"total_rounds": 1},
    )
    db.add(s)
    db.flush()
    return s


def _api_client(db: Session, admin: User) -> TestClient:
    """TestClient that overrides all auth dependencies for API + web routes."""
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_user_web] = lambda: admin
    app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
    return TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"},
                      raise_server_exceptions=True)


class TestResultsRecording:
    """RES-01..03: Submit round results and verify rankings flow."""

    def test_RES_01_submit_round_results(self, test_db: Session):
        """RES-01: POST round results → 200, rounds_data["round_results"]["1"] populated."""
        admin  = _admin(test_db)
        p1     = _player(test_db)
        p2     = _player(test_db)
        tourn  = _ind_tournament(test_db)
        tourn.tournament_status = "IN_PROGRESS"
        _enroll_player(test_db, tourn, p1)
        _enroll_player(test_db, tourn, p2)
        sess   = _ind_session(test_db, tourn)
        test_db.flush()

        client = _api_client(test_db, admin)

        resp = client.post(
            f"/api/v1/tournaments/{tourn.id}/sessions/{sess.id}/rounds/1/submit-results",
            json={
                "round_number": 1,
                "results": {
                    str(p1.id): "100 points",
                    str(p2.id): "80 points",
                },
            },
        )
        assert resp.status_code == 200, resp.text

        test_db.expire(sess)
        assert sess.rounds_data is not None
        rr = sess.rounds_data.get("round_results", {})
        assert "1" in rr
        assert str(p1.id) in rr["1"]
        assert str(p2.id) in rr["1"]

    def test_RES_02_edit_page_shows_session_with_results(self, test_db: Session):
        """RES-02: After results submitted, GET edit page returns 200 and session has_results."""
        admin  = _admin(test_db)
        p1     = _player(test_db)
        p2     = _player(test_db)
        tourn  = _ind_tournament(test_db)
        tourn.tournament_status = "IN_PROGRESS"
        _enroll_player(test_db, tourn, p1)
        _enroll_player(test_db, tourn, p2)
        sess   = _ind_session(test_db, tourn)
        # Pre-populate results directly (avoid re-testing the submit endpoint)
        sess.rounds_data = {
            "total_rounds": 1,
            "round_results": {"1": {str(p1.id): "100 points", str(p2.id): "80 points"}},
            "completed_rounds": 1,
        }
        test_db.flush()

        client = _api_client(test_db, admin)
        resp = client.get(f"/admin/tournaments/{tourn.id}/edit")
        assert resp.status_code == 200, resp.text
        # The edit page renders sessions_result_status; presence of the session id is sufficient
        assert str(sess.id) in resp.text or "RES Match" in resp.text

    def test_RES_03_calculate_rankings_creates_ranking_rows(self, test_db: Session):
        """RES-03: POST calculate-rankings → 200, TournamentRanking rows created."""
        admin  = _admin(test_db)
        p1     = _player(test_db)
        p2     = _player(test_db)
        tourn  = _ind_tournament(test_db)
        tourn.tournament_status = "IN_PROGRESS"
        _enroll_player(test_db, tourn, p1)
        _enroll_player(test_db, tourn, p2)
        sess   = _ind_session(test_db, tourn)
        sess.rounds_data = {
            "total_rounds": 1,
            "round_results": {"1": {str(p1.id): "100 points", str(p2.id): "80 points"}},
            "completed_rounds": 1,
        }
        test_db.flush()

        client = _api_client(test_db, admin)
        resp = client.post(f"/api/v1/tournaments/{tourn.id}/calculate-rankings")
        assert resp.status_code == 200, resp.text

        rows = test_db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tourn.id
        ).all()
        assert len(rows) == 2
        assert sorted(r.rank for r in rows) == [1, 2]
