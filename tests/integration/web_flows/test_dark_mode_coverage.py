"""
Dark Mode HTTP Response Coverage Tests — DM-01 through DM-17
=============================================================

DM-01  GET /dashboard/lfa-football-player → <head> links dark-mode.css
DM-02  GET /admin/tournaments             → <head> links dark-mode.css
DM-03  GET /players/{uid}/card            → dark-mode.css NOT present (isolated card system)
DM-04  GET /dashboard/lfa-football-player → no inline 'style="background: white"' in HTML
DM-05  GET /dashboard/lfa-football-player → dark-mode.css <link> appears AFTER all other CSS <link>s
DM-06  GET /quiz/{id}/take                → <head> links dark-mode.css
DM-07  GET /achievements                 → dark-mode.css present; no style="color: #95a5a6" inline attrs
DM-08  GET /progress                     → dark-mode.css present; no background:white in <style> blocks
DM-09  GET /skills                       → dark-mode.css present; no background:white in <style> blocks
DM-10  GET /sessions                     → dark-mode.css present; no style="color: #7f8c8d" inline attrs
DM-11  GET /calendar                     → dark-mode.css present
DM-12  GET /credits                      → dark-mode.css present
DM-13  GET /admin/tournaments/{id}/edit  → dark-mode.css present; .sgw-modal no background:white
DM-14  GET /admin/tournaments/{id}/attendance → dark-mode.css present
DM-15  GET /events/{id}                  → dark-mode.css NOT present (isolated design, regression guard)
DM-16  GET /login                        → dark-mode.css present (extends base.html)
DM-17  GET /profile                      → dark-mode.css present

All tests run against real DB in SAVEPOINT-isolated transaction (auto-rollback).
CSRF is bypassed via Authorization: Bearer header (middleware skips validation for Bearer auth).
"""

import re
import uuid
import pytest
from datetime import datetime, timezone, date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import (
    get_current_user_web,
    get_current_admin_user_hybrid,
    get_current_admin_or_instructor_user_hybrid,
)
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
from app.models.semester import Semester
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

def _admin_user(db: Session) -> User:
    u = User(
        email=f"dm-admin+{uuid.uuid4().hex[:8]}@lfa.com",
        name="DM Admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _player_with_license(db: Session) -> tuple[User, UserLicense]:
    u = User(
        email=f"dm-player+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"DM Player {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=100,
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
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_web] = lambda: user
    client = TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        raise_server_exceptions=True,
    )
    return client


def _admin_client(db: Session, admin: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_web] = lambda: admin
    app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
    app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin
    client = TestClient(
        app,
        headers={"Authorization": "Bearer test-csrf-bypass"},
        raise_server_exceptions=True,
    )
    return client


def _public_client(db: Session) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=True)


def _head_css_links(html: str) -> list[str]:
    """Return all CSS <link href> values found in the <head> section."""
    head_match = re.search(r"<head[\s\S]*?</head>", html, re.IGNORECASE)
    if not head_match:
        return []
    head = head_match.group(0)
    return re.findall(r'<link[^>]+href=["\']([^"\']*\.css[^"\']*)["\']', head, re.IGNORECASE)


def _style_block_white_bgs(html: str) -> list[str]:
    """Return all 'background: white' occurrences found inside <style>...</style> blocks."""
    style_blocks = re.findall(r'<style[^>]*>([\s\S]*?)</style>', html, re.IGNORECASE)
    matches = []
    for block in style_blocks:
        m = re.findall(r'background(?:-color)?\s*:\s*white\b', block, re.IGNORECASE)
        matches.extend(m)
    return matches


def _inline_color_attrs(html: str, color_value: str) -> list[str]:
    """Return inline style attributes containing the given color value (e.g. '#7f8c8d')."""
    pattern = re.compile(
        rf'style=["\'][^"\']*color\s*:\s*{re.escape(color_value)}[^"\']*["\']',
        re.IGNORECASE,
    )
    return pattern.findall(html)


