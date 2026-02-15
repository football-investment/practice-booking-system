from playwright.sync_api import sync_playwright
import time

def test_query_param():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        tournament_id = 530  # Valid tournament from config0 test
        url = f"http://localhost:8501?tournament_id={tournament_id}"

        print(f"Navigating to: {url}")
        page.goto(url)

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)

        time.sleep(3)
        page.screenshot(path="debug_streamlit_530.png")

        # Check for data-testid elements
        status_exists = page.locator('[data-testid="tournament-status"]').count()
        rankings_exists = page.locator('[data-testid="tournament-rankings"]').count()
        rewards_exists = page.locator('[data-testid="rewards-summary"]').count()

        print(f"\n--- Checking for data-testid elements ---")
        print(f"tournament-status found: {status_exists}")
        print(f"tournament-rankings found: {rankings_exists}")
        print(f"rewards-summary found: {rewards_exists}")

        print(f"\nPage title: {page.title()}")

        if status_exists > 0:
            print(f"\n✅ tournament-status FOUND in HTML!")
            status_elem = page.locator('[data-testid="tournament-status"]')
            status_value = status_elem.get_attribute('data-status')
            print(f"   data-status value: {status_value}")
        else:
            print(f"\n❌ tournament-status NOT in HTML")

        # Print first 500 chars of body HTML
        html = page.content()
        print(f"\nFirst 500 chars of HTML:\n{html[:500]}")

        browser.close()

if __name__ == "__main__":
    test_query_param()
