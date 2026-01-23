"""
CSRF (Cross-Site Request Forgery) Protection

Implementation: Double Submit Cookie Pattern
- Generate random CSRF token
- Send token in both cookie AND custom header
- Validate that cookie matches header on state-changing requests

Security properties:
- Attacker cannot read cookie from different origin (Same-Origin Policy)
- Attacker cannot set custom headers from simple HTML forms
- CORS preflight required for custom headers (blocked by CORS allowlist)
"""

import secrets
from fastapi import Request, HTTPException, status
from typing import Optional


def generate_csrf_token() -> str:
    """
    Generate cryptographically secure random CSRF token

    Returns:
        str: 32-byte (64-character) hex token

    Example:
        >>> token = generate_csrf_token()
        >>> len(token)
        64
    """
    return secrets.token_hex(32)


def get_csrf_token_from_cookie(request: Request) -> Optional[str]:
    """
    Extract CSRF token from cookie

    Args:
        request: FastAPI Request object

    Returns:
        Optional[str]: CSRF token if present in cookie, None otherwise
    """
    return request.cookies.get("csrf_token")


def get_csrf_token_from_header(request: Request) -> Optional[str]:
    """
    Extract CSRF token from custom header

    Looks for token in:
    1. X-CSRF-Token (standard)
    2. X-CSRFToken (alternative)

    Args:
        request: FastAPI Request object

    Returns:
        Optional[str]: CSRF token if present in header, None otherwise
    """
    return (
        request.headers.get("X-CSRF-Token") or
        request.headers.get("X-CSRFToken")
    )


def validate_csrf_token(request: Request, raise_exception: bool = True) -> bool:
    """
    Validate CSRF token using Double Submit Cookie pattern

    Validation steps:
    1. Extract token from cookie
    2. Extract token from header
    3. Check both tokens exist
    4. Check tokens match (constant-time comparison)

    Args:
        request: FastAPI Request object
        raise_exception: If True, raise HTTPException on validation failure

    Returns:
        bool: True if valid, False if invalid (when raise_exception=False)

    Raises:
        HTTPException: 403 Forbidden if validation fails and raise_exception=True

    Security Notes:
        - Uses secrets.compare_digest() for constant-time comparison
        - Prevents timing attacks that could leak token information
    """
    csrf_cookie = get_csrf_token_from_cookie(request)
    csrf_header = get_csrf_token_from_header(request)

    # Check both tokens exist
    if not csrf_cookie or not csrf_header:
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing. Include X-CSRF-Token header matching csrf_token cookie."
            )
        return False

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(csrf_cookie, csrf_header):
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed. Token mismatch between cookie and header."
            )
        return False

    return True


def set_csrf_cookie(response, token: str, settings) -> None:
    """
    Set CSRF token in response cookie

    Args:
        response: FastAPI Response object
        token: CSRF token to set
        settings: Application settings (for cookie security config)

    Cookie attributes:
        - httponly: False (JavaScript must read this to send in header)
        - secure: True in production (HTTPS only)
        - samesite: "strict" (prevents CSRF - cookie not sent cross-origin)
        - max_age: Same as access token (1 hour)

    Security Note:
        HttpOnly is FALSE (unlike auth cookies) because client-side JavaScript
        must read this token to include it in the X-CSRF-Token header.
        This is safe because:
        1. CSRF protection doesn't rely on secrecy
        2. Attacker on different origin cannot read cookie (Same-Origin Policy)
        3. Token must match cookie AND header (attacker can do neither)
    """
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # ⚠️ Must be False - JavaScript needs to read this
        secure=settings.COOKIE_SECURE,  # HTTPS only in production
        samesite=settings.COOKIE_SAMESITE,  # "strict" prevents cross-origin
        max_age=settings.COOKIE_MAX_AGE,  # 1 hour
        path="/"
    )


# Helper function for use in dependencies
async def require_csrf(request: Request) -> None:
    """
    FastAPI dependency that enforces CSRF protection

    Usage:
        @router.post("/critical-endpoint", dependencies=[Depends(require_csrf)])
        async def critical_operation(...):
            # CSRF validated before reaching here
            pass

    Raises:
        HTTPException: 403 if CSRF validation fails
    """
    validate_csrf_token(request, raise_exception=True)