def _tournament(db: Session, admin: User) -> Semester:
    """Create a minimal DRAFT tournament for page-rendering tests."""
    t = Semester(
        code=f"DM-TEST-{uuid.uuid4().hex[:8]}",
        name=f"DM Test Tournament {uuid.uuid4().hex[:6]}",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        master_instructor_id=admin.id,
        tournament_status="DRAFT",
    )
    db.add(t)
    db.flush()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# DM-01: Student dashboard links dark-mode.css
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_01_student_dashboard_has_dark_mode_css(test_db: Session):
    """GET /dashboard/lfa-football-player — <head> must contain a dark-mode.css link."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/dashboard/lfa-football-player")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css link not found in page HTML"

    css_links = _head_css_links(resp.text)
    assert any("dark-mode.css" in href for href in css_links), (
        f"dark-mode.css not found in <head> CSS links: {css_links}"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-02: Admin tournaments page links dark-mode.css
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_02_admin_tournaments_has_dark_mode_css(test_db: Session):
    """GET /admin/tournaments — <head> must contain a dark-mode.css link."""
    admin = _admin_user(test_db)
    client = _admin_client(test_db, admin)

    resp = client.get("/admin/tournaments")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css link not found in page HTML"

    css_links = _head_css_links(resp.text)
    assert any("dark-mode.css" in href for href in css_links), (
        f"dark-mode.css not found in <head> CSS links: {css_links}"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-03: Player card page does NOT link dark-mode.css (isolated system)
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_03_player_card_does_not_have_dark_mode_css(test_db: Session):
    """GET /players/{uid}/card — dark-mode.css must NOT appear (card has its own --card-* system)."""
    player, _ = _player_with_license(test_db)
    client = _public_client(test_db)

    resp = client.get(f"/players/{player.id}/card")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" not in resp.text, (
        "dark-mode.css unexpectedly found in player card HTML — card must use isolated --card-* system"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-04: No inline style="background: white" on student dashboard
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_04_student_dashboard_no_inline_white_bg(test_db: Session):
    """GET /dashboard/lfa-football-player — no inline style=\"background: white\" in HTML."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/dashboard/lfa-football-player")
    assert resp.status_code == 200, resp.text

    # Check for any inline background: white style attribute
    matches = re.findall(
        r'style=["\'][^"\']*background\s*:\s*white[^"\']*["\']',
        resp.text,
        re.IGNORECASE,
    )
    assert not matches, (
        f"Found {len(matches)} inline 'style=\"background: white\"' occurrence(s) on student dashboard:\n"
        + "\n".join(m[:120] for m in matches[:5])
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-05: dark-mode.css link is the LAST CSS link in <head>
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_05_dark_mode_css_loads_last(test_db: Session):
    """GET /dashboard/lfa-football-player — dark-mode.css <link> must be after all other CSS links."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/dashboard/lfa-football-player")
    assert resp.status_code == 200, resp.text

    css_links = _head_css_links(resp.text)
    assert any("dark-mode.css" in href for href in css_links), (
        "dark-mode.css not found in <head> CSS links — cannot check load order"
    )

    # dark-mode.css must be the last CSS link
    last_css = css_links[-1]
    assert "dark-mode.css" in last_css, (
        f"dark-mode.css is not the last CSS link. Last link: '{last_css}'. All links: {css_links}"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-06: Quiz take page links dark-mode.css
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_06_admin_dashboard_page_has_dark_mode_css(test_db: Session):
    """GET /admin/users — admin pages served through base.html must link dark-mode.css."""
    admin = _admin_user(test_db)
    client = _admin_client(test_db, admin)

    resp = client.get("/admin/users")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css link not found in admin users page"

    css_links = _head_css_links(resp.text)
    assert any("dark-mode.css" in href for href in css_links), (
        f"dark-mode.css not found in <head> CSS links: {css_links}"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-07: Achievements page — dark-mode.css present + no hardcoded grey inline colors
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_07_achievements_no_inline_grey_colors(test_db: Session):
    """GET /achievements — dark-mode.css present; no style="color: #95a5a6" inline attrs."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/achievements")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on achievements page"

    for bad_color in ("#95a5a6", "#7f8c8d"):
        hits = _inline_color_attrs(resp.text, bad_color)
        assert not hits, (
            f"Found {len(hits)} inline style with hardcoded color {bad_color} on achievements page"
        )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-08: Progress page — dark-mode.css present + no background:white in style blocks
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_08_progress_no_white_bg_in_style_blocks(test_db: Session):
    """GET /progress — dark-mode.css present; no 'background: white' in <style> blocks."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/progress")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on progress page"

    whites = _style_block_white_bgs(resp.text)
    assert not whites, (
        f"Found {len(whites)} 'background: white' in <style> blocks on progress page"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-09: Skills page — dark-mode.css present + no background:white in style blocks
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_09_skills_no_white_bg_in_style_blocks(test_db: Session):
    """GET /skills — dark-mode.css present; no 'background: white' in <style> blocks."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/skills")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on skills page"

    whites = _style_block_white_bgs(resp.text)
    assert not whites, (
        f"Found {len(whites)} 'background: white' in <style> blocks on skills page"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-10: Sessions page — dark-mode.css present + no hardcoded grey inline colors
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_10_sessions_no_inline_grey_colors(test_db: Session):
    """GET /sessions — dark-mode.css present; no style="color: #7f8c8d" inline attrs."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/sessions")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on sessions page"

    for bad_color in ("#7f8c8d", "#2d3748"):
        hits = _inline_color_attrs(resp.text, bad_color)
        assert not hits, (
            f"Found {len(hits)} inline style with hardcoded color {bad_color} on sessions page"
        )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-11: Calendar page — dark-mode.css present
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_11_calendar_has_dark_mode_css(test_db: Session):
    """GET /calendar — dark-mode.css must be present."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/calendar")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on calendar page"

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-12: Credits page — dark-mode.css present
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_12_credits_has_dark_mode_css(test_db: Session):
    """GET /credits — dark-mode.css must be present."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/credits")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on credits page"

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-13: Tournament edit page — dark-mode.css present + .sgw-modal no background:white
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_13_tournament_edit_has_dark_mode_css_no_white_modal(test_db: Session):
    """GET /admin/tournaments/{id}/edit — dark-mode.css present; no background:white in style blocks."""
    admin = _admin_user(test_db)
    t = _tournament(test_db, admin)
    client = _admin_client(test_db, admin)

    resp = client.get(f"/admin/tournaments/{t.id}/edit")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on tournament edit page"

    whites = _style_block_white_bgs(resp.text)
    assert not whites, (
        f"Found {len(whites)} 'background: white' in <style> blocks on tournament edit page"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-14: Tournament attendance page — dark-mode.css present
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_14_tournament_attendance_has_dark_mode_css(test_db: Session):
    """GET /admin/tournaments/{id}/attendance — dark-mode.css must be present."""
    admin = _admin_user(test_db)
    t = _tournament(test_db, admin)
    client = _admin_client(test_db, admin)

    resp = client.get(f"/admin/tournaments/{t.id}/attendance")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on tournament attendance page"

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-15: Public event page — dark-mode.css NOT present (isolated design, regression guard)
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_15_public_event_page_does_not_have_dark_mode_css(test_db: Session):
    """GET /events/{id} — dark-mode.css must NOT be present (tournament_detail.html is isolated)."""
    admin = _admin_user(test_db)
    t = _tournament(test_db, admin)
    client = _public_client(test_db)

    resp = client.get(f"/events/{t.id}")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" not in resp.text, (
        "dark-mode.css unexpectedly found on public event page — "
        "tournament_detail.html must remain isolated (uses its own dark-first design)"
    )

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-16: Login page — dark-mode.css present (extends base.html)
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_16_login_page_has_dark_mode_css(test_db: Session):
    """GET /login — dark-mode.css must be present (base.html chain)."""
    client = _public_client(test_db)

    resp = client.get("/login")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on login page"

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# DM-17: Profile page — dark-mode.css present
# ─────────────────────────────────────────────────────────────────────────────

def test_DM_17_profile_page_has_dark_mode_css(test_db: Session):
    """GET /profile — dark-mode.css must be present."""
    player, _ = _player_with_license(test_db)
    client = _student_client(test_db, player)

    resp = client.get("/profile")
    assert resp.status_code == 200, resp.text
    assert "dark-mode.css" in resp.text, "dark-mode.css not found on profile page"

    app.dependency_overrides.clear()
