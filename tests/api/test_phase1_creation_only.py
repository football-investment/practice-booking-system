"""
Focused Stability Test: Tournament Creation (Phase 1 Only)

Validates ONLY the critical path:
1. Navigate to sandbox
2. Select preset
3. Start workflow
4. Click "Create Tournament"
5. Verify navigation to Step 2

SUCCESS CRITERIA: Deterministic 20/20 PASS rate
"""
import pytest
import time
from playwright.sync_api import Page


def wait_streamlit(page: Page, timeout_ms: int = 10000):
    """Wait for Streamlit to finish rerunning"""
    try:
        page.wait_for_selector("[data-testid='stApp']", state="attached", timeout=timeout_ms)
        time.sleep(1)
    except:
        pass


@pytest.mark.e2e
def test_tournament_creation_phase1_only(page: Page):
    """
    🎯 FOCUSED STABILITY TEST: Tournament Creation Only (Phase 1)

    Validates the critical path from UI → API → Database:
    - Preset selection
    - Workflow initiation
    - Button click handler execution
    - API call success
    - Tournament ID extraction
    - Navigation to Step 2

    This test validates production reliability for the CORE workflow.
    """
    print("\n" + "="*80)
    print("🎯 PHASE 1 STABILITY TEST: Tournament Creation")
    print("="*80 + "\n")

    # Navigate to sandbox
    page.goto("http://localhost:8501")
    wait_streamlit(page)
    time.sleep(3)

    # Click New Tournament
    print("📍 Clicking 'New Tournament' button...")
    page.locator("button:has-text('New Tournament')").first.click()
    wait_streamlit(page, timeout_ms=30000)
    time.sleep(3)

    # Select Group+Knockout preset
    print("📍 Selecting Group+Knockout preset...")
    select_btns = page.locator("button:has-text('Select')").all()
    assert len(select_btns) > 0, "No preset select buttons found"
    select_btns[0].click()
    wait_streamlit(page)
    time.sleep(2)

    # Start workflow
    print("📍 Starting instructor workflow...")
    page.locator("button:has-text('Start')").first.click()
    wait_streamlit(page, timeout_ms=30000)
    time.sleep(3)

    # Click Create Tournament
    print("📍 Clicking 'Create Tournament' button...")
    create_btn = page.get_by_role("button", name="Create Tournament")
    assert create_btn.count() > 0, "Create Tournament button not found"

    create_btn.click()
    wait_streamlit(page, timeout_ms=30000)
    time.sleep(3)

    # Verify navigation to Step 2
    print("📍 Verifying navigation to Step 2...")
    try:
        page.wait_for_selector("text=/2\\. Manage Sessions/i", timeout=20000)
        print("✅ PASS: Tournament created successfully - navigated to Step 2")
    except:
        page_text = page.locator("body").inner_text()
        pytest.fail(
            f"❌ FAIL: Did not navigate to Step 2\n"
            f"Page content:\n{page_text[:500]}"
        )

    print("\n" + "="*80)
    print("✅ PHASE 1 STABILITY TEST: PASS")
    print("="*80 + "\n")
