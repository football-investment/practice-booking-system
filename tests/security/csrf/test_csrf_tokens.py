"""
CSRF Token Generation and Validation Tests

Tests the Double Submit Cookie pattern implementation:
1. Token generation (cryptographic randomness)
2. Token validation (cookie + header matching)
3. Token rotation (new token after use)
4. Constant-time comparison (timing attack prevention)
"""

import pytest
import requests
import time
from typing import Dict, Optional


API_BASE = "http://localhost:8000"


class TestCSRFTokenGeneration:
    """Test CSRF token generation"""

    def test_csrf_token_generated_on_get(self):
        """
        Test that GET request generates CSRF token

        Expected: csrf_token cookie set in response
        """
        response = requests.get(f"{API_BASE}/login")

        # Should set csrf_token cookie
        assert "csrf_token" in response.cookies, \
            "CSRF token should be generated on GET request"

        # Token should be non-empty
        token = response.cookies["csrf_token"]
        assert len(token) > 0, "CSRF token should not be empty"

    def test_csrf_token_length(self):
        """
        Test that CSRF token has sufficient entropy

        Expected: 64 characters (32 bytes hex) for security
        """
        response = requests.get(f"{API_BASE}/login")
        token = response.cookies.get("csrf_token", "")

        # Should be 64-character hex string (32 bytes)
        assert len(token) == 64, \
            f"CSRF token should be 64 characters (32 bytes hex), got {len(token)}"

        # Should be hexadecimal
        try:
            int(token, 16)  # Verify it's valid hex
        except ValueError:
            pytest.fail(f"CSRF token should be hexadecimal, got: {token}")

    def test_csrf_token_randomness(self):
        """
        Test that CSRF tokens are random (not predictable)

        Generate 10 tokens and verify they're all different
        """
        tokens = set()

        for _ in range(10):
            response = requests.get(f"{API_BASE}/login")
            token = response.cookies.get("csrf_token", "")
            tokens.add(token)

        # All tokens should be unique
        assert len(tokens) == 10, \
            f"CSRF tokens should be random, got {len(tokens)} unique tokens out of 10"

    def test_csrf_token_persistent_across_requests(self):
        """
        Test that CSRF token persists across requests (via cookie)

        Expected: Same token returned if cookie is sent back
        """
        # First request: Get token
        response1 = requests.get(f"{API_BASE}/login")
        token1 = response1.cookies.get("csrf_token")

        # Second request: Send token back
        response2 = requests.get(
            f"{API_BASE}/dashboard",
            cookies={"csrf_token": token1}
        )

        # Should return same token (or generate new one, both acceptable)
        token2 = response2.cookies.get("csrf_token")
        assert token2 is not None, "Token should persist or be regenerated"


