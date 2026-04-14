"""
Virtual Tournament Tests — Phase 1 Validation

VT-01  _resolve_session_type() returns 'virtual' when session_type_config='virtual'
VT-02  _resolve_base_xp('virtual') == 50  (not 75 like on_site)
VT-03  PATCH session_type_config after sessions_generated=True → HTTP 400
VT-04  Result submission on virtual session → HTTP 200 (no actual_start_time needed)
VT-05  GET /events/{id} renders 200 for virtual tournament (no crash, no 404)

All tests use SAVEPOINT-isolated DB — no side effects across tests.
"""

import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.dependencies import get_current_admin_user_hybrid, get_current_admin_or_instructor_user_hybrid
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.session import Session as SessionModel, SessionType, EventCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.services.tournament.session_generation.formats.base_format_generator import BaseFormatGenerator

_PFX = "vt"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ─────────────────────────────────────────────────────────────────────────────
# Minimal factories
# ─────────────────────────────────────────────────────────────────────────────

def _tournament(
    db: Session,
    sessions_generated: bool = False,
    session_type_config: str = "virtual",
    tournament_status: str = "DRAFT",
) -> Semester:
    """Minimal tournament (Semester) with TournamentConfiguration."""
    sem = Semester(
        code=f"{_PFX}-{_uid()}",
        name=f"VT Test Tournament {_uid()}",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=SemesterStatus.DRAFT,
        semester_category="TOURNAMENT",
        tournament_status=tournament_status,
    )
    db.add(sem)
    db.flush()

    cfg = TournamentConfiguration(
        semester_id=sem.id,
        participant_type="INDIVIDUAL",
        sessions_generated=sessions_generated,
        session_type_config=session_type_config,
    )
    db.add(cfg)
    db.flush()
    return sem


def _virtual_session(db: Session, semester: Semester, admin_user) -> SessionModel:
    """Minimal MATCH virtual session for result submission tests."""
    sess = SessionModel(
        title=f"VT Virtual Session {_uid()}",
        semester_id=semester.id,
        session_type=SessionType.virtual,
        event_category=EventCategory.MATCH,
        date_start=datetime.utcnow() + timedelta(hours=1),
        date_end=datetime.utcnow() + timedelta(hours=2),
        base_xp=50,
        instructor_id=admin_user.id,
    )
    db.add(sess)
    db.flush()
    return sess


@contextmanager
def _admin_client(db: Session, admin_user):
    """TestClient sharing test SAVEPOINT session with admin dependency override."""
    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin_user
    app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin_user
    try:
        with TestClient(
            app,
            headers={"Authorization": "Bearer test-csrf-bypass"},
            raise_server_exceptions=True,
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@contextmanager
def _public_client(db: Session):
    """TestClient for public (unauthenticated) routes, sharing test SAVEPOINT session."""
    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    try:
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Stub generator for testing helpers
# ─────────────────────────────────────────────────────────────────────────────

class _StubGenerator(BaseFormatGenerator):
    """Concrete subclass so BaseFormatGenerator (abstract) can be instantiated."""
    def generate(self, *args, **kwargs):
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_VT_01_resolve_session_type_returns_virtual(test_db: Session):
    """_resolve_session_type() returns 'virtual' when session_type_config='virtual'."""
    gen = _StubGenerator(db=test_db)

    tournament = _tournament(test_db, session_type_config="virtual")
    test_db.refresh(tournament)

    result = gen._resolve_session_type(tournament)
    assert result == "virtual", (
        f"Expected _resolve_session_type to return 'virtual', got {result!r}"
    )


def test_VT_02_resolve_base_xp_virtual_is_50(test_db: Session):
    """_resolve_base_xp('virtual') == 50 — virtual sessions earn less XP than on_site (75)."""
    gen = _StubGenerator(db=test_db)

    assert gen._resolve_base_xp("virtual") == 50, (
        f"Expected base_xp 50 for virtual, got {gen._resolve_base_xp('virtual')}"
    )
    # Sanity: on_site is different
    assert gen._resolve_base_xp("on_site") == 75
    assert gen._resolve_base_xp("hybrid") == 100


def test_VT_03_guard_rejects_session_type_change_after_sessions_generated(
    test_db: Session, admin_user
):
    """PATCH session_type_config after sessions_generated=True → HTTP 400 (same guard as STC-03)."""
    tournament = _tournament(test_db, sessions_generated=True, session_type_config="virtual")
    test_db.commit()

    with _admin_client(test_db, admin_user) as client:
        resp = client.patch(
            f"/api/v1/tournaments/{tournament.id}",
            json={"session_type_config": "on_site"},
        )

    assert resp.status_code == 400, (
        f"Expected 400 when changing session_type_config after sessions generated, "
        f"got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # Custom exception handler returns {"error": {"message": ...}};
    # fall back to standard FastAPI {"detail": ...} format.
    error_msg = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "session_type_config" in error_msg or "sessions" in error_msg.lower(), (
        f"Expected error mentioning session_type_config/sessions, got: {error_msg!r}"
    )


def test_VT_04_result_submission_on_virtual_session_returns_200(
    test_db: Session, admin_user
):
    """Result submission on virtual session → HTTP 200 — no actual_start_time required.

    Proves that the virtual session flow does NOT gate result submission on
    instructor start (actual_start_time), unlike the hybrid flow.
    """
    tournament = _tournament(test_db, session_type_config="virtual")
    tournament.master_instructor_id = admin_user.id
    test_db.flush()

    sess = _virtual_session(test_db, tournament, admin_user)
    test_db.commit()

    # Verify actual_start_time is NOT set — proving it's not needed
    assert sess.actual_start_time is None, (
        "Test pre-condition: actual_start_time must be None for this test"
    )

    with _admin_client(test_db, admin_user) as client:
        resp = client.patch(
            f"/api/v1/sessions/{sess.id}/results",
            json={
                "results": [
                    {"user_id": admin_user.id, "score": 95.0, "rank": 1},
                ],
            },
        )

    assert resp.status_code == 200, (
        f"Expected 200 for result submission on virtual session (no instructor start needed), "
        f"got {resp.status_code}: {resp.text}"
    )


def test_VT_05_public_event_page_renders_for_virtual_tournament(
    test_db: Session,
):
    """GET /events/{id} returns 200 for virtual tournament in DRAFT state — no crash, no 404."""
    tournament = _tournament(
        test_db,
        session_type_config="virtual",
        tournament_status="DRAFT",
    )
    test_db.commit()

    with _public_client(test_db) as client:
        resp = client.get(f"/events/{tournament.id}")

    assert resp.status_code == 200, (
        f"Expected 200 for /events/{{id}} on virtual tournament in DRAFT, "
        f"got {resp.status_code}: {resp.text[:300]}"
    )
    # UI: rendered HTML must contain the tournament name (proves it's not an error page)
    assert tournament.name in resp.text, (
        f"Tournament name '{tournament.name}' must appear in rendered HTML. "
        f"Snippet: {resp.text[:400]}"
    )
