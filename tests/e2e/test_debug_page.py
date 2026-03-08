"""
Debug test to see what's on the page
"""
import time
from playwright.sync_api import Page


def test_debug_page(page: Page):
    """Debug: Take screenshot and dump HTML"""
    page.goto("http://localhost:8501/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Take screenshot
    page.screenshot(path="tests_e2e/screenshots/debug_initial_page.png", full_page=True)
    print("✓ Screenshot saved")

    # Dump HTML
    html = page.content()
    with open("tests_e2e/debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ HTML saved")

    # Print visible text
    body_text = page.locator("body").inner_text()
    print("\n=== VISIBLE TEXT ===")
    print(body_text[:2000])
