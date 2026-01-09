"""
Inspect the HTML structure of Streamlit date_input widget
"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch(headless=False)
    page = browser.new_page()
    
    # Navigate to Streamlit home page
    page.goto("http://localhost:8501")
    page.wait_for_timeout(3000)
    
    # Click Register with Invitation Code
    register_btn = page.locator("button:has-text('Register with Invitation Code')")
    register_btn.click()
    page.wait_for_timeout(2000)
    
    # Get the HTML of the Date of Birth field
    date_field_html = page.locator("div:has-text('Date of Birth')").first.evaluate(
        "el => el.parentElement.innerHTML"
    )
    
    print("=" * 80)
    print("DATE OF BIRTH FIELD HTML:")
    print("=" * 80)
    print(date_field_html)
    print("=" * 80)
    
    # Also try to find all input elements
    all_inputs = page.locator("input").all()
    print(f"\n✅ Found {len(all_inputs)} input elements")
    
    for i, inp in enumerate(all_inputs):
        input_type = inp.get_attribute("type")
        placeholder = inp.get_attribute("placeholder")
        data_baseweb = inp.get_attribute("data-baseweb")
        print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}', data-baseweb='{data_baseweb}'")
    
    page.wait_for_timeout(5000)
    browser.close()
