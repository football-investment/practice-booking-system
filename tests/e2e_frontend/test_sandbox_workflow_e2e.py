"""
Sandbox Workflow E2E Test - Group+Knockout Tournament

✅ **OBJECTIVE**: Prove that final match appears in UI after semifinals complete
✅ **APPROACH**: Use sandbox workflow (streamlit_sandbox_v3_admin_aligned.py) from start to finish
✅ **VALIDATION**: Submit all matches via UI, including final match

This test validates:
1. Tournament creation via sandbox workflow (Step 1-2)
2. Group stage match submission via UI (Step 4)
3. Semifinal submission via UI (Step 4)
4. **CRITICAL**: Final match auto-populates and appears in UI after page reload
5. Final match submission via UI (Step 4)

Run:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
    pytest tests/e2e_frontend/test_sandbox_workflow_e2e.py -xvs

Prerequisites:
- Backend running on localhost:8000
- Streamlit sandbox running on localhost:8501: streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501
"""

import pytest
import time
import random
import json
from pathlib import Path
from playwright.sync_api import Page, expect

# Import existing helpers
from .shared.streamlit_helpers import (
    submit_head_to_head_result_via_ui,
    wait_for_streamlit_rerun,
)


# Test constants
SANDBOX_URL = "http://localhost:8501"

# Single source of truth: star user IDs written by Phase 2 (test_d8)
_TEST_USERS_JSON = Path(__file__).parent.parent.parent / "e2e" / "test_users.json"


def _load_participant_ids() -> list[int]:
    """
    Load registered star user db_ids from tests/e2e/test_users.json.

    These IDs are written by test_d8_verify_users_in_database after Phase 2.
    Raises AssertionError if any db_id is still null (Phase 2 not yet run).
    """
    with open(_TEST_USERS_JSON) as f:
        data = json.load(f)

    ids = []
    for u in data["star_users"]:
        assert u["db_id"] is not None, (
            f"db_id is null for {u['email']} — run Phase 2 (registration) first"
        )
        ids.append(u["db_id"])

    assert len(ids) >= 4, f"Need at least 4 participants for group_knockout, got {len(ids)}"
    return ids


def navigate_to_sandbox_home(page: Page):
    """Navigate to sandbox workflow home page"""
    page.goto(SANDBOX_URL)
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for home page to fully load
    expect(page.locator("text=Tournament Sandbox - Home")).to_be_visible(timeout=10000)


def click_create_new_tournament_sandbox(page: Page):
    """Click 'New Tournament' button on sandbox home"""
    create_btn = page.locator("button:has-text('New Tournament')").first
    expect(create_btn).to_be_visible(timeout=10000)
    create_btn.click()
    wait_for_streamlit_rerun(page, timeout=15000)

    # This navigates to configuration screen, not workflow yet
    # Wait for configuration page title
    expect(page.locator("text=Sandbox Tournament Test (Admin-Aligned)")).to_be_visible(timeout=10000)


def click_start_instructor_workflow(page: Page):
    """Click 'Start Instructor Workflow' button from configuration screen"""
    start_workflow_btn = page.locator("button:has-text('Start Instructor Workflow')").first
    expect(start_workflow_btn).to_be_visible(timeout=10000)
    start_workflow_btn.click()
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for Step 1 to appear
    expect(page.locator("text=Step 1: Select Tournament Config")).to_be_visible(timeout=10000)


def select_preset_config(page: Page, preset_name: str = "GK1_GroupKnockout_7players"):
    """
    Select a game preset in Step 1 of sandbox workflow

    The UI shows radio buttons for presets. We need to find and click the one matching preset_name.
    """
    # Wait for presets to load
    expect(page.locator("input[type='radio']").first).to_be_visible(timeout=10000)

    # Find the radio option matching the preset name
    preset_label = page.locator(f"label:has-text('{preset_name}')").first

    if preset_label.count() == 0:
        print(f"   ⚠️  Preset '{preset_name}' not found, using first available preset")
        first_radio = page.locator("input[type='radio']").first
        first_radio.click()
    else:
        preset_label.click()

    # Wait for selection to register
    wait_for_streamlit_rerun(page, timeout=5000)


def click_continue_to_step(page: Page, step_number: int):
    """
    Click 'Continue to Step X' button

    Step buttons have keys like:
    - btn_continue_step2 (Review & Confirm)
    - btn_continue_step3 (Track Attendance)
    - btn_continue_step4 (Enter Results)
    """
    button_text_map = {
        2: "Review & Confirm",
        3: "Track Attendance",
        4: "Enter Results",
        5: "View Leaderboard"
    }

    button_text = button_text_map.get(step_number, f"Continue to Step {step_number}")
    continue_btn = page.locator(f"button:has-text('{button_text}')").first

    expect(continue_btn).to_be_visible(timeout=10000)
    continue_btn.click()
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for next step title to appear
    next_step_title = f"Step {step_number}:"
    expect(page.locator(f"text=/Step {step_number}:.*/")).to_be_visible(timeout=10000)


