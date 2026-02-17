"""
Tournament Manager Sidebar Navigation — Headless Playwright E2E Tests
======================================================================

Verifies that Admin and Instructor users can reach the Tournament Manager
page via the canonical sidebar button on their respective dashboards.

Auth strategy: URL-param injection (same as test_tournament_monitor_e2e.py).
    GET /{Dashboard}?token=<JWT>&user=<JSON>
    restore_session_from_url() in each page picks this up automatically.
    No UI login form interaction required.

Coverage:
    A1 — Admin sidebar has "🏆 Tournament Manager" button
    A2 — Admin clicks button → Tournament Manager page loads
    I1 — Instructor sidebar has "🏆 Tournament Manager" button
    I2 — Instructor clicks button → Tournament Manager page loads
    L1 — Legacy "📡 Tournament Monitor" button is absent from admin sidebar

Run (all):
    pytest tests_e2e/test_tournament_manager_sidebar_nav.py -v --tb=short

Run (smoke only):
    pytest tests_e2e/test_tournament_manager_sidebar_nav.py -m smoke -v

Run (headed, slow — for debugging):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=800 pytest tests_e2e/test_tournament_manager_sidebar_nav.py -v -s

Credentials:
    Override defaults via environment variables:
        TEST_ADMIN_EMAIL      (default: admin@lfa.com)
        TEST_ADMIN_PASSWORD   (default: admin123)
        TEST_INSTRUCTOR_EMAIL (default: instructor@lfa.com)
        TEST_INSTRUCTOR_PASSWORD (default: instructor123)
"""

import json
import os
import re
import time
import urllib.parse

import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ─────────────────────────────────────────────────────────────────

_ADMIN_EMAIL    = os.environ.get("TEST_ADMIN_EMAIL",       "admin@lfa.com")
_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD",    "admin123")
_INSTR_EMAIL    = os.environ.get("TEST_INSTRUCTOR_EMAIL",  "instructor@lfa.com")
_INSTR_PASSWORD = os.environ.get("TEST_INSTRUCTOR_PASSWORD", "instructor123")

_LOAD_TIMEOUT     = 30_000   # ms — page / navigation loads
_STREAMLIT_SETTLE = 3        # s  — wait after Streamlit reruns/switch_page

# ── Auth helpers ───────────────────────────────────────────────────────────────

def _api_login(api_url: str, email: str, password: str) -> str:
    """Authenticate via API and return JWT access token."""
    resp = requests.post(
        f"{api_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Login failed for {email}: HTTP {resp.status_code} — {resp.text[:200]}"
    )
    return resp.json()["access_token"]


def _api_user(api_url: str, token: str) -> dict:
    """Fetch /users/me and return the user dict."""
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to fetch user: {resp.text[:200]}"
    return resp.json()


def _inject_auth_url(base_url: str, path: str, token: str, user: dict) -> str:
    """Build a URL with ?token=...&user=... for session restoration."""
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    return f"{base_url}{path}?{params}"


# ── Navigation helpers ─────────────────────────────────────────────────────────

def _sidebar(page: Page):
    """Return the Streamlit sidebar locator."""
    return page.locator("section[data-testid='stSidebar']")


