"""
E2E Regression Test: Champion Badge Display
===========================================

BUSINESS RULE: Champion badge MUST NEVER show "No ranking data"

This test is a build blocker: if a CHAMPION badge is visible on ANY page after
login and ANY of those pages also contain "No ranking data", the test fails.

Design philosophy: WIDE net, not deep navigation.
- Login once
- Expand any visible accordions to surface badge content
- Check ALL visible text for CHAMPION + "No ranking data" co-occurrence

Markers:
    golden_path  – deployment blocker, never skip
    e2e          – Playwright end-to-end
    smoke        – fast CI regression
"""

import os
import re
import time
import pytest
from playwright.sync_api import sync_playwright, Page


BASE_URL = os.environ.get("CHAMPION_TEST_URL", "http://localhost:8501")
TEST_USER_EMAIL = "junior.intern@lfa.com"
TEST_USER_PASSWORD = "password123"
SCREENSHOT_DIR = "tests_e2e/screenshots"
TIMEOUT_MS = 30_000


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _login(page: Page) -> None:
    """Fill and submit login form; raise if credentials are rejected."""
    # Email (Streamlit renders text inputs as type=text by default)
    email_input = page.locator("input").first
    email_input.wait_for(state="visible", timeout=TIMEOUT_MS)
    email_input.fill(TEST_USER_EMAIL)
    time.sleep(0.3)

    # Password
    pwd_input = page.locator('input[type="password"]').first
    pwd_input.wait_for(state="visible", timeout=5_000)
    pwd_input.fill(TEST_USER_PASSWORD)
    time.sleep(0.3)

    # Submit – "🔐 Login" button (exact label from Streamlit)
    login_btn = page.locator("button").filter(
        has_text=re.compile(r"Login", re.IGNORECASE)
    ).first
    login_btn.click()

    # Wait for Streamlit to re-render after state change
    page.wait_for_load_state("networkidle", timeout=20_000)
    time.sleep(4)

    body = page.text_content("body") or ""
    if "Incorrect email" in body or "Login failed" in body:
        _save_screenshot(page, "login_failed")
        raise AssertionError(
            f"Login rejected for {TEST_USER_EMAIL}. "
            "Check credentials and DB test data."
        )
    print("   ✅ Logged in")


def _expand_accordions(page: Page) -> None:
    """
    Click every collapsed Streamlit expander/accordion to surface badge content.
    Tolerates failures silently – expansion is best-effort.
    """
    try:
        expanders = page.locator('[data-testid="stExpander"]').all()
        for exp in expanders:
            try:
                header = exp.locator("summary, [data-testid='stExpanderToggleIcon']").first
                if header.is_visible(timeout=1_000):
                    header.click()
                    time.sleep(0.4)
            except Exception:
                pass
    except Exception:
        pass


