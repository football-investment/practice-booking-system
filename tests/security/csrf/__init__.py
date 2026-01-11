"""
Phase 3: CSRF (Cross-Site Request Forgery) Security Tests

Test Suite Coverage:
1. CORS configuration validation
2. CSRF token generation and validation
3. Cookie security attributes (SameSite, Secure, HttpOnly)
4. Critical endpoint protection (18+ endpoints)
5. Double Submit Cookie pattern verification
6. Middleware exemption paths
7. Token rotation and expiry

Security Properties Tested:
- CORS allowlist enforcement (no wildcard origins)
- CSRF token required for state-changing methods
- SameSite=strict prevents cross-origin cookie sending
- Secure flag enforces HTTPS in production
- Constant-time token comparison (timing attack prevention)
"""

__all__ = [
    "TestCORSConfiguration",
    "TestCSRFTokens",
    "TestCookieSecurity",
    "TestCriticalEndpoints",
]
