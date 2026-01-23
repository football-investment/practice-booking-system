"""
Playwright E2E Tests for Coupon Creation Form UI

Tests the complete UI flow for creating all 3 coupon types via the Streamlit admin interface.

CRITICAL REQUIREMENT:
- Must use Firefox headed mode
- Must FIX selectbox interaction (not bypass it)
- Tests complete UI workflow from login → form fill → coupon creation

Coverage:
1. BONUS_CREDITS: Instant free credits form
2. PURCHASE_DISCOUNT_PERCENT: Purchase discount % form
3. PURCHASE_BONUS_CREDITS: Purchase bonus credits form
"""

import pytest
from playwright.sync_api import Page, expect
import time


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def streamlit_login(page: Page, email: str, password: str):
    """
    Login to Streamlit app

    IMPORTANT: This assumes the Streamlit app is running at http://localhost:8501
    """
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Wait for login form
    page.wait_for_selector("input[aria-label='Email']", timeout=10000)

    # Fill login form
    page.fill("input[aria-label='Email']", email)
    page.fill("input[aria-label='Password']", password)

    # Click login button
    page.click("button:has-text('Login')")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Wait for redirect


def navigate_to_financial_tab(page: Page):
    """Navigate to Financial Management tab in admin dashboard"""
    # Look for Financial tab button (💳 is credit card emoji, not money bag)
    page.click("button:has-text('💳 Financial')")
    page.wait_for_load_state("networkidle")
    time.sleep(1)


def click_create_coupon_button(page: Page):
    """Click the '➕ Create Coupon' button to open modal"""
    page.click("button:has-text('Create Coupon')")
    page.wait_for_load_state("networkidle")

    # Wait for the st.dialog modal to appear
    # The modal should contain the "Create Coupon" heading
    page.wait_for_selector("text='Create Coupon'", timeout=5000, state="visible")
    time.sleep(1)  # Extra wait for modal animation


def fill_coupon_code(page: Page, code: str):
    """Fill the coupon code input field"""
    # Find the text input with label "Code *"
    page.fill("input[aria-label='Code *']", code)


def fill_coupon_description(page: Page, description: str):
    """Fill the coupon description textarea"""
    page.fill("textarea[aria-label='Description']", description)


def select_coupon_type_firefox_headed(page: Page, coupon_type: str):
    """
    Select coupon type from selectbox in Firefox headed mode

    This is the CRITICAL function that must work - NO BYPASSING!

    Args:
        coupon_type: One of "BONUS_CREDITS", "PURCHASE_DISCOUNT_PERCENT", "PURCHASE_BONUS_CREDITS"
    """
    # Step 1: Wait for the "Type *" label to be visible in the modal
    selectbox_label = page.locator("label:has-text('Type *')")
    selectbox_label.wait_for(state="visible", timeout=5000)

    # Step 2: Find the VISIBLE selectbox in the modal
    # CRITICAL FIX: There are multiple selectboxes on the page (some hidden)
    # We need to filter by visibility and get the visible one
    all_selectboxes = page.locator("[data-baseweb='select']")
    visible_selectbox = None

    # Find the first visible selectbox
    for i in range(all_selectboxes.count()):
        sb = all_selectboxes.nth(i)
        if sb.is_visible():
            visible_selectbox = sb
            break

    if not visible_selectbox:
        raise Exception("No visible selectbox found in modal!")

    # Step 3: Click the visible selectbox to open dropdown
    visible_selectbox.click()
    page.wait_for_timeout(500)  # Wait for dropdown animation

    # Step 4: Wait for dropdown options to appear
    # NOTE: Streamlit selectbox renders options directly as [role='option'],
    # without a parent [role='listbox'] or [role='menu'] container
    page.wait_for_selector("[role='option']", timeout=5000)

    # Step 5: Map coupon type to display text
    type_display_map = {
        "BONUS_CREDITS": "🎁 Bonus Credits (Instant)",
        "PURCHASE_DISCOUNT_PERCENT": "💰 Purchase Discount (%)",
        "PURCHASE_BONUS_CREDITS": "🎉 Purchase Bonus Credits"
    }

    display_text = type_display_map.get(coupon_type)
    if not display_text:
        raise ValueError(f"Invalid coupon type: {coupon_type}")

    # Step 5: Click the option in dropdown
    option = page.locator(f"[role='option']:has-text('{display_text}')")
    option.click()
    page.wait_for_timeout(300)  # Wait for selection to register


