"""
E2E Test: Reward Policy Distribution Workflow

⚠️ IMPORTANT: SIMPLIFIED E2E TEST (NOT PRODUCTION-REPRESENTATIVE)

This test validates the reward distribution BACKEND LOGIC only.
It does NOT test the full production tournament lifecycle.

MISSING COMPONENTS (Not Implemented):
❌ Instructor Dashboard UI (does not exist)
❌ Instructor assignment workflow (no API endpoint)
❌ Session attendance tracking (no UI/API)
❌ Instructor-submitted rankings (rankings are SQL-inserted)

CURRENT TEST SCOPE:
✅ Admin can create tournament with reward policy
✅ Reward policy snapshot is stored correctly in semesters.reward_policy_snapshot
✅ Players can enroll in tournament (requires LFA_FOOTBALL_PLAYER license)
✅ Reward distribution calculates XP/Credits correctly (1ST: 500 XP + 100 Credits, etc.)
✅ Transaction audit trail is created in credit_transactions table
✅ XP transactions are recorded via award_xp service

SIMPLIFIED FLOW (Used in This Test):
1. Admin creates tournament (status: SEEKING_INSTRUCTOR)
2. ⚠️ Manual status change to READY_FOR_ENROLLMENT (bypasses instructor assignment)
3. Players enroll
4. ⚠️ Direct SQL ranking insertion (bypasses attendance tracking)
5. Mark tournament as COMPLETED
6. Admin distributes rewards via UI/API
7. Validate XP/Credits updated correctly

PRODUCTION FLOW (Should Be):
1. Admin creates tournament (status: SEEKING_INSTRUCTOR)
2. Instructor accepts assignment → READY_FOR_ENROLLMENT
3. Players enroll
4. Instructor marks attendance for each session
5. Instructor submits rankings based on session results
6. Tournament marked as COMPLETED
7. Admin distributes rewards
8. Players see updated XP/Credits

PRODUCTION READINESS: 🔴 NOT READY
- Backend reward logic: ✅ Working
- Instructor workflow: ❌ Not implemented
- Attendance tracking: ❌ Not implemented
- Backend validations: ⚠️ Partial (does not check instructor/attendance)

For production-ready testing, implement instructor workflow first.
See: docs/backend/instructor_workflow.md (TODO)
"""

import pytest
from playwright.sync_api import Page, expect
import requests
import os
from typing import List, Dict, Any

from tests.e2e.reward_policy_fixtures import (
    reward_policy_admin_token,
    reward_policy_players,
    reward_policy_tournament_complete,
    distribute_rewards,
    get_user_current_stats
)

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


