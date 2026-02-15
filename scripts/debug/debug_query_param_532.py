from playwright.sync_api import sync_playwright
import time

def test_query_param():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        tournament_id = 532  # Latest tournament from config0 test
        url = f"http://localhost:8501?tournament_id={tournament_id}"

        print(f"Navigating to: {url}")
        page.goto(url)

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)

        time.sleep(3)
        page.screenshot(path="debug_streamlit_532.png")

        # Check for data-testid elements
        status_exists = page.locator('[data-testid="tournament-status"]').count()
        rankings_exists = page.locator('[data-testid="tournament-rankings"]').count()
        rows_count = page.locator('[data-testid="ranking-row"]').count()
        rewards_exists = page.locator('[data-testid="rewards-summary"]').count()

        print(f"\n--- Checking for data-testid elements ---")
        print(f"tournament-status found: {status_exists}")
        print(f"tournament-rankings found: {rankings_exists}")
        print(f"ranking-row count: {rows_count}")
        print(f"rewards-summary found: {rewards_exists}")

        if rows_count > 0:
            print(f"\n✅ {rows_count} ranking rows found!")
            # Print first row details
            first_row = page.locator('[data-testid="ranking-row"]').first
            rank_attr = first_row.get_attribute('data-rank')
            is_winner_attr = first_row.get_attribute('data-is-winner')
            print(f"   First row rank: {rank_attr}, is_winner: {is_winner_attr}")
        else:
            print(f"\n❌ No ranking rows found")

        browser.close()

if __name__ == "__main__":
    test_query_param()
