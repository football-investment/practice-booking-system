"""
Debug script to inspect Streamlit login page structure
"""

import pytest
import time
from playwright.sync_api import Page

STREAMLIT_URL = "http://localhost:8501"


@pytest.mark.e2e
def test_inspect_login_page(page: Page):
    """Inspect Streamlit login page to find correct selectors"""

    print("\nNavigating to Streamlit...")
    page.goto(STREAMLIT_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Take screenshot
    page.screenshot(path="tests/e2e/screenshots/streamlit_login.png")
    print("Screenshot saved: tests/e2e/screenshots/streamlit_login.png")

    # Print page HTML structure
    html = page.content()
    with open("tests/e2e/streamlit_login_html.txt", "w") as f:
        f.write(html)
    print("HTML saved: tests/e2e/streamlit_login_html.txt")

    # List all input fields
    inputs = page.locator("input").all()
    print(f"\nFound {len(inputs)} input fields:")
    for i, inp in enumerate(inputs):
        input_type = inp.get_attribute("type")
        input_name = inp.get_attribute("name")
        input_placeholder = inp.get_attribute("placeholder")
        input_aria_label = inp.get_attribute("aria-label")
        print(f"  Input {i}: type={input_type}, name={input_name}, placeholder={input_placeholder}, aria-label={input_aria_label}")

    # List all buttons
    buttons = page.locator("button").all()
    print(f"\nFound {len(buttons)} buttons:")
    for i, btn in enumerate(buttons):
        btn_text = btn.inner_text()
        print(f"  Button {i}: {btn_text}")

    # Wait so we can inspect in browser
    print("\nWaiting 10 seconds so you can inspect the browser window...")
    time.sleep(10)