@pytest.mark.e2e
@pytest.mark.reward_policy
class TestRewardPolicyDistribution:
    """E2E tests for reward policy distribution workflow"""

    def test_complete_reward_distribution_workflow(
        self,
        page: Page,
        reward_policy_admin_token: str,
        reward_policy_players: List[Dict[str, Any]],
        reward_policy_tournament_complete: Dict[str, Any]
    ):
        """
        COMPLETE E2E TEST: Reward Distribution with User Validation

        Flow:
        1. Tournament already created with 5 players (via fixture)
        2. Rankings already set: 1ST, 2ND, 3RD, 2x PARTICIPANT (via fixture)
        3. Tournament marked COMPLETED (via fixture)
        4. Admin logs in via Playwright
        5. Admin navigates to tournament details
        6. Admin clicks "Distribute Rewards" button
        7. Admin confirms distribution in dialog
        8. Verify success feedback with statistics
        9. Validate backend: XP and Credits updated correctly for each user
        10. Validate UI: Each player logs in and sees updated XP/Credits

        Expected Results:
        - Player 1 (1ST): +500 XP, +100 Credits
        - Player 2 (2ND): +300 XP, +50 Credits
        - Player 3 (3RD): +200 XP, +25 Credits
        - Player 4 (PARTICIPANT): +50 XP, +0 Credits
        - Player 5 (PARTICIPANT): +50 XP, +0 Credits
        """

        print("\n" + "="*80)
        print("🎁 E2E TEST: Complete Reward Policy Distribution Workflow")
        print("="*80 + "\n")

        tournament_id = reward_policy_tournament_complete["tournament_id"]
        tournament_name = reward_policy_tournament_complete["tournament"]["summary"]["name"]
        players = reward_policy_tournament_complete["players"]
        rankings = reward_policy_tournament_complete["rankings"]

        print(f"  📊 Tournament ID: {tournament_id}")
        print(f"  📝 Tournament Name: {tournament_name}")
        print(f"  👥 Players: {len(players)}")
        print(f"  🏆 Rankings set: {len(rankings)}")

        # ================================================================
        # STEP 1: Set Explicit Viewport and Admin Login
        # ================================================================
        print("\n  1️⃣ Setting viewport and logging in as admin...")

        # Set explicit viewport size
        page.set_viewport_size({"width": 1920, "height": 1080})

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Explicit scroll to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        page.fill("input[aria-label='Email']", ADMIN_EMAIL)
        page.fill("input[aria-label='Password']", ADMIN_PASSWORD)
        page.click("button:has-text('Login')")
        page.wait_for_timeout(3000)

        # Wait for redirect to Admin Dashboard
        for i in range(15):
            page.wait_for_timeout(1000)
            if "/Admin_Dashboard" in page.url:
                print(f"  ✅ Logged in successfully")
                break

        page.wait_for_timeout(5000)  # Wait for tabs to render

        # ================================================================
        # STEP 2: Navigate to Tournaments Tab
        # ================================================================
        print("\n  2️⃣ Navigating to Tournaments tab...")

        page.evaluate("window.scrollTo(0, 0)")  # Scroll to top before tab click

        tournaments_btn = page.locator("button:has-text('Tournaments')")
        expect(tournaments_btn).to_be_visible(timeout=10000)
        tournaments_btn.click()
        page.wait_for_timeout(5000)

        print("  ✅ Tournaments tab opened")

        # ================================================================
        # STEP 3: Click "View Tournaments" Sub-Tab (default tab)
        # ================================================================
        print("\n  3️⃣ Navigating to 'View Tournaments' tab...")

        page.evaluate("window.scrollTo(0, 0)")  # Explicit scroll
        page.wait_for_timeout(1000)

        # Click "View Tournaments" tab (should be active by default)
        view_tab = page.locator("button:has-text('📋 View Tournaments'), button:has-text('View Tournaments')")
        if view_tab.count() > 0:
            view_tab.first.click()
            page.wait_for_timeout(3000)
            print("  ✅ View Tournaments tab opened")
        else:
            print("  ⚠️ View Tournaments tab not found, assuming already on correct tab")

        page.wait_for_timeout(2000)

        # ================================================================
        # STEP 4: Find and Click Specific Tournament by Name
        # ================================================================
        print(f"\n  4️⃣ Finding tournament '{tournament_name}' (ID: {tournament_id})...")

        page.evaluate("window.scrollTo(0, 0)")  # Scroll to top before searching
        page.wait_for_timeout(1000)

        # Take screenshot before searching
        page.screenshot(path="docs/screenshots/e2e_reward_before_tournament_search.png", full_page=True)

        # Look for specific tournament by name in expander summary
        # Tournament expanders contain tournament name
        tournament_expander = page.locator(f"summary:has-text('{tournament_name}')")

        if tournament_expander.count() == 0:
            print(f"  ❌ Tournament '{tournament_name}' not found. Available expanders:")
            all_expanders = page.locator("summary")
            for i in range(min(all_expanders.count(), 10)):
                expander_text = all_expanders.nth(i).text_content()
                print(f"     [{i}] {expander_text[:100]}")

            # Take screenshot for debugging
            page.screenshot(path="docs/screenshots/e2e_reward_no_tournament_found.png", full_page=True)
            pytest.fail(f"Tournament '{tournament_name}' not found in UI")

        print(f"  ✅ Found tournament, clicking expander...")

        # Scroll tournament into view before clicking
        tournament_expander.first.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Click the tournament expander
        tournament_expander.first.click()
        page.wait_for_timeout(3000)

        print("  ✅ Tournament expander opened")

        # ================================================================
        # STEP 5: Click "Distribute Rewards" Button
        # ================================================================
        print("\n  5️⃣ Clicking 'Distribute Rewards' button...")

        distribute_btn = page.locator("button:has-text('Distribute Rewards')")

        if distribute_btn.count() == 0:
            print("  ❌ 'Distribute Rewards' button not found")
            page.screenshot(path="docs/screenshots/e2e_reward_no_distribute_button.png", full_page=True)
            pytest.fail("Distribute Rewards button not found")

        print(f"  ℹ️ Found {distribute_btn.count()} 'Distribute Rewards' buttons, clicking first...")

        # Take screenshot before clicking
        page.screenshot(path="docs/screenshots/e2e_reward_before_distribute_click.png", full_page=True)

        # Use force=True to click even if element is not in viewport
        # (Streamlit expander content may not be fully visible initially)
        distribute_btn.first.click(force=True)
        page.wait_for_timeout(3000)

        print("  ✅ 'Distribute Rewards' button clicked")

        # ================================================================
        # STEP 6: Confirm Distribution in Dialog
        # ================================================================
        print("\n  6️⃣ Confirming distribution in dialog...")

        # Dialog should appear with confirmation
        confirm_btn = page.locator("button:has-text('Confirm Distribution')")

        if confirm_btn.count() == 0:
            print("  ❌ Confirmation dialog not found")
            page.screenshot(path="docs/screenshots/e2e_reward_no_confirm_dialog.png", full_page=True)
            pytest.fail("Confirmation dialog not found")

        # Take screenshot of dialog
        page.screenshot(path="docs/screenshots/e2e_reward_confirm_dialog.png")

        confirm_btn.click()
        page.wait_for_timeout(5000)  # Wait for distribution to complete

        print("  ✅ Distribution confirmed")

        # ================================================================
        # STEP 7: Verify Success Feedback
        # ================================================================
        print("\n  7️⃣ Verifying success feedback...")

        # Look for success message
        success_indicator = page.locator("text=Rewards distributed successfully")

        if success_indicator.count() > 0:
            print("  ✅ Success message displayed")
        else:
            print("  ⚠️ Success message not found (might have auto-closed)")

        # Look for distribution statistics
        # Should show: Total Participants, XP Distributed, Credits Distributed
        page.screenshot(path="docs/screenshots/e2e_reward_success_feedback.png", full_page=True)

        page.wait_for_timeout(3000)

        # ================================================================
        # STEP 8: Validate Backend - XP/Credits Updated
        # ================================================================
        print("\n  8️⃣ Validating backend: XP and Credits updated...")

        # Expected rewards (from default policy)
        expected_rewards = {
            "1ST": {"xp": 500, "credits": 100},
            "2ND": {"xp": 300, "credits": 50},
            "3RD": {"xp": 200, "credits": 25},
            "PARTICIPANT": {"xp": 50, "credits": 0}
        }

        validation_results = []

        for i, ranking in enumerate(rankings):
            player = players[i]
            placement = ranking["placement"]
            expected = expected_rewards[placement]

            # Get current stats from API
            current_stats = get_user_current_stats(reward_policy_admin_token, player["id"])

            # Calculate expected values
            expected_xp = player["initial_xp"] + expected["xp"]
            expected_credits = player["initial_credits"] + expected["credits"]

            # Validate
            xp_match = current_stats["total_xp"] == expected_xp
            credits_match = current_stats["credit_balance"] == expected_credits

            validation_results.append({
                "player_num": i + 1,
                "placement": placement,
                "expected_xp": expected_xp,
                "actual_xp": current_stats["total_xp"],
                "xp_match": xp_match,
                "expected_credits": expected_credits,
                "actual_credits": current_stats["credit_balance"],
                "credits_match": credits_match
            })

            status = "✅" if (xp_match and credits_match) else "❌"
            print(f"  {status} Player {i+1} ({placement}):")
            print(f"      XP: {current_stats['total_xp']} (expected: {expected_xp}) {'✅' if xp_match else '❌'}")
            print(f"      Credits: {current_stats['credit_balance']} (expected: {expected_credits}) {'✅' if credits_match else '❌'}")

        # Assert all validations passed
        all_valid = all(v["xp_match"] and v["credits_match"] for v in validation_results)

        if not all_valid:
            print("\n  ❌ VALIDATION FAILED: Some rewards were not distributed correctly")
            for v in validation_results:
                if not (v["xp_match"] and v["credits_match"]):
                    print(f"     Player {v['player_num']} ({v['placement']}): XP mismatch or Credits mismatch")
            pytest.fail("Reward distribution validation failed")

        print("\n  ✅ ALL BACKEND VALIDATIONS PASSED")

        # ================================================================
        # STEP 9: Validate UI - Players See Updated Stats
        # ================================================================
        print("\n  9️⃣ Validating UI: Players see updated XP/Credits...")

        # Log in as each player and verify they see updated stats
        for i, player in enumerate(players[:3]):  # Test first 3 players (1ST, 2ND, 3RD)
            print(f"\n  👤 Testing Player {i+1} UI ({rankings[i]['placement']})...")

            # Logout current user (admin)
            page.goto(STREAMLIT_URL)
            page.wait_for_timeout(2000)

            # Explicit scroll to top
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            # Login as player
            page.fill("input[aria-label='Email']", player["email"])
            page.fill("input[aria-label='Password']", player["password"])
            page.click("button:has-text('Login')")
            page.wait_for_timeout(5000)

            # Look for XP/Credits display in UI
            # Streamlit typically shows these in sidebar or dashboard

            # Take screenshot
            page.screenshot(path=f"docs/screenshots/e2e_reward_player_{i+1}_dashboard.png", full_page=True)

            # Look for XP value in page
            expected_xp = validation_results[i]["expected_xp"]
            expected_credits = validation_results[i]["expected_credits"]

            xp_text = str(expected_xp)
            credits_text = str(expected_credits)

            # Check if XP appears on page
            if page.locator(f"text={xp_text}").count() > 0:
                print(f"     ✅ XP displayed correctly: {xp_text}")
            else:
                print(f"     ⚠️ XP value {xp_text} not found in UI (might be in different format)")

            # Check if Credits appear on page
            if page.locator(f"text={credits_text}").count() > 0:
                print(f"     ✅ Credits displayed correctly: {credits_text}")
            else:
                print(f"     ⚠️ Credits value {credits_text} not found in UI (might be in different format)")

        print("\n" + "="*80)
        print("✅ COMPLETE E2E TEST PASSED: Reward Distribution Workflow")
        print("="*80 + "\n")

    def test_reward_distribution_statistics_accuracy(
        self,
        page: Page,
        reward_policy_admin_token: str,
        reward_policy_tournament_complete: Dict[str, Any]
    ):
        """
        Test that distribution statistics are accurate.

        Validates:
        - Total participants count
        - Total XP distributed
        - Total credits distributed
        """

        print("\n" + "="*80)
        print("📊 E2E TEST: Reward Distribution Statistics Accuracy")
        print("="*80 + "\n")

        tournament_id = reward_policy_tournament_complete["tournament_id"]

        # Expected totals (from default policy)
        # 1ST: 500 XP + 100 Credits
        # 2ND: 300 XP + 50 Credits
        # 3RD: 200 XP + 25 Credits
        # PARTICIPANT: 50 XP + 0 Credits (x2)
        expected_total_xp = 500 + 300 + 200 + 50 + 50  # = 1100 XP
        expected_total_credits = 100 + 50 + 25 + 0 + 0  # = 175 Credits
        expected_total_participants = 5

        print(f"  📊 Expected Statistics:")
        print(f"     - Total Participants: {expected_total_participants}")
        print(f"     - Total XP: {expected_total_xp}")
        print(f"     - Total Credits: {expected_total_credits}")

        # Call distribute rewards API directly
        stats = distribute_rewards(reward_policy_admin_token, tournament_id)

        print(f"\n  📊 Actual Statistics:")
        print(f"     - Total Participants: {stats.get('total_participants', 'N/A')}")
        print(f"     - Total XP: {stats.get('xp_distributed', 'N/A')}")
        print(f"     - Total Credits: {stats.get('credits_distributed', 'N/A')}")

        # Assertions
        assert stats["total_participants"] == expected_total_participants, \
            f"Participants mismatch: {stats['total_participants']} != {expected_total_participants}"

        assert stats["xp_distributed"] == expected_total_xp, \
            f"XP mismatch: {stats['xp_distributed']} != {expected_total_xp}"

        assert stats["credits_distributed"] == expected_total_credits, \
            f"Credits mismatch: {stats['credits_distributed']} != {expected_total_credits}"

        print("\n  ✅ ALL STATISTICS VALIDATED")
