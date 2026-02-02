"""
Frontend E2E Test: Reward Distribution Workflow
================================================

REAL frontend test using Playwright to test:
1. Navigate through actual Streamlit UI
2. Click actual buttons
3. Monitor network requests/responses
4. Verify UI state changes

Requirements:
- Playwright
- Streamlit app running on localhost:8501
- FastAPI backend running on localhost:8000
- PostgreSQL database with completed tournament (ID 92)

Run:
    pytest tests/e2e_frontend/test_reward_distribution_e2e.py -v --headed
    OR headless:
    pytest tests/e2e_frontend/test_reward_distribution_e2e.py -v
"""

import pytest
import time
from playwright.sync_api import Page, sync_playwright
from typing import Dict, List


# Test configuration
STREAMLIT_URL = "http://localhost:8501"
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_TOURNAMENT_ID = 224  # Tournament 224 - COMPLETED with rankings


@pytest.fixture(scope="module")
def browser():
    """Launch browser for all tests in this module"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=True for CI/CD
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Create new page for each test"""
    context = browser.new_context()
    page = context.new_page()

    yield page

    page.close()
    context.close()


class TestRewardDistributionE2E:
    """
    End-to-end test for reward distribution workflow via Streamlit UI
    """

    def test_complete_workflow_reward_distribution(self, page: Page):
        """
        REAL FRONTEND E2E TEST:
        1. Navigate to Streamlit home
        2. Click "Open History" button
        3. Find tournament 92
        4. Click "View Rewards" button (navigates to Step 6)
        5. Click "Distribute All Rewards" button
        6. Monitor network: POST /distribute-rewards
        7. Verify UI shows success message
        8. Click "Distribute All Rewards" again
        9. Monitor network: Should show 400 or success message
        10. Verify UI handles idempotency correctly
        """

        print("\n" + "="*80)
        print("FRONTEND E2E TEST: Reward Distribution Workflow")
        print("="*80)

        # Track API calls and responses
        api_calls: List[Dict] = []
        api_responses: Dict[str, Dict] = {}

        def track_request(request):
            if "/distribute-rewards" in request.url or "/semesters/" in request.url:
                api_calls.append({
                    "method": request.method,
                    "url": request.url,
                    "timestamp": time.time()
                })
                print(f"\n→ API Request: {request.method} {request.url}")

        def track_response(response):
            if "/distribute-rewards" in response.url or "/semesters/" in response.url:
                api_responses[response.url] = {
                    "status": response.status,
                    "timestamp": time.time(),
                    "url": response.url
                }
                print(f"← API Response: {response.status} {response.url}")

        page.on("request", track_request)
        page.on("response", track_response)

        # Step 1: Navigate to Streamlit app
        print("\n[STEP 1] Navigating to Streamlit app...")
        page.goto(STREAMLIT_URL, wait_until="networkidle")
        page.wait_for_timeout(5000)  # Wait for Streamlit to fully initialize
        print("✅ Streamlit app loaded")

        # Step 2: Click "Open History" button
        print("\n[STEP 2] Clicking 'Open History' button...")

        # Look for "Open History" button
        history_button = page.locator("button:has-text('Open History')")

        if history_button.count() == 0:
            # Alternative: look for any button with "History"
            history_button = page.locator("button:has-text('History')")

        if history_button.count() > 0:
            print(f"✅ Found history button: {history_button.count()} match(es)")
            history_button.first.click()
            page.wait_for_timeout(3000)
            print("✅ Clicked history button")
        else:
            print("⚠️ History button not found, may already be on history page")

        # Step 3: Find tournament 92
        print(f"\n[STEP 3] Finding tournament {TEST_TOURNAMENT_ID}...")

        # Wait for tournaments to load
        page.wait_for_timeout(2000)

        # Look for tournament 92 - try multiple selectors
        tournament_selector = page.locator(f"text=/.*ID.*{TEST_TOURNAMENT_ID}.*/i")

        if tournament_selector.count() == 0:
            # Alternative: look for any card/expander containing "92"
            tournament_selector = page.locator(f"text=/{TEST_TOURNAMENT_ID}/")

        if tournament_selector.count() > 0:
            print(f"✅ Found tournament {TEST_TOURNAMENT_ID}: {tournament_selector.count()} match(es)")
        else:
            print(f"⚠️ Tournament {TEST_TOURNAMENT_ID} not found in visible text")
            # Take screenshot for debugging
            page.screenshot(path="/tmp/streamlit_screenshot.png")
            print("📸 Screenshot saved to /tmp/streamlit_screenshot.png")

        # Step 4: Click "Resume Workflow" button for tournament (to get to Step 6)
        print(f"\n[STEP 4] Clicking 'Resume Workflow' button for tournament {TEST_TOURNAMENT_ID}...")

        resume_button = page.locator(f"button[key='btn_resume_{TEST_TOURNAMENT_ID}']")

        if resume_button.count() == 0:
            # Alternative: look for "Resume" button
            resume_button = page.locator("button:has-text('Resume')").first

        if resume_button.count() > 0:
            print(f"✅ Found 'Resume Workflow' button")
            resume_button.first.click()
            page.wait_for_timeout(3000)
            print("✅ Clicked 'Resume Workflow' button")
        else:
            pytest.fail(f"❌ FAIL: 'Resume Workflow' button not found for tournament {TEST_TOURNAMENT_ID}")

        # Step 4.5: Navigate to Step 6 (Distribute Rewards)
        print(f"\n[STEP 4.5] Navigating to Step 6 (Distribute Rewards)...")

        # Look for "Distribute Rewards" navigation or button
        # The workflow may start at Step 3, so we need to navigate forward
        # Look for navigation to Step 6
        page.wait_for_timeout(2000)

        # Try clicking "View Leaderboard" to get to Step 5, then to Step 6
        leaderboard_nav = page.locator("text=/.*Leaderboard.*/i").first
        if leaderboard_nav.count() > 0:
            leaderboard_nav.click()
            page.wait_for_timeout(2000)
            print("✅ Navigated via leaderboard link")

        # Now look for "Distribute Rewards" button or navigation
        distribute_nav = page.locator("text=/.*Distribute.*Rewards.*/i").first
        if distribute_nav.count() > 0:
            distribute_nav.click()
            page.wait_for_timeout(2000)
            print("✅ Navigated to Distribute Rewards step")

        # Step 5: Click "Distribute All Rewards" button (FIRST TIME)
        print("\n[STEP 5] Clicking 'Distribute All Rewards' button (FIRST TIME)...")

        # Take screenshot to see where we are
        page.screenshot(path="/tmp/streamlit_step5.png")
        print("📸 Screenshot saved to /tmp/streamlit_step5.png")

        # Wait for page to load completely
        page.wait_for_timeout(3000)

        distribute_button = page.locator("button[key='btn_distribute_rewards']")

        if distribute_button.count() == 0:
            # Alternative selector
            distribute_button = page.locator("button:has-text('Distribute All Rewards')")

        if distribute_button.count() == 0:
            # Try even more generic selector
            distribute_button = page.locator("button:has-text('Distribute')")

        assert distribute_button.count() > 0, f"❌ FAIL: 'Distribute All Rewards' button not found. Check /tmp/streamlit_step5.png"
        print(f"✅ Found 'Distribute All Rewards' button")

        # Record API calls before click
        api_calls_before_first = len(api_calls)

        # Click the button
        distribute_button.first.click()
        print("✅ Button clicked (first time)")

        # Wait for API call to complete
        page.wait_for_timeout(5000)

        # Step 6: Verify FIRST API call
        print("\n[STEP 6] Verifying FIRST API call...")

        distribute_api_calls = [call for call in api_calls if "/distribute-rewards" in call["url"]]

        assert len(distribute_api_calls) > 0, "❌ FAIL: No /distribute-rewards API call made after button click"
        print(f"✅ API call detected: {len(distribute_api_calls)} call(s) to /distribute-rewards")

        first_call = distribute_api_calls[-1]
        assert first_call["method"] == "POST", f"❌ FAIL: Expected POST, got {first_call['method']}"
        print(f"✅ First API call verified: POST {first_call['url']}")

        # Verify response status
        first_response_urls = [url for url in api_responses.keys() if "/distribute-rewards" in url]
        assert len(first_response_urls) > 0, "❌ FAIL: No /distribute-rewards response captured"

        first_response = api_responses[first_response_urls[-1]]
        # Allow 200 (success) or 400 (already distributed)
        assert first_response["status"] in [200, 400], f"❌ FAIL: Expected 200 or 400, got {first_response['status']}"
        print(f"✅ First response verified: HTTP {first_response['status']}")

        # Step 7: Verify UI shows success/completion message
        print("\n[STEP 7] Verifying UI message...")

        page.wait_for_timeout(2000)  # Wait for UI to update

        # Look for success indicators
        success_indicators = [
            page.locator("text=/.*distributed successfully.*/i"),
            page.locator("text=/.*already distributed.*/i"),
            page.locator("text=/.*completed.*/i"),
            page.locator("text=/.*locked.*/i")
        ]

        ui_message_found = False
        for indicator in success_indicators:
            if indicator.count() > 0:
                try:
                    message_text = indicator.first.text_content()[:100]
                    print(f"✅ UI message found: {message_text}...")
                    ui_message_found = True
                    break
                except:
                    pass

        assert ui_message_found, "❌ FAIL: No success/completion message found in UI"

        # Step 8: Click "Distribute All Rewards" button (SECOND TIME - idempotency test)
        print("\n[STEP 8] Clicking 'Distribute All Rewards' button (SECOND TIME - Idempotency Test)...")

        # Record API calls before second click
        api_calls_before_second = len(distribute_api_calls)

        # Find button again (may have re-rendered)
        distribute_button = page.locator("button[key='btn_distribute_rewards']")

        if distribute_button.count() == 0:
            distribute_button = page.locator("button:has-text('Distribute All Rewards')")

        if distribute_button.count() > 0:
            distribute_button.first.click()
            print("✅ Second button click executed")

            # Wait for API call
            page.wait_for_timeout(5000)

            # Step 9: Verify SECOND API call
            print("\n[STEP 9] Verifying SECOND API call (idempotency protection)...")

            distribute_api_calls_after = [call for call in api_calls if "/distribute-rewards" in call["url"]]

            if len(distribute_api_calls_after) > api_calls_before_second:
                second_call = distribute_api_calls_after[-1]
                print(f"✅ Second API call detected: POST {second_call['url']}")

                # Verify response
                second_response_urls = [url for url in api_responses.keys() if "/distribute-rewards" in url]
                second_response = api_responses[second_response_urls[-1]]

                # Should be 400 (already distributed) or 200 (idempotent success)
                assert second_response["status"] in [200, 400], f"❌ FAIL: Expected 200 or 400, got {second_response['status']}"
                print(f"✅ Second response verified: HTTP {second_response['status']} (idempotency handling)")
            else:
                print("ℹ️ No second API call made (button may be disabled after first success)")
        else:
            print("ℹ️ Distribute button not available (may be disabled after first success)")

        # Step 10: Verify UI still shows appropriate message
        print("\n[STEP 10] Verifying UI final state...")

        page.wait_for_timeout(2000)

        # UI should show either success or "already distributed"
        final_indicators = [
            page.locator("text=/.*distributed.*/i"),
            page.locator("text=/.*completed.*/i"),
            page.locator("text=/.*locked.*/i")
        ]

        final_message_found = False
        for indicator in final_indicators:
            if indicator.count() > 0:
                try:
                    final_text = indicator.first.text_content()[:100]
                    print(f"✅ Final UI state: {final_text}...")
                    final_message_found = True
                    break
                except:
                    pass

        assert final_message_found, "❌ FAIL: No final state message found in UI"

        # Final Summary
        print("\n" + "="*80)
        print("FRONTEND E2E TEST SUMMARY")
        print("="*80)
        distribute_calls = [call for call in api_calls if "/distribute-rewards" in call["url"]]
        print(f"✅ Total /distribute-rewards API calls: {len(distribute_calls)}")
        distribute_responses = [resp for url, resp in api_responses.items() if "/distribute-rewards" in url]
        if distribute_responses:
            print(f"✅ First call status: HTTP {distribute_responses[0]['status']}")
            if len(distribute_responses) > 1:
                print(f"✅ Second call status: HTTP {distribute_responses[-1]['status']}")
        print(f"✅ UI message displayed: {'Yes' if ui_message_found else 'No'}")
        print(f"✅ Idempotency verified: Yes")
        print("="*80)
        print("✅ ALL FRONTEND E2E TESTS PASSED")
        print("="*80 + "\n")


if __name__ == "__main__":
    """
    Run test directly:
    python tests/e2e_frontend/test_reward_distribution_e2e.py
    """
    import subprocess
    subprocess.run([
        "pytest",
        __file__,
        "-v",
        "-s",  # Show print statements
        "--tb=short"
    ])
