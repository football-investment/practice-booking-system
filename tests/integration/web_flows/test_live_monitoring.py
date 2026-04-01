"""
Live Monitoring Integration Tests — LM-01 through LM-03

LM-01  Admin GET /admin/tournaments/{id}/live → 200 HTML
LM-02  Session result POST → _publish_session_result fires without raising
LM-03  Aggregate stats endpoint: completed_count / total_count correct after
       result submission

Note on LM-02
-------------
We don't spin up Redis or a real WebSocket in these integration tests.
Instead we verify that:
  (a) _publish_session_result() is called and does NOT raise even when Redis
      is unavailable (graceful fallback), and
  (b) the HTTP result endpoint still returns 200 when Redis is down.

This mirrors how the production code behaves — live monitoring is best-effort.

All tests run against the real DB in a SAVEPOINT-isolated transaction (auto-rollback).
"""
import uuid
import json
import pytest
from datetime import datetime, date, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user, get_current_user_web, get_current_admin_or_instructor_user_hybrid
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel, SessionType, EventCategory
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.core.security import get_password_hash


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

def _make_user(db: Session, role: UserRole = UserRole.ADMIN) -> User:
    u = User(
        email=f"live-test+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"Live Test {uuid.uuid4().hex[:4]}",
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


def _make_tournament(db: Session) -> Semester:
    t = Semester(
        code=f"LIVE-{uuid.uuid4().hex[:8].upper()}",
        name="Live Monitoring Test Tournament",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
        age_group="YOUTH",
    )
    db.add(t)
    db.flush()
    return t


def _make_match_session(db: Session, tournament: Semester) -> SessionModel:
    s = SessionModel(
        title="LM Test Session",
        date_start=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        session_type=SessionType.on_site,
        event_category=EventCategory.MATCH,
        semester_id=tournament.id,
        instructor_id=None,
        session_status="scheduled",
    )
    db.add(s)
    db.flush()
    return s


def _client_for(test_db: Session, current_user: User) -> TestClient:
    """TestClient with given user injected for both Bearer and cookie auth."""
    def _override_db():
        yield test_db

    def _override_user():
        return current_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_current_user_web] = lambda: current_user
    app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = _override_user
    return TestClient(app, raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# LM-01: Admin GET /admin/tournaments/{id}/live → 200 HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_01_live_dashboard_returns_200(test_db: Session):
    admin = _make_user(test_db, role=UserRole.ADMIN)
    tournament = _make_tournament(test_db)

    client = _client_for(test_db, admin)
    resp = client.get(
        f"/admin/tournaments/{tournament.id}/live",
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp.status_code == 200, resp.text
    html = resp.text
    assert "Live Monitoring" in html
    assert str(tournament.id) in html
    assert "WebSocket" in html or "ws-dot" in html  # JS widget present

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# LM-02: Result submission works even when Redis is unavailable
#        (_publish_session_result must NOT raise)
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_02_result_submit_succeeds_when_redis_unavailable(test_db: Session):
    """
    Verifies that the PATCH /sessions/{id}/results endpoint returns 200 even
    when Redis pub/sub is unavailable.  Live monitoring is best-effort.
    """
    admin = _make_user(test_db, role=UserRole.ADMIN)
    tournament = _make_tournament(test_db)
    # Assign admin as master instructor so auth check passes
    tournament.master_instructor_id = admin.id
    test_db.flush()

    session = _make_match_session(test_db, tournament)
    player1 = _make_user(test_db, role=UserRole.STUDENT)
    player2 = _make_user(test_db, role=UserRole.STUDENT)

    # Patch publish to simulate Redis being down (raises)
    with patch(
        "app.api.api_v1.endpoints.sessions.results.publish_tournament_update",
        side_effect=ConnectionError("Redis down"),
    ):
        client = _client_for(test_db, admin)
        resp = client.patch(
            f"/api/v1/sessions/{session.id}/results",
            json={
                "results": [
                    {"user_id": player1.id, "score": 90.0, "rank": 1},
                    {"user_id": player2.id, "score": 75.0, "rank": 2},
                ]
            },
            headers={"Authorization": "Bearer test-csrf-bypass"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["results_count"] == 2

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# LM-03: _publish_session_result sends correct aggregate counts
# ─────────────────────────────────────────────────────────────────────────────

def test_LM_03_publish_sends_correct_aggregate_stats(test_db: Session):
    """
    After submitting a result:
      - completed_count should be 1 (this session is the only completed one)
      - total_count should be 2 (two sessions in the tournament)
      - progress_pct = 0.5
    """
    admin = _make_user(test_db, role=UserRole.ADMIN)
    tournament = _make_tournament(test_db)
    tournament.master_instructor_id = admin.id
    test_db.flush()

    session1 = _make_match_session(test_db, tournament)
    session2 = _make_match_session(test_db, tournament)  # noqa: F841 — remains scheduled

    # Pre-mark session1 as completed so the aggregate query counts it
    # (submit_game_results stores rounds_data but does not flip session_status;
    # we simulate here the state that would exist after full finalization)
    session1.session_status = "completed"
    test_db.flush()

    player1 = _make_user(test_db, role=UserRole.STUDENT)
    player2 = _make_user(test_db, role=UserRole.STUDENT)

    published_payloads = []

    def capture_publish(tournament_id, payload):
        published_payloads.append(payload)

    with patch(
        "app.api.api_v1.endpoints.sessions.results.publish_tournament_update",
        side_effect=capture_publish,
    ):
        client = _client_for(test_db, admin)
        resp = client.patch(
            f"/api/v1/sessions/{session1.id}/results",
            json={
                "results": [
                    {"user_id": player1.id, "score": 88.0, "rank": 1},
                    {"user_id": player2.id, "score": 72.0, "rank": 2},
                ]
            },
            headers={"Authorization": "Bearer test-csrf-bypass"},
        )
        assert resp.status_code == 200, resp.text

    assert len(published_payloads) == 1
    payload = published_payloads[0]
    assert payload["type"] == "session_result"
    assert payload["session_id"] == session1.id
    assert payload["total_count"] == 2
    assert payload["completed_count"] == 1
    assert abs(payload["progress_pct"] - 0.5) < 0.01

    app.dependency_overrides.clear()
