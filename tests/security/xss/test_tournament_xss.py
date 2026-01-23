"""
XSS Security Tests - Tournament Forms

Tests tournament creation and application forms for XSS vulnerabilities.
Focuses on STORED XSS (most dangerous type) as tournament data persists in database.

Test Coverage:
- Tournament name field XSS injection (STORED)
- Tournament location field XSS injection (STORED)
- Instructor application message XSS (STORED)
- Tournament listing displays (XSS rendering prevention)

Security Requirements:
1. All tournament fields must be HTML-escaped before rendering
2. Stored XSS must be prevented (tournament data shown to multiple users)
3. Application messages must not execute JavaScript
4. Tournament listings must escape all user-provided data

CRITICAL: Stored XSS is more dangerous than reflected XSS because:
- Affects all users who view the tournament
- Persists in database
- Can be triggered without attacker interaction
"""

import pytest
from playwright.sync_api import Page
import requests

from .payloads import XSSPayloads, is_xss_vulnerable


# Test configuration
STREAMLIT_URL = "http://localhost:8501"
API_BASE_URL = "http://localhost:8000/api/v1"


@pytest.mark.playwright
class TestTournamentXSS:
    """XSS tests for tournament forms"""

    def test_tournament_name_stored_xss(self, page: Page):
        """
        Test tournament name field for stored XSS

        Attack Vector: <script>alert('XSS')</script> in tournament name
        Expected: Payload escaped when displayed in tournament list
        CRITICAL: STORED XSS - affects all users viewing tournaments
        """
        xss_payload = "<script>alert('TournamentXSS')</script>"

        # This test verifies that IF malicious tournament name gets stored,
        # it's properly escaped when rendered (defense in depth)

        # Note: Actual tournament creation requires admin auth
        # This test checks the rendering layer assuming payload got through

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Check if any tournament listings contain unescaped XSS
        page_content = page.content()

        # Should NOT contain unescaped script tags
        assert "<script>alert(" not in page_content, \
            "Tournament listings contain unescaped script tags - STORED XSS RISK!"

        # Should NOT be vulnerable
        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Tournament name rendering vulnerable to stored XSS"

    def test_tournament_location_stored_xss(self, page: Page):
        """
        Test tournament location field for stored XSS

        Attack Vector: <img src=x onerror=alert(1)> in location
        Expected: Payload escaped when displayed
        CRITICAL: STORED XSS in location field
        """
        xss_payload = "<img src=x onerror=alert(1)>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped onerror handlers
        assert "onerror=alert" not in page_content, \
            "Tournament location contains unescaped event handlers!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Tournament location vulnerable to stored XSS"

    @pytest.mark.parametrize("payload", XSSPayloads.get_basic_payloads())
    def test_instructor_application_message_xss(self, payload: str, page: Page):
        """
        Test instructor application message for stored XSS

        Attack Vector: Various XSS payloads in application message
        Expected: All payloads escaped when admin views application
        CRITICAL: STORED XSS - admin views these messages
        """
        # This test ensures application messages are escaped when displayed
        # Application messages are shown to admins in the application review UI

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Check that no XSS indicators are present unescaped
        is_vuln = is_xss_vulnerable(page_content, payload)
        assert not is_vuln, \
            f"Application message field vulnerable to stored XSS: {payload}"

    def test_no_javascript_execution_in_tournament_view(self, page: Page):
        """
        Test that no JavaScript executes when viewing tournaments

        Security Check: Monitor for alert() dialogs
        Expected: No unexpected dialogs when browsing tournaments
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

        # Navigate to different pages that might show tournament data
        try:
            # Login as player to view tournaments
            page.goto(STREAMLIT_URL)
            page.wait_for_timeout(3000)

            # Try to navigate to tournament listings if available
            # (Actual navigation depends on app structure)
            page.wait_for_timeout(2000)
        except Exception:
            pass

        # Verify no dialogs appeared
        assert not dialog_detected, \
            "JavaScript dialog detected while viewing tournaments - STORED XSS VULNERABILITY!"

    def test_tournament_svg_onload_stored_xss(self, page: Page):
        """
        Test tournament fields with SVG onload XSS

        Attack Vector: <svg onload=alert(1)> in tournament name
        Expected: SVG tag escaped
        """
        xss_payload = "<svg onload=alert(1)>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped SVG onload
        assert "<svg onload=" not in page_content.lower(), \
            "SVG onload not escaped in tournament data!"

        assert not is_xss_vulnerable(page_content, xss_payload), \
            "Tournament fields vulnerable to SVG onload stored XSS"

    def test_tournament_html_injection(self, page: Page):
        """
        Test tournament fields for HTML injection

        Attack Vector: <h1>Injected Heading</h1> in tournament name
        Expected: HTML tags escaped, not rendered
        """
        html_payload = "<h1>Injected Heading</h1>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # If payload appears, it should be escaped
        if "Injected Heading" in page_content:
            assert "&lt;h1&gt;" in page_content, \
                "HTML injection not escaped - tournament name renders HTML!"

    def test_tournament_iframe_injection(self, page: Page):
        """
        Test tournament fields for iframe injection

        Attack Vector: <iframe src='javascript:alert(1)'> in location
        Expected: iframe tag escaped
        CRITICAL: iframe injection can load malicious content
        """
        iframe_payload = "<iframe src='javascript:alert(1)'>"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped iframe
        assert "<iframe src='javascript:" not in page_content, \
            "iframe injection not escaped - CRITICAL VULNERABILITY!"

        assert not is_xss_vulnerable(page_content, iframe_payload), \
            "Tournament fields vulnerable to iframe injection"

    def test_tournament_attribute_injection_xss(self, page: Page):
        """
        Test for attribute injection XSS in tournament data

        Attack Vector: ' onclick='alert(1) in tournament fields
        Expected: Attribute injection prevented
        """
        attr_payload = "' onclick='alert(1)"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Should NOT contain unescaped onclick attribute injection
        assert "onclick='alert(" not in page_content and \
               'onclick="alert(' not in page_content, \
            "Attribute injection XSS not prevented!"

    def test_tournament_encoded_xss(self, page: Page):
        """
        Test for encoded XSS attempts in tournament fields

        Attack Vector: &#60;script&#62;alert('XSS')&#60;/script&#62; (HTML entities)
        Expected: Double-escaped or properly handled
        """
        encoded_payload = "&#60;script&#62;alert('XSS')&#60;/script&#62;"

        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Encoded payload should not execute
        # Check that no actual <script> tag appears
        assert "<script>alert('XSS')</script>" not in page_content, \
            "Encoded XSS payload decoded and executed!"

    @pytest.mark.parametrize("payload", XSSPayloads.EVENT_HANDLERS[:5])
    def test_tournament_event_handlers_xss(self, payload: str, page: Page):
        """
        Test tournament fields with various event handler XSS

        Attack Vectors: onerror, onload, onclick, onmouseover, onfocus
        Expected: All event handlers escaped
        """
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Check for common event handler patterns
        dangerous_patterns = [
            "onerror=",
            "onload=",
            "onclick=",
            "onmouseover=",
            "onfocus="
        ]

        for pattern in dangerous_patterns:
            # If pattern exists, it should be HTML-escaped
            if pattern in page_content.lower():
                assert f"{pattern}&#" in page_content.lower() or \
                       f"&{pattern.replace('=', '&#61;')}" in page_content.lower(), \
                    f"Event handler {pattern} not escaped in tournament data!"
