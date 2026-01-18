"""
E2E Test: Admin Creates Tournament Semester

Sprint 1.3: Testing admin tournament creation workflow

This test validates:
1. Admin login
2. Navigate to Tournaments tab
3. Fill tournament creation form
4. Submit and verify tournament created
"""

import pytest
from playwright.sync_api import Page, expect
import os
from datetime import datetime, timedelta

ADMIN_DASHBOARD_URL = os.getenv("ADMIN_DASHBOARD_URL", "http://localhost:8501/Admin_Dashboard")


@pytest.mark.e2e
@pytest.mark.tournament
class TestAdminCreateTournament:
    """E2E test for admin tournament creation"""

    def test_admin_can_create_tournament(self, page: Page):
        """
        Test: Admin can create a new tournament semester

        Steps:
        1. Login as admin
        2. Navigate to Admin Dashboard > Tournaments tab
        3. Click "Create Tournament" tab
        4. Fill tournament form with all required fields
        5. Submit form
        6. Verify tournament appears in tournament list
        """

        print("\n" + "="*70)
        print("🏆 E2E TEST: Admin Creates Tournament Semester")
        print("="*70 + "\n")

        # ================================================================
        # STEP 1: Login as Admin
        # ================================================================
        print("  1. Logging in as admin...")

        page.goto("http://localhost:8501")
        page.wait_for_timeout(2000)

        # Fill login form
        page.fill("input[aria-label='Email']", "admin@lfa.com")
        page.fill("input[aria-label='Password']", "admin123")
        page.click("button:has-text('Login')")
        page.wait_for_timeout(3000)

        # After login, admin is automatically redirected to Admin Dashboard
        # Wait for the redirect to complete (same approach as test_admin_invitation_code.py)
        print("  2. Waiting for automatic redirect to Admin Dashboard...")

        # Wait longer with incremental checks
        for i in range(15):  # Try for up to 15 seconds
            page.wait_for_timeout(1000)
            current_url = page.url
            if "/Admin_Dashboard" in current_url:
                print(f"  ✅ Redirected to Admin Dashboard after {i+1} seconds")
                break
        else:
            # If we didn't break, redirect didn't happen
            raise AssertionError(f"No redirect to Admin_Dashboard after 15s. Current URL: {current_url}")

        print(f"  📍 URL: {current_url}")

        # Wait additional time for tabs to fully render
        page.wait_for_timeout(8000)  # Same as test_admin_invitation_code.py
        print("  ✅ Admin Dashboard fully loaded")

        # Take screenshot for documentation
        page.screenshot(path="docs/screenshots/e2e_tournament_admin_dashboard.png")

        # ================================================================
        # STEP 2: Navigate to Tournaments Tab
        # ================================================================
        print("  3. Navigating to Tournaments tab...")

        # Use EXACT same pattern as test_admin_invitation_code.py for Financial tab
        tournaments_btn = page.locator("button:has-text('Tournaments')")

        try:
            # Wait for button to be visible
            expect(tournaments_btn).to_be_visible(timeout=10000)
            tournaments_btn.click()
            page.wait_for_timeout(5000)  # Wait for tab content to render after rerun
            print("  ✅ Clicked Tournaments tab")
        except:
            print("  ⚠️ Tournaments tab button not found after 10s wait - exploring page...")

            # Take screenshot to see current state
            page.screenshot(path="docs/screenshots/e2e_tournament_no_tournaments_tab.png")

            # Print all visible buttons for debugging
            buttons = page.locator("button").all()
            print(f"  📋 Found {len(buttons)} buttons on page")
            for i, btn in enumerate(buttons[:20]):  # First 20
                try:
                    text = btn.inner_text(timeout=500)
                    if text:
                        print(f"    Button {i}: {text[:50]}")
                except:
                    pass

            raise AssertionError("Cannot find Tournaments tab button")

        # ================================================================
        # STEP 3: Open Create Tournament Form
        # ================================================================
        print("  3. Opening tournament creation form...")

        # Click "Create Tournament" tab (sub-tab within Tournaments)
        create_tab = page.locator("button[data-baseweb='tab']:has-text('Create Tournament')").or_(
            page.locator("div[role='tab']:has-text('Create Tournament')")
        )

        if create_tab.count() > 0:
            create_tab.first.click()
            page.wait_for_timeout(2000)
        else:
            print("  ⚠️  'Create Tournament' tab not found - taking screenshot")
            page.screenshot(path="docs/screenshots/debug_tournaments_tab.png")

        print("  ✅ Create Tournament form displayed")

        # ================================================================
        # STEP 4: Fill Tournament Creation Form
        # ================================================================
        print("  4. Filling tournament creation form...")

        # Generate unique tournament name
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        tournament_name = f"E2E Test Tournament {timestamp}"

        # ================================================================
        # CRITICAL: Fill Location & Campus FIRST (outside form, required for validation)
        # ================================================================
        print("  4a. Selecting Location & Campus...")

        # Select Location (first selectbox on page)
        location_selects = page.locator("div[data-baseweb='select']")
        if location_selects.count() > 0:
            first_location_select = location_selects.first
            first_location_select.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            first_location_select.click()
            page.wait_for_timeout(1000)

            # Click first location option
            location_option = page.locator("li[role='option']").first
            location_option.click()
            page.wait_for_timeout(1000)
            print("  ✅ Location selected")
        else:
            print("  ⚠️ Location selector not found")

        # Select Campus (second selectbox after location is selected)
        campus_selects = page.locator("div[data-baseweb='select']")
        if campus_selects.count() > 1:
            second_campus_select = campus_selects.nth(1)
            second_campus_select.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            second_campus_select.click()
            page.wait_for_timeout(1000)

            # Click first campus option
            campus_option = page.locator("li[role='option']").first
            campus_option.click()
            page.wait_for_timeout(1000)
            print("  ✅ Campus selected")
        else:
            print("  ⚠️ Campus selector not found")

        page.wait_for_timeout(2000)  # Wait for form to update after location/campus selection

        # ================================================================
        # Fill Tournament Name (inside form)
        # ================================================================
        name_input = page.locator("input[aria-label='Tournament Name *']")
        name_input.fill(tournament_name)
        print(f"  ✅ Tournament Name: {tournament_name}")

        # Select tournament date (tomorrow)
        tomorrow = datetime.now() + timedelta(days=1)
        date_input = page.locator("input[aria-label='Select a date.']").or_(
            page.locator("input[placeholder*='date']")
        )

        if date_input.count() > 0:
            date_input.first.fill(tomorrow.strftime("%Y/%m/%d"))
            print(f"  ✅ Tournament Date: {tomorrow.strftime('%Y/%m/%d')}")
        else:
            print("  ⚠️  Date input not found")

        # Take screenshot before Age Group selection to debug
        page.screenshot(path="docs/screenshots/e2e_tournament_before_age_group.png")
        print("  📸 Screenshot taken before Age Group selection")

        # ================================================================
        # Select Age Group (inside form, after Location & Campus)
        # ================================================================
        print("  4b. Selecting Age Group...")

        # Age Group is the 3rd selectbox overall:
        # 1. Location (outside form)
        # 2. Campus (outside form)
        # 3. Age Group (inside form) ← THIS ONE
        try:
            all_selects = page.locator("div[data-baseweb='select']")
            select_count = all_selects.count()
            print(f"  📋 Found {select_count} selectboxes on page")

            if select_count >= 3:
                # Click the 3rd selectbox (Age Group inside form)
                age_group_select = all_selects.nth(2)  # Index 2 = 3rd element
                age_group_select.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                age_group_select.click()
                page.wait_for_timeout(1000)
                print("  ✅ Clicked Age Group selectbox")

                # Now click YOUTH option
                youth_option = page.locator("li[role='option']:has-text('YOUTH')").first
                youth_option.click()
                page.wait_for_timeout(1000)
                print("  ✅ Age Group: YOUTH")
            else:
                print(f"  ⚠️ Not enough selectboxes (expected ≥3, found {select_count})")
        except Exception as e:
            print(f"  ⚠️ Age Group selection failed: {e}")
            print("  ⚠️ Continuing test...")

        # Select template (if checkbox exists)
        use_template_checkbox = page.locator("input[type='checkbox']").filter(has_text="Use Template")
        if use_template_checkbox.count() > 0:
            if not use_template_checkbox.is_checked():
                use_template_checkbox.check()
            print("  ✅ Using template: Yes")

        # Select template type
        template_select = page.locator("div[data-baseweb='select']").filter(has_text="Select Template")
        if template_select.count() > 0:
            template_select.first.click()
            page.wait_for_timeout(500)
            page.locator("text=Half-Day Tournament").or_(page.locator("li:has-text('Half-Day')")).first.click()
            print("  ✅ Template: Half-Day Tournament")

        # Take screenshot of filled form
        page.screenshot(path="docs/screenshots/e2e_tournament_form_filled.png")
        print("  ✅ Form filled - screenshot saved")

        # ================================================================
        # STEP 5: Submit Tournament Creation
        # ================================================================
        print("  5. Submitting tournament creation...")

        # Find and click submit button (inside form)
        submit_btn = page.locator("button[type='submit']:has-text('Create')").or_(
            page.locator("button:has-text('Generate Tournament')")
        ).or_(
            page.locator("button:has-text('Create Tournament')")
        )

        if submit_btn.count() > 0:
            submit_btn.first.click()
            print("  ✅ Submit button clicked")
        else:
            print("  ⚠️  Submit button not found - trying form submit")
            # Try pressing Enter in the form
            page.keyboard.press("Enter")

        # Wait for submission
        page.wait_for_timeout(5000)

        # ================================================================
        # STEP 6: Verify Tournament Created (UI Level)
        # ================================================================
        print("  6. Verifying tournament creation (UI)...")

        # Look for success message
        success_indicators = [
            page.locator("text=successfully").first,
            page.locator("text=created").first,
            page.locator("div[data-testid='stSuccess']").first,
        ]

        success_found = False
        tournament_id = None

        for indicator in success_indicators:
            try:
                if indicator.is_visible(timeout=2000):
                    success_text = indicator.text_content()
                    print(f"  ✅ Success indicator found: {success_text}")
                    success_found = True

                    # Try to extract tournament ID from success message
                    # Format: "Tournament created successfully! (ID: 123)"
                    import re
                    id_match = re.search(r'ID:\s*(\d+)', success_text)
                    if id_match:
                        tournament_id = int(id_match.group(1))
                        print(f"  ✅ Extracted Tournament ID: {tournament_id}")
                    break
            except:
                pass

        # Take final screenshot
        page.screenshot(path="docs/screenshots/e2e_tournament_created.png")

        # Navigate to "View Tournaments" tab to verify in UI
        view_tab = page.locator("button[data-baseweb='tab']:has-text('View Tournaments')").or_(
            page.locator("div[role='tab']:has-text('View Tournaments')")
        )

        if view_tab.count() > 0:
            view_tab.first.click()
            page.wait_for_timeout(2000)

            # Look for our tournament in the list
            tournament_in_list = page.locator(f"text={tournament_name}")

            if tournament_in_list.count() > 0:
                print(f"  ✅ Tournament found in UI list: {tournament_name}")
                success_found = True
            else:
                print(f"  ⚠️  Tournament not found in UI list (might be pagination issue)")

        # ================================================================
        # STEP 7: BACKEND VERIFICATION (DATABASE CHECK)
        # ================================================================
        print("\n  7. ⚡ BACKEND VERIFICATION: Checking database...")

        import requests
        import os

        # Get admin token from environment or use test default
        admin_token_env = os.getenv("TEST_ADMIN_TOKEN", None)
        backend_verified = False  # Initialize early

        if not admin_token_env:
            # Login to get token (FastAPI uses form data, not JSON)
            import urllib.parse
            login_response = requests.post(
                "http://localhost:8000/api/v1/auth/login",
                data=urllib.parse.urlencode({"username": "admin@lfa.com", "password": "admin123"}),
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if login_response.status_code == 200:
                admin_token = login_response.json()["access_token"]
            else:
                print(f"  ⚠️ Login failed: {login_response.status_code} - {login_response.text}")
                admin_token = None
                backend_verified = False
        else:
            admin_token = admin_token_env

        # Fetch all semesters from API
        response = requests.get(
            "http://localhost:8000/api/v1/semesters/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            all_semesters = data.get("semesters", []) if isinstance(data, dict) else data

            # Filter tournaments (code starts with TOURN-)
            tournaments = [s for s in all_semesters if s.get("code", "").startswith("TOURN-")]

            # Find our tournament by name
            our_tournament = next((t for t in tournaments if t.get("name") == tournament_name), None)

            if our_tournament:
                print(f"  ✅✅✅ BACKEND VERIFIED: Tournament exists in database!")
                print(f"      ID: {our_tournament.get('id')}")
                print(f"      Name: {our_tournament.get('name')}")
                print(f"      Code: {our_tournament.get('code')}")
                print(f"      Status: {our_tournament.get('status')}")
                print(f"      Age Group: {our_tournament.get('age_group')}")
                print(f"      Start Date: {our_tournament.get('start_date')}")

                # Verify it has TOURN- prefix
                assert our_tournament.get("code", "").startswith("TOURN-"), "Tournament code should start with TOURN-"

                # Verify status is SEEKING_INSTRUCTOR
                assert our_tournament.get("status") == "SEEKING_INSTRUCTOR", f"Expected status SEEKING_INSTRUCTOR, got {our_tournament.get('status')}"

                backend_verified = True
            else:
                print(f"  ❌ BACKEND VERIFICATION FAILED: Tournament '{tournament_name}' NOT found in database!")
                print(f"  📋 Found {len(tournaments)} tournaments in database:")
                for t in tournaments[-5:]:  # Last 5
                    print(f"      - {t.get('name')} (ID: {t.get('id')}, Code: {t.get('code')})")
                backend_verified = False
        else:
            print(f"  ❌ Failed to fetch semesters from API: {response.status_code}")
            backend_verified = False

        print("\n" + "="*70)
        if success_found and backend_verified:
            print("✅✅✅ TEST FULLY PASSED: Tournament created AND verified in database!")
        elif success_found and not backend_verified:
            print("⚠️  UI PASSED but BACKEND VERIFICATION FAILED!")
            print("    Tournament creation was optimistic UI only - API call may have failed")
        else:
            print("❌ TEST FAILED: Tournament creation did not succeed")
        print("="*70 + "\n")

        # Assert BOTH UI success AND backend verification
        assert success_found, "Tournament creation did not show success indicator in UI"
        assert backend_verified, "Tournament was NOT found in database after creation!"


if __name__ == "__main__":
    print("\n" + "="*70)
    print("ADMIN TOURNAMENT CREATION E2E TEST")
    print("="*70)
    print("\nRun with:")
    print("  pytest tests/e2e/test_admin_create_tournament.py -v --headed --slowmo=300")
    print("="*70 + "\n")
