import logging
import json
from typing import Any, Dict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from ..middleware.logging import get_current_request_id

logger = logging.getLogger(__name__)

# ── Jinja2 template renderer (shared, path relative to this file) ─────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
_templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))

# ── Status code → (title, template) map ──────────────────────────────────────
_STATUS_META: Dict[int, tuple] = {
    400: ("Bad Request",           "errors/4xx.html"),
    401: ("Unauthorized",          "errors/4xx.html"),
    403: ("Access Denied",         "errors/4xx.html"),
    404: ("Page Not Found",        "errors/4xx.html"),
    409: ("Conflict",              "errors/4xx.html"),
    422: ("Invalid Request",       "errors/4xx.html"),
    429: ("Too Many Requests",     "errors/4xx.html"),
    500: ("Internal Server Error", "errors/5xx.html"),
    503: ("Service Unavailable",   "errors/5xx.html"),
}


def _wants_html(request: Request) -> bool:
    """Return True when the client prefers an HTML response (browser navigation)."""
    accept = request.headers.get("accept", "")
    return "text/html" in accept


class ProductionExceptionHandler:
    """
    Centralized exception handling for production deployment.

    Features:
    - Standardized error response format
    - Content-type negotiation: browser → HTML, API → JSON
    - Security-conscious error messages (no sensitive data exposure)
    - Comprehensive logging with request context
    """

    @staticmethod
    def create_error_response(
        status_code: int,
        error_code: str,
        message: str,
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """Create standardized JSON error response."""
        response_data = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id or get_current_request_id()
            }
        }
        if details:
            response_data["error"]["details"] = details

        return JSONResponse(
            status_code=status_code,
            content=response_data
        )

    @staticmethod
    def create_html_error_response(
        request: Request,
        status_code: int,
        message: str,
    ) -> HTMLResponse:
        """Render a user-friendly HTML error page."""
        request_id = get_current_request_id()
        title, template_name = _STATUS_META.get(
            status_code,
            ("Error", "errors/5xx.html" if status_code >= 500 else "errors/4xx.html"),
        )
        return _templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "status_code": status_code,
                "title": title,
                "message": message,
                "request_id": request_id,
            },
            status_code=status_code,
        )

    @staticmethod
    def respond(
        request: Request,
        status_code: int,
        error_code: str,
        message: str,
        details: Dict[str, Any] = None,
    ):
        """Return HTML or JSON depending on the client's Accept header."""
        if _wants_html(request):
            return ProductionExceptionHandler.create_html_error_response(
                request, status_code, message
            )
        return ProductionExceptionHandler.create_error_response(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details,
        )

    @staticmethod
    def log_exception(
        request: Request,
        exc: Exception,
        status_code: int,
        error_code: str,
        user_message: str
    ):
        """Log exception with full context."""
        request_id = get_current_request_id()

        error_log = {
            "event_type": "application_error",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error_code": error_code,
            "status_code": status_code,
            "user_message": user_message,
            "internal_message": str(exc),
            "url": str(request.url),
            "method": request.method,
            "client_ip": getattr(request.client, "host", "unknown") if request.client else "unknown"
        }

        if status_code >= 500:
            logger.error(json.dumps(error_log), exc_info=True)
        elif status_code >= 400:
            logger.warning(json.dumps(error_log))
        else:
            logger.info(json.dumps(error_log))


# ── Exception handlers ────────────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with content-type negotiation."""
    error_code = f"http_{exc.status_code}"

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=exc.status_code,
        error_code=error_code,
        user_message=exc.detail
    )

    # Browser 401 → redirect to /login?next=<original_url> instead of error page
    if exc.status_code == 401 and _wants_html(request):
        next_url = str(request.url.path)
        if request.url.query:
            next_url += f"?{request.url.query}"
        return RedirectResponse(url=f"/login?next={next_url}", status_code=302)

    return ProductionExceptionHandler.respond(
        request=request,
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail,
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions with content-type negotiation."""
    error_code = f"http_{exc.status_code}"

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=exc.status_code,
        error_code=error_code,
        user_message=exc.detail
    )

    # Browser 401 → redirect to /login?next=<original_url> instead of error page
    if exc.status_code == 401 and _wants_html(request):
        next_url = str(request.url.path)
        if request.url.query:
            next_url += f"?{request.url.query}"
        return RedirectResponse(url=f"/login?next={next_url}", status_code=302)

    return ProductionExceptionHandler.respond(
        request=request,
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors — JSON only (API contract)."""
    error_code = "validation_error"
    user_message = "Invalid request data"

    validation_details = []
    for error in exc.errors():
        validation_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=error_code,
        user_message=user_message
    )

    return ProductionExceptionHandler.create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=error_code,
        message=user_message,
        details={"validation_errors": validation_details}
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database-related exceptions with content-type negotiation."""
    if isinstance(exc, IntegrityError):
        error_code = "integrity_error"
        user_message = "Data integrity constraint violated"
        status_code = status.HTTP_409_CONFLICT
    else:
        error_code = "database_error"
        user_message = "A database error occurred. Please try again."
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status_code,
        error_code=error_code,
        user_message=user_message
    )

    return ProductionExceptionHandler.respond(
        request=request,
        status_code=status_code,
        error_code=error_code,
        message=user_message,
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors — JSON only (API contract)."""
    error_code = "pydantic_validation_error"
    user_message = "Data validation failed"

    validation_details = []
    for error in exc.errors():
        validation_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=error_code,
        user_message=user_message
    )

    return ProductionExceptionHandler.create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=error_code,
        message=user_message,
        details={"validation_errors": validation_details}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions with content-type negotiation."""
    error_code = "internal_server_error"
    user_message = "An unexpected error occurred. Please try again."

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        user_message=user_message
    )

    return ProductionExceptionHandler.respond(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        message=user_message,
    )


# ── Custom business logic exceptions ──────────────────────────────────────────

class BusinessLogicError(Exception):
    """Base exception for business logic errors."""
    def __init__(self, message: str, error_code: str = "business_logic_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class BookingError(BusinessLogicError):
    """Booking-related business logic errors."""
    def __init__(self, message: str):
        super().__init__(message, "booking_error")


class AuthenticationError(BusinessLogicError):
    """Authentication-related errors."""
    def __init__(self, message: str):
        super().__init__(message, "authentication_error")


class AuthorizationError(BusinessLogicError):
    """Authorization-related errors."""
    def __init__(self, message: str):
        super().__init__(message, "authorization_error")


async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    """Handle custom business logic exceptions — JSON only (programmatic callers)."""
    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=exc.error_code,
        user_message=exc.message
    )

    return ProductionExceptionHandler.create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=exc.error_code,
        message=exc.message
    )
