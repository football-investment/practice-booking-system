"""
Cookie Security Attributes Tests

Tests that cookies have proper security attributes:
1. SameSite=strict (prevents CSRF)
2. Secure=true (HTTPS only in production)
3. HttpOnly (prevents XSS theft for auth cookies)
4. Explicit max-age (prevents session fixation)

Cookie Types:
- access_token: Authentication cookie (HttpOnly=true)
- csrf_token: CSRF protection cookie (HttpOnly=false, must be readable by JS)
"""

import pytest
import requests
from http.cookies import SimpleCookie

        from app.config import settings

        # Check that COOKIE_SECURE setting exists

        # Check all required cookie settings exist

        # Should be set
API_BASE = "http://localhost:8000"


class TestCookieSecurityAttributes:
    """Test security attributes of cookies"""

    def parse_set_cookie(self, response) -> dict:
        """
        Parse Set-Cookie headers into dict

        Returns:
            dict: {cookie_name: SimpleCookie object}
        """
        cookies = {}
        for header in response.headers.get_list("Set-Cookie"):
            cookie = SimpleCookie()
            cookie.load(header)
            for key in cookie.keys():
                cookies[key] = cookie[key]
        return cookies

    def test_csrf_cookie_samesite_strict(self):
        """
        Test that CSRF cookie has SameSite=strict

        CRITICAL SECURITY: Prevents CSRF attacks by blocking cross-origin requests
        """
        response = requests.get(f"{API_BASE}/login")

        # Check csrf_token cookie attributes
        set_cookie_header = response.headers.get("Set-Cookie", "")

        # Should contain csrf_token
        assert "csrf_token=" in set_cookie_header, \
            "CSRF token cookie should be set on GET /login"

        # Should have SameSite=strict (or Strict, case-insensitive)
        assert "samesite=strict" in set_cookie_header.lower(), \
            "CSRF cookie MUST have SameSite=strict to prevent CSRF"

    def test_csrf_cookie_not_httponly(self):
        """
        Test that CSRF cookie is NOT HttpOnly

        Required: JavaScript must read this to send in X-CSRF-Token header
        """
        response = requests.get(f"{API_BASE}/login")
        set_cookie_header = response.headers.get("Set-Cookie", "")

        # csrf_token should NOT have HttpOnly
        # (it needs to be readable by JavaScript)
        csrf_cookies = [c for c in set_cookie_header.split(",") if "csrf_token=" in c]

        if csrf_cookies:
            csrf_cookie_str = csrf_cookies[0].lower()
            # Should NOT contain "httponly"
            assert "httponly" not in csrf_cookie_str, \
                "CSRF cookie must NOT be HttpOnly (JavaScript needs to read it)"

    def test_access_token_httponly(self):
        """
        Test that access_token cookie IS HttpOnly

        SECURITY: Prevents XSS from stealing authentication token
        """
        # Login to get access_token cookie
        response = requests.post(
            f"{API_BASE}/login",
            data={"email": "test@example.com", "password": "testpass"}
        )

        set_cookie_header = response.headers.get("Set-Cookie", "")

        # Should contain access_token
        if "access_token=" in set_cookie_header:
            # access_token should have HttpOnly
            access_cookies = [c for c in set_cookie_header.split(",") if "access_token=" in c]
            if access_cookies:
                access_cookie_str = access_cookies[0].lower()
                assert "httponly" in access_cookie_str, \
                    "access_token cookie MUST be HttpOnly to prevent XSS theft"

    def test_access_token_samesite_strict(self):
        """
        Test that access_token cookie has SameSite=strict

        SECURITY: Prevents CSRF attacks on authenticated sessions
        """
        # Login to get access_token cookie
        response = requests.post(
            f"{API_BASE}/login",
            data={"email": "test@example.com", "password": "testpass"}
        )

        set_cookie_header = response.headers.get("Set-Cookie", "")

        if "access_token=" in set_cookie_header:
            access_cookies = [c for c in set_cookie_header.split(",") if "access_token=" in c]
            if access_cookies:
                access_cookie_str = access_cookies[0].lower()
                assert "samesite=strict" in access_cookie_str, \
                    "access_token cookie MUST have SameSite=strict to prevent CSRF"

    def test_cookie_secure_flag_in_production(self):
        """
        Test that cookies have Secure flag in production

        Note: In development (HTTP), Secure=false is acceptable
        This test checks that the SETTING exists for production
        """
        assert hasattr(settings, "COOKIE_SECURE"), \
            "Config must have COOKIE_SECURE setting for production"

        # In production, should be True
        # (In development/testing, False is OK since we use HTTP)
        if settings.ENVIRONMENT == "production":
            assert settings.COOKIE_SECURE is True, \
                "COOKIE_SECURE must be True in production (HTTPS required)"

    def test_cookie_max_age_set(self):
        """
        Test that cookies have explicit max-age

        Security: Prevents indefinite session duration
        """
        response = requests.get(f"{API_BASE}/login")
        set_cookie_header = response.headers.get("Set-Cookie", "")

        # csrf_token should have Max-Age
        if "csrf_token=" in set_cookie_header:
            csrf_cookies = [c for c in set_cookie_header.split(",") if "csrf_token=" in c]
            if csrf_cookies:
                csrf_cookie_str = csrf_cookies[0].lower()
                assert "max-age=" in csrf_cookie_str, \
                    "CSRF cookie should have explicit Max-Age (prevents indefinite sessions)"

    def test_cookie_path_is_root(self):
        """
        Test that cookies have path=/

        Required: Cookies must be sent for all paths
        """
        response = requests.get(f"{API_BASE}/login")
        set_cookie_header = response.headers.get("Set-Cookie", "")

        # Should have Path=/
        assert "path=/" in set_cookie_header.lower(), \
            "Cookies should have Path=/ to be available across all paths"

    @pytest.mark.parametrize("samesite_value", ["None", "none"])
    def test_no_samesite_none(self, samesite_value: str):
        """
        Test that cookies do NOT use SameSite=None

        SECURITY: SameSite=None allows cross-origin cookie sending
        This defeats CSRF protection!
        """
        response = requests.get(f"{API_BASE}/login")
        set_cookie_header = response.headers.get("Set-Cookie", "")

        # Should NEVER have SameSite=None
        assert f"samesite={samesite_value}" not in set_cookie_header.lower(), \
            f"CRITICAL: Cookies must NOT use SameSite={samesite_value} (defeats CSRF protection)"


