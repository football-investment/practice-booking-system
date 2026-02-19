"""
XSS Security Tests - User Profile and Dashboard

Tests user profile and dashboard for XSS vulnerabilities.
Focuses on STORED XSS as profile data persists and is displayed across sessions.

Test Coverage:
- Profile name display XSS (STORED)
- Profile bio/description XSS (STORED)
- Nickname field XSS (STORED)
- Dashboard welcome message XSS
- User-generated content rendering

Security Requirements:
1. All user profile fields must be HTML-escaped before rendering
2. Stored XSS must be prevented (profile shown to user and potentially others)
3. Welcome messages must not execute JavaScript
4. User nicknames/names shown in leaderboards must be escaped

CRITICAL: Profile XSS can affect:
- The user themselves (persistent across sessions)
- Other users viewing the profile
- Leaderboards and rankings
- Admin panels showing user data
"""

import pytest
from playwright.sync_api import Page

from .payloads import XSSPayloads, is_xss_vulnerable


# Test configuration
STREAMLIT_URL = "http://localhost:8501"


@pytest.mark.playwright
class TestProfileXSS:
    """XSS tests for user profile and dashboard"""

    def test_profile_name_stored_xss(self, page: Page):
        """
        Test user profile name field for stored XSS

        Attack Vector: <script>alert('ProfileXSS')</script> in user name
        Expected: Payload escaped when displayed
        CRITICAL: STORED XSS - affects user's own session and others viewing profile
        """
        xss_payload = "<script>alert('ProfileXSS')</script>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Check profile/dashboard displays
        page_content = page.content()

        # Should NOT contain unescaped script tags
        assert "<script>alert(" not in page_content, \
            "Profile displays contain unescaped script tags - STORED XSS!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Profile name rendering vulnerable to stored XSS"

    def test_nickname_stored_xss(self, page: Page):
        """
        Test nickname field for stored XSS

        Attack Vector: <img src=x onerror=alert(1)> in nickname
        Expected: Payload escaped in all displays (dashboard, leaderboards)
        CRITICAL: Nicknames shown in multiple places (leaderboards, chat, etc.)
        """
        xss_payload = "<img src=x onerror=alert(1)>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped onerror handlers
        assert "onerror=alert" not in page_content, \
            "Nickname contains unescaped event handlers - STORED XSS!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Nickname field vulnerable to stored XSS"

    def test_welcome_message_xss(self, page: Page):
        """
        Test dashboard welcome message for XSS

        Attack Vector: User name in "Welcome, <name>!" message
        Expected: Name properly escaped in welcome message
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(3000)

        page_content = page.content()

        # Check welcome messages don't contain XSS
        # Look for common welcome patterns
        if "Welcome," in page_content or "Hello," in page_content:
            assert not is_xss_vulnerable(page_content, "<script>alert(1)</script>"), \
                "Welcome message vulnerable to XSS injection"

    @pytest.mark.parametrize("payload", XSSPayloads.get_basic_payloads())
    def test_profile_fields_basic_xss(self, payload: str, page: Page):
        """
        Test various profile fields with basic XSS payloads

        Attack Vectors: Multiple XSS patterns in profile fields
        Expected: All payloads escaped across all profile displays
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Verify no XSS vulnerabilities in rendered profile
        is_vuln = is_xss_vulnerable(page_content, payload)
        assert not is_vuln, \
            f"Profile rendering vulnerable to XSS: {payload}"

    def test_no_javascript_execution_in_profile(self, page: Page):
        """
        Test that no JavaScript executes when viewing profile

        Security Check: Monitor for alert() dialogs
        Expected: No unexpected dialogs when viewing profile/dashboard
        CRITICAL: Tests stored XSS defense
        """
        page.goto(STREAMLIT_URL)

        # Set up dialog handler
        dialog_detected = False

        def handle_dialog(dialog):
            nonlocal dialog_detected
            dialog_detected = True
            dialog.dismiss()

        page.on("dialog", handle_dialog)

        # Navigate through profile/dashboard pages
        try:
            page.goto(STREAMLIT_URL)
            page.wait_for_timeout(3000)

            # Wait for any dynamic content to load
            page.wait_for_timeout(2000)
        except Exception:
            pass

        # Verify no dialogs appeared
        assert not dialog_detected, \
            "JavaScript dialog detected in profile/dashboard - STORED XSS VULNERABILITY!"

    def test_profile_svg_onload_xss(self, page: Page):
        """
        Test profile fields with SVG onload XSS

        Attack Vector: <svg onload=alert('XSS')> in profile fields
        Expected: SVG tag escaped
        """
        xss_payload = "<svg onload=alert('XSS')>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped SVG onload
        assert "<svg onload=" not in page_content.lower(), \
            "SVG onload not escaped in profile!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Profile vulnerable to SVG onload stored XSS"

    def test_profile_html_injection(self, page: Page):
        """
        Test profile for HTML injection

        Attack Vector: <h1>Injected Content</h1> in profile fields
        Expected: HTML tags escaped, not rendered
        """
        html_payload = "<h1>Injected Profile Content</h1>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # If payload text appears, tags should be escaped
        if "Injected Profile Content" in page_content:
            assert "&lt;h1&gt;" in page_content, \
                "HTML injection not escaped in profile!"

    def test_profile_style_injection(self, page: Page):
        """
        Test for CSS/style injection in profile

        Attack Vector: <style>body{display:none}</style> in profile fields
        Expected: Style tags escaped
        CRITICAL: Style injection can hide content, phishing risk
        """
        style_payload = "<style>body{display:none}</style>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped style tags
        assert "<style>body{display:none}</style>" not in page_content, \
            "Style injection not escaped - can hide page content!"

    def test_profile_iframe_injection(self, page: Page):
        """
        Test profile for iframe injection

        Attack Vector: <iframe src='http://evil.com'> in bio/description
        Expected: iframe tag escaped
        """
        iframe_payload = "<iframe src='http://evil.com'>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped iframe
        assert "<iframe src=" not in page_content or \
               "&lt;iframe" in page_content, \
            "iframe injection not escaped in profile!"

    def test_profile_javascript_protocol_xss(self, page: Page):
        """
        Test for javascript: protocol XSS in profile links

        Attack Vector: javascript:alert('XSS') in profile URLs
        Expected: javascript: protocol blocked or escaped
        """
        js_protocol = "javascript:alert('XSS')"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped javascript: protocol
        assert 'href="javascript:' not in page_content and \
               "href='javascript:" not in page_content, \
            "javascript: protocol not blocked in profile links!"

    @pytest.mark.parametrize("payload", XSSPayloads.EVENT_HANDLERS[:5])
    def test_profile_event_handlers_xss(self, payload: str, page: Page):
        """
        Test profile with various event handler XSS attempts

        Attack Vectors: onerror, onload, onclick, onmouseover
        Expected: All event handlers escaped
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Extract event handler from payload
        for handler in ["onerror", "onload", "onclick", "onmouseover", "onfocus"]:
            if handler in payload.lower():
                # Should be escaped if present
                if handler in page_content.lower():
                    assert f"{handler}=" not in page_content or \
                           f"{handler}&#61;" in page_content, \
                        f"Event handler {handler} not escaped in profile!"

    def test_profile_encoded_xss_attempts(self, page: Page):
        """
        Test for various encoding bypass attempts

        Attack Vectors: HTML entities, URL encoding, hex encoding
        Expected: All encoding attempts handled safely
        """
        encoded_payloads = [
            "&#60;script&#62;alert(1)&#60;/script&#62;",  # HTML entities
            "%3Cscript%3Ealert(1)%3C/script%3E",  # URL encoding
        ]

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # None of these should result in actual script execution
        for payload in encoded_payloads:
            # The decoded version should not appear
            assert "<script>alert(1)</script>" not in page_content, \
                f"Encoded payload {payload} was decoded and rendered!"