def fill_number_input_by_label(page: Page, label: str, value: float):
    """
    Fill a number input field by its label

    Args:
        label: The label text (e.g., "Bonus Credits *", "Discount Percentage *")
        value: The numeric value to fill
    """
    # Streamlit number inputs are rendered as input[type="number"]
    # Find by aria-label or by proximity to label
    input_field = page.locator(f"input[aria-label='{label}']")

    # Click to focus (force=True to bypass overlays like help tooltips)
    input_field.click(force=True)
    page.wait_for_timeout(500)  # Longer wait for focus

    # Convert float to int string if it's a whole number (100.0 -> "100")
    if isinstance(value, float) and value.is_integer():
        value_str = str(int(value))
    else:
        value_str = str(value)

    # Fill using Playwright's fill() method (clears and types)
    input_field.fill(value_str)
    page.wait_for_timeout(500)  # Wait for Streamlit to register

    # Press Tab to trigger blur event (helps Streamlit register the change)
    page.keyboard.press("Tab")
    page.wait_for_timeout(300)


def submit_coupon_form(page: Page):
    """Submit coupon form by pressing Enter key"""
    # CRITICAL: Give Streamlit time to process all form changes
    # Streamlit needs time to register all input changes before form submission
    print("\n⏳ Waiting 3 seconds for Streamlit to process all form inputs...")
    page.wait_for_timeout(3000)  # 3 seconds for Streamlit to sync all form state

    # CRITICAL FIX: Streamlit forms don't work with click() in Playwright
    # We need to press Enter key to submit the form instead
    print("⌨️  Pressing Enter to submit form...")
    page.keyboard.press("Enter")

    # Wait for HTTP POST request to be sent (check backend logs)
    page.wait_for_timeout(2000)

    # Wait for modal to close and page to reload
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Extra wait for Streamlit rerun
    print("✅ Form submitted via Enter key, modal should be closed")


def verify_coupon_in_list(page: Page, coupon_code: str):
    """Verify that coupon appears in the coupon list"""
    # Wait for page to reload and modal to close after form submission
    page.wait_for_load_state("networkidle")
    time.sleep(3)  # Extra wait for Streamlit rerun and list refresh

    # Debug: Print what we're looking for
    print(f"\n🔍 Looking for coupon code: {coupon_code}")

    # Take screenshot for debugging
    screenshot_path = f"tests/e2e/screenshots/verify_{coupon_code}.png"
    page.screenshot(path=screenshot_path)
    print(f"📸 Screenshot saved: {screenshot_path}")

    # Debug: Print page content to see what's actually rendered
    page_text = page.inner_text("body")
    print(f"📄 Page contains text (first 500 chars): {page_text[:500]}")

    # Check if coupon code appears anywhere in page
    if coupon_code in page_text:
        print(f"✅ Coupon code '{coupon_code}' FOUND in page text!")
    else:
        print(f"❌ Coupon code '{coupon_code}' NOT FOUND in page text!")

    # Try using get_by_text with flexible matching
    coupon_element = page.get_by_text(coupon_code, exact=False).first

    # Wait for element to be visible with longer timeout
    expect(coupon_element).to_be_visible(timeout=15000)


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

# Note: browser_type_launch_args configured via command line:
# pytest --browser firefox --headed

@pytest.fixture(scope="function")
def admin_page(page: Page):
    """
    Fixture that provides an authenticated admin page

    Prerequisites:
    - Streamlit app running at http://localhost:8501
    - Admin user exists: admin@lfa.com / admin123
    - Run tests with: pytest --browser firefox --headed
    """
    streamlit_login(page, "admin@lfa.com", "admin123")
    navigate_to_financial_tab(page)
    yield page


# =============================================================================
# TEST GROUP 1: BONUS_CREDITS Form UI
# =============================================================================

@pytest.mark.e2e
@pytest.mark.coupon_ui
def test_b1_create_bonus_credits_coupon_via_ui(admin_page: Page):
    """
    Test B2.1: Admin creates BONUS_CREDITS coupon via UI form

    Expected:
    - Selectbox interaction works in Firefox headed mode
    - Number input accepts bonus credits value
    - Form submits successfully
    - Coupon appears in list with "Instant" label
    """
    # Click create coupon button
    click_create_coupon_button(admin_page)

    # Fill coupon code
    fill_coupon_code(admin_page, "UI_BONUS_100")

    # Fill description
    fill_coupon_description(admin_page, "UI test - 100 credits instant")

    # Select BONUS_CREDITS type (CRITICAL: selectbox interaction)
    select_coupon_type_firefox_headed(admin_page, "BONUS_CREDITS")

    # Fill bonus credits value
    fill_number_input_by_label(admin_page, "Bonus Credits *", 100.0)

    # Fill optional fields (use non-zero values to trigger Streamlit change detection)
    fill_number_input_by_label(admin_page, "Max Uses", 10)
    fill_number_input_by_label(admin_page, "Expires in (days)", 5)

    # Submit form
    submit_coupon_form(admin_page)

    # Verify coupon appears in list
    verify_coupon_in_list(admin_page, "UI_BONUS_100")

    # Verify "Instant" label is present (use .first since there may be multiple)
    instant_label = admin_page.locator("text=Instant").first
    expect(instant_label).to_be_visible()


# =============================================================================
# TEST GROUP 2: PURCHASE_DISCOUNT_PERCENT Form UI
# =============================================================================

