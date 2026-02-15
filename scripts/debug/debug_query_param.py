"""
Debug script to test query parameter navigation
"""
from playwright.sync_api import sync_playwright
import time

def test_query_param():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Headless for automated debug
        page = browser.new_page()

        tournament_id = 529  # From last test
        url = f"http://localhost:8501?tournament_id={tournament_id}"

        print(f"Navigating to: {url}")
        page.goto(url)

        # Wait for Streamlit to load
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)

        # Wait a bit for auto-navigation
        time.sleep(3)

        # Take screenshot
        page.screenshot(path="debug_streamlit.png")
        print("Screenshot saved: debug_streamlit.png")

        # Check for data-testid elements
        print("\n--- Checking for data-testid elements ---")

        status_exists = page.locator('[data-testid="tournament-status"]').count()
        print(f"tournament-status found: {status_exists}")

        rankings_exists = page.locator('[data-testid="tournament-rankings"]').count()
        print(f"tournament-rankings found: {rankings_exists}")

        rewards_exists = page.locator('[data-testid="rewards-summary"]').count()
        print(f"rewards-summary found: {rewards_exists}")

        # Print page title
        print(f"\nPage title: {page.title()}")

        # Print HTML snippet
        html_content = page.content()
        if "tournament-status" in html_content:
            print("\n✅ tournament-status found in HTML!")
        else:
            print("\n❌ tournament-status NOT in HTML")
            print(f"\nFirst 500 chars of HTML:\n{html_content[:500]}")

        browser.close()

if __name__ == "__main__":
    test_query_param()