class TestCookieCrossSiteBehavior:
    """Test that cookies are NOT sent cross-site"""

    def test_csrf_cookie_not_sent_cross_origin(self):
        """
        Test that CSRF cookie with SameSite=strict is NOT sent cross-origin

        Note: This is browser behavior, hard to test server-side
        This test documents the expected behavior
        """
        # This test is more of a documentation than actual test
        # Browser enforces SameSite=strict, not server

        # If we could simulate cross-origin request in browser:
        # 1. User visits https://practice-booking.com (gets csrf_token cookie)
        # 2. User visits https://evil.com
        # 3. evil.com makes fetch() to practice-booking.com
        # 4. Browser should NOT send csrf_token cookie (SameSite=strict)

        # For now, we verify the attribute is set correctly
        response = requests.get(f"{API_BASE}/login")
        set_cookie_header = response.headers.get("Set-Cookie", "")

        assert "samesite=strict" in set_cookie_header.lower(), \
            "SameSite=strict ensures cookie is NOT sent cross-origin"

    def test_access_token_not_sent_cross_origin(self):
        """
        Test that access_token cookie is NOT sent cross-origin

        Same as above - browser enforcement, server sets attribute
        """
        # Login to get access_token
        response = requests.post(
            f"{API_BASE}/login",
            data={"email": "test@example.com", "password": "testpass"}
        )

        set_cookie_header = response.headers.get("Set-Cookie", "")

        if "access_token=" in set_cookie_header:
            assert "samesite=strict" in set_cookie_header.lower(), \
                "SameSite=strict ensures access_token is NOT sent cross-origin"


class TestCookieConfiguration:
    """Test that cookie configuration settings are correct"""

    def test_cookie_config_exists(self):
        """
        Test that cookie security configuration exists in settings
        """
        assert hasattr(settings, "COOKIE_SECURE"), "Missing COOKIE_SECURE setting"
        assert hasattr(settings, "COOKIE_SAMESITE"), "Missing COOKIE_SAMESITE setting"
        assert hasattr(settings, "COOKIE_HTTPONLY"), "Missing COOKIE_HTTPONLY setting"
        assert hasattr(settings, "COOKIE_MAX_AGE"), "Missing COOKIE_MAX_AGE setting"

    def test_cookie_samesite_is_strict(self):
        """
        Test that default SameSite value is 'strict'

        CRITICAL SECURITY: Must be strict (not lax or none)
        """
        assert settings.COOKIE_SAMESITE.lower() == "strict", \
            f"COOKIE_SAMESITE must be 'strict' for CSRF protection, got '{settings.COOKIE_SAMESITE}'"

    def test_cookie_httponly_is_true(self):
        """
        Test that HttpOnly is enabled by default

        For auth cookies (not CSRF cookies)
        """
        assert settings.COOKIE_HTTPONLY is True, \
            "COOKIE_HTTPONLY should be True for auth cookies (prevents XSS theft)"

    def test_cookie_max_age_reasonable(self):
        """
        Test that cookie max age is reasonable (not too long)

        Prevents indefinite sessions
        """
        assert settings.COOKIE_MAX_AGE > 0, \
            "COOKIE_MAX_AGE must be positive"

        # Should not be too long (24 hours = 86400 seconds)
        assert settings.COOKIE_MAX_AGE <= 86400, \
            f"COOKIE_MAX_AGE should not exceed 24 hours, got {settings.COOKIE_MAX_AGE} seconds"
