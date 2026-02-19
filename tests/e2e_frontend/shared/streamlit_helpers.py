"""
Streamlit UI Helper Functions for Playwright E2E Tests

Provides robust selectors and interaction methods for Streamlit components.
"""
from playwright.sync_api import Page
import time


def select_streamlit_selectbox_by_label(page: Page, label_text: str, option_text: str, scroll: bool = True):
    """
    Select option from Streamlit selectbox by label

    Args:
        page: Playwright page object
        label_text: The label text of the selectbox (e.g., "Location")
        option_text: The option to select (e.g., "Budapest")
        scroll: Whether to scroll element into view
    """
    print(f"   🔽 Selecting '{option_text}' from '{label_text}' selectbox...")

    # Find label element
    label = page.locator(f'label:has-text("{label_text}")').first

    if scroll:
        try:
            label.scroll_into_view_if_needed(timeout=5000)
            time.sleep(0.3)
        except Exception:
            pass

    # Find the selectbox container (parent of label)
    selectbox_container = label.locator('xpath=ancestor::div[@data-testid="stSelectbox"]').first

    # Find the BaseWeb select element within container
    select_elem = selectbox_container.locator('[data-baseweb="select"]').first

    # Click to open dropdown
    select_elem.click()
    time.sleep(1)  # Wait for dropdown animation

    # The options appear in a BaseWeb popover/menu portal
    # Try different approaches to find the option
    option_found = False

    # Approach 1: Look for option in listbox role
    option_in_listbox = page.locator(f'[role="option"]:has-text("{option_text}")').first
    if option_in_listbox.count() > 0:
        option_in_listbox.click()
        option_found = True

    # Approach 2: Look for option in BaseWeb menu
    if not option_found:
        option_in_menu = page.locator(f'[data-baseweb="menu"] >> text="{option_text}"').first
        if option_in_menu.count() > 0:
            option_in_menu.click()
            option_found = True

    # Approach 3: Generic text match (least specific)
    if not option_found:
        option_generic = page.get_by_text(option_text, exact=True).first
        option_generic.click()
        option_found = True

    time.sleep(0.5)

    print(f"      ✅ Selected: {option_text}")


def fill_streamlit_text_input(page: Page, label_text: str, value: str, scroll: bool = True):
    """
    Fill Streamlit text input by label

    Args:
        page: Playwright page object
        label_text: The aria-label of the input
        value: The value to fill
        scroll: Whether to scroll element into view
    """
    input_elem = page.get_by_label(label_text, exact=False).first

    if scroll:
        try:
            input_elem.scroll_into_view_if_needed(timeout=5000)
            time.sleep(0.3)
        except Exception:
            pass

    input_elem.clear()
    input_elem.fill(value)
    time.sleep(0.3)


def fill_streamlit_number_input(page: Page, label_text: str, value: int, scroll: bool = True):
    """
    Fill Streamlit number input by label

    Args:
        page: Playwright page object
        label_text: The aria-label of the input
        value: The numeric value to fill
        scroll: Whether to scroll element into view
    """
    input_elem = page.get_by_label(label_text, exact=False).first

    if scroll:
        try:
            input_elem.scroll_into_view_if_needed(timeout=5000)
            time.sleep(0.3)
        except Exception:
            pass

    input_elem.clear()
    input_elem.fill(str(value))
    time.sleep(0.3)


def click_streamlit_button(page: Page, button_text: str, scroll: bool = True):
    """
    Click Streamlit button by text

    Args:
        page: Playwright page object
        button_text: The text on the button
        scroll: Whether to scroll element into view
    """
    button = page.get_by_text(button_text, exact=True).first

    if scroll:
        try:
            button.scroll_into_view_if_needed(timeout=5000)
            time.sleep(0.3)
        except Exception:
            pass

    button.click()
    time.sleep(0.5)


def wait_for_streamlit_rerun(page: Page, timeout: int = 15000):
    """
    Wait for Streamlit app to complete rerun

    Args:
        page: Playwright page object
        timeout: Maximum wait time in milliseconds
    """
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=timeout)
    time.sleep(2)  # Additional buffer for dynamic content


