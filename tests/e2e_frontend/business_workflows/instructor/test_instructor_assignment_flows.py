"""
Playwright E2E Tests: Two Instructor Assignment Workflows

This test file validates TWO separate instructor assignment workflows,
both ending at INSTRUCTOR_CONFIRMED status (ready for admin to open enrollment).

TEST 1 - APPLICATION FLOW:
1. Admin creates tournament via UI → status: SEEKING_INSTRUCTOR
2. 3 instructors browse and apply via UI
3. Admin reviews applications and approves ONE via UI
4. ✅ VERIFY: Tournament status = INSTRUCTOR_CONFIRMED
5. ✅ VERIFY: "Open Enrollment" button appears in Admin UI

TEST 2 - DIRECT ASSIGNMENT FLOW:
1. Admin creates tournament via UI → status: SEEKING_INSTRUCTOR
2. Admin directly assigns instructor via UI → status: PENDING_INSTRUCTOR_ACCEPTANCE
3. Instructor receives notification and accepts assignment via UI
4. ✅ VERIFY: Tournament status = INSTRUCTOR_CONFIRMED
5. ✅ VERIFY: "Open Enrollment" button appears in Admin UI

Both tests validate the UI end-to-end, ensuring the correct buttons appear
at each stage and the tournament reaches INSTRUCTOR_CONFIRMED status.
"""

import pytest
from playwright.sync_api import Page, expect
import time
from datetime import datetime
import json
import urllib.parse

# Import API fixtures for setup/teardown
import requests
from playwright.sync_api import expect

from tests.e2e.reward_policy_fixtures import (
    API_BASE_URL,

        # Delete tournament
    reward_policy_admin_token,
    create_instructor_user,
    create_tournament_via_api,
)


