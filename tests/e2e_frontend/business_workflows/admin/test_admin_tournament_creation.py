"""
E2E Test: Admin Creates Tournament with TournamentType System

REFACTORED for new tournament architecture:
- Uses tournament_type_id (TournamentType model)
- Requires age_group selection
- No more templates - uses tournament types instead
- Session generation is separate step after enrollment closes

This test validates:
1. Admin login
2. Navigate to Tournaments tab
3. Fill tournament creation form with tournament_type
4. Submit and verify tournament created
5. Verify tournament appears in list with correct fields
"""

import pytest
from playwright.sync_api import Page, expect
import os
import requests
from datetime import datetime, timedelta

ADMIN_DASHBOARD_URL = os.getenv("ADMIN_DASHBOARD_URL", "http://localhost:8501/Admin_Dashboard")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


@pytest.mark.e2e
@pytest.mark.tournament
class TestAdminCreateTournamentRefactored:
    """E2E test for admin tournament creation with new TournamentType system"""

    def test_admin_can_create_tournament_with_type(self, page: Page):
        """
        Test: Admin can create 6 tournaments with different types and assignment types

        Creates:
        1-3. APPLICATION_BASED tournaments (League, Knockout, Group+KO)
        4-6. OPEN_ASSIGNMENT tournaments (League, Knockout, Group+KO)

        This creates the checkpoint needed for both:
        - test_ui_instructor_application_workflow.py
        - test_ui_instructor_invitation_workflow.py
        """

        print("\n" + "="*80)
        print("🏆 E2E TEST: Admin Creates 6 Tournaments (3 APPLICATION + 3 OPEN_ASSIGNMENT)")
        print("="*80 + "\n")

        # Generate unique tournament names
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        tournaments_to_create = [
            # APPLICATION_BASED tournaments
            {
                "name": f"Budapest HU League {timestamp}",
                "type": "League (Round Robin)",
                "max_players": 8,
                "location_index": 0,  # Budapest
                "assignment_type": "APPLICATION_BASED",
            },
            {
                "name": f"Vienna AT Knockout {timestamp}",
                "type": "Single Elimination (Knockout)",
                "max_players": 8,
                "location_index": 1,  # Vienna
                "assignment_type": "APPLICATION_BASED",
            },
            {
                "name": f"Bratislava SK Group+KO {timestamp}",
                "type": "Group Stage + Knockout",
                "max_players": 8,
                "location_index": 2,  # Bratislava
                "assignment_type": "APPLICATION_BASED",
            },
            # OPEN_ASSIGNMENT tournaments (admin invites instructor)
            {
                "name": f"Budapest HU League INV {timestamp}",
                "type": "League (Round Robin)",
                "max_players": 8,
                "location_index": 0,  # Budapest
                "assignment_type": "OPEN_ASSIGNMENT",
            },
            {
                "name": f"Vienna AT Knockout INV {timestamp}",
                "type": "Single Elimination (Knockout)",
                "max_players": 8,
                "location_index": 1,  # Vienna
                "assignment_type": "OPEN_ASSIGNMENT",
            },
            {
                "name": f"Bratislava SK Group+KO INV {timestamp}",
                "type": "Group Stage + Knockout",
                "max_players": 8,
                "location_index": 2,  # Bratislava
                "assignment_type": "OPEN_ASSIGNMENT",
            },
        ]

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

        # Wait for automatic redirect to Admin Dashboard
        print("  2. Waiting for automatic redirect to Admin Dashboard...")

        for i in range(15):  # Try for up to 15 seconds
            page.wait_for_timeout(1000)
            current_url = page.url
            if "/Admin_Dashboard" in current_url:
                print(f"  ✅ Redirected to Admin Dashboard after {i+1} seconds")
                break
        else:
            raise AssertionError(f"No redirect to Admin_Dashboard after 15s. Current URL: {current_url}")

        print(f"  📍 URL: {current_url}")

        # Wait for tabs to fully render
        page.wait_for_timeout(8000)
        print("  ✅ Admin Dashboard fully loaded")

        # ================================================================
        # STEP 2: Navigate to Tournaments Tab
        # ================================================================
        print("  3. Navigating to Tournaments tab...")

        tournaments_btn = page.locator("button:has-text('Tournaments')")

        try:
            expect(tournaments_btn).to_be_visible(timeout=10000)
            tournaments_btn.click()
            page.wait_for_timeout(5000)  # Wait for tab content to render
            print("  ✅ Clicked Tournaments tab")
        except Exception as e:
            print(f"  ❌ Tournaments tab button not found: {e}")
            page.screenshot(path="docs/screenshots/e2e_no_tournaments_tab.png")
            raise AssertionError("Cannot find Tournaments tab")

        # ================================================================
        # STEP 3-8: Create 6 Tournaments (Loop)
        # ================================================================
        created_tournament_ids = []

        for idx, tournament_config in enumerate(tournaments_to_create, 1):
            print(f"\n  {'='*70}")
            print(f"  Creating Tournament {idx}/6: {tournament_config['name']}")
            print(f"  {'='*70}")

            tournament_name = tournament_config['name']
            tournament_type = tournament_config['type']
            max_players = tournament_config['max_players']
            location_index = tournament_config['location_index']
            assignment_type = tournament_config['assignment_type']

            # ================================================================
            # Click "Create Tournament" Tab
            # ================================================================
            print(f"  4.{idx} Opening Create Tournament tab...")

            create_tab = page.locator("button[data-baseweb='tab']:has-text('Create Tournament')").or_(
                page.locator("div[role='tab']:has-text('Create Tournament')")
            )

            try:
                expect(create_tab).to_be_visible(timeout=5000)
                create_tab.click()
                page.wait_for_timeout(3000)
                print(f"  ✅ Create Tournament tab opened")
            except Exception as e:
                print(f"  ❌ Create Tournament tab not found: {e}")
                page.screenshot(path=f"docs/screenshots/e2e_no_create_tab_{idx}.png")
                raise AssertionError("Cannot find Create Tournament tab")

            # ================================================================
            # Fill Tournament Creation Form
            # ================================================================
            print(f"  5.{idx} Filling tournament creation form...")

            # Wait for form to load
            page.wait_for_timeout(2000)

            # 4a. Fill Tournament Name
            name_input = page.locator("input[aria-label='Tournament Name *']").or_(
                page.locator("input[placeholder*='Tournament Name']")
            )

            if name_input.count() > 0:
                name_input.first.fill(tournament_name)
                print(f"  ✅ Tournament Name: {tournament_name}")
            else:
                print("  ⚠️  Tournament Name input not found")

            # 4b. Select Tournament Date (tomorrow)
            tomorrow = datetime.now() + timedelta(days=1)
            date_input = page.locator("input[aria-label='Select a date.']").or_(
                page.locator("input[placeholder*='date']")
            )

            if date_input.count() > 0:
                date_input.first.fill(tomorrow.strftime("%Y/%m/%d"))
                print(f"  ✅ Tournament Date: {tomorrow.strftime('%Y/%m/%d')}")
            else:
                print("  ⚠️  Date input not found")

            page.wait_for_timeout(1000)

            # 4c. Select Location (by index)
            print(f"  5.{idx}a. Selecting Location (index {location_index})...")

            try:
                # Wait for location selectbox to be visible and stable
                page.wait_for_timeout(2000)
                location_selects = page.locator("div[data-baseweb='select']")

                # Wait for at least one select to be visible
                location_selects.first.wait_for(state="visible", timeout=10000)

                first_location_select = location_selects.first

                # Try to scroll into view (with timeout)
                try:
                    first_location_select.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    # If scroll fails, just continue - element might already be visible
                    pass

                page.wait_for_timeout(500)
                first_location_select.click()
                page.wait_for_timeout(1500)

                # Click location option by index
                location_option = page.locator("li[role='option']").nth(location_index)
                location_option.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Location selected (index {location_index})")
            except Exception as e:
                print(f"  ⚠️  Location selection failed: {e}")
                # Take screenshot for debugging
                page.screenshot(path=f"tests/e2e/screenshots/location_error_{idx}.png")

            # 4d. Select Campus (corresponding to location)
            print(f"  5.{idx}b. Selecting Campus...")

            try:
                page.wait_for_timeout(1500)
                campus_selects = page.locator("div[data-baseweb='select']")

                if campus_selects.count() > 1:
                    second_campus_select = campus_selects.nth(1)

                    try:
                        second_campus_select.scroll_into_view_if_needed(timeout=5000)
                    except Exception:
                        pass

                    page.wait_for_timeout(500)
                    second_campus_select.click()
                    page.wait_for_timeout(1500)

                    campus_option = page.locator("li[role='option']").first
                    campus_option.click()
                    page.wait_for_timeout(1500)
                    print("  ✅ Campus selected")
                else:
                    print("  ⚠️  Campus selector not found")
            except Exception as e:
                print(f"  ⚠️  Campus selection failed: {e}")

            page.wait_for_timeout(2000)

            # 4e. Select Age Group (AMATEUR for 18+)
            print(f"  5.{idx}c. Selecting Age Group (AMATEUR)...")

            try:
                age_group_select = page.locator("[data-testid='stSelectbox']:has-text('Age Group')").first

                try:
                    age_group_select.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass

                page.wait_for_timeout(500)
                age_group_select.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Clicked Age Group selectbox")

                amateur_option = page.locator("li[role='option']:has-text('AMATEUR')").first
                amateur_option.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Age Group: AMATEUR (18+)")
            except Exception as e:
                print(f"  ⚠️  Age Group selection failed: {e}")

            page.wait_for_timeout(1000)

            # 4f. Select Tournament Type (dynamic based on config)
            print(f"  5.{idx}d. Selecting Tournament Type ({tournament_type})...")

            try:
                tournament_type_select = page.locator("[data-testid='stSelectbox']:has-text('Tournament Type')").first

                try:
                    tournament_type_select.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass

                page.wait_for_timeout(500)
                tournament_type_select.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Clicked Tournament Type selectbox")

                # Select tournament type based on config
                type_option = page.locator(f"li[role='option']:has-text('{tournament_type}')").first
                type_option.click()
                page.wait_for_timeout(2000)  # Wait for duration estimation to load
                print(f"  ✅ Tournament Type: {tournament_type}")
            except Exception as e:
                print(f"  ⚠️  Tournament Type selection failed: {e}")

            page.wait_for_timeout(1000)

            # 4g. Fill Max Players
            print(f"  5.{idx}e. Setting Max Players ({max_players})...")
            try:
                max_players_input = page.locator("[data-testid='stNumberInput']:has-text('Max Players')").first.locator("input")
                max_players_input.fill(str(max_players))
                print(f"  ✅ Max Players: {max_players}")
            except Exception as e:
                print(f"  ⚠️  Max Players input failed: {e}")

            # 4h. Fill Enrollment Cost (500 credits)
            print(f"  5.{idx}f. Setting Enrollment Cost...")
            try:
                enrollment_cost_input = page.locator("[data-testid='stNumberInput']:has-text('Price')").first.locator("input")
                enrollment_cost_input.fill("500")
                print(f"  ✅ Enrollment Cost: 500 credits")
            except Exception as e:
                print(f"  ⚠️  Enrollment Cost input failed: {e}")

            # 4i. Select Assignment Type (dynamic based on config)
            print(f"  5.{idx}g. Selecting Assignment Type ({assignment_type})...")

            try:
                assignment_type_select = page.locator("[data-testid='stSelectbox']:has-text('Assignment Type')").first

                try:
                    assignment_type_select.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass

                page.wait_for_timeout(500)
                assignment_type_select.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Clicked Assignment Type selectbox")

                assignment_option = page.locator(f"li[role='option']:has-text('{assignment_type}')").first
                assignment_option.click()
                page.wait_for_timeout(1500)
                print(f"  ✅ Assignment Type: {assignment_type}")
            except Exception as e:
                print(f"  ⚠️  Assignment Type selection failed: {e}")

            # Take screenshot of filled form
            page.screenshot(path=f"docs/screenshots/e2e_tournament_form_filled_{idx}.png")
            print(f"  ✅ Form filled - screenshot saved")

            # ================================================================
            # Submit Tournament Creation
            # ================================================================
            print(f"  6.{idx} Submitting tournament creation...")

            try:
                submit_btn = page.locator("[data-testid='stFormSubmitButton']:has-text('Create Tournament')").first
                submit_btn.click()
                print(f"  ✅ Submit button clicked")
            except Exception as e:
                print(f"  ⚠️  Submit button click failed: {e}")
                print(f"  ⚠️  Trying Enter key as fallback")
                page.keyboard.press("Enter")

            # Wait for submission and UI update
            page.wait_for_timeout(5000)

            # ================================================================
            # Verify Tournament Created (UI Level)
            # ================================================================
            print(f"  7.{idx} Verifying tournament creation (UI)...")

            # Look for success indicators
            success_indicators = [
                page.locator("text=successfully").first,
                page.locator("text=created").first,
                page.locator("div[data-testid='stSuccess']").first,
                page.locator("text=Tournament created").first,
            ]

            success_found = False

            for indicator in success_indicators:
                try:
                    if indicator.is_visible(timeout=2000):
                        success_found = True
                        print(f"  ✅ Success indicator found: {indicator.inner_text()}")
                        break
                except:
                    continue

            if not success_found:
                print(f"  ⚠️  No explicit success message found - will check via API...")

            # Take screenshot after submission
            page.screenshot(path=f"docs/screenshots/e2e_tournament_after_submit_{idx}.png")

            # Store tournament ID for later
            created_tournament_ids.append(tournament_name)

        # End of loop - all 6 tournaments created
        print(f"\n  {'='*70}")
        print(f"  ✅ All {len(tournaments_to_create)} tournaments created!")
        print(f"     - 3 APPLICATION_BASED tournaments")
        print(f"     - 3 OPEN_ASSIGNMENT tournaments")
        print(f"  {'='*70}\n")

        # ================================================================
        # Final Verification: Check all tournaments in backend API
        # ================================================================
        print("  8. Verifying all tournaments in backend API...")

        # Get admin token from environment or login
        admin_token_env = os.getenv("ADMIN_TOKEN")
        admin_token = None

        if admin_token_env:
            admin_token = admin_token_env
            print("  ✅ Using admin token from environment")
        else:
            # Login via API to get token
            login_response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": "admin@lfa.com", "password": "admin123"}
            )

            if login_response.status_code == 200:
                admin_token = login_response.json().get("access_token")
                print("  ✅ Obtained admin token via API login")
            else:
                print(f"  ⚠️  API login failed: {login_response.status_code}")

        backend_verified = False
        tournament_id = None

        if admin_token:
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Fetch semesters from API
            response = requests.get(f"{API_BASE_URL}/semesters", headers=headers)

            if response.status_code == 200:
                response_data = response.json()

                # Handle paginated response ({"semesters": [...], "total": N})
                if isinstance(response_data, dict) and "semesters" in response_data:
                    tournaments = response_data["semesters"]
                elif isinstance(response_data, list):
                    tournaments = response_data
                else:
                    # Unexpected format
                    print(f"  ⚠️  Unexpected API response format: {type(response_data)}")
                    tournaments = []

                # Look for all our tournaments
                found_count = 0
                for created_name in created_tournament_ids:
                    for t in tournaments:
                        full_name = t.get("name", "")
                        if created_name in full_name:
                            found_count += 1
                            print(f"  ✅ Tournament found: {full_name}")
                            print(f"      - ID: {t.get('id')}")
                            print(f"      - Status: {t.get('tournament_status')}")
                            print(f"      - Type ID: {t.get('tournament_type_id')}")
                            break

                if found_count == len(created_tournament_ids):
                    backend_verified = True
                    print(f"\n  ✅ All {found_count}/{len(created_tournament_ids)} tournaments verified in backend!")
                else:
                    print(f"\n  ⚠️  Only found {found_count}/{len(created_tournament_ids)} tournaments in API")
            else:
                print(f"  ❌ Failed to fetch semesters from API: {response.status_code}")

        # ================================================================
        # FINAL ASSERTIONS
        # ================================================================
        print("\n" + "="*80)

        if backend_verified:
            print("✅✅✅ TEST FULLY PASSED: All 3 tournaments created AND verified in database!")
            print(f"    Created tournaments: {created_tournament_ids}")
        else:
            print("❌ TEST FAILED: Not all tournaments verified in backend")

        print("="*80 + "\n")

        # Assert backend verification
        assert backend_verified, f"Not all tournaments were found in database after creation!"

        print(f"🎉 Test completed successfully! Created {len(created_tournament_ids)} tournaments")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ADMIN TOURNAMENT CREATION E2E TEST (REFACTORED)")
    print("="*80)
    print("\nRun with:")
    print("  pytest tests/e2e/test_admin_create_tournament_refactored.py -v --headed --slowmo=500")
    print("\nPrerequisites:")
    print("  - Backend running: http://localhost:8000")
    print("  - Frontend running: http://localhost:8501")
    print("  - Tournament types seeded (run: python scripts/seed_tournament_types.py)")
    print("  - At least one location and campus exist")
    print("="*80 + "\n")
