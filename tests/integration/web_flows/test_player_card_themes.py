"""
Player Card Theme Integration Tests — PC-01 through PC-04

PC-01  GET /players/{uid}/card → 200 + HTML contains 'fifa-left' class
PC-02  POST /dashboard/card-theme with free theme → {"ok": true}
PC-03  POST /dashboard/card-theme with locked (premium) theme → 400
PC-04  GET /players/{uid}/card with Arctic theme → <body class="theme-arctic"> present

All tests run against real DB in SAVEPOINT-isolated transaction (auto-rollback).
CSRF is bypassed via Authorization: Bearer header (middleware skips validation for Bearer auth).
"""
import uuid
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user_web
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
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
    session.begin_nested()

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

def _player_with_license(db: Session, credit_balance: int = 100) -> tuple[User, UserLicense]:
    """Create a student user with an active LFA_FOOTBALL_PLAYER license."""
    u = User(
        email=f"pc-player+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"PC Player {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=credit_balance,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    lic = UserLicense(
        user_id=u.id,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
        onboarding_completed=True,
        motivation_scores={"position": "MIDFIELDER"},
    )
    db.add(lic)
    db.flush()
    return u, lic


def _student_client(db: Session, user: User) -> TestClient:
    """TestClient with student user injected. Bearer header bypasses CSRF middleware."""
    def _override_db():
        yield db
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_web] = lambda: user
    return TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        raise_server_exceptions=True,
    )