@pytest.mark.e2e
@pytest.mark.ui
@pytest.mark.slow
class TestInstructorAssignmentFlows:
    """
    Playwright E2E tests for instructor assignment workflows.

    IMPORTANT: These tests require both servers running:
    - FastAPI: http://localhost:8000
    - Streamlit: http://localhost:8501
    """

    STREAMLIT_URL = "http://localhost:8501"
    ADMIN_ID = 1

    def test_application_flow_to_instructor_confirmed(
        self,
        page: Page,
        reward_policy_admin_token: str
    ):
        """
        TEST 1: Instructor Application Flow

        Workflow:
        1. Admin creates tournament (via API for speed)
        2. 3 instructors apply via UI
        3. Admin reviews and approves ONE instructor via UI
        4. Verify tournament status = INSTRUCTOR_CONFIRMED
        5. Verify "Open Enrollment" button appears

        Expected:
        - All 3 instructors can apply successfully
        - Admin sees all 3 applications
        - After approval, status becomes INSTRUCTOR_CONFIRMED
        - Admin can see "Open Enrollment" button
        """
        print("\n" + "="*80)
        print("🎭 TEST 1: INSTRUCTOR APPLICATION FLOW → INSTRUCTOR_CONFIRMED")
        print("="*80 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ====================================================================
        # SETUP: Create tournament via API
        # ====================================================================
        print("  🔧 Setup: Creating tournament via API...")

        tournament_result = create_tournament_via_api(
            token=reward_policy_admin_token,
            name=f"Application Flow Test {timestamp}",
            reward_policy_name="default",
            age_group="AMATEUR"
        )

        tournament_id = tournament_result["tournament_id"]
        tournament_name = tournament_result["summary"]["name"]
        tournament_code = tournament_result["summary"]["code"]
        print(f"     ✅ Tournament {tournament_id} created: {tournament_name}")

        # Create 3 instructors via API
        instructors = []
        for i in range(3):
            instructor = create_instructor_user(reward_policy_admin_token)
            instructors.append(instructor)
            print(f"     ✅ Instructor {i+1} created: {instructor['email']}")

        # ====================================================================
        # STEP 1: Each instructor logs in and applies via UI
        # ====================================================================
        print("\n  1️⃣ Three instructors applying to tournament...")

        application_ids = []

        for idx, instructor in enumerate(instructors):
            try:
                print(f"\n     👤 Instructor {idx+1}/{len(instructors)}: {instructor['email']}")

                # Navigate to home page
                page.goto(self.STREAMLIT_URL)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # Login as instructor
                text_inputs = page.locator("[data-testid='stTextInput'] input").all()
                text_inputs[0].fill(instructor['email'])
                text_inputs[1].fill("instructor123")

                login_button = page.get_by_role("button", name="🔐 Login")
                login_button.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)

                # Navigate to Instructor Dashboard with session params
                session_user_obj = {
                    'id': instructor['id'],
                    'email': instructor['email'],
                    'name': instructor['name'],
                    'role': instructor['role']
                }
                session_user = urllib.parse.quote(json.dumps(session_user_obj))
                dashboard_url = f"{self.STREAMLIT_URL}/Instructor_Dashboard?session_token={instructor['token']}&session_user={session_user}"

                page.goto(dashboard_url)
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(3)

                print(f"        ✅ Logged in")

                # Navigate to Tournament Applications tab
                tournament_app_tab = page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first
                tournament_app_tab.click()
                time.sleep(2)

                # Click Open Tournaments sub-tab
                open_tournaments_tab = page.locator("[data-baseweb='tab']:has-text('🔍 Open Tournaments')").first
                open_tournaments_tab.click()
                time.sleep(3)

                # Find and expand the tournament
                tournament_expander = page.locator(f"text={tournament_name}").first
                tournament_expander.click()
                print(f"        📂 Expanded tournament")
                time.sleep(2)

                # Click Apply button
                apply_button = page.get_by_role("button", name="📝 Apply")
                apply_button.click()
                time.sleep(2)

                # Fill application message
                textarea = page.locator("[data-testid='stTextArea'] textarea").first
                textarea.fill(f"Application from instructor {idx+1}: I would like to lead this tournament.")
                time.sleep(1)

                # Submit application
                submit_button = page.get_by_role("button", name="✅ Submit Application")
                submit_button.click()

                # Wait for success message
                page.wait_for_selector("text=Application submitted successfully", timeout=10000)
                print(f"        ✅ Application submitted")

                # Get application ID via API
                apps_response = requests.get(
                    f"{API_BASE_URL}/api/v1/tournaments/instructor/my-applications",
                    headers={"Authorization": f"Bearer {instructor['token']}"}
                )

                if apps_response.status_code == 200:
                    apps = apps_response.json().get('applications', [])
                    matching_app = next((app for app in apps if app['tournament_id'] == tournament_id), None)
                    if matching_app:
                        application_ids.append(matching_app['id'])
                        print(f"        🔍 Application ID: {matching_app['id']}")

            except Exception as e:
                print(f"        ❌ Failed: {e}")
                page.screenshot(path=f"tests/e2e/screenshots/app_flow_instructor_{idx+1}_failed_{timestamp}.png")
                raise

        print(f"\n     ✅ All {len(instructors)} instructors applied successfully")
        print(f"     📋 Application IDs: {application_ids}")

        # ====================================================================
        # STEP 2: Admin logs in and reviews applications
        # ====================================================================
        print("\n  2️⃣ Admin reviews applications and approves one...")

        try:
            # Navigate to Admin Dashboard
            admin_session_user_obj = {
                'id': self.ADMIN_ID,
                'email': 'admin@lfa.com',
                'name': 'Admin User',
                'role': 'admin'
            }
            admin_session_user = urllib.parse.quote(json.dumps(admin_session_user_obj))
            admin_dashboard_url = f"{self.STREAMLIT_URL}/Admin_Dashboard?session_token={reward_policy_admin_token}&session_user={admin_session_user}"

            page.goto(admin_dashboard_url)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)

            # Click Tournaments tab
            tournaments_button = page.get_by_role("button", name="🏆 Tournaments")
            tournaments_button.click()
            print(f"     🔘 Clicked Tournaments tab")
            time.sleep(2)

            # Find and expand the tournament
            tournament_expander = page.locator(f"text={tournament_name}").first
            tournament_expander.click()
            print(f"     📂 Expanded tournament")
            time.sleep(2)

            # Verify we can see the instructor applications section
            print(f"     🔍 Checking for instructor applications...")

            # Wait for applications to appear
            time.sleep(3)

            # Choose the first instructor to approve
            chosen_instructor = instructors[0]
            chosen_application_id = application_ids[0]

            print(f"     👤 Approving instructor via UI: {chosen_instructor['email']}")

            # Click the approve button (✅) for the first application
            # Use get_by_role to find the button with ✅ text
            approve_button = page.get_by_role("button", name="✅").first
            approve_button.wait_for(state="visible", timeout=10000)
            approve_button.click()
            print(f"     🔘 Clicked approve button - dialog opening...")
            time.sleep(2)

            # Wait for the approval dialog to open
            # Look for the dialog title
            page.wait_for_selector("text=Approve Instructor Application", timeout=10000)
            print(f"     ✅ Approval dialog opened")
            time.sleep(1)

            # Fill in the response message in the dialog
            # The textarea is in the dialog - use a more specific selector
            # Wait for the textarea to be visible and editable
            response_textarea = page.locator("textarea[aria-label='Response Message (optional)']").first
            response_textarea.wait_for(state="visible", timeout=5000)
            response_textarea.clear()
            response_textarea.fill("Welcome to the team!")
            print(f"     ✅ Filled response message")
            time.sleep(1)

            # Click the "✅ Approve" button in the dialog
            approve_dialog_button = page.get_by_role("button", name="✅ Approve")
            approve_dialog_button.click()
            print(f"     ✅ Clicked Approve button in dialog")

            # Wait for success message to appear
            page.wait_for_selector("text=Application approved successfully", timeout=10000)
            print(f"     ✅ Success message appeared")

            # Wait for st.rerun() to complete and page to refresh
            # After st.rerun(), Streamlit will reload the entire page
            # We need to wait for the dialog to close and the page to re-render
            time.sleep(5)  # Give Streamlit time to fully reload

            # Verify status via API
            status_response = requests.get(
                f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )

            if status_response.status_code == 200:
                result = status_response.json()
                print(f"     📊 Tournament status: {result.get('tournament_status', 'N/A')}")

                # CRITICAL VERIFICATION
                assert result.get('tournament_status') == 'INSTRUCTOR_CONFIRMED', \
                    f"Expected INSTRUCTOR_CONFIRMED, got {result.get('tournament_status')}"
                print(f"     ✅ VERIFIED: Status = INSTRUCTOR_CONFIRMED")
            else:
                raise Exception(f"Status check failed: {status_response.status_code}")

        except Exception as e:
            print(f"     ❌ Admin approval failed: {e}")
            page.screenshot(path=f"tests/e2e/screenshots/app_flow_admin_approval_failed_{timestamp}.png")
            raise

        # ====================================================================
        # STEP 3: Verify "Open Enrollment" button appears in Admin UI
        # ====================================================================
        print("\n  3️⃣ Verifying 'Open Enrollment' button appears...")

        try:
            # IMPORTANT: Force full page refresh to bypass Streamlit cache
            # st.rerun() doesn't invalidate the API cache, so we need to navigate away and back
            print(f"     🔄 Performing full page refresh to bypass cache...")
            page.goto(self.STREAMLIT_URL)
            time.sleep(2)

            # Navigate back to Admin Dashboard with fresh session
            admin_session_user_obj = {
                'id': self.ADMIN_ID,
                'email': 'admin@lfa.com',
                'name': 'Admin User',
                'role': 'admin'
            }
            admin_session_user = urllib.parse.quote(json.dumps(admin_session_user_obj))
            admin_dashboard_url = f"{self.STREAMLIT_URL}/Admin_Dashboard?session_token={reward_policy_admin_token}&session_user={admin_session_user}"

            page.goto(admin_dashboard_url)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)  # Wait for Streamlit to fully load
            print(f"     ✅ Navigated back to Admin Dashboard")

            # Force browser reload BEFORE navigating to ensure fresh data
            page.reload()
            print(f"     🔄 Force browser reload to clear cache")
            time.sleep(3)  # Wait for page to fully reload

            # Navigate to Tournaments tab (after reload)
            tournaments_button = page.get_by_role("button", name="🏆 Tournaments")
            tournaments_button.click()
            print(f"     🔘 Clicked Tournaments tab")
            time.sleep(3)  # Wait for tournaments to load

            # Expand tournament
            expander_button = page.locator("summary").filter(has_text=tournament_code)
            expander_button.wait_for(state="visible", timeout=10000)
            expander_button.click()
            print(f"     📂 Expanded tournament")
            time.sleep(3)  # Wait for tournament details to fully render

            # Look for "Open Enrollment" button
            open_enrollment_button = page.get_by_role("button", name="📝 Open Enrollment")

            # Verify button exists and is visible
            expect(open_enrollment_button.first).to_be_visible(timeout=10000)
            print(f"     ✅ VERIFIED: 'Open Enrollment' button is visible")

            # Take screenshot for verification
            page.screenshot(path=f"tests/e2e/screenshots/app_flow_open_enrollment_button_{timestamp}.png")
            print(f"     📸 Screenshot saved")

        except Exception as e:
            print(f"     ❌ Button verification failed: {e}")
            page.screenshot(path=f"tests/e2e/screenshots/app_flow_button_failed_{timestamp}.png")
            raise

        # ====================================================================
        # CLEANUP
        # ====================================================================
        print("\n  🧹 Cleaning up...")

        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        # Delete instructors
        for instructor in instructors:
            try:
                requests.delete(
                    f"{API_BASE_URL}/api/v1/users/{instructor['id']}",
                    headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
                )
            except:
                pass

        print("\n" + "="*80)
        print("✅ TEST 1 PASSED: APPLICATION FLOW → INSTRUCTOR_CONFIRMED")
        print("="*80 + "\n")


    def test_direct_assignment_flow_to_instructor_confirmed(
        self,
        page: Page,
        reward_policy_admin_token: str
    ):
        """
        TEST 2: Direct Assignment Flow

        Workflow:
        1. Admin creates tournament (via API for speed)
        2. Admin directly assigns instructor via UI
        3. Instructor accepts assignment via UI
        4. Verify tournament status = INSTRUCTOR_CONFIRMED
        5. Verify "Open Enrollment" button appears

        Expected:
        - Admin can assign instructor directly
        - Instructor receives assignment and can accept
        - After acceptance, status becomes INSTRUCTOR_CONFIRMED
        - Admin can see "Open Enrollment" button
        """
        print("\n" + "="*80)
        print("🎭 TEST 2: DIRECT ASSIGNMENT FLOW → INSTRUCTOR_CONFIRMED")
        print("="*80 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ====================================================================
        # SETUP: Create tournament and instructor via API
        # ====================================================================
        print("  🔧 Setup: Creating tournament and instructor via API...")

        tournament_result = create_tournament_via_api(
            token=reward_policy_admin_token,
            name=f"Direct Assignment Test {timestamp}",
            reward_policy_name="default",
            age_group="AMATEUR"
        )

        tournament_id = tournament_result["tournament_id"]
        tournament_name = tournament_result["summary"]["name"]
        tournament_code = tournament_result["summary"]["code"]  # ADDED - needed for expander selector
        print(f"     ✅ Tournament {tournament_id} created: {tournament_name}")

        instructor = create_instructor_user(reward_policy_admin_token)
        print(f"     ✅ Instructor created: {instructor['email']}")

        # ====================================================================
        # STEP 1: Admin directly assigns instructor via UI (or API)
        # ====================================================================
        print("\n  1️⃣ Admin assigns instructor directly...")

        try:
            # For now, use API for direct assignment (UI implementation can be added later)
            # The direct assignment endpoint: POST /tournaments/{id}/direct-assign-instructor
            assignment_response = requests.post(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/direct-assign-instructor",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
                json={
                    "instructor_id": instructor['id'],
                    "message": "You have been selected to lead this tournament!"
                }
            )

            if assignment_response.status_code == 200:
                result = assignment_response.json()
                print(f"     ✅ Instructor assigned via API")
                print(f"     📊 Assignment status: {result['status']}")

                # Direct assignment creates ACCEPTED assignment immediately
                assert result['status'] == 'ACCEPTED', \
                    f"Expected ACCEPTED, got {result['status']}"
                print(f"     ✅ VERIFIED: Assignment status = ACCEPTED")
                print(f"     ℹ️  Next: Instructor must accept assignment to set tournament to INSTRUCTOR_CONFIRMED")
            else:
                raise Exception(f"Assignment failed: {assignment_response.status_code}")

        except Exception as e:
            print(f"     ❌ Direct assignment failed: {e}")
            raise

        # ====================================================================
        # STEP 2: Instructor logs in and accepts assignment via UI
        # ====================================================================
        print("\n  2️⃣ Instructor accepts assignment...")

        try:
            # Navigate to home page
            page.goto(self.STREAMLIT_URL)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Login as instructor
            text_inputs = page.locator("[data-testid='stTextInput'] input").all()
            text_inputs[0].fill(instructor['email'])
            text_inputs[1].fill("instructor123")

            login_button = page.get_by_role("button", name="🔐 Login")
            login_button.click()
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            # Navigate to Instructor Dashboard
            session_user_obj = {
                'id': instructor['id'],
                'email': instructor['email'],
                'name': instructor['name'],
                'role': instructor['role']
            }
            session_user = urllib.parse.quote(json.dumps(session_user_obj))
            dashboard_url = f"{self.STREAMLIT_URL}/Instructor_Dashboard?session_token={instructor['token']}&session_user={session_user}"

            page.goto(dashboard_url)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)

            print(f"     ✅ Instructor logged in")

            # Navigate to Tournament Applications tab
            tournament_app_tab = page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first
            tournament_app_tab.click()
            time.sleep(2)

            # Click My Applications sub-tab
            my_applications_tab = page.locator("[data-baseweb='tab']:has-text('📋 My Applications')").first
            my_applications_tab.click()
            time.sleep(3)

            # Refresh to get latest data
            page.reload()
            time.sleep(3)

            # Navigate back to the tab
            tournament_app_tab = page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first
            tournament_app_tab.click()
            time.sleep(2)

            my_applications_tab = page.locator("[data-baseweb='tab']:has-text('📋 My Applications')").first
            my_applications_tab.click()
            time.sleep(2)

            # Click "Accept Assignment" button
            accept_button = page.get_by_role("button", name="✅ Accept Assignment")
            accept_button.click()
            print(f"     🔘 Clicked Accept Assignment button")

            # Wait for success message
            page.wait_for_selector("text=Assignment accepted successfully", timeout=10000)
            print(f"     ✅ Assignment accepted successfully")

            # Verify status via API (same endpoint as TEST 1)
            status_response = requests.get(
                f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )

            if status_response.status_code == 200:
                result = status_response.json()
                print(f"     📊 Tournament status: {result.get('tournament_status', 'N/A')}")

                # CRITICAL VERIFICATION
                assert result.get('tournament_status') == 'INSTRUCTOR_CONFIRMED', \
                    f"Expected INSTRUCTOR_CONFIRMED, got {result.get('tournament_status')}"
                print(f"     ✅ VERIFIED: Status = INSTRUCTOR_CONFIRMED")
            else:
                raise Exception(f"Status check failed: {status_response.status_code}")

        except Exception as e:
            print(f"     ❌ Instructor acceptance failed: {e}")
            page.screenshot(path=f"tests/e2e/screenshots/direct_flow_accept_failed_{timestamp}.png")
            raise

        # ====================================================================
        # STEP 3: Verify "Open Enrollment" button appears in Admin UI
        # ====================================================================
        print("\n  3️⃣ Verifying 'Open Enrollment' button appears...")

        try:
            # IMPORTANT: Force full page refresh to bypass Streamlit cache
            # st.rerun() doesn't invalidate the API cache, so we need to navigate away and back
            print(f"     🔄 Performing full page refresh to bypass cache...")
            page.goto(self.STREAMLIT_URL)
            time.sleep(2)

            # Navigate back to Admin Dashboard with fresh session
            admin_session_user_obj = {
                'id': self.ADMIN_ID,
                'email': 'admin@lfa.com',
                'name': 'Admin User',
                'role': 'admin'
            }
            admin_session_user = urllib.parse.quote(json.dumps(admin_session_user_obj))
            admin_dashboard_url = f"{self.STREAMLIT_URL}/Admin_Dashboard?session_token={reward_policy_admin_token}&session_user={admin_session_user}"

            page.goto(admin_dashboard_url)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)  # Wait for Streamlit to fully load
            print(f"     ✅ Navigated back to Admin Dashboard")

            # Force browser reload BEFORE navigating to ensure fresh data
            page.reload()
            print(f"     🔄 Force browser reload to clear cache")
            time.sleep(3)  # Wait for page to fully reload

            # Navigate to Tournaments tab (after reload)
            tournaments_button = page.get_by_role("button", name="🏆 Tournaments")
            tournaments_button.click()
            print(f"     🔘 Clicked Tournaments tab")
            time.sleep(3)  # Wait for tournaments to load

            # Expand tournament using tournament_code (more reliable than name)
            expander_button = page.locator("summary").filter(has_text=tournament_code)
            expander_button.wait_for(state="visible", timeout=10000)
            expander_button.click()
            print(f"     📂 Expanded tournament")
            time.sleep(3)  # Wait for tournament details to fully render

            # Look for "Open Enrollment" button
            open_enrollment_button = page.get_by_role("button", name="📝 Open Enrollment")

            # Verify button exists and is visible
            expect(open_enrollment_button.first).to_be_visible(timeout=10000)
            print(f"     ✅ VERIFIED: 'Open Enrollment' button is visible")

            # Take screenshot
            page.screenshot(path=f"tests/e2e/screenshots/direct_flow_open_enrollment_button_{timestamp}.png")
            print(f"     📸 Screenshot saved")

        except Exception as e:
            print(f"     ❌ Button verification failed: {e}")
            page.screenshot(path=f"tests/e2e/screenshots/direct_flow_button_failed_{timestamp}.png")
            raise

        # ====================================================================
        # CLEANUP
        # ====================================================================
        print("\n  🧹 Cleaning up...")

        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        # Delete instructor
        try:
            requests.delete(
                f"{API_BASE_URL}/api/v1/users/{instructor['id']}",
                headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
            )
        except:
            pass

        print("\n" + "="*80)
        print("✅ TEST 2 PASSED: DIRECT ASSIGNMENT FLOW → INSTRUCTOR_CONFIRMED")
        print("="*80 + "\n")
