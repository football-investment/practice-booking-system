"""
Demo: Player Login Test - Headed Firefox Mode

This test demonstrates a fully onboarded player logging in.
Perfect for presenting to a friend!
"""

import pytest
from playwright.sync_api import Page
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

# Fully onboarded player (set up via scripts/setup_demo_player.py)
PLAYER_EMAIL = "pwt.p3t1k3@f1stteam.hu"
PLAYER_PASSWORD = "password123"
PLAYER_NAME = "Péter Pataki"


@pytest.mark.e2e
def test_player_login_demo(page: Page):
    """
    Demo test: Player login with fully onboarded user.

    Prerequisites:
    - Run: python scripts/setup_demo_player.py
    - Streamlit running on http://localhost:8501
    - FastAPI running on http://localhost:8000

    Usage:
    pytest tests/e2e/demo_player_login.py --headed --browser firefox -v
    """
    print(f"\n🎮 Demo: Player Login Test")
    print(f"   Player: {PLAYER_EMAIL}")
    print(f"   Name: {PLAYER_NAME}")

    # Navigate to Streamlit
    print(f"\n📍 Navigating to {STREAMLIT_URL}...")
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(3000)

    # Fill credentials
    print(f"\n🔐 Entering credentials...")
    page.fill("input[aria-label='Email']", PLAYER_EMAIL)
    page.wait_for_timeout(500)

    page.fill("input[aria-label='Password']", PLAYER_PASSWORD)
    page.wait_for_timeout(500)

    # Take screenshot before login
    page.screenshot(path="docs/screenshots/demo_player_before_login.png")
    print("📸 Screenshot: Before login")

    # Click login button
    print(f"\n🖱️  Clicking login button...")
    page.click("button:has-text('Login')")
    page.wait_for_timeout(5000)

    # Take screenshot after login
    page.screenshot(path="docs/screenshots/demo_player_after_login.png")
    print("📸 Screenshot: After login")

    # Check for successful login
    print(f"\n🔍 Checking login result...")

    # Check for error messages
    if page.locator("text=Login failed").count() > 0:
        print("❌ LOGIN FAILED!")
        assert False, "Login failed error displayed"

    if page.locator("text=Incorrect").count() > 0:
        print("❌ INCORRECT CREDENTIALS!")
        assert False, "Incorrect credentials error displayed"

    # Look for success indicators
    success_indicators = []

    if page.locator(f"text={PLAYER_NAME}").count() > 0:
        print(f"✅ Found player name: {PLAYER_NAME}")
        success_indicators.append("name")

    if page.locator("text=Dashboard").count() > 0:
        print("✅ Found 'Dashboard' text")
        success_indicators.append("dashboard")

    if page.locator("text=Player").count() > 0:
        print("✅ Found 'Player' text")
        success_indicators.append("player")

    if page.locator("text=Football").count() > 0:
        print("✅ Found 'Football' text")
        success_indicators.append("football")

    # Print current URL
    print(f"\n🌐 Current URL: {page.url}")

    # Verify at least one success indicator
    assert len(success_indicators) > 0, \
        "Login appears to have failed - no success indicators found"

    print(f"\n✅ LOGIN SUCCESSFUL!")
    print(f"   Success indicators: {', '.join(success_indicators)}")

    # Keep browser open for 5 seconds to allow manual inspection
    print(f"\n⏱️  Keeping browser open for 5 seconds...")
    page.wait_for_timeout(5000)

    print(f"\n🎉 Demo complete!")