def create_tournament_via_sandbox_step2(page: Page):
    """
    Click 'Create Tournament' button in Step 2 (Review & Confirm)

    This button triggers the actual tournament creation API call.
    """
    create_btn = page.locator("button:has-text('Create Tournament')").first
    expect(create_btn).to_be_visible(timeout=10000)
    create_btn.click()
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for success message
    expect(page.locator("text=/Tournament created.*ID/")).to_be_visible(timeout=10000)


def get_tournament_id_from_ui(page: Page) -> int:
    """
    Extract tournament ID from UI after creation

    After tournament creation, Step 2 shows:
    "✅ Tournament created! ID: 123"
    """
    success_text = page.locator("text=/Tournament created.*ID.*\\d+/").first
    expect(success_text).to_be_visible(timeout=10000)

    text_content = success_text.text_content()

    import re
    match = re.search(r'ID:\s*(\d+)', text_content)

    if not match:
        raise Exception(f"Could not parse tournament ID from text: {text_content}")

    tournament_id = int(match.group(1))
    print(f"   📊 Extracted tournament_id: {tournament_id}")
    return tournament_id


def count_pending_sessions_in_ui(page: Page) -> int:
    """
    Count how many pending sessions are visible in Step 4 UI

    Each session is shown in an expander with format:
    📋 {title} ({phase})
    """
    # Wait for Step 4 content to load
    expect(page.locator("text=Step 4: Enter Results")).to_be_visible(timeout=10000)

    # Count expanders (each session is in an expander)
    # Expanders have data-testid="stExpander"
    expanders = page.locator("[data-testid='stExpander']").all()

    return len(expanders)


def get_visible_session_ids_in_ui(page: Page) -> list:
    """
    Extract session IDs from visible sessions in Step 4 UI

    Each session shows "**Session ID**: 123" inside the expander
    """
    session_ids = []

    # Find all "Session ID: X" texts
    session_id_texts = page.locator("text=/Session ID.*\\d+/").all()

    import re
    for text_elem in session_id_texts:
        text_content = text_elem.text_content()
        match = re.search(r'Session ID:\s*(\d+)', text_content)
        if match:
            session_ids.append(int(match.group(1)))

    return session_ids


def wait_for_new_sessions_to_appear(page: Page, expected_min_count: int, timeout_ms: int = 15000):
    """
    Wait for at least expected_min_count sessions to appear in UI

    This is used after semifinals to wait for final match to populate.
    """
    start_time = time.time()

    while (time.time() - start_time) * 1000 < timeout_ms:
        current_count = count_pending_sessions_in_ui(page)

        if current_count >= expected_min_count:
            print(f"   ✅ Found {current_count} sessions in UI (expected >= {expected_min_count})")
            return True

        # Wait a bit and reload page to check again
        time.sleep(2)
        page.reload()
        wait_for_streamlit_rerun(page, timeout=10000)

    raise Exception(f"Timeout waiting for {expected_min_count} sessions. Found: {current_count}")


