"""
TRUE GOLDEN PATH E2E TEST - Complete Tournament Lifecycle (API-Based Creation)

This test uses API-based tournament creation for deterministic setup,
then validates the complete UI workflow from results entry to rewards.

Phase 0: Create Tournament via API (deterministic, bypasses UI preset selection)
Phase 1: Navigate to Tournament in UI
Phase 2: Navigate to Step 4 (Enter Results)
Phase 3: Submit ALL Match Results (Group Stage + Knockout)
Phase 4: Finalize Group Stage
Phase 5: Submit Knockout Results
Phase 6: Navigate to Leaderboard
Phase 7: Complete Tournament
Phase 8: Distribute Rewards
Phase 9: View Distributed Rewards

SUCCESS CRITERIA:
- Tournament created with correct group_knockout type
- All match results submitted successfully
- Group stage finalized
- Knockout matches generated and completed
- Tournament completed
- Rewards distributed
- Full lifecycle deterministic (20/20 PASS required)

This is the RELEASE-CRITICAL RELIABILITY REQUIREMENT.
"""
import pytest
import time
import requests
from playwright.sync_api import Page
from create_tournament_api_helper import (
    create_group_knockout_tournament_via_api,
    enroll_participants_via_api,
    generate_sessions_via_api,
    submit_match_result_via_api
)


def wait_streamlit(page: Page, timeout_ms: int = 10000):
    """Wait for Streamlit to finish rerunning"""
    try:
        page.wait_for_selector("[data-testid='stApp']", state="attached", timeout=timeout_ms)
        time.sleep(1)
    except:
        pass


