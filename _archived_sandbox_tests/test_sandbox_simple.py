"""
Simple proof-of-concept test: Group+Knockout via sandbox UI

Just proves:
1. Group stage results submitted via UI
2. Semifinals submitted via UI
3. Final appears in UI after semifinals
4. Final result submitted via UI
"""
import time
import random
from playwright.sync_api import sync_playwright

SANDBOX_URL = "http://localhost:8501"

def wait_streamlit(page, timeout_ms=10000):
    """Wait for Streamlit to finish rerunning"""
    try:
        page.wait_for_selector("[data-testid='stApp']", state="attached", timeout=timeout_ms)
        time.sleep(1)
    except:
        pass

def submit_match_result(page, session_id, score1, score2):
    """Submit HEAD_TO_HEAD result via UI"""
    # Find "Session ID: {session_id}" text
    session_text = page.locator(f"text=/Session ID.*{session_id}/").first

    if session_text.count() == 0:
        print(f"   ⚠️  Session {session_id} NOT FOUND in UI")
        return False

    # Find score inputs - they're number inputs near the session ID text
    # Get parent container
    container = session_text.locator("xpath=ancestor::div[@data-testid='stExpander']").first

    # Find number inputs in this container
    inputs = container.locator("input[type='number']").all()

    if len(inputs) < 2:
        print(f"   ⚠️  Score inputs not found for session {session_id}")
        return False

    # Fill scores
    inputs[0].fill(str(score1))
    inputs[1].fill(str(score2))

    # Click submit button in this container
    submit_btn = container.locator("button:has-text('Submit Result')").first
    submit_btn.click()

    wait_streamlit(page, timeout_ms=15000)

    # Verify database write
    import psycopg2
    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost"
    )
    cur = conn.cursor()
    cur.execute("SELECT game_results FROM sessions WHERE id = %s", (session_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result and result[0]:
        print(f"   ✅ Match {session_id}: {score1}-{score2} (DB verified)")
        return True
    else:
        print(f"   ❌ Match {session_id}: DB write FAILED")
        return False

def get_pending_sessions(tournament_id):
    """Get pending sessions from database"""
    import psycopg2
    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tournament_phase, round_number, participant_user_ids, game_results
        FROM sessions
        WHERE semester_id = %s
        AND is_tournament_game = true
        ORDER BY tournament_phase, round_number, id
    """, (tournament_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    sessions = []
    for row in rows:
        sessions.append({
            'id': row[0],
            'tournament_phase': row[1],
            'round_number': row[2],
            'participant_user_ids': row[3],
            'game_results': row[4]
        })

    return [s for s in sessions if not s['game_results']]

def main():
    print("\n" + "="*80)
    print("SIMPLE SANDBOX E2E TEST: Group+Knockout")
    print("="*80 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()

        try:
            # Navigate to sandbox
            print("📍 Step 1: Navigate to sandbox...")
            page.goto(SANDBOX_URL)
            wait_streamlit(page)

            # Wait for auth to complete
            time.sleep(3)

            # Click "New Tournament"
            print("📍 Step 2: Click 'New Tournament'...")
            new_tournament_btn = page.locator("button:has-text('New Tournament')").first
            new_tournament_btn.wait_for(state="visible", timeout=10000)
            new_tournament_btn.click()
            wait_streamlit(page)

            # Click "Start Instructor Workflow"
            print("📍 Step 3: Click 'Start Instructor Workflow'...")
            start_workflow_btn = page.locator("button:has-text('Start Instructor Workflow')").first
            start_workflow_btn.wait_for(state="visible", timeout=10000)
            start_workflow_btn.click()
            wait_streamlit(page)

            # Verify we're on Step 1
            step1_text = page.locator("text=Step 1").first
            if step1_text.count() == 0:
                print("❌ FAILED: Step 1 not visible after clicking Start Workflow")
                browser.close()
                return

            print("✅ Step 1 visible\n")

            # Continue to Step 2 (Review & Confirm)
            print("📍 Step 4: Continue to Step 2...")
            continue_btn = page.locator("button:has-text('Review & Confirm')").first
            continue_btn.wait_for(state="visible", timeout=10000)
            continue_btn.click()
            wait_streamlit(page)

            # Create tournament
            print("📍 Step 5: Create tournament...")
            create_btn = page.locator("button:has-text('Create Tournament')").first
            create_btn.wait_for(state="visible", timeout=10000)
            create_btn.click()
            wait_streamlit(page, timeout_ms=15000)

            # Extract tournament ID from UI
            success_text = page.locator("text=/Tournament created.*ID/").first
            success_text.wait_for(state="visible", timeout=10000)
            text = success_text.text_content()

            import re
            match = re.search(r'ID:\s*(\d+)', text)
            tournament_id = int(match.group(1))
            print(f"✅ Tournament {tournament_id} created\n")

            # Continue to Step 4 (Enter Results)
            print("📍 Step 6: Navigate to Step 4 (Enter Results)...")
            continue_btn = page.locator("button:has-text('Enter Results')").first
            continue_btn.wait_for(state="visible", timeout=10000)
            continue_btn.click()
            wait_streamlit(page)
            time.sleep(2)

            # PHASE 1: Submit group stage matches
            print("\n" + "="*80)
            print("PHASE 1: GROUP STAGE")
            print("="*80 + "\n")

            pending = get_pending_sessions(tournament_id)
            group_sessions = [s for s in pending if s['tournament_phase'] == 'Group Stage']

            print(f"Found {len(group_sessions)} group matches")

            for idx, session in enumerate(group_sessions, 1):
                sid = session['id']
                score1 = random.randint(0, 5)
                score2 = random.randint(0, 5)
                if score1 == score2:
                    score1 += 1

                if not submit_match_result(page, sid, score1, score2):
                    print(f"❌ FAILED at group match {idx}")
                    browser.close()
                    return

            print(f"\n✅ All {len(group_sessions)} group matches submitted\n")

            # Reload to get knockout bracket
            print("🔄 Reloading page to get knockout bracket...")
            page.reload()
            wait_streamlit(page, timeout_ms=15000)
            time.sleep(3)

            # PHASE 2: Submit semifinals
            print("\n" + "="*80)
            print("PHASE 2: SEMIFINALS")
            print("="*80 + "\n")

            pending = get_pending_sessions(tournament_id)
            semifinal_sessions = [
                s for s in pending
                if s['tournament_phase'] in ['Knockout Stage', 'Knockout']
                and s['round_number'] == 1
                and s['participant_user_ids']
                and len(s['participant_user_ids']) == 2
            ]

            print(f"Found {len(semifinal_sessions)} semifinals")

            for idx, session in enumerate(semifinal_sessions, 1):
                sid = session['id']
                score1 = random.randint(0, 5)
                score2 = random.randint(0, 5)
                if score1 == score2:
                    score1 += 1

                if not submit_match_result(page, sid, score1, score2):
                    print(f"❌ FAILED at semifinal {idx}")
                    browser.close()
                    return

            print(f"\n✅ All {len(semifinal_sessions)} semifinals submitted\n")

            # PHASE 3: Verify final appears
            print("\n" + "="*80)
            print("PHASE 3: FINAL MATCH (CRITICAL TEST)")
            print("="*80 + "\n")

            print("⏳ Waiting 5 seconds for backend to populate final...")
            time.sleep(5)

            print("🔄 Reloading page to fetch final match...")
            page.reload()
            wait_streamlit(page, timeout_ms=15000)
            time.sleep(3)

            # Check database for final
            pending = get_pending_sessions(tournament_id)
            final_sessions = [
                s for s in pending
                if s['tournament_phase'] in ['Knockout Stage', 'Knockout']
                and s['round_number'] == 2
                and s['participant_user_ids']
                and len(s['participant_user_ids']) == 2
            ]

            if len(final_sessions) == 0:
                print("❌ CRITICAL FAILURE: Final match NOT FOUND in database!")
                browser.close()
                return

            final_session = final_sessions[0]
            final_id = final_session['id']
            final_participants = final_session['participant_user_ids']

            print(f"✅ DB: Final match exists (Session {final_id}, participants {final_participants})")

            # Check UI for final
            session_text = page.locator(f"text=/Session ID.*{final_id}/").first

            try:
                session_text.wait_for(state="visible", timeout=5000)
                print(f"✅ UI: Final match IS VISIBLE in UI")
            except:
                print(f"❌ CRITICAL FAILURE: Final match {final_id} NOT VISIBLE in UI!")
                print("\nTaking screenshot...")
                page.screenshot(path="/tmp/final_not_visible.png")
                print("Screenshot saved to /tmp/final_not_visible.png")
                browser.close()
                return

            # Submit final
            print(f"\n📍 Submitting final match...")
            score1 = random.randint(0, 5)
            score2 = random.randint(0, 5)
            if score1 == score2:
                score1 += 1

            if not submit_match_result(page, final_id, score1, score2):
                print("❌ FAILED to submit final")
                browser.close()
                return

            print("\n" + "="*80)
            print("✅ 100% SUCCESS: Complete tournament via sandbox UI")
            print(f"   - Group: {len(group_sessions)} matches")
            print(f"   - Semifinals: {len(semifinal_sessions)} matches")
            print(f"   - Final: 1 match")
            print(f"   - Total: {len(group_sessions) + len(semifinal_sessions) + 1} matches")
            print("="*80 + "\n")

            time.sleep(3)

        finally:
            browser.close()

if __name__ == "__main__":
    main()