def _public_client(db: Session) -> TestClient:
    """TestClient for public routes (no auth required)."""
    def _override_db():
        yield db
    app.dependency_overrides[get_db] = _override_db
    return TestClient(app, raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# PC-01: Public player card returns 200 with card HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_01_public_player_card_200(test_db: Session):
    """GET /players/{uid}/card returns 200 and contains the card HTML structure."""
    player, _ = _player_with_license(test_db)
    client = _public_client(test_db)

    resp = client.get(f"/players/{player.id}/card")
    assert resp.status_code == 200, resp.text
    assert "fifa-left" in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# PC-02: Apply free theme succeeds
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_02_apply_free_theme(test_db: Session):
    """POST /dashboard/card-theme with a free theme ID returns {"ok": true}."""
    player, lic = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.post("/dashboard/card-theme", json={"theme": "midnight"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["theme"] == "midnight"

    test_db.refresh(lic)
    assert lic.card_theme == "midnight"


# ─────────────────────────────────────────────────────────────────────────────
# PC-03: Apply locked premium theme returns 400
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_03_apply_locked_theme_returns_400(test_db: Session):
    """POST /dashboard/card-theme with a premium (not unlocked) theme returns 400."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.post("/dashboard/card-theme", json={"theme": "gold"})
    assert resp.status_code == 400, resp.text
    data = resp.json()
    assert data["ok"] is False
    assert "locked" in data["error"].lower() or "required" in data["error"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# PC-04: Arctic theme renders with correct body class
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_04_arctic_theme_renders_body_class(test_db: Session):
    """GET /players/{uid}/card with Arctic theme shows <body class=\"theme-arctic\">."""
    player, lic = _player_with_license(test_db)
    lic.card_theme = "arctic"
    test_db.flush()

    client = _public_client(test_db)
    resp = client.get(f"/players/{player.id}/card")
    assert resp.status_code == 200, resp.text
    assert 'class="theme-arctic"' in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# PC-05: Preview compact_bg returns 200
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_05_preview_compact_bg_returns_200(test_db: Session):
    """GET /players/{uid}/card?preview=compact_bg returns 200 with compact_bg template."""
    player, _ = _player_with_license(test_db)
    client = _public_client(test_db)

    resp = client.get(f"/players/{player.id}/card?preview=compact_bg")
    assert resp.status_code == 200, resp.text
    assert "cmp-photo-col" in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# PC-06: Preview showcase_bg returns 200
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_06_preview_showcase_bg_returns_200(test_db: Session):
    """GET /players/{uid}/card?preview=showcase_bg returns 200 with showcase_bg template."""
    player, _ = _player_with_license(test_db)
    client = _public_client(test_db)

    resp = client.get(f"/players/{player.id}/card?preview=showcase_bg")
    assert resp.status_code == 200, resp.text
    assert "sc-banner" in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# PC-07: BG fallback — renders without error when bg_url is None
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_07_bg_url_none_fallback_no_crash(test_db: Session):
    """compact_bg and showcase_bg templates render cleanly when bg URL columns are NULL."""
    player, lic = _player_with_license(test_db)
    assert lic.card_bg_compact_url is None
    assert lic.card_bg_showcase_url is None

    client = _public_client(test_db)
    for variant in ("compact_bg", "showcase_bg"):
        resp = client.get(f"/players/{player.id}/card?preview={variant}")
        assert resp.status_code == 200, f"{variant} returned {resp.status_code}: {resp.text[:300]}"
        # No inline background-image → bg_url was None
        assert "background-image" not in resp.text, (
            f"{variant}: unexpected background-image in output when bg_url is None"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PC-08: Unlock compact_bg deducts 400 CR
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_08_unlock_compact_bg_deducts_credits(test_db: Session):
    """POST /dashboard/unlock-variant compact_bg deducts 400 CR and adds to unlocked list."""
    player, lic = _player_with_license(test_db, credit_balance=500)
    client = _student_client(test_db, player)

    resp = client.post("/dashboard/unlock-variant", json={"variant": "compact_bg"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["new_balance"] == 100  # 500 - 400 CR

    test_db.refresh(lic)
    assert "compact_bg" in (lic.unlocked_card_variants or [])


# ─────────────────────────────────────────────────────────────────────────────
# PC-09: Apply compact_bg after unlock saves card_variant
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_09_apply_compact_bg_after_unlock(test_db: Session):
    """POST /dashboard/card-variant compact_bg succeeds when already unlocked."""
    player, lic = _player_with_license(test_db, credit_balance=500)
    lic.unlocked_card_variants = ["compact_bg"]
    test_db.flush()

    client = _student_client(test_db, player)
    resp = client.post("/dashboard/card-variant", json={"variant": "compact_bg"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True

    test_db.refresh(lic)
    assert lic.card_variant == "compact_bg"


# ─────────────────────────────────────────────────────────────────────────────
# PC-10: Card editor page returns 200 with correct HTML for licensed player
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_10_card_editor_200(test_db: Session):
    """GET /dashboard/lfa-football-player/card-editor returns 200 with card editor HTML."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)
    resp = client.get("/dashboard/lfa-football-player/card-editor")
    assert resp.status_code == 200, resp.text
    html = resp.text
    assert "player-card-iframe" in html
    assert "theme-picker" in html
    assert "variant-picker" in html


# ─────────────────────────────────────────────────────────────────────────────
# PC-11: Card editor returns 403 for user without LFA license
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_11_card_editor_403_no_license(test_db: Session):
    """GET /dashboard/lfa-football-player/card-editor returns 403 when no LFA license."""
    user = User(
        email=f"pc-nolic+{uuid.uuid4().hex[:8]}@lfa.com",
        name="PC NoLic",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=0,
    )
    test_db.add(user)
    test_db.flush()

    client = _student_client(test_db, user)
    resp = client.get("/dashboard/lfa-football-player/card-editor", follow_redirects=False)
    assert resp.status_code == 403, resp.text


# ─────────────────────────────────────────────────────────────────────────────
# PC-12: Card editor redirects to onboarding when license not yet completed
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_12_card_editor_redirect_no_onboarding(test_db: Session):
    """GET /dashboard/lfa-football-player/card-editor redirects if onboarding incomplete."""
    user = User(
        email=f"pc-noob+{uuid.uuid4().hex[:8]}@lfa.com",
        name="PC NoOnboard",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=False,
        credit_balance=0,
    )
    test_db.add(user)
    test_db.flush()
    lic = UserLicense(
        user_id=user.id,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
        onboarding_completed=False,  # not yet completed
    )
    test_db.add(lic)
    test_db.flush()

    client = _student_client(test_db, user)
    resp = client.get("/dashboard/lfa-football-player/card-editor", follow_redirects=False)
    assert resp.status_code == 303, resp.text
    assert "/onboarding" in resp.headers["location"]


# ─────────────────────────────────────────────────────────────────────────────
# PC-13: Card editor shows photo upload section and "My Player Card" heading
# ─────────────────────────────────────────────────────────────────────────────

def test_PC_13_card_editor_shows_photo_and_heading(test_db: Session):
    """GET /dashboard/lfa-football-player/card-editor contains photo section and heading."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)
    resp = client.get("/dashboard/lfa-football-player/card-editor")
    assert resp.status_code == 200, resp.text
    html = resp.text
    assert "My Player Card" in html
    assert "player-photo-section" in html
    assert "player-photo-section-title" in html