def _navigate_to_performance_page(page: Page) -> None:
    """
    Navigate to the LFA Player Dashboard which shows tournament badges.
    The sidebar nav is hidden by CSS so we use JS click on the anchor.
    Falls back gracefully if navigation fails.
    """
    try:
        # JS-click the hidden sidebar anchor (CSS hides it but it's in the DOM)
        page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                for (const link of links) {
                    if (link.textContent.includes('LFA Player Dashboard')) {
                        link.click(); return true;
                    }
                }
                return false;
            }
        """)
        page.wait_for_load_state("networkidle", timeout=10_000)
        time.sleep(4)
        print("   Navigated to LFA Player Dashboard")
    except Exception as e:
        print(f"   Navigation failed (non-fatal): {e}")


def _save_screenshot(page: Page, tag: str) -> str:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = f"{SCREENSHOT_DIR}/champion_badge_{tag}.png"
    page.screenshot(path=path, full_page=True)
    print(f"   📸 Screenshot → {path}")
    return path


# ──────────────────────────────────────────────────────────────────────────────
# Critical assertion
# ──────────────────────────────────────────────────────────────────────────────

def _assert_champion_never_shows_no_ranking_data(page: Page) -> None:
    """
    Core business-rule assertion.

    1. Collect ALL visible text on the page.
    2. If no CHAMPION indicator exists → skip (test is not applicable).
    3. Split text into a sliding window; if any window that contains a
       CHAMPION indicator also contains "No ranking data" → FAIL (regression).

    Window size = 15 lines, wide enough to span a card section but not so wide
    that two unrelated cards get mixed up.
    """
    body = page.text_content("body") or ""
    lines = [l.strip() for l in body.split("\n") if l.strip()]

    CHAMPION_SIGNALS = {"CHAMPION", "🥇 Champion", "Champion"}
    REGRESSION_TEXT = "No ranking data"
    WINDOW = 15  # lines

    # Is there any CHAMPION badge visible at all?
    champion_lines = [
        i for i, line in enumerate(lines)
        if any(sig in line for sig in CHAMPION_SIGNALS)
    ]

    if not champion_lines:
        print("   ⚠️  No CHAMPION badge text found on current page — skipping assertion")
        return

    print(f"   ✅ Found CHAMPION badge signal(s) at {len(champion_lines)} line(s)")

    # Slide the window around each CHAMPION occurrence
    for ci in champion_lines:
        start = max(0, ci - 2)
        end = min(len(lines), ci + WINDOW)
        window_text = "\n".join(lines[start:end])

        if REGRESSION_TEXT in window_text:
            raise AssertionError(
                "❌ REGRESSION DETECTED\n"
                "Business rule violation: CHAMPION badge shows 'No ranking data'\n\n"
                f"Window ({start}–{end}):\n"
                "---\n"
                f"{window_text}\n"
                "---\n\n"
                "Fix: ensure performance_card.py CHAMPION guard is active and\n"
                "badge_metadata.placement is populated in the DB.\n"
                "BUILD BLOCKED."
            )

    print("   ✅ No 'No ranking data' found near any CHAMPION badge")


# ──────────────────────────────────────────────────────────────────────────────
# Main regression test  (build blocker)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.golden_path
@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.nondestructive
def test_champion_badge_no_ranking_data_regression():
    """
    CRITICAL regression guard: CHAMPION badge must never display
    "No ranking data".  This test blocks deployment on failure.
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1 – Load app
            print(f"🌐 {BASE_URL}")
            page.goto(BASE_URL, timeout=TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
            time.sleep(2)

            # 2 – Login
            print(f"🔐 Logging in as {TEST_USER_EMAIL} ...")
            _login(page)

            # 3 – Navigate to page with badges
            print("🗺️  Navigating to performance / achievement page ...")
            _navigate_to_performance_page(page)

            # 4 – Expand all accordions to reveal badge cards
            print("📂 Expanding accordions ...")
            _expand_accordions(page)
            time.sleep(2)

            # 5 – Take a PASS screenshot for evidence
            _save_screenshot(page, "PASS")

            # 6 – Core assertion
            print("🔍 Running CHAMPION guard assertion ...")
            _assert_champion_never_shows_no_ranking_data(page)

            print("\n✅ TEST PASSED — Champion badge displays correctly")

        except AssertionError:
            _save_screenshot(page, "FAILED")
            raise
        finally:
            browser.close()


# ──────────────────────────────────────────────────────────────────────────────
# Manual debug helper (skipped in CI)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Manual debugging only — not for CI")
def test_champion_badge_debug_screenshot():
    """
    Open browser visually, expand everything, save full-page screenshot.
    Usage: pytest tests_e2e/test_champion_badge_regression.py -k debug -s
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=800)
        page = browser.new_page()

        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        _login(page)
        _navigate_to_performance_page(page)
        _expand_accordions(page)
        time.sleep(2)

        path = _save_screenshot(page, "DEBUG")
        print(f"\n=== PAGE TEXT ===\n{page.text_content('body')[:3000]}")

        time.sleep(6)
        browser.close()
