"""
Minimal Form Test - Playwright E2E

Purpose: Test Streamlit form button behavior in automated browser context.

This test validates whether form buttons work reliably when clicked by Playwright
in both headed and headless modes.

Run:
  pytest tests/e2e_frontend/test_minimal_form.py -v -s           # headless
  pytest tests/e2e_frontend/test_minimal_form.py -v -s --headed  # headed
"""

import pytest
import time
from playwright.sync_api import Page, expect


def wait_for_streamlit(page: Page, timeout_ms: int = 10000):
    """Wait for Streamlit to finish rendering."""
    # Wait for Streamlit's running indicator to disappear
    page.wait_for_selector('[data-testid="stStatusWidget"]', state="hidden", timeout=timeout_ms)
    time.sleep(0.5)  # Additional buffer


@pytest.mark.e2e
def test_minimal_plain_button(page: Page):
    """Test 1: Plain st.button() without form wrapper."""
    print("\n" + "="*80)
    print("TEST 1: Plain st.button()")
    print("="*80)

    # Navigate to minimal test app
    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Find initial counter value
    initial_count_text = page.locator("text=/Plain button click count:/").inner_text()
    print(f"Initial state: {initial_count_text}")

    # Click plain button
    plain_button = page.locator("button:has-text('Plain Button - Click Me')").first
    plain_button.wait_for(state="visible", timeout=10000)
    print("Clicking plain button...")
    plain_button.click()

    # Wait for Streamlit to process
    wait_for_streamlit(page, timeout_ms=5000)
    time.sleep(1)

    # Check if handler executed
    try:
        success_msg = page.locator("text=/Plain button clicked!/")
        success_msg.wait_for(state="visible", timeout=3000)
        print("✅ PASS: Plain button handler executed")
        return True
    except Exception as e:
        print(f"❌ FAIL: Plain button handler did NOT execute")
        print(f"   Error: {e}")
        # Show page content for debugging
        page_content = page.locator("body").inner_text()
        print(f"   Page content:\n{page_content[:500]}")
        pytest.fail("Plain button handler did not execute")


@pytest.mark.e2e
def test_minimal_form_button(page: Page):
    """Test 2: st.form_submit_button() with form wrapper."""
    print("\n" + "="*80)
    print("TEST 2: st.form_submit_button()")
    print("="*80)

    # Navigate to minimal test app
    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Find initial counter value
    initial_count_text = page.locator("text=/Form submission count:/").inner_text()
    print(f"Initial state: {initial_count_text}")

    # Click form button
    form_button = page.locator("button:has-text('Form Button - Click Me')").first
    form_button.wait_for(state="visible", timeout=10000)
    print("Clicking form button...")
    form_button.click()

    # Wait for Streamlit to process
    wait_for_streamlit(page, timeout_ms=5000)
    time.sleep(1)

    # Check if handler executed
    try:
        success_msg = page.locator("text=/Form button clicked!/")
        success_msg.wait_for(state="visible", timeout=3000)
        print("✅ PASS: Form button handler executed")
        return True
    except Exception as e:
        print(f"❌ FAIL: Form button handler did NOT execute")
        print(f"   Error: {e}")
        # Show page content for debugging
        page_content = page.locator("body").inner_text()
        print(f"   Page content:\n{page_content[:500]}")
        pytest.fail("Form button handler did not execute")


@pytest.mark.e2e
def test_minimal_complex_form(page: Page):
    """Test 3: Complex form with multiple fields."""
    print("\n" + "="*80)
    print("TEST 3: Complex form with multiple fields")
    print("="*80)

    # Navigate to minimal test app
    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Scroll to complex form section
    page.locator("text=/Test 4: Complex Form/").scroll_into_view_if_needed()
    time.sleep(1)

    # Fill form fields
    name_input = page.locator("input[aria-label='Name']").first
    name_input.fill("Test User")
    print("Filled name field: Test User")

    age_input = page.locator("input[aria-label='Age']").first
    age_input.fill("25")
    print("Filled age field: 25")

    # Click submit
    submit_button = page.locator("button:has-text('Submit Complex Form')").first
    submit_button.wait_for(state="visible", timeout=10000)
    print("Clicking complex form submit button...")
    submit_button.click()

    # Wait for Streamlit to process
    wait_for_streamlit(page, timeout_ms=5000)
    time.sleep(1)

    # Check if handler executed
    try:
        success_msg = page.locator("text=/Complex form submitted!/")
        success_msg.wait_for(state="visible", timeout=3000)
        print("✅ PASS: Complex form handler executed")
        return True
    except Exception as e:
        print(f"❌ FAIL: Complex form handler did NOT execute")
        print(f"   Error: {e}")
        page_content = page.locator("body").inner_text()
        print(f"   Page content:\n{page_content[:500]}")
        pytest.fail("Complex form handler did not execute")


