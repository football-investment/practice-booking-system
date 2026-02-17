"""
Instructor Dashboard — Tab-Level Smoke Tests (Headless Playwright)
==================================================================

Prerequisite for Phase 3 modularization (ARCHITECTURE.md §Phase 3).
Each extraction step requires the corresponding tab test to be green BEFORE
the tab is extracted to a component module.

Coverage:
    T1 — Today & Upcoming tab renders (no error, expected heading present)
    T2 — My Jobs tab renders
    T3 — Tournament Applications tab renders (MCC sub-tab shows redirect)
    T4 — My Students tab renders
    T5 — Check-in & Groups tab renders
    T6 — Inbox tab renders
    T7 — My Profile tab renders
    S1 — Sidebar: Tournament Manager button visible
    S2 — Sidebar: Refresh button visible
    S3 — Sidebar: Logout button visible

Auth strategy: URL-param injection via restore_session_from_url().
No UI login interaction required.

Run:
    pytest tests_e2e/test_instructor_dashboard_tab_smoke.py -v --tb=short
    pytest tests_e2e/test_instructor_dashboard_tab_smoke.py -m smoke -v

Credentials:
    TEST_INSTRUCTOR_EMAIL    (default: instructor@lfa.com)
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

_INSTR_EMAIL    = os.environ.get("TEST_INSTRUCTOR_EMAIL",    "instructor@lfa.com")
_INSTR_PASSWORD = os.environ.get("TEST_INSTRUCTOR_PASSWORD", "instructor123")

_LOAD_TIMEOUT     = 30_000   # ms
_STREAMLIT_SETTLE = 3        # s — after page load / tab click


# ── Auth + navigation helpers ─────────────────────────────────────────────────

def _api_login(api_url: str, email: str, password: str) -> str:
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
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to fetch user: {resp.text[:200]}"
    return resp.json()


def _load_instructor_dashboard(page: Page, base_url: str, api_url: str) -> None:
    """Navigate to Instructor Dashboard with session injected via URL params."""
    token = _api_login(api_url, _INSTR_EMAIL, _INSTR_PASSWORD)
    user  = _api_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})
    url = f"{base_url}/Instructor_Dashboard?{params}"
    page.goto(url, timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("domcontentloaded", timeout=_LOAD_TIMEOUT)
    time.sleep(_STREAMLIT_SETTLE)


def _click_tab(page: Page, tab_name: str) -> None:
    """Click a top-level dashboard tab by its text label."""
    page.get_by_role("tab", name=re.compile(re.escape(tab_name), re.IGNORECASE)).click()
    time.sleep(_STREAMLIT_SETTLE)


def _no_error_in_body(page: Page) -> None:
    """Assert no Streamlit error widget is visible."""
    # Streamlit renders errors inside [data-testid="stAlert"] with kind=error
    error_els = page.locator('[data-testid="stAlert"][kind="error"]')
    assert error_els.count() == 0, (
        f"Error widget found on tab. First message: "
        f"{error_els.first.text_content() if error_els.count() > 0 else 'N/A'}"
    )


# ── Session-scoped dashboard fixture ──────────────────────────────────────────
#
# We use a module-scoped browser + a fresh page per test to keep test isolation
# while avoiding repeated browser launches.  The `page` fixture from conftest.py
# is function-scoped (new page, new browser per test), which is safe but slow
# for a tab-smoke suite.  We override it here at module scope.

@pytest.fixture(scope="module")
def _browser_mod(browser_config):
    """Module-scoped browser for the tab smoke suite."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        bt = getattr(p, browser_config["browser_type"])
        b = bt.launch(
            headless=browser_config["headless"],
            slow_mo=browser_config["slow_mo"],
        )
        yield b
        b.close()


@pytest.fixture(scope="module")
def _dashboard_page(_browser_mod, base_url, api_url):
    """
    Single Instructor Dashboard page loaded once for the whole module.

    Individual tab tests click tabs on this shared page — they do NOT navigate
    away, so test isolation is maintained within the same Streamlit app state.
    """
    p = _browser_mod.new_page()
    _load_instructor_dashboard(p, base_url, api_url)
    yield p
    p.close()


# ── Tab smoke tests ───────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.e2e
def test_t1_today_upcoming_tab(_dashboard_page):
    """T1 — 'Today & Upcoming' tab renders without error."""
    _click_tab(_dashboard_page, "Today & Upcoming")
    _no_error_in_body(_dashboard_page)
    # Expected heading present
    body = _dashboard_page.text_content("body") or ""
    assert "Today" in body or "Upcoming" in body, (
        "Tab T1: expected 'Today' or 'Upcoming' content not found"
    )