def _go_to_dashboard(page: Page, base_url: str, api_url: str,
                     path: str, email: str, password: str) -> None:
    """Authenticate via API and navigate to *path* with session injected."""
    token = _api_login(api_url, email, password)
    user  = _api_user(api_url, token)
    url   = _inject_auth_url(base_url, path, token, user)
    page.goto(url, timeout=_LOAD_TIMEOUT)
    # Streamlit uses WebSocket — networkidle may not fully settle; use DOMContentLoaded
    page.wait_for_load_state("domcontentloaded", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _click_sidebar_tournament_manager(page: Page) -> None:
    """Click the '🏆 Tournament Manager' button in the sidebar."""
    _sidebar(page).get_by_role(
        "button", name=re.compile("Tournament Manager", re.IGNORECASE)
    ).click()
    time.sleep(_STREAMLIT_SETTLE)


# ── Tests: Admin ───────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.e2e
def test_a1_admin_sidebar_has_tournament_manager_button(page, base_url, api_url):
    """A1 — Admin Dashboard sidebar exposes the '🏆 Tournament Manager' button."""
    _go_to_dashboard(page, base_url, api_url,
                     "/Admin_Dashboard", _ADMIN_EMAIL, _ADMIN_PASSWORD)

    btn = _sidebar(page).get_by_role(
        "button", name=re.compile("Tournament Manager", re.IGNORECASE)
    )
    expect(btn).to_be_visible(timeout=_LOAD_TIMEOUT)


@pytest.mark.smoke
@pytest.mark.e2e
def test_a2_admin_sidebar_tournament_manager_navigates(page, base_url, api_url):
    """A2 — Clicking the Admin sidebar button lands on the Tournament Manager page."""
    _go_to_dashboard(page, base_url, api_url,
                     "/Admin_Dashboard", _ADMIN_EMAIL, _ADMIN_PASSWORD)

    _click_sidebar_tournament_manager(page)

    # st.switch_page() changes the URL to /Tournament_Manager
    expect(page).to_have_url(
        re.compile(r"Tournament_Manager", re.IGNORECASE),
        timeout=_LOAD_TIMEOUT,
    )

    # Page content sanity-check: title or heading should mention Tournament Manager
    body = page.text_content("body") or ""
    assert "Tournament" in body, (
        "Tournament Manager page loaded but expected content not found in body"
    )


# ── Tests: Instructor ──────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.e2e
def test_i1_instructor_sidebar_has_tournament_manager_button(page, base_url, api_url):
    """I1 — Instructor Dashboard sidebar exposes the '🏆 Tournament Manager' button."""
    _go_to_dashboard(page, base_url, api_url,
                     "/Instructor_Dashboard", _INSTR_EMAIL, _INSTR_PASSWORD)

    btn = _sidebar(page).get_by_role(
        "button", name=re.compile("Tournament Manager", re.IGNORECASE)
    )
    expect(btn).to_be_visible(timeout=_LOAD_TIMEOUT)


@pytest.mark.smoke
@pytest.mark.e2e
def test_i2_instructor_sidebar_tournament_manager_navigates(page, base_url, api_url):
    """I2 — Clicking the Instructor sidebar button lands on the Tournament Manager page."""
    _go_to_dashboard(page, base_url, api_url,
                     "/Instructor_Dashboard", _INSTR_EMAIL, _INSTR_PASSWORD)

    _click_sidebar_tournament_manager(page)

    expect(page).to_have_url(
        re.compile(r"Tournament_Manager", re.IGNORECASE),
        timeout=_LOAD_TIMEOUT,
    )

    body = page.text_content("body") or ""
    assert "Tournament" in body, (
        "Tournament Manager page loaded but expected content not found in body"
    )


# ── Tests: Legacy guard ────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.e2e
def test_l1_admin_sidebar_no_legacy_monitor_button(page, base_url, api_url):
    """L1 — Admin sidebar no longer has the legacy '📡 Tournament Monitor' button.

    The button was removed when Tournament_Monitor.py was archived.
    If this test fails, a broken st.switch_page() call was re-introduced.
    """
    _go_to_dashboard(page, base_url, api_url,
                     "/Admin_Dashboard", _ADMIN_EMAIL, _ADMIN_PASSWORD)

    legacy_btn = _sidebar(page).get_by_role(
        "button", name=re.compile("Tournament Monitor", re.IGNORECASE)
    )
    # Must NOT exist — count() should be 0
    assert legacy_btn.count() == 0, (
        "Legacy '📡 Tournament Monitor' button is still present in the admin sidebar. "
        "This points to a broken st.switch_page('pages/Tournament_Monitor.py') call "
        "for a page that has been archived."
    )