@pytest.mark.e2e
def test_minimal_column_form(page: Page):
    """Test 4: Form button inside column layout."""
    print("\n" + "="*80)
    print("TEST 4: Form button in column layout")
    print("="*80)

    # Navigate to minimal test app
    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Scroll to column form section
    page.locator("text=/Test 5: Form in Column Layout/").scroll_into_view_if_needed()
    time.sleep(1)

    # Click form button in column
    column_form_button = page.locator("button:has-text('Form Button in Column')").first
    column_form_button.wait_for(state="visible", timeout=10000)
    print("Clicking form button in column...")
    column_form_button.click()

    # Wait for Streamlit to process
    wait_for_streamlit(page, timeout_ms=5000)
    time.sleep(1)

    # Check if handler executed
    try:
        success_msg = page.locator("text=/Form button in column clicked!/")
        success_msg.wait_for(state="visible", timeout=3000)
        print("✅ PASS: Column form handler executed")
        return True
    except Exception as e:
        print(f"❌ FAIL: Column form handler did NOT execute")
        print(f"   Error: {e}")
        page_content = page.locator("body").inner_text()
        print(f"   Page content:\n{page_content[:500]}")
        pytest.fail("Column form handler did not execute")


@pytest.mark.e2e
def test_minimal_api_simulation(page: Page):
    """Test 5: Form with simulated API call."""
    print("\n" + "="*80)
    print("TEST 5: Form with simulated API call")
    print("="*80)

    # Navigate to minimal test app
    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Scroll to API simulation section
    page.locator("text=/Test 6: Form with Simulated API Call/").scroll_into_view_if_needed()
    time.sleep(1)

    # Fill API input
    api_input = page.locator("input[aria-label='API Input Data']").first
    api_input.fill("test_data_123")
    print("Filled API input: test_data_123")

    # Click submit
    api_submit_button = page.locator("button:has-text('Submit to API')").first
    api_submit_button.wait_for(state="visible", timeout=10000)
    print("Clicking API submit button...")
    api_submit_button.click()

    # Wait for Streamlit to process (including API delay simulation)
    wait_for_streamlit(page, timeout_ms=5000)
    time.sleep(2)  # API simulation has 0.5s delay

    # Check if handler executed
    try:
        success_msg = page.locator("text=/API call successful!/")
        success_msg.wait_for(state="visible", timeout=3000)
        print("✅ PASS: API simulation handler executed")
        return True
    except Exception as e:
        print(f"❌ FAIL: API simulation handler did NOT execute")
        print(f"   Error: {e}")
        page_content = page.locator("body").inner_text()
        print(f"   Page content:\n{page_content[:500]}")
        pytest.fail("API simulation handler did not execute")


@pytest.mark.e2e
def test_minimal_full_suite(page: Page):
    """Test 6: Run all tests in sequence to verify consistency."""
    print("\n" + "="*80)
    print("TEST 6: Full suite - sequential button clicks")
    print("="*80)

    page.goto("http://localhost:8502")
    wait_for_streamlit(page)

    # Test sequence: Click each button type once
    results = []

    # 1. Plain button
    print("\n1. Testing plain button...")
    plain_btn = page.locator("button:has-text('Plain Button - Click Me')").first
    plain_btn.click()
    wait_for_streamlit(page)
    time.sleep(1)
    plain_success = page.locator("text=/Plain button clicked!/").count() > 0
    results.append(("Plain Button", plain_success))
    print(f"   Result: {'✅ PASS' if plain_success else '❌ FAIL'}")

    # 2. Form button
    print("\n2. Testing form button...")
    form_btn = page.locator("button:has-text('Form Button - Click Me')").first
    form_btn.click()
    wait_for_streamlit(page)
    time.sleep(1)
    form_success = page.locator("text=/Form button clicked!/").count() > 0
    results.append(("Form Button", form_success))
    print(f"   Result: {'✅ PASS' if form_success else '❌ FAIL'}")

    # 3. Complex form
    print("\n3. Testing complex form...")
    page.locator("text=/Test 4: Complex Form/").scroll_into_view_if_needed()
    time.sleep(0.5)
    complex_btn = page.locator("button:has-text('Submit Complex Form')").first
    complex_btn.click()
    wait_for_streamlit(page)
    time.sleep(1)
    complex_success = page.locator("text=/Complex form submitted!/").count() > 0
    results.append(("Complex Form", complex_success))
    print(f"   Result: {'✅ PASS' if complex_success else '❌ FAIL'}")

    # 4. Column form
    print("\n4. Testing column form...")
    page.locator("text=/Test 5: Form in Column/").scroll_into_view_if_needed()
    time.sleep(0.5)
    column_btn = page.locator("button:has-text('Form Button in Column')").first
    column_btn.click()
    wait_for_streamlit(page)
    time.sleep(1)
    column_success = page.locator("text=/Form button in column clicked!/").count() > 0
    results.append(("Column Form", column_success))
    print(f"   Result: {'✅ PASS' if column_success else '❌ FAIL'}")

    # 5. API simulation
    print("\n5. Testing API simulation...")
    page.locator("text=/Test 6: Form with Simulated API/").scroll_into_view_if_needed()
    time.sleep(0.5)
    api_btn = page.locator("button:has-text('Submit to API')").first
    api_btn.click()
    wait_for_streamlit(page)
    time.sleep(2)
    api_success = page.locator("text=/API call successful!/").count() > 0
    results.append(("API Simulation", api_success))
    print(f"   Result: {'✅ PASS' if api_success else '❌ FAIL'}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20s} {status}")

    # Overall result
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed < total:
        pytest.fail(f"Only {passed}/{total} tests passed. Some handlers did not execute.")

    print("✅ ALL TESTS PASSED")
