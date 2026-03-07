"""
Quick screenshot tool to see what's on the page
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8501"

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        print(f"Opening {BASE_URL}...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("Taking screenshot...")
        page.screenshot(path="screenshot_home.png")
        print("Screenshot saved as screenshot_home.png")

        print("\n=== PAGE CONTENT ===")
        # Get all buttons
        buttons = page.locator('button').all()
        print(f"\nFound {len(buttons)} buttons:")
        for i, btn in enumerate(buttons):
            text = btn.text_content()
            if text:
                print(f"  {i+1}. '{text.strip()}'")

        # Get page text
        print("\n=== PAGE TEXT (first 500 chars) ===")
        page_text = page.text_content('body')
        if page_text:
            print(page_text[:500])

        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    take_screenshot()