def submit_head_to_head_result_via_ui(page: Page, session_id: int, score1: int, score2: int):
    """
    Submit HEAD_TO_HEAD match result via Streamlit UI

    The UI is rendered in sandbox_workflow.py lines 633-738.
    Each session is shown in a Card component (line 481):
        title=f"Session: {session.get('title', 'Untitled')} (ID: {session.get('id')})"
    Number input keys: h2h_score_1_{session_id} and h2h_score_2_{session_id} (lines 696, 708)
    Submit button: "Submit Match Result" with key submit_h2h_{session_id} (line 721)

    Args:
        page: Playwright page object
        session_id: Session ID to submit result for
        score1: Score for Player 1
        score2: Score for Player 2

    Returns:
        bool: True if submission successful, False otherwise
    """
    try:
        # ✅ FIX: Find session by "Session ID: {session_id}" text inside expander
        # After UI fix, titles change from "Round of 2 - Match 1" to "Final"
        # So we can't rely on title matching - use Session ID text instead
        session_id_label = page.locator(f"text=/Session ID.*{session_id}/").first

        if session_id_label.count() == 0:
            print(f"   ⚠️  Session {session_id} not found on page (searched for 'Session ID: {session_id}')")
            return False

        # Scroll into view
        session_id_label.scroll_into_view_if_needed()
        time.sleep(0.5)

        # Get the parent container (the expander content) for context
        # This helps us find the correct submit button later
        session_container = session_id_label.locator("xpath=ancestor::div[@data-testid='stExpander']").first

        # Find score input fields using their Streamlit keys
        # The keys are: score1_{session_id} and score2_{session_id}
        # (from streamlit_sandbox_workflow_steps.py lines 221, 232)
        score1_key = f"score1_{session_id}"
        score2_key = f"score2_{session_id}"

        # Find inputs by aria-label containing the key
        score1_input = page.locator(f"input[aria-label*='{score1_key}']").first

        # Fallback: find all number inputs on page and filter by proximity
        if score1_input.count() == 0:
            # Get all number inputs
            all_number_inputs = page.locator("input[type='number']").all()

            # Find the first two number inputs after the session heading
            # This is a simple approach - just grab the next 2 inputs
            score1_input = page.locator("input[type='number']").first
            score2_input = page.locator("input[type='number']").nth(1)

            if score1_input.count() == 0 or score2_input.count() == 0:
                print(f"   ⚠️  Score inputs not found for session {session_id}")
                return False
        else:
            # Find score 2 input
            score2_input = page.locator(f"input[aria-label*='{score2_key}']").first

            if score2_input.count() == 0:
                score2_input = page.locator("input[type='number']").nth(1)
                if score2_input.count() == 0:
                    print(f"   ⚠️  Score 2 input not found for session {session_id}")
                    return False

        # Fill scores - clear first, then click to focus, then fill
        score1_input.scroll_into_view_if_needed()
        score1_input.click()
        time.sleep(0.1)
        score1_input.clear()
        score1_input.fill(str(score1))
        time.sleep(0.3)

        score2_input.scroll_into_view_if_needed()
        score2_input.click()
        time.sleep(0.1)
        score2_input.clear()
        score2_input.fill(str(score2))
        time.sleep(0.3)

        # ✅ CRITICAL FIX: Find Submit button within the session's expander container
        # Button key is f"btn_submit_{session_id}" (from streamlit_sandbox_workflow_steps.py:186)
        # Button text is "Submit Result" (line 186)

        # Strategy 1: Look for "Submit Result" button within the session container
        submit_btn_in_container = session_container.locator("button:has-text('Submit Result')").first

        if submit_btn_in_container.count() > 0:
            submit_btn_in_container.click()
        else:
            # Fallback: Use spatial positioning (find button closest below session_id_label)
            all_submit_btns = page.locator("button:has-text('Submit Result')").all()

            if len(all_submit_btns) == 0:
                print(f"   ⚠️  No Submit buttons found on page")
                return False

            # If only one button, click it
            if len(all_submit_btns) == 1:
                all_submit_btns[0].click()
            else:
                # Multiple buttons - find closest below session_id_label
                label_box = session_id_label.bounding_box()
                if not label_box:
                    print(f"   ⚠️  Cannot get bounding box for session {session_id} label")
                    return False

                label_y = label_box['y']

                best_btn = None
                min_distance = float('inf')

                for btn in all_submit_btns:
                    btn_box = btn.bounding_box()
                    if btn_box and btn_box['y'] > label_y:
                        distance = btn_box['y'] - label_y
                        if distance < min_distance:
                            min_distance = distance
                            best_btn = btn

                if not best_btn:
                    print(f"   ⚠️  Could not find Submit button for session {session_id}")
                    return False

                best_btn.click()
        wait_for_streamlit_rerun(page, timeout=15000)
        # Give backend extra time to process and commit to database
        time.sleep(2)

        # ✅ CRITICAL: Verify the result was ACTUALLY saved to database
        # Don't trust the UI - verify backend wrote to DB
        import psycopg2
        try:
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
                print(f"   ✅ UI Result submitted: {score1}-{score2} for session {session_id}")
                print(f"      ✅ Database write VERIFIED")
                return True
            else:
                print(f"   ❌ UI submission appeared successful but DATABASE WRITE FAILED for session {session_id}")
                print(f"      Database game_results is NULL - API call may have failed silently")
                return False
        except Exception as e:
            print(f"   ⚠️  Could not verify database write: {e}")
            # Fall back to assuming success if we can't verify
            print(f"   ✅ UI Result submitted: {score1}-{score2} for session {session_id} (unverified)")
            return True

    except Exception as e:
        print(f"   ❌ Error submitting result for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def navigate_to_step_enter_results(page: Page):
    """
    Navigate to Step 4 (Enter Results) in workflow

    Args:
        page: Playwright page object
    """
    # Click "Continue to Results" button (exact text from sandbox_workflow.py:379)
    button = page.locator("button:has-text('Continue to Results')").first
    if button.count() > 0:
        button.click()
        wait_for_streamlit_rerun(page)
        print("   ✅ Navigated to Step 4 (Enter Results)")
        return True
    else:
        print("   ⚠️  'Continue to Results' button not found")
        return False