class TestCSRFTokenValidation:
    """Test CSRF token validation on state-changing requests"""

    def get_csrf_token(self) -> tuple[str, Dict[str, str]]:
        """
        Helper: Get CSRF token from server

        Returns:
            tuple: (csrf_token, cookies_dict)
        """
        response = requests.get(f"{API_BASE}/login")
        token = response.cookies.get("csrf_token", "")
        cookies = {"csrf_token": token}
        return token, cookies

    def test_post_without_csrf_token_blocked(self):
        """
        Test that POST without CSRF token is blocked

        CRITICAL SECURITY TEST: This prevents CSRF attacks
        """
        response = requests.post(
            f"{API_BASE}/auth/change-password",
            json={"current_password": "test", "new_password": "test2"}
        )

        # Should be blocked with 403 Forbidden
        assert response.status_code == 403, \
            f"POST without CSRF token should return 403, got {response.status_code}"

        # Error should mention CSRF
        error_detail = response.json().get("detail", "")
        assert "csrf" in error_detail.lower() or "token" in error_detail.lower(), \
            f"Error should mention CSRF/token, got: {error_detail}"

    def test_post_with_valid_csrf_token_allowed(self):
        """
        Test that POST with valid CSRF token is allowed

        Expected: Request proceeds if token matches
        """
        # Get CSRF token
        token, cookies = self.get_csrf_token()

        # POST with token in both cookie and header
        response = requests.post(
            f"{API_BASE}/some-protected-endpoint",
            cookies=cookies,
            headers={"X-CSRF-Token": token},
            json={"data": "test"}
        )

        # Should NOT be blocked by CSRF (may fail for other reasons)
        assert response.status_code != 403 or "csrf" not in response.text.lower(), \
            "POST with valid CSRF token should not be blocked by CSRF protection"

    def test_post_with_mismatched_csrf_token_blocked(self):
        """
        Test that POST with mismatched token is blocked

        Attack scenario: Attacker tries to guess token
        """
        # Get real CSRF token
        token, cookies = self.get_csrf_token()

        # Send different token in header (mismatch)
        fake_token = "a" * 64  # Wrong token

        response = requests.post(
            f"{API_BASE}/auth/change-password",
            cookies=cookies,  # Real cookie
            headers={"X-CSRF-Token": fake_token},  # Fake header
            json={"current_password": "test", "new_password": "test2"}
        )

        # Should be blocked
        assert response.status_code == 403, \
            "POST with mismatched CSRF token should return 403"

    def test_post_with_only_cookie_blocked(self):
        """
        Test that POST with only cookie (no header) is blocked

        Attack scenario: Simple form submission (cannot set custom headers)
        """
        # Get CSRF token cookie
        token, cookies = self.get_csrf_token()

        # POST with cookie but NO header
        response = requests.post(
            f"{API_BASE}/auth/change-password",
            cookies=cookies,
            # NO X-CSRF-Token header
            json={"current_password": "test", "new_password": "test2"}
        )

        # Should be blocked (missing header)
        assert response.status_code == 403, \
            "POST with only cookie (no header) should be blocked"

    def test_post_with_only_header_blocked(self):
        """
        Test that POST with only header (no cookie) is blocked

        Attack scenario: Attacker tries to bypass cookie requirement
        """
        # Get CSRF token
        token, _ = self.get_csrf_token()

        # POST with header but NO cookie
        response = requests.post(
            f"{API_BASE}/auth/change-password",
            # NO cookies
            headers={"X-CSRF-Token": token},
            json={"current_password": "test", "new_password": "test2"}
        )

        # Should be blocked (missing cookie)
        assert response.status_code == 403, \
            "POST with only header (no cookie) should be blocked"

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_csrf_protection_on_all_methods(self, method: str):
        """
        Test that CSRF protection applies to all state-changing methods

        Security: POST, PUT, PATCH, DELETE all modify state
        """
        # Get CSRF token
        token, cookies = self.get_csrf_token()

        # Try method WITHOUT CSRF token
        response = requests.request(
            method,
            f"{API_BASE}/auth/logout",  # Any endpoint
            # NO CSRF token
        )

        # Should be blocked (or may return 404/405 if endpoint doesn't exist)
        # The key is it should NOT succeed without CSRF
        assert response.status_code in [403, 404, 405], \
            f"{method} without CSRF should be blocked or not found, got {response.status_code}"

    def test_get_request_does_not_require_csrf(self):
        """
        Test that GET request does NOT require CSRF token

        GET is safe (read-only), so no CSRF protection needed
        """
        response = requests.get(f"{API_BASE}/dashboard")

        # Should succeed without CSRF token (or redirect to login, or 401 unauthorized)
        # The key is: should NOT return 403 with "CSRF" error
        assert response.status_code in [200, 302, 303, 401], \
            f"GET should not require CSRF token, got {response.status_code}"

        # If it's a 403, make sure it's NOT a CSRF error
        if response.status_code == 403:
            error_text = response.text.lower()
            assert "csrf" not in error_text, \
                "GET request should not be blocked by CSRF protection"

    def test_api_endpoints_with_bearer_token_exempt(self):
        """
        Test that API endpoints with Bearer token skip CSRF

        Security: Bearer token in Authorization header is CSRF-safe
        (requires JavaScript, which triggers CORS preflight)
        """
        # POST to API endpoint with Bearer token (no CSRF token)
        response = requests.post(
            f"{API_BASE}/api/v1/auth/login",
            headers={"Authorization": "Bearer fake-token-for-testing"},
            json={"email": "test@test.com", "password": "test"}
        )

        # Should NOT be blocked by CSRF (may fail for other reasons like invalid token)
        # The key is: should not return 403 with "CSRF" in error
        if response.status_code == 403:
            error_text = response.text.lower()
            assert "csrf" not in error_text, \
                "Bearer auth requests should skip CSRF validation"


class TestCSRFTokenRotation:
    """Test CSRF token rotation after use"""

    def test_token_rotates_after_post(self):
        """
        Test that CSRF token is rotated (new token) after POST

        Security: Prevents token replay attacks
        """
        # Get initial token
        response1 = requests.get(f"{API_BASE}/login")
        token1 = response1.cookies.get("csrf_token")

        # Make a POST request (this should rotate token)
        # Note: May need valid endpoint, using login as example
        response2 = requests.post(
            f"{API_BASE}/login",
            cookies={"csrf_token": token1},
            headers={"X-CSRF-Token": token1},
            data={"email": "test@test.com", "password": "test"}
        )

        # Check if new token was set
        token2 = response2.cookies.get("csrf_token")

        # New token should be different (rotation)
        # NOTE: This test may need adjustment based on actual implementation
        if token2:
            # If new token is set, it should be different
            assert token2 != token1, \
                "CSRF token should rotate after POST (prevents replay)"


class TestCSRFTimingAttacks:
    """Test protection against timing attacks"""

    def get_csrf_token(self) -> tuple[str, Dict[str, str]]:
        """
        Helper: Get CSRF token from server

        Returns:
            tuple: (csrf_token, cookies_dict)
        """
        response = requests.get(f"{API_BASE}/login")
        token = response.cookies.get("csrf_token", "")
        cookies = {"csrf_token": token}
        return token, cookies

    def test_constant_time_comparison(self):
        """
        Test that token comparison is constant-time

        Security: Prevents timing attacks to leak token information

        Note: This is a best-effort test. True timing attack prevention
        requires constant-time comparison in code (secrets.compare_digest)
        """
        # Get real token
        token, cookies = self.get_csrf_token()

        # Test with token that differs at different positions
        wrong_tokens = [
            "a" + token[1:],  # First char wrong
            token[:32] + "a" + token[33:],  # Middle char wrong
            token[:-1] + "a",  # Last char wrong
        ]

        timings = []

        for wrong_token in wrong_tokens:
            start = time.perf_counter()

            requests.post(
                f"{API_BASE}/auth/change-password",
                cookies=cookies,
                headers={"X-CSRF-Token": wrong_token},
                json={"current_password": "test", "new_password": "test2"}
            )

            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        # Timings should be similar (within reasonable variance)
        # This is NOT a perfect test, but gives indication
        max_timing = max(timings)
        min_timing = min(timings)
        variance = max_timing - min_timing

        # Variance should be small (< 10ms as rough threshold)
        # Actual threshold may need tuning
        assert variance < 0.01, \
            f"Timing variance suggests non-constant-time comparison: {variance}s"
