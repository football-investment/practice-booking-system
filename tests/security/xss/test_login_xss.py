"""
XSS Security Tests - Login Form

Tests login form for XSS vulnerabilities using Playwright.
Verifies that user input is properly escaped/sanitized before rendering.

Test Coverage:
- Email field XSS injection
- Password field XSS injection
- Reflected XSS in error messages
- No JavaScript execution from malicious input

Security Requirements:
1. Login form inputs must be HTML-escaped before rendering
2. Error messages must escape user input (reflected XSS prevention)
3. No JavaScript execution from user input
4. Failed login attempts must not leak XSS payloads
"""

import pytest
from playwright.sync_api import Page

from .payloads import XSSPayloads, is_xss_vulnerable


# Test configuration
STREAMLIT_URL = "http://localhost:8501"


@pytest.mark.playwright
class TestLoginXSS:
    """XSS tests for login form"""

    def test_login_email_basic_xss(self, page: Page):
        """
        Test login form email field with basic XSS payload

        Attack Vector: <script>alert('XSS')</script> in email field
        Expected: Payload escaped, no script execution, safe error message
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        xss_payload = "<script>alert('XSS')</script>"

        # Fill login form with XSS payload in email
        try:
            email_inputs = page.locator("[data-testid='stTextInput'] input").all()
            if len(email_inputs) >= 2:
                # Fill email with XSS payload
                email_inputs[0].fill(xss_payload)
                # Fill password with dummy value
                email_inputs[1].fill("password123")

                # Click login button
                login_button = page.get_by_role("button", name="🔐 Login")
                if login_button.count() > 0:
                    login_button.click()
                    page.wait_for_timeout(2000)
        except Exception:
            # If login form not available, just check current page
            pass

        # Check that script tag is NOT executed in any displayed content
        page_content = page.content()

        # Should NOT contain unescaped script tag
        assert "<script>alert('XSS')</script>" not in page_content, \
            "XSS payload not escaped in email field - CRITICAL VULNERABILITY!"

        # Should NOT be vulnerable
        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Login email field vulnerable to XSS injection"

    def test_login_event_handler_xss(self, page: Page):
        """
        Test login form with event handler XSS

        Attack Vector: <img src=x onerror=alert(1)> in email field
        Expected: Event handler escaped, no execution
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        xss_payload = "<img src=x onerror=alert(1)>"

        # Fill login form
        try:
            email_inputs = page.locator("[data-testid='stTextInput'] input").all()
            if len(email_inputs) >= 2:
                email_inputs[0].fill(xss_payload)
                email_inputs[1].fill("password123")

                login_button = page.get_by_role("button", name="🔐 Login")
                if login_button.count() > 0:
                    login_button.click()
                    page.wait_for_timeout(2000)
        except Exception:
            pass

        # Check rendered content
        page_content = page.content()

        # Should NOT contain unescaped onerror handler
        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Event handler XSS not escaped in login form!"

    @pytest.mark.parametrize("payload", XSSPayloads.get_basic_payloads())
    def test_login_error_message_xss(self, payload: str, page: Page):
        """
        Test that login error messages don't reflect unescaped input

        Attack Vector: Various XSS payloads in email, check error message
        Expected: Error message escapes all payloads
        CRITICAL: Reflected XSS in error messages is common vulnerability
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Attempt login with XSS payload
        try:
            email_inputs = page.locator("[data-testid='stTextInput'] input").all()
            if len(email_inputs) >= 2:
                email_inputs[0].fill(payload)
                email_inputs[1].fill("wrongpassword")

                login_button = page.get_by_role("button", name="🔐 Login")
                if login_button.count() > 0:
                    login_button.click()
                    page.wait_for_timeout(2000)
        except Exception:
            pass

        # Check for vulnerability in error messages
        page_content = page.content()

        # Error message should NOT contain unescaped payload
        is_vuln = is_xss_vulnerable(page_content, payload)
        assert not is_vuln, \
            f"Login error message vulnerable to reflected XSS: {payload}"

    def test_no_javascript_execution_on_login(self, page: Page):
        """
        Test that no JavaScript from login input executes

        Security Check: Monitor for alert() dialogs during login
        Expected: No unexpected dialogs appear
        """
        page.goto(STREAMLIT_URL)

        # Set up dialog handler to catch any alerts
        dialog_detected = False

        def handle_dialog(dialog):
            nonlocal dialog_detected
            dialog_detected = True
            dialog.dismiss()

        page.on("dialog", handle_dialog)

        # Try multiple XSS payloads in login
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('XSS')"
        ]

        for payload in payloads:
            try:
                page.goto(STREAMLIT_URL)
                page.wait_for_timeout(1000)

                email_inputs = page.locator("[data-testid='stTextInput'] input").all()
                if len(email_inputs) >= 2:
                    email_inputs[0].fill(payload)
                    email_inputs[1].fill("password")

                    login_button = page.get_by_role("button", name="🔐 Login")
                    if login_button.count() > 0:
                        login_button.click()
                        page.wait_for_timeout(2000)
            except Exception:
                pass

        # Verify no dialogs appeared
        assert not dialog_detected, \
            "Unexpected JavaScript dialog detected - CRITICAL XSS VULNERABILITY!"

    def test_login_svg_onload_xss(self, page: Page):
        """
        Test login form with SVG onload XSS

        Attack Vector: <svg onload=alert('XSS')> in email field
        Expected: SVG tag escaped, no onload execution
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        xss_payload = "<svg onload=alert('XSS')>"

        try:
            email_inputs = page.locator("[data-testid='stTextInput'] input").all()
            if len(email_inputs) >= 2:
                email_inputs[0].fill(xss_payload)
                email_inputs[1].fill("password123")

                login_button = page.get_by_role("button", name="🔐 Login")
                if login_button.count() > 0:
                    login_button.click()
                    page.wait_for_timeout(2000)
        except Exception:
            pass

        page_content = page.content()

        # Should NOT contain unescaped SVG or onload
        assert "<svg onload=" not in page_content.lower(), \
            "SVG onload XSS not escaped in login form!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Login form vulnerable to SVG onload XSS"