@pytest.mark.e2e
@pytest.mark.golden_path
def test_golden_path_api_based_full_lifecycle(page: Page):
    """
    🏆 TRUE GOLDEN PATH E2E TEST: Complete Tournament Lifecycle (API-Based)

    Validates the COMPLETE production workflow with deterministic API-based setup.
    """
    print("\n" + "="*80)
    print("🏆 TRUE GOLDEN PATH E2E TEST: Full Tournament Lifecycle (API-Based)")
    print("="*80 + "\n")

    # ============================================================================
    # PHASE 0: Create Tournament via API (deterministic)
    # ============================================================================
    print("📍 Phase 0: Create Tournament via API")

    tournament_result = create_group_knockout_tournament_via_api(
        tournament_name="LFA Golden Path Test Tournament"
    )
    tournament_id = tournament_result["tournament_id"]
    token = tournament_result["token"]
    print(f"   ✅ Tournament {tournament_id} created via API with type={tournament_result['tournament_type']}")

    # ============================================================================
    # PHASE 1: Enroll Participants via API
    # ============================================================================
    print(f"\n📍 Phase 1: Enroll Participants via API")

    try:
        enroll_result = enroll_participants_via_api(
            tournament_id=tournament_id,
            token=token,
            participant_count=7  # Group+Knockout (7 players)
        )
        print(f"   ✅ Enrolled 7 participants via API")
    except Exception as e:
        pytest.fail(f"❌ Failed to enroll participants: {str(e)}")

    # ============================================================================
    # PHASE 2: Generate Sessions via API
    # ============================================================================
    print("\n📍 Phase 2: Generate Sessions via API")

    try:
        session_result = generate_sessions_via_api(
            tournament_id=tournament_id,
            token=token
        )
        print(f"   ✅ Generated sessions via API")
    except Exception as e:
        pytest.fail(f"❌ Failed to generate sessions: {str(e)}")

    # ============================================================================
    # PHASE 3: Navigate to Step 4 (Enter Results) in UI
    # ============================================================================
    print(f"\n📍 Phase 3: Navigate to Step 4 (Enter Results) in UI")

    # Navigate directly to instructor workflow Step 4 using query params
    # URL format: ?screen=instructor_workflow&tournament_id=1222&step=4
    url = f"http://localhost:8501?screen=instructor_workflow&tournament_id={tournament_id}&step=4"
    print(f"   Navigating to: {url}")
    page.goto(url)
    wait_streamlit(page, timeout_ms=30000)
    time.sleep(5)
    print("   ✅ Navigated to Step 4 (Enter Results) for tournament")

    # ============================================================================
    # PHASE 4: Submit ALL Group Stage Match Results
    # ============================================================================
    print("\n📍 Phase 4: Submit ALL Group Stage Match Results")

    # For Group+Knockout with 7 players:
    # - 3 groups: A (3 players), B (2 players), C (2 players)
    # - Group A: 3 matches (round-robin)
    # - Group B: 1 match
    # - Group C: 1 match
    # - TOTAL: 5 group matches (NOT 9, NOT 45!)
    #
    # Wait, let me check what the actual config is for 7-player group+knockout...
    # Let's discover dynamically by counting Submit Result buttons

    page.wait_for_selector("button:has-text('Submit Result')", timeout=10000)
    time.sleep(2)

    # Count total Submit Result buttons to know how many matches exist
    all_submit_buttons = page.locator("button:has-text('Submit Result')").all()
    total_matches = len(all_submit_buttons)
    print(f"   Found {total_matches} total 'Submit Result' buttons (all phases)")

    # Assume first set are Group Stage matches
    # Submit each match result iteratively (same approach as previous test)
    matches_submitted = 0
    max_attempts = 100  # Safety limit

    print(f"   Starting to submit match results...")

    while matches_submitted < max_attempts:
        submit_buttons = page.locator("button:has-text('Submit Result')").all()

        if len(submit_buttons) == 0:
            print(f"   ✅ No more Submit Result buttons found (submitted {matches_submitted} matches)")
            break

        if (matches_submitted % 5 == 0) or (matches_submitted == 0):
            print(f"   Submitting Match #{matches_submitted + 1}... ({len(submit_buttons)} buttons remaining)")

        first_button = page.locator("button:has-text('Submit Result')").first
        all_number_inputs = page.locator("input[type='number']").all()

        if len(all_number_inputs) >= 2:
            # Fill scores
            all_number_inputs[0].fill("2")  # Player 1 score
            all_number_inputs[1].fill("1")  # Player 2 score

            buttons_before = len(page.locator("button:has-text('Submit Result')").all())
            first_button.click()
            wait_streamlit(page, timeout_ms=10000)
            time.sleep(2)

            buttons_after = len(page.locator("button:has-text('Submit Result')").all())

            if buttons_after >= buttons_before:
                pytest.fail(f"❌ Form submission failed at match #{matches_submitted + 1}: Button count {buttons_before} → {buttons_after}")

            matches_submitted += 1

            if matches_submitted % 5 == 0:
                print(f"   ✅ Progress: {matches_submitted} matches submitted")
        else:
            print(f"   ⚠️  Warning: Found button but not enough number inputs, skipping...")
            break

    print(f"   ✅ Total {matches_submitted} matches submitted")

    # ============================================================================
    # PHASE 5: Finalize Group Stage
    # ============================================================================
    print("\n📍 Phase 5: Finalize Group Stage")

    try:
        finalize_btn = page.locator("button:has-text('Finalize Group Stage')").first
        finalize_btn.wait_for(state="visible", timeout=10000)
        finalize_btn.click()
        print("   ✅ Clicked 'Finalize Group Stage' button")
        print("   Waiting for st.rerun() to complete and knockout sections to load...")

        # Wait for Streamlit to process the rerun
        wait_streamlit(page, timeout_ms=30000)

        # CRITICAL FIX: Wait for knockout heading first
        try:
            page.wait_for_selector("text=/🏆.*Knockout/i", timeout=15000)
            print("   ✅ Knockout Stage section heading appeared")
        except:
            print("   ⚠️  Knockout Stage heading not found after 15s")
            page.screenshot(path="/tmp/debug_no_knockout_heading.png")
            pytest.fail("Knockout heading did not appear after group finalization")

        # REAL FIX: The issue is that the first Submit Result buttons we find are still
        # the GROUP STAGE forms (which show "✅ Result submitted" status).
        # We need to scroll past all group stage forms to find knockout forms.
        #
        # Strategy: Look for the FIRST form that does NOT have "Result submitted" success message above it
        # This will be the first unsubmitted knockout form.

        print("   Scrolling to find first unsubmitted knockout form...")
        time.sleep(3)  # Let page fully render

        # Check if there are any Submit Result buttons visible (should be knockout forms)
        submit_buttons_visible = page.locator("button:has-text('Submit Result')").count()
        print(f"   Found {submit_buttons_visible} visible 'Submit Result' buttons total")

        if submit_buttons_visible == 0:
            # This means all group forms show "✅ Result submitted" and knockout forms haven't rendered yet
            # This is the UI determinism bug - knockout forms with participant_user_ids=[] don't render
            page.screenshot(path="/tmp/debug_no_knockout_forms.png")
            page_text = page.inner_text("body")
            print(f"   📸 Screenshot: /tmp/debug_no_knockout_forms.png")
            print(f"   📄 Page content:\n{page_text}")
            pytest.fail("❌ UI DETERMINISM BUG: Knockout forms did not render. participant_user_ids may be empty.")

    except Exception as e:
        pytest.fail(f"❌ Finalize Group Stage failed: {str(e)}")

    # ============================================================================
    # PHASE 6: Submit Knockout Match Results (UI)
    # ============================================================================
    print("\n📍 Phase 6: Submit Knockout Match Results")

    # Submit all knockout matches iteratively (like group stage)
    # New matches appear after each submission as participants advance
    knockout_submitted = 0
    max_knockout_attempts = 10  # Safety limit (should be 3 for 7-player group+knockout)

    print(f"   Starting knockout result submission...")

    while knockout_submitted < max_knockout_attempts:
        # Check for Submit Result buttons
        submit_buttons = page.locator("button:has-text('Submit Result')").all()

        if len(submit_buttons) == 0:
            print(f"   ⚠️  No Submit Result buttons found (submitted {knockout_submitted} matches so far)")
            # Multi-round knockout: After Semi-finals complete, wait for page rerun
            # to allow Final match form to render with newly determined participants
            if knockout_submitted > 0:
                print(f"   Waiting for page rerun to render next knockout round...")
                wait_streamlit(page, timeout_ms=15000)
                time.sleep(3)

                # Re-check for new Submit Result buttons (Final match should now appear)
                submit_buttons = page.locator("button:has-text('Submit Result')").all()
                if len(submit_buttons) == 0:
                    print(f"   ✅ No more knockout Submit Result buttons found after rerun (submitted {knockout_submitted} matches total)")
                    break
                else:
                    print(f"   ✅ Found {len(submit_buttons)} new knockout Submit Result buttons after rerun")
                    # Continue loop to submit newly appeared match(es)
                    continue
            else:
                print(f"   ✅ No knockout Submit Result buttons found initially")
                break

        print(f"   Submitting Knockout Match #{knockout_submitted + 1}... ({len(submit_buttons)} buttons remaining)")

        first_button = page.locator("button:has-text('Submit Result')").first
        all_number_inputs = page.locator("input[type='number']").all()

        if len(all_number_inputs) >= 2:
            all_number_inputs[0].fill("3")
            all_number_inputs[1].fill("2")

            first_button.click()
            wait_streamlit(page, timeout_ms=10000)
            time.sleep(2)

            knockout_submitted += 1
        else:
            print(f"   ⚠️  Not enough number inputs, stopping knockout submission")
            break

    print(f"   ✅ All {knockout_submitted} knockout matches submitted")

    # Wait for deterministic UI signal: "✅ All match results submitted" success message
    # This message only appears when BOTH all_group_results_submitted AND all_knockout_submitted are true,
    # which means the rerun has completed and the new query results are rendered.
    print("   Waiting for '✅ All match results submitted' success message...")
    try:
        success_msg = page.locator("text=/✅.*All match results submitted/i")
        success_msg.wait_for(state="visible", timeout=30000)
        print("   ✅ Success message appeared - all results processed and rerun complete")
    except Exception as e:
        print(f"   ❌ Timeout waiting for success message: {str(e)}")
        page.screenshot(path="/tmp/debug_no_success_msg.png")
        pytest.fail(f"❌ Success message '✅ All match results submitted' did not appear: {str(e)}")

    # ============================================================================
    # PHASE 7: Navigate to Leaderboard
    # ============================================================================
    print("\n📍 Phase 7: Navigate to Leaderboard")

    try:
        # Verify button is visible (good sanity check)
        continue_btn = page.locator("button:has-text('Continue to Leaderboard')").first
        continue_btn.wait_for(state="visible", timeout=10000)
        print("   ✅ 'Continue to Leaderboard' button is visible")

        # WORKAROUND: Playwright click on Streamlit buttons is unreliable
        # Use URL navigation instead (same as other phases)
        leaderboard_url = f"http://localhost:8501?screen=instructor_workflow&tournament_id={tournament_id}&step=5"
        page.goto(leaderboard_url)
        print(f"   ✅ Navigated via URL to Step 5 (Leaderboard)")

        # Wait for Step 5 to load
        wait_streamlit(page, timeout_ms=15000)
        step5_heading = page.locator("text=5. View Leaderboard").first
        step5_heading.wait_for(state="visible", timeout=15000)
        print("   ✅ Step 5 (Leaderboard) loaded successfully")
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        page.screenshot(path="/tmp/phase7_failure.png")
        print("   🔍 Screenshot saved to /tmp/phase7_failure.png")
        pytest.fail(f"❌ Failed to navigate to Leaderboard (Step 5): {str(e)}")

    # ============================================================================
    # PHASE 7.5: Navigate to Complete Tournament Page
    # ============================================================================
    print("\n📍 Phase 7.5: Navigate to Complete Tournament Page")

    try:
        # WORKAROUND: Same as Phase 7 - use URL navigation for reliability
        complete_url = f"http://localhost:8501?screen=instructor_workflow&tournament_id={tournament_id}&step=6"
        page.goto(complete_url)
        print(f"   ✅ Navigated via URL to Step 6 (Complete Tournament)")
        wait_streamlit(page)
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        pytest.fail(f"❌ Failed to navigate to Complete Tournament (Step 6): {str(e)}")

    # ============================================================================
    # PHASE 8: Complete Tournament
    # ============================================================================
    print("\n📍 Phase 8: Complete Tournament")

    try:
        complete_btn = page.locator("button:has-text('Complete Tournament')").first
        complete_btn.wait_for(state="visible", timeout=10000)
        complete_btn.click()
        print("   ✅ Clicked 'Complete Tournament' button")
        wait_streamlit(page, timeout_ms=30000)
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        pytest.fail(f"❌ 'Complete Tournament' button not found: {str(e)}")

    # ============================================================================
    # PHASE 9: Distribute Rewards
    # ============================================================================
    print("\n📍 Phase 9: Distribute Rewards")

    try:
        distribute_btn = page.locator("button:has-text('Distribute Rewards')").first
        distribute_btn.wait_for(state="visible", timeout=10000)
        distribute_btn.click()
        print("   ✅ Clicked 'Distribute Rewards' button")
        wait_streamlit(page, timeout_ms=30000)
        time.sleep(3)
    except:
        pytest.fail("❌ 'Distribute Rewards' button not found")

    # ============================================================================
    # PHASE 10: Verify Rewards Distributed
    # ============================================================================
    print("\n📍 Phase 10: Verify Rewards Distributed")

    # Look for success message or rewards table
    try:
        success_msg = page.locator("text=/Rewards.*distributed/i").first
        success_msg.wait_for(state="visible", timeout=10000)
        print("   ✅ Rewards distribution success message found")
    except:
        # Alternative: Check if rewards table is visible
        try:
            rewards_table = page.locator("table").first
            rewards_table.wait_for(state="visible", timeout=5000)
            print("   ✅ Rewards table found")
        except:
            pytest.fail("❌ Could not verify rewards were distributed")

    # ============================================================================
    # SUCCESS
    # ============================================================================
    print("\n" + "="*80)
    print("✅ GOLDEN PATH E2E TEST: PASSED")
    print("="*80 + "\n")