@pytest.mark.smoke
@pytest.mark.e2e
def test_t2_my_jobs_tab(_dashboard_page):
    """T2 — 'My Jobs' tab renders without error."""
    _click_tab(_dashboard_page, "My Jobs")
    _no_error_in_body(_dashboard_page)
    body = _dashboard_page.text_content("body") or ""
    assert "Jobs" in body or "Completed" in body or "Active" in body, (
        "Tab T2: expected 'My Jobs' content not found"
    )


@pytest.mark.smoke
@pytest.mark.e2e
def test_t3_tournament_applications_tab(_dashboard_page):
    """T3 — 'Tournament Applications' tab renders; MCC sub-tab shows redirect."""
    _click_tab(_dashboard_page, "Tournament Applications")
    _no_error_in_body(_dashboard_page)

    # Sub-tab '⚽ Match Command Center' must show redirect (not inline MCC)
    _dashboard_page.get_by_role(
        "tab", name=re.compile("Match Command Center", re.IGNORECASE)
    ).click()
    time.sleep(_STREAMLIT_SETTLE)

    body = _dashboard_page.text_content("body") or ""
    # The redirect version shows "Tournament Manager" link/button, not inline MCC content
    assert "Tournament Manager" in body, (
        "MCC sub-tab should show Tournament Manager redirect, "
        "but 'Tournament Manager' text not found in body"
    )
    # Ensure it does NOT render the old inline MCC ("Select Active Tournament" selectbox)
    assert "Select Active Tournament" not in body, (
        "Old inline MCC content ('Select Active Tournament') still present — "
        "redirect replacement may have failed"
    )


@pytest.mark.smoke
@pytest.mark.e2e
def test_t4_my_students_tab(_dashboard_page):
    """T4 — 'My Students' tab renders without error."""
    _click_tab(_dashboard_page, "My Students")
    _no_error_in_body(_dashboard_page)
    body = _dashboard_page.text_content("body") or ""
    assert "Student" in body or "Player" in body or "No student" in body.lower(), (
        "Tab T4: expected student list content not found"
    )


@pytest.mark.smoke
@pytest.mark.e2e
def test_t5_checkin_groups_tab(_dashboard_page):
    """T5 — 'Check-in & Groups' tab renders without error."""
    _click_tab(_dashboard_page, "Check-in")
    _no_error_in_body(_dashboard_page)


@pytest.mark.smoke
@pytest.mark.e2e
def test_t6_inbox_tab(_dashboard_page):
    """T6 — 'Inbox' tab renders without error."""
    _click_tab(_dashboard_page, "Inbox")
    _no_error_in_body(_dashboard_page)


@pytest.mark.smoke
@pytest.mark.e2e
def test_t7_my_profile_tab(_dashboard_page):
    """T7 — 'My Profile' tab renders without error."""
    _click_tab(_dashboard_page, "My Profile")
    _no_error_in_body(_dashboard_page)
    body = _dashboard_page.text_content("body") or ""
    assert "Profile" in body or "Email" in body, (
        "Tab T7: expected profile content not found"
    )


# ── Sidebar presence tests ─────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.e2e
def test_s1_sidebar_tournament_manager_button(_dashboard_page):
    """S1 — Sidebar '🏆 Tournament Manager' button is present."""
    sidebar = _dashboard_page.locator("section[data-testid='stSidebar']")
    btn = sidebar.get_by_role(
        "button", name=re.compile("Tournament Manager", re.IGNORECASE)
    )
    expect(btn).to_be_visible(timeout=_LOAD_TIMEOUT)


@pytest.mark.smoke
@pytest.mark.e2e
def test_s2_sidebar_refresh_button(_dashboard_page):
    """S2 — Sidebar 'Refresh' button is present."""
    sidebar = _dashboard_page.locator("section[data-testid='stSidebar']")
    btn = sidebar.get_by_role("button", name=re.compile("Refresh", re.IGNORECASE))
    expect(btn).to_be_visible(timeout=_LOAD_TIMEOUT)


@pytest.mark.smoke
@pytest.mark.e2e
def test_s3_sidebar_logout_button(_dashboard_page):
    """S3 — Sidebar 'Logout' button is present."""
    sidebar = _dashboard_page.locator("section[data-testid='stSidebar']")
    btn = sidebar.get_by_role("button", name=re.compile("Logout", re.IGNORECASE))
    expect(btn).to_be_visible(timeout=_LOAD_TIMEOUT)
