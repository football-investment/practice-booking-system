"""
Debug script to identify navigation selectors after login.

Run with: PYTHONPATH=. pytest tests/e2e/debug_navigation.py -v -s --headed --slowmo 1000
"""

import pytest
from playwright.sync_api import Page
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
INSTRUCTOR_EMAIL = os.getenv("TEST_INSTRUCTOR_EMAIL", "instructor@lfa.com")
INSTRUCTOR_PASSWORD = os.getenv("TEST_INSTRUCTOR_PASSWORD", "instructor123")


@pytest.mark.e2e
def test_find_navigation_options(page: Page):
    """
    After login, identify all available navigation options.
    """
    print("\n🔍 Finding navigation options...")

    # Login
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    page.fill("input[aria-label='Email']", INSTRUCTOR_EMAIL)
    page.fill("input[aria-label='Password']", INSTRUCTOR_PASSWORD)
    page.click("button:has-text('Login')")
    page.wait_for_timeout(3000)

    # Take screenshot of logged-in page
    page.screenshot(path="docs/screenshots/debug_after_login.png")
    print("📸 Screenshot saved: debug_after_login.png")

    # Find sidebar
    sidebar = page.locator("[data-testid='stSidebar']")
    if sidebar.count() > 0:
        print("\n✅ Found sidebar")

        # Get all text from sidebar
        sidebar_text = sidebar.text_content()
        print(f"\n📋 Sidebar full text ({len(sidebar_text)} chars):")
        print(sidebar_text)

        # Find all links in sidebar
        links = sidebar.locator("a, button, div[role='button']")
        print(f"\n🔗 Found {links.count()} clickable elements in sidebar:")

        for i in range(links.count()):
            elem = links.nth(i)
            text = elem.text_content() or ""
            href = elem.get_attribute("href") or ""
            role = elem.get_attribute("role") or ""
            aria_label = elem.get_attribute("aria-label") or ""

            if text.strip():  # Only print if has text
                print(f"\nElement {i}:")
                print(f"  - text: '{text}'")
                print(f"  - href: '{href}'")
                print(f"  - role: '{role}'")
                print(f"  - aria-label: '{aria-label}'")

    # Check main content area
    main_content = page.locator("[data-testid='stMain']")
    if main_content.count() > 0:
        print("\n✅ Found main content area")

        # Get headings
        headings = main_content.locator("h1, h2, h3")
        print(f"\n📋 Found {headings.count()} headings in main content:")
        for i in range(min(5, headings.count())):
            print(f"  - {headings.nth(i).text_content()}")

        # Get all buttons
        buttons = main_content.locator("button")
        print(f"\n🔘 Found {buttons.count()} buttons in main content:")
        for i in range(min(10, buttons.count())):
            btn_text = buttons.nth(i).text_content() or ""
            if btn_text.strip():
                print(f"  - '{btn_text}'")

    # Try to find tournament-related text
    print("\n\n🏆 Looking for tournament-related elements:")

    tournament_text_elements = page.locator("text=/tournament/i")
    print(f"Found {tournament_text_elements.count()} elements containing 'tournament'")

    for i in range(min(5, tournament_text_elements.count())):
        elem = tournament_text_elements.nth(i)
        print(f"  - '{elem.text_content()}'")

    # Look for session-related text
    print("\n\n📅 Looking for session-related elements:")

    session_text_elements = page.locator("text=/session/i")
    print(f"Found {session_text_elements.count()} elements containing 'session'")

    for i in range(min(5, session_text_elements.count())):
        elem = session_text_elements.nth(i)
        print(f"  - '{elem.text_content()}'")

    # Check for expandable sections
    print("\n\n📂 Looking for expandable sections:")

    expanders = page.locator("[data-testid='stExpander']")
    print(f"Found {expanders.count()} expanders")

    for i in range(expanders.count()):
        expander = expanders.nth(i)
        print(f"\nExpander {i}:")
        print(f"  - text: '{expander.text_content()[:100]}'")

        # Try to expand it
        try:
            expander.click()
            page.wait_for_timeout(500)

            # See what's inside
            page.screenshot(path=f"docs/screenshots/debug_expander_{i}.png")
            print(f"  - Screenshot: debug_expander_{i}.png")
        except:
            pass

    print("\n\n✅ Navigation debug complete")