@pytest.mark.e2e
@pytest.mark.coupon_ui
def test_b2_create_purchase_discount_coupon_via_ui(admin_page: Page):
    """
    Test B3.1: Admin creates PURCHASE_DISCOUNT_PERCENT coupon via UI form

    Expected:
    - Selectbox interaction works in Firefox headed mode
    - Percentage input validates range (1-100)
    - Warning message appears about admin approval requirement
    - Coupon appears in list with "Purchase" label
    """
    # Click create coupon button
    click_create_coupon_button(admin_page)

    # Fill coupon code
    fill_coupon_code(admin_page, "UI_DISC_20")

    # Fill description
    fill_coupon_description(admin_page, "UI test - 20% purchase discount")

    # Select PURCHASE_DISCOUNT_PERCENT type (CRITICAL: selectbox interaction)
    select_coupon_type_firefox_headed(admin_page, "PURCHASE_DISCOUNT_PERCENT")

    # Wait for form to update with new type-specific fields
    admin_page.wait_for_timeout(1000)

    # Verify warning message appears (use partial text match, may include emoji)
    warning = admin_page.get_by_text("Requires invoice generation and admin approval", exact=False)
    expect(warning).to_be_visible(timeout=10000)

    # Fill discount percentage (20%)
    fill_number_input_by_label(admin_page, "Discount Percentage *", 20.0)

    # Submit form
    submit_coupon_form(admin_page)

    # Verify coupon appears in list
    verify_coupon_in_list(admin_page, "UI_DISC_20")

    # Verify "Purchase" label is present
    purchase_label = admin_page.locator("text=Purchase").first
    expect(purchase_label).to_be_visible()


# =============================================================================
# TEST GROUP 3: PURCHASE_BONUS_CREDITS Form UI
# =============================================================================

@pytest.mark.e2e
@pytest.mark.coupon_ui
def test_b3_create_purchase_bonus_coupon_via_ui(admin_page: Page):
    """
    Test B4.1: Admin creates PURCHASE_BONUS_CREDITS coupon via UI form

    Expected:
    - Selectbox interaction works in Firefox headed mode
    - Bonus credits input accepts value
    - Warning message appears about admin approval requirement
    - Coupon appears in list with "Purchase" label
    """
    # Click create coupon button
    click_create_coupon_button(admin_page)

    # Fill coupon code
    fill_coupon_code(admin_page, "UI_PBONUS_300")

    # Fill description
    fill_coupon_description(admin_page, "UI test - +300 bonus credits after purchase")

    # Select PURCHASE_BONUS_CREDITS type (CRITICAL: selectbox interaction)
    select_coupon_type_firefox_headed(admin_page, "PURCHASE_BONUS_CREDITS")

    # Wait for form to update with new type-specific fields
    admin_page.wait_for_timeout(1000)

    # Verify warning message appears (use partial text match, may include emoji)
    warning = admin_page.get_by_text("Requires invoice generation and admin approval", exact=False)
    expect(warning).to_be_visible(timeout=10000)

    # Fill bonus credits value
    fill_number_input_by_label(admin_page, "Bonus Credits *", 300.0)

    # Submit form
    submit_coupon_form(admin_page)

    # Verify coupon appears in list
    verify_coupon_in_list(admin_page, "UI_PBONUS_300")

    # Verify "Purchase" label is present
    purchase_label = admin_page.locator("text=Purchase").first
    expect(purchase_label).to_be_visible()


# =============================================================================
# TEST GROUP 4: Form Validation
# =============================================================================

@pytest.mark.e2e
@pytest.mark.coupon_ui
def test_b4_form_validation_empty_code(admin_page: Page):
    """
    Test B5.1: Form validation rejects empty coupon code

    Expected:
    - Error message appears when submitting with empty code
    - Form does not submit
    """
    click_create_coupon_button(admin_page)

    # Select type without filling code
    select_coupon_type_firefox_headed(admin_page, "BONUS_CREDITS")
    fill_number_input_by_label(admin_page, "Bonus Credits *", 50.0)

    # Try to submit
    submit_coupon_form(admin_page)

    # Verify error message appears
    error = admin_page.locator("text=Code is required")
    expect(error).to_be_visible()


@pytest.mark.e2e
@pytest.mark.coupon_ui
def test_b5_form_validation_zero_value(admin_page: Page):
    """
    Test B5.2: Form validation rejects zero/negative discount value

    Expected:
    - Error message appears when value <= 0
    - Form does not submit
    """
    click_create_coupon_button(admin_page)

    fill_coupon_code(admin_page, "INVALID_ZERO")
    select_coupon_type_firefox_headed(admin_page, "BONUS_CREDITS")

    # Try to fill zero value (should be prevented by input constraint)
    # Most browsers prevent typing 0 in a min=1 input
    # But we can verify the error message if attempted

    # Try to submit without filling value
    submit_coupon_form(admin_page)

    # Verify error message
    error = admin_page.locator("text=Value must be greater than 0")
    expect(error).to_be_visible()
