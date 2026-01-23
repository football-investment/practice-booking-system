"""
CSRF Protection Middleware

Automatically generates and validates CSRF tokens for state-changing requests.

How it works:
1. On GET requests: Generate CSRF token, add to response cookie
2. On POST/PUT/PATCH/DELETE: Validate CSRF token from cookie + header
3. Skip validation for:
   - Safe methods (GET, HEAD, OPTIONS, TRACE)
   - API endpoints using Bearer token auth (already CSRF-safe)
   - Explicitly exempted paths

Security rationale:
- Bearer tokens in Authorization header require JavaScript
- JavaScript cross-origin requests require CORS preflight
- CORS allowlist blocks unauthorized origins
- Cookie-based auth (web routes) needs CSRF protection
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable, Set
import re

from ..core.csrf import (
    generate_csrf_token,
    validate_csrf_token,
    get_csrf_token_from_cookie,
    set_csrf_cookie
)
from ..config import settings


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically protect against CSRF attacks

    Features:
    - Auto-generates CSRF tokens for GET requests
    - Auto-validates CSRF tokens for state-changing requests
    - Skips validation for API endpoints with Bearer auth
    - Configurable exempt paths
    """

    # HTTP methods that are safe (read-only, no state changes)
    SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}

    # Paths that are exempt from CSRF protection
    # These typically use Bearer token auth (already CSRF-safe)
    EXEMPT_PATHS: Set[str] = {
        "/docs",  # Swagger UI
        "/redoc",  # ReDoc
        "/openapi.json",  # OpenAPI schema
        "/health",  # Health check
    }

    # Regex patterns for exempt paths (e.g., all /api/v1/* endpoints)
    EXEMPT_PATTERNS: list[re.Pattern] = [
        re.compile(r"^/api/v1/.*"),  # API endpoints use Bearer auth
    ]

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)

    def _is_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from CSRF protection

        Args:
            path: Request path

        Returns:
            bool: True if path is exempt, False otherwise
        """
        # Check exact matches
        if path in self.EXEMPT_PATHS:
            return True

        # Check pattern matches
        for pattern in self.EXEMPT_PATTERNS:
            if pattern.match(path):
                return True

        return False

    def _has_bearer_auth(self, request: Request) -> bool:
        """
        Check if request uses Bearer token authentication

        Bearer auth is CSRF-safe because:
        1. Requires JavaScript to set Authorization header
        2. JavaScript cross-origin requests trigger CORS preflight
        3. CORS allowlist blocks unauthorized origins

        Args:
            request: FastAPI Request object

        Returns:
            bool: True if request has valid Bearer token format
        """
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Bearer ")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through CSRF protection logic

        Flow:
        1. Skip if exempt path or safe method
        2. GET request: Generate token, add to response
        3. POST/PUT/PATCH/DELETE: Validate token
        4. If validation fails: Return 403
        5. If validation succeeds: Call next middleware

        Args:
            request: FastAPI Request object
            call_next: Next middleware in chain

        Returns:
            Response: Either error response or result from call_next
        """
        path = request.url.path
        method = request.method

        # Skip CSRF for exempt paths
        if self._is_exempt(path):
            return await call_next(request)

        # Skip CSRF for API requests with Bearer auth
        if self._has_bearer_auth(request):
            return await call_next(request)

        # Safe methods: Generate token for subsequent requests
        if method in self.SAFE_METHODS:
            # Get existing token or generate new one
            csrf_token = get_csrf_token_from_cookie(request)
            if not csrf_token:
                csrf_token = generate_csrf_token()

            # Process request
            response = await call_next(request)

            # Add token to response cookie
            if hasattr(response, 'set_cookie'):
                set_csrf_cookie(response, csrf_token, settings)

            return response

        # State-changing methods: Validate CSRF token
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Validate CSRF token (raises HTTPException on failure)
            try:
                validate_csrf_token(request, raise_exception=True)
            except Exception as e:
                # Return 403 Forbidden with error details
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": str(e),
                        "error_type": "CSRF_VALIDATION_FAILED",
                        "help": "Include X-CSRF-Token header matching csrf_token cookie"
                    }
                )

            # CSRF validation passed, continue to endpoint
            response = await call_next(request)

            # Refresh token in response (rotate after use)
            new_token = generate_csrf_token()
            if hasattr(response, 'set_cookie'):
                set_csrf_cookie(response, new_token, settings)

            return response

        # Other methods: Pass through
        return await call_next(request)


# Decorator for explicit CSRF exemption on specific endpoints
def csrf_exempt(func):
    """
    Decorator to mark endpoint as exempt from CSRF protection

    Usage:
        @router.post("/webhook")
        @csrf_exempt
        async def webhook_handler():
            # This endpoint skips CSRF validation
            pass

    Note:
        Use sparingly! Only for webhooks, public APIs, etc.
        Never use for authenticated user actions!
    """
    func._csrf_exempt = True
    return func
