"""
Debug test to see configuration screen
"""
import re
import time
from playwright.sync_api import Page


def test_debug_config_screen(page: Page):
    """Debug: Screenshot after clicking New Tournament"""
    page.goto("http://localhost:8501/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Click New Tournament
    new_tournament_button = page.get_by_role("button", name=re.compile(r"New Tournament", re.IGNORECASE))
    new_tournament_button.click()
    time.sleep(3)

    # Take screenshot
    page.screenshot(path="tests_e2e/screenshots/debug_config_screen.png", full_page=True)
    print("✓ Screenshot saved")

    # Dump HTML
    html = page.content()
    with open("tests_e2e/debug_config_screen.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ HTML saved")

    # Print visible text
    body_text = page.locator("body").inner_text()
    print("\n=== VISIBLE TEXT ===")
    print(body_text[:3000])