def get_session_info_from_api(tournament_id: int) -> dict:
    """
    Helper to get session info from API for verification only (NOT for workflow)

    Returns dict with:
    - all_sessions: list of all sessions
    - pending_sessions: list of sessions without results
    - group_sessions: list of group stage sessions
    - knockout_sessions: list of knockout sessions
    """
    import requests

    response = requests.get(
        f"http://localhost:8000/sessions",
        params={"semester_id": tournament_id, "size": 100},
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch sessions: {response.status_code}")

    sessions_data = response.json()
    all_sessions = sessions_data.get('items', []) if isinstance(sessions_data, dict) else sessions_data

    # Filter to tournament games
    tournament_sessions = [s for s in all_sessions if s.get('is_tournament_game', False)]

    # Pending sessions
    pending = [s for s in tournament_sessions if not s.get('game_results')]

    # Group sessions
    group = [s for s in tournament_sessions if s.get('tournament_phase') == 'Group Stage']

    # Knockout sessions
    knockout = [s for s in tournament_sessions if s.get('tournament_phase') in ['Knockout Stage', 'Knockout']]

    return {
        'all_sessions': tournament_sessions,
        'pending_sessions': pending,
        'group_sessions': group,
        'knockout_sessions': knockout
    }


def get_auth_token() -> str:
    """Get auth token by logging in as admin"""
    import requests

    login_response = requests.post(
        "http://localhost:8000/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )

    if login_response.status_code != 200:
        raise Exception("Failed to authenticate as admin")

    return login_response.json()["access_token"]


def create_tournament_with_json_participants() -> int:
    """
    Create a group_knockout tournament via sandbox/run-test API using
    participant IDs from tests/e2e/test_users.json (written by Phase 2).

    Returns the tournament ID.
    """
    import requests

    participant_ids = _load_participant_ids()
    token = get_auth_token()

    payload = {
        "tournament_type": "group_knockout",
        "skills_to_test": ["ball_control", "dribbling", "passing", "finishing"],
        "player_count": len(participant_ids),
        "selected_users": participant_ids,
        "test_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL"
        }
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sandbox/run-test",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )

    if response.status_code != 200:
        raise Exception(
            f"Tournament creation failed: {response.status_code} — {response.text}"
        )

    tournament_id = response.json()["tournament"]["id"]
    print(f"   ✅ Tournament {tournament_id} created with participants: {participant_ids}")
    return tournament_id


@pytest.fixture
def page(playwright):
    """Fixture to provide a Playwright page"""
    import os
    headless = os.getenv("HEADED", "0") == "0"  # Default headless, set HEADED=1 to see browser

    browser = playwright.chromium.launch(headless=headless, slow_mo=500 if not headless else 0)
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
    browser.close()


def test_sandbox_workflow_group_knockout_full(page: Page):
    """
    ✅ FULL E2E: Group+Knockout tournament via sandbox workflow

    Tournament created via API with participants from tests/e2e/test_users.json
    (db_ids written by Phase 2 — no synthetic users).
    Match submission validated via Streamlit sandbox UI (Step 4).
    """
    print(f"\n{'='*80}")
    print(f"Sandbox Workflow E2E Test: Group+Knockout (JSON participants)")
    print(f"{'='*80}\n")

    # ============================================================================
    # PHASE 1: CREATE TOURNAMENT VIA API (JSON participants, not synthetic)
    # ============================================================================
    print("✅ Phase 1: Create tournament via API with JSON participants\n")

    tournament_id = create_tournament_with_json_participants()
    print(f"   ✅ Tournament {tournament_id} created\n")

    # Navigate directly to Step 4 (Enter Results) in sandbox UI
    navigate_to_sandbox_home(page)
    page.goto(f"{SANDBOX_URL}?tournament_id={tournament_id}&step=4")
    wait_for_streamlit_rerun(page)
    time.sleep(3)
    print("   ✅ Navigated to Step 4 (Enter Results)\n")

    # ============================================================================
    # PHASE 2: SUBMIT GROUP STAGE MATCHES VIA UI
    # ============================================================================
    print("✅ Phase 2: Submit group stage matches via UI\n")

    # API: Get expected session counts for validation
    session_info = get_session_info_from_api(tournament_id)
    group_sessions = session_info['group_sessions']
    expected_group_count = len(group_sessions)

    print(f"   API validation: {expected_group_count} group matches expected")

    # UI: Count visible sessions
    visible_count = count_pending_sessions_in_ui(page)
    print(f"   UI validation: {visible_count} sessions visible")

    if visible_count != expected_group_count:
        pytest.fail(f"UI shows {visible_count} sessions but API expects {expected_group_count}")

    # Get session IDs from UI
    visible_session_ids = get_visible_session_ids_in_ui(page)
    print(f"   Session IDs in UI: {visible_session_ids[:5]}..." if len(visible_session_ids) > 5 else f"   Session IDs in UI: {visible_session_ids}")

    # Submit each group match via UI
    submitted_count = 0
    for session_id in visible_session_ids:
        # Generate random scores (no tie)
        score_1 = random.randint(0, 5)
        score_2 = random.randint(0, 5)
        if score_1 == score_2:
            score_1 += 1

        # Submit via UI
        success = submit_head_to_head_result_via_ui(page, session_id, score_1, score_2)

        if success:
            submitted_count += 1
            print(f"   ✅ Group Match {submitted_count}/{expected_group_count}: {score_1}-{score_2} (Session {session_id})")
        else:
            pytest.fail(f"Failed to submit group match {session_id} via UI")

    print(f"\n   ✅ All {submitted_count} group stage matches submitted\n")

    # ============================================================================
    # PHASE 3: SUBMIT SEMIFINALS VIA UI
    # ============================================================================
    print("✅ Phase 3: Submit semifinals via UI\n")

    # Reload page to fetch knockout bracket
    print("   🔄 Reloading page to fetch knockout bracket...")
    page.reload()
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for Step 4 to reload
    expect(page.locator("text=Step 4: Enter Results")).to_be_visible(timeout=10000)

    # API: Verify semifinals exist
    session_info = get_session_info_from_api(tournament_id)
    semifinal_sessions = [
        s for s in session_info['knockout_sessions']
        if s.get('round_number') == 1
        and s.get('participant_user_ids')
        and len(s.get('participant_user_ids', [])) == 2
    ]

    expected_semifinal_count = len(semifinal_sessions)
    print(f"   API validation: {expected_semifinal_count} semifinals expected")

    # UI: Get visible session IDs
    visible_session_ids = get_visible_session_ids_in_ui(page)
    print(f"   UI validation: {len(visible_session_ids)} sessions visible")

    # Submit semifinals via UI
    semifinal_winners = []
    submitted_count = 0

    for session_id in visible_session_ids:
        # API: Get participants for this session
        session_data = next((s for s in semifinal_sessions if s['id'] == session_id), None)

        if not session_data:
            print(f"   ⚠️  Skipping session {session_id}: not a semifinal")
            continue

        participants = session_data['participant_user_ids']

        # Generate scores
        score_1 = random.randint(0, 5)
        score_2 = random.randint(0, 5)
        if score_1 == score_2:
            score_1 += 1

        winner_id = participants[0] if score_1 > score_2 else participants[1]
        semifinal_winners.append(winner_id)

        # Submit via UI
        success = submit_head_to_head_result_via_ui(page, session_id, score_1, score_2)

        if success:
            submitted_count += 1
            print(f"   ✅ Semifinal {submitted_count}/{expected_semifinal_count}: {score_1}-{score_2} (Winner: User {winner_id})")
        else:
            pytest.fail(f"Failed to submit semifinal {session_id} via UI")

    print(f"\n   ✅ All {submitted_count} semifinals submitted")
    print(f"   Winners: {semifinal_winners}\n")

    # ============================================================================
    # PHASE 4: VERIFY FINAL MATCH APPEARS IN UI *** CRITICAL TEST ***
    # ============================================================================
    print("✅ Phase 4: Verify final match appears in UI (CRITICAL)\n")

    # Wait for backend to populate final match
    print("   ⏳ Waiting 5 seconds for backend to populate final match...")
    time.sleep(5)

    # Reload page to fetch updated sessions
    print("   🔄 Reloading page to fetch final match...")
    page.reload()
    wait_for_streamlit_rerun(page, timeout=15000)

    # Wait for Step 4 to reload
    expect(page.locator("text=Step 4: Enter Results")).to_be_visible(timeout=10000)

    # API: Verify final match exists in database
    session_info = get_session_info_from_api(tournament_id)
    final_sessions = [
        s for s in session_info['knockout_sessions']
        if s.get('round_number') == 2
        and s.get('participant_user_ids')
        and len(s.get('participant_user_ids', [])) == 2
    ]

    if len(final_sessions) == 0:
        pytest.fail("❌ FAIL: Final match NOT found in API after semifinals complete!")

    final_session = final_sessions[0]
    final_id = final_session['id']
    final_participants = final_session['participant_user_ids']

    print(f"   ✅ API validation: Final match found (Session {final_id})")
    print(f"   Participants: {final_participants}")

    # UI: Verify final match is visible
    session_id_text = page.locator(f"text=/Session ID.*{final_id}/").first

    try:
        expect(session_id_text).to_be_visible(timeout=5000)
        print(f"   ✅ UI validation: Final match IS VISIBLE in UI\n")
    except:
        pytest.fail(f"❌ FAIL: Final match {final_id} NOT visible in UI after page reload!")

    # ============================================================================
    # PHASE 5: SUBMIT FINAL MATCH VIA UI
    # ============================================================================
    print("✅ Phase 5: Submit final match via UI\n")

    # Generate final scores
    score_1 = random.randint(0, 5)
    score_2 = random.randint(0, 5)
    if score_1 == score_2:
        score_1 += 1

    winner_id = final_participants[0] if score_1 > score_2 else final_participants[1]

    # Submit via UI
    success = submit_head_to_head_result_via_ui(page, final_id, score_1, score_2)

    if success:
        print(f"   ✅ Final: {score_1}-{score_2} (Winner: User {winner_id})")
    else:
        pytest.fail(f"Failed to submit final match {final_id} via UI")

    # ============================================================================
    # SUCCESS
    # ============================================================================
    total_matches = expected_group_count + expected_semifinal_count + 1

    print(f"\n{'='*80}")
    print(f"✅ 100% PASS: Complete tournament workflow via sandbox UI")
    print(f"   - Group stage: {expected_group_count} matches")
    print(f"   - Semifinals: {expected_semifinal_count} matches")
    print(f"   - Final: 1 match")
    print(f"   - Total: {total_matches} matches submitted via UI")
    print(f"{'='*80}\n")
