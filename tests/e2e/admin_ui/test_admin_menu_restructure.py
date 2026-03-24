"""
Playwright E2E — Admin Menu Restructure (NR-01..NR-05)
=======================================================

Validates the new dropdown navigation structure and the three new admin pages
introduced in the admin menu audit + restructuring sprint.

  NR-01  Nav structure: dropdown groups exist, sub-links correct, active states
  NR-02  /admin/pitches: page loads with filters + data table
  NR-03  /admin/sport-directors: page loads with assign form + assignments table
  NR-04  /admin/teams: page loads with tournament filter + teams table
  NR-05  Live button: IN_PROGRESS tournament shows .btn-live in tournament list

Run (CI / headless, with video):
    PLAYWRIGHT_VIDEO_DIR=test-results/videos/admin-menu \\
    PYTHONPATH=. pytest tests/e2e/admin_ui/test_admin_menu_restructure.py -v -s

Run (local / headed):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=400 \\
    PLAYWRIGHT_VIDEO_DIR=test-results/videos/admin-menu \\
    PYTHONPATH=. pytest tests/e2e/admin_ui/test_admin_menu_restructure.py -v -s
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

APP_URL        = os.environ.get("API_URL", "http://localhost:8000")
DB_URL         = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# DB fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    yield s
    s.close()


# ─────────────────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ss(page, name: str) -> None:
    ts = datetime.now().strftime("%H%M%S")
    (SCREENSHOTS_DIR / f"{ts}_NR_{name}.png").write_bytes(page.screenshot(full_page=True))


def _admin_login(page) -> None:
    page.goto(f"{APP_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", ADMIN_EMAIL)
    page.fill("input[name=password]", ADMIN_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{APP_URL}/dashboard*", timeout=10_000)


# ─────────────────────────────────────────────────────────────────────────────
# NR-01 — Dropdown nav structure
# ─────────────────────────────────────────────────────────────────────────────

class TestNRNavDropdown:
    """NR-01: New dropdown nav — groups, sub-links, active states, hover."""

    def test_NR_01a_nav_groups_exist(self, page):
        """All 6 dropdown group labels are present in the nav HTML."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        _ss(page, "01a_nav_groups")

        content = page.content()
        for label in ("People", "Venues", "Programs", "Events", "Sessions", "Finance"):
            assert label in content, f"Nav group label '{label}' not found in HTML"

        assert "/admin/analytics" in content, "Analytics flat link missing"
        assert "/admin/system-events" in content, "System Events link missing"

    def test_NR_01b_people_group_sub_links(self, page):
        """People dropdown contains /admin/users, /admin/instructors, /admin/sport-directors."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/users")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert 'href="/admin/users"' in content, "People → Users link missing"
        assert 'href="/admin/instructors"' in content, "People → Instructors link missing"
        assert 'href="/admin/sport-directors"' in content, "People → Sport Directors link missing"

    def test_NR_01c_venues_group_sub_links(self, page):
        """Venues dropdown contains /admin/locations and /admin/pitches."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/locations")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert 'href="/admin/locations"' in content, "Venues → Locations link missing"
        assert 'href="/admin/pitches"' in content, "Venues → Pitches link missing"

    def test_NR_01d_finance_label_not_commerce(self, page):
        """Old '🛒 Commerce' is gone; new '💰 Finance' is present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/payments")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "Finance" in content, "New 'Finance' label not found in nav"
        assert "Commerce" not in content, "Old 'Commerce' label still in nav"

    def test_NR_01e_active_state_on_instructors(self, page):
        """
        On /admin/instructors the People nav-group has .active and the
        Instructors sub-link has .active.
        """
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/instructors")
        page.wait_for_load_state("networkidle")
        _ss(page, "01e_instructors_active")

        active_group = page.locator(".nav-group.active")
        assert active_group.count() >= 1, "No .nav-group.active on /admin/instructors"

        active_sub = page.locator('.nav-dropdown-item.active[href="/admin/instructors"]')
        assert active_sub.count() >= 1, "Instructors sub-link not .active on its own page"

    def test_NR_01f_hover_reveals_dropdown(self, page):
        """
        Hovering over the first .nav-group makes its .nav-dropdown visible.
        (CSS :hover simulation — works in Chromium headless.)
        """
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/users")
        page.wait_for_load_state("networkidle")

        first_group = page.locator(".nav-group").first
        first_group.hover()
        page.wait_for_timeout(250)
        _ss(page, "01f_after_hover")

        dropdown = first_group.locator(".nav-dropdown")
        assert dropdown.is_visible(), ".nav-dropdown not visible after hover on .nav-group"


# ─────────────────────────────────────────────────────────────────────────────
# NR-02 — /admin/pitches
# ─────────────────────────────────────────────────────────────────────────────

class TestNRPitchesPage:
    """NR-02: /admin/pitches loads with filter bar and data table."""

    def test_NR_02a_pitches_page_loads(self, page):
        """Admin navigates to /admin/pitches → 200, heading + filter bar present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/pitches")
        page.wait_for_load_state("networkidle")
        _ss(page, "02a_pitches_page")

        assert "/admin/pitches" in page.url, f"Unexpected URL: {page.url}"
        content = page.content()
        assert "Pitches" in content, "Page heading 'Pitches' not found"
        assert "Internal Server Error" not in content, "500 on /admin/pitches"

    def test_NR_02b_pitches_filter_bar(self, page):
        """Location + campus filter selects are present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/pitches")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert 'name="location_filter"' in content, "location_filter select missing"
        assert 'name="campus_filter"' in content, "campus_filter select missing"

    def test_NR_02c_pitches_content_structure(self, page):
        """
        Pitches page shows either campus-section + pitches-table (if pitches exist)
        or the no-pitches empty state. The page uses campus-grouped layout.
        """
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/pitches")
        page.wait_for_load_state("networkidle")

        content = page.content()
        has_content = (
            "campus-section" in content
            or "pitches-table" in content
            or "No pitches found" in content
            or "no-pitches" in content
        )
        assert has_content, "Expected campus section or empty state on /admin/pitches"

    def test_NR_02d_pitches_accessible_via_nav(self, page):
        """
        Hovering over the Venues nav group reveals the Pitches sub-link,
        and clicking it navigates to /admin/pitches.
        """
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/locations")
        page.wait_for_load_state("networkidle")

        # Find the Venues nav-group and hover to reveal dropdown
        venues_group = page.locator(".nav-group").filter(has_text="Venues")
        venues_group.hover()
        page.wait_for_timeout(300)

        link = page.locator('a.nav-dropdown-item[href="/admin/pitches"]')
        link.click()
        page.wait_for_url(f"{APP_URL}/admin/pitches*", timeout=8_000)
        _ss(page, "02d_pitches_via_nav")

        assert "/admin/pitches" in page.url


# ─────────────────────────────────────────────────────────────────────────────
# NR-03 — /admin/sport-directors
# ─────────────────────────────────────────────────────────────────────────────

class TestNRSportDirectorsPage:
    """NR-03: /admin/sport-directors loads with assign form + assignments table."""

    def test_NR_03a_page_loads(self, page):
        """Admin navigates to /admin/sport-directors → 200, heading present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/sport-directors")
        page.wait_for_load_state("networkidle")
        _ss(page, "03a_sport_directors")

        assert "/admin/sport-directors" in page.url, f"Unexpected URL: {page.url}"
        content = page.content()
        assert "Sport Directors" in content, "Heading 'Sport Directors' not found"
        assert "Internal Server Error" not in content, "500 on /admin/sport-directors"

    def test_NR_03b_assign_form(self, page):
        """Assign form with user_id + location_id selects is present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/sport-directors")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert 'name="user_id"' in content, "user_id select missing from assign form"
        assert 'name="location_id"' in content, "location_id select missing"
        assert 'action="/admin/sport-directors/assign"' in content, "Assign form action wrong"

    def test_NR_03c_assignments_table(self, page):
        """Assignments .data-table is present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/sport-directors")
        page.wait_for_load_state("networkidle")

        assert page.locator(".data-table").count() >= 1, (
            "No .data-table on /admin/sport-directors"
        )

    def test_NR_03d_info_box(self, page):
        """The Sport Director role info box is rendered."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/sport-directors")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "info-box" in content, ".info-box not found on sport-directors page"


# ─────────────────────────────────────────────────────────────────────────────
# NR-04 — /admin/teams
# ─────────────────────────────────────────────────────────────────────────────

class TestNRTeamsPage:
    """NR-04: /admin/teams global teams list loads correctly."""

    def test_NR_04a_teams_page_loads(self, page):
        """Admin navigates to /admin/teams → 200, heading + filter present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/teams")
        page.wait_for_load_state("networkidle")
        _ss(page, "04a_teams_page")

        assert "/admin/teams" in page.url, f"Unexpected URL: {page.url}"
        content = page.content()
        assert "Teams" in content, "Heading 'Teams' not found"
        assert "Internal Server Error" not in content, "500 on /admin/teams"

    def test_NR_04b_tournament_filter(self, page):
        """Tournament filter select (tournament_filter) is present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/teams")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert 'name="tournament_filter"' in content, "tournament_filter select missing"

    def test_NR_04c_teams_data_table(self, page):
        """.data-table is present on the teams page."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/teams")
        page.wait_for_load_state("networkidle")

        assert page.locator(".data-table").count() >= 1, "No .data-table on /admin/teams"

    def test_NR_04d_stats_pills(self, page):
        """.stat-pill elements (team counts) are present."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/teams")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "stat-pill" in content, ".stat-pill not found on /admin/teams"


# ─────────────────────────────────────────────────────────────────────────────
# NR-05 — Live button on IN_PROGRESS tournament
# ─────────────────────────────────────────────────────────────────────────────

class TestNRLiveButton:
    """NR-05: IN_PROGRESS tournaments get a 📡 Live button in the list."""

    def test_NR_05a_live_button_visible(self, page, db_engine):
        """
        Seed an IN_PROGRESS tournament with 1 session (so not "stuck"),
        navigate to /admin/tournaments.
        Expected: .btn-live link visible → /admin/tournaments/{id}/live.
        Skip if TournamentType not available.

        Note: Live button only shows when tournament_status=IN_PROGRESS AND
        session_count > 0 (otherwise the "stuck" warning is shown instead).
        """
        from app.models.tournament_type import TournamentType
        from app.models.session import Session as SessionModel, SessionType
        from datetime import timezone

        db = sessionmaker(bind=db_engine)()
        sem_id = None
        session_id = None
        try:
            tt = db.query(TournamentType).first()
            admin_user = db.query(User).filter_by(email=ADMIN_EMAIL).first()
            if not tt or not admin_user:
                pytest.skip("Missing TournamentType / admin user")

            suffix = uuid.uuid4().hex[:6]
            sem = Semester(
                code=f"NR05-{suffix.upper()}",
                name=f"NR-05 Live Test {suffix[:4]}",
                semester_category=SemesterCategory.TOURNAMENT,
                status=SemesterStatus.ONGOING,
                tournament_status="IN_PROGRESS",
                age_group="YOUTH",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30),
                enrollment_cost=0,
                specialization_type="LFA_FOOTBALL_PLAYER",
                master_instructor_id=admin_user.id,
            )
            db.add(sem)
            db.flush()
            tc = TournamentConfiguration(
                semester_id=sem.id,
                tournament_type_id=tt.id,
                max_players=8,
                parallel_fields=1,
                team_enrollment_cost=0,
            )
            db.add(tc)
            db.flush()

            # Add a session so the tournament is not "stuck" (session_count > 0)
            session_dt = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
            sess = SessionModel(
                title=f"NR05 Session {suffix[:4]}",
                date_start=session_dt,
                date_end=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
                session_type=SessionType.on_site,
                semester_id=sem.id,
                capacity=8,
            )
            db.add(sess)
            db.commit()
            db.refresh(sem)
            sem_id = sem.id
            session_id = sess.id

            _admin_login(page)
            page.goto(f"{APP_URL}/admin/tournaments")
            page.wait_for_load_state("networkidle")
            _ss(page, "05a_tournaments_list")

            live_btn = page.locator(f'a.btn-live[href="/admin/tournaments/{sem.id}/live"]')
            assert live_btn.count() >= 1, (
                f"No .btn-live found for IN_PROGRESS tournament id={sem.id}"
            )
            _ss(page, "05a_live_btn_found")

        finally:
            if session_id:
                db.query(SessionModel).filter_by(id=session_id).delete(synchronize_session=False)
            if sem_id:
                db.query(TournamentConfiguration).filter_by(
                    semester_id=sem_id
                ).delete(synchronize_session=False)
                db.query(Semester).filter_by(id=sem_id).delete(synchronize_session=False)
            db.commit()
            db.close()

    def test_NR_05b_tournaments_smoke(self, page):
        """Smoke: /admin/tournaments loads without 500."""
        _admin_login(page)
        page.goto(f"{APP_URL}/admin/tournaments")
        page.wait_for_load_state("networkidle")
        _ss(page, "05b_tournaments_smoke")

        content = page.content()
        assert "Tournaments" in content, "Tournaments heading missing"
        assert "Internal Server Error" not in content, "500 on /admin/tournaments"
