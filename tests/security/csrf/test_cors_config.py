"""
CORS Configuration Security Tests

Tests that CORS middleware properly restricts cross-origin requests
to prevent CSRF attacks via unauthorized origins.

Critical Security Requirement:
- NO allow_origins=["*"] (wildcard) with allow_credentials=True
- Explicit allowlist of trusted origins only
"""

import pytest
import requests
from typing import Dict


API_BASE = "http://localhost:8000"


class TestCORSConfiguration:
    """Test CORS configuration security"""

    def test_cors_preflight_allowed_origin(self):
        """
        Test that CORS preflight succeeds for allowed origin

        Security: Localhost is in CORS_ALLOWED_ORIGINS for development
        """
        response = requests.options(
            f"{API_BASE}/api/v1/tournaments",
            headers={
                "Origin": "http://localhost:8501",  # Streamlit default port
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            }
        )

        # Preflight should succeed for allowed origin
        assert response.status_code in [200, 204]

        # Should include CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8501"

    def test_cors_preflight_disallowed_origin(self):
        """
        Test that CORS preflight fails for disallowed origin

        CRITICAL SECURITY TEST: Attacker from evil.com should be blocked
        """
        response = requests.options(
            f"{API_BASE}/api/v1/tournaments",
            headers={
                "Origin": "https://evil.com",  # Unauthorized origin
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )

        # Preflight should succeed (OPTIONS always returns 200)
        # BUT: Should NOT include Access-Control-Allow-Origin for evil.com
        if "Access-Control-Allow-Origin" in response.headers:
            # If header present, it should NOT be evil.com
            assert response.headers["Access-Control-Allow-Origin"] != "https://evil.com"
            # And should NOT be wildcard
            assert response.headers["Access-Control-Allow-Origin"] != "*"

    def test_cors_no_wildcard_with_credentials(self):
        """
        Test that CORS does NOT use wildcard origin with credentials

        CRITICAL SECURITY VIOLATION:
        - allow_origins=["*"] + allow_credentials=True is forbidden by spec
        - If present, browsers reject (but attackers can bypass)
        """
        response = requests.get(
            f"{API_BASE}/api/v1/tournaments",
            headers={"Origin": "http://localhost:8501"}
        )

        # Check CORS headers
        if "Access-Control-Allow-Origin" in response.headers:
            # Should NEVER be wildcard when credentials are allowed
            assert response.headers["Access-Control-Allow-Origin"] != "*", \
                "CRITICAL: allow_origins=['*'] with allow_credentials=True"

            # Should be specific origin or null
            allowed_origin = response.headers["Access-Control-Allow-Origin"]
            assert allowed_origin in ["http://localhost:8501", "http://localhost:8000", "http://127.0.0.1:8501", "http://127.0.0.1:8000"], \
                f"Unexpected CORS origin: {allowed_origin}"

    def test_cors_credentials_allowed(self):
        """
        Test that CORS allows credentials for trusted origins

        Required for cookie-based authentication
        """
        response = requests.get(
            f"{API_BASE}/api/v1/tournaments",
            headers={"Origin": "http://localhost:8501"}
        )

        # Should allow credentials
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_cors_custom_headers_allowed(self):
        """
        Test that CORS allows X-CSRF-Token header

        Required for CSRF protection (Double Submit Cookie pattern)
        """
        response = requests.options(
            f"{API_BASE}/api/v1/tournaments",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-CSRF-Token, Content-Type",
            }
        )

        # Should allow X-CSRF-Token header
        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "").lower()
        assert "x-csrf-token" in allowed_headers, \
            "CORS must allow X-CSRF-Token header for CSRF protection"

    def test_cors_exposed_headers(self):
        """
        Test that CORS exposes X-CSRF-Token header to client

        Client JavaScript must be able to read the token from response
        """
        response = requests.get(
            f"{API_BASE}/api/v1/tournaments",
            headers={"Origin": "http://localhost:8501"}
        )

        # Should expose X-CSRF-Token header
        exposed_headers = response.headers.get("Access-Control-Expose-Headers", "").lower()
        assert "x-csrf-token" in exposed_headers, \
            "CORS must expose X-CSRF-Token header so client can read it"

    @pytest.mark.parametrize("malicious_origin", [
        "https://evil.com",
        "http://attacker.net",
        "https://phishing-site.org",
        "http://localhost.evil.com",  # Subdomain attack
        "http://localhost:8501.evil.com",  # Port-based attack
    ])
    def test_cors_rejects_malicious_origins(self, malicious_origin: str):
        """
        Test that various malicious origins are rejected

        Attack scenarios:
        - Direct evil domain
        - Subdomain confusion attack
        - Port-based confusion attack
        """
        response = requests.get(
            f"{API_BASE}/api/v1/tournaments",
            headers={"Origin": malicious_origin}
        )

        # Should NOT set Access-Control-Allow-Origin to malicious origin
        if "Access-Control-Allow-Origin" in response.headers:
            assert response.headers["Access-Control-Allow-Origin"] != malicious_origin, \
                f"CRITICAL: Malicious origin {malicious_origin} was allowed!"

    def test_cors_methods_explicit(self):
        """
        Test that CORS uses explicit method list (not wildcard)

        Security: Wildcard methods allow unexpected HTTP verbs
        """
        response = requests.options(
            f"{API_BASE}/api/v1/tournaments",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "POST",
            }
        )

        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")

        # Should NOT be wildcard
        assert allowed_methods != "*", \
            "SECURITY: CORS should use explicit method list, not wildcard"

        # Should include standard methods
        assert "GET" in allowed_methods.upper()
        assert "POST" in allowed_methods.upper()
        assert "PUT" in allowed_methods.upper() or "PATCH" in allowed_methods.upper()
