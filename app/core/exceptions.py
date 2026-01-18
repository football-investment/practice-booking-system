import logging
import json
from typing import Any, Dict
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from ..middleware.logging import get_current_request_id

logger = logging.getLogger(__name__)


class ProductionExceptionHandler:
    """
    Centralized exception handling for production deployment.
    
    Features:
    - Standardized error response format
    - Security-conscious error messages (no sensitive data exposure)
    - Comprehensive logging with request context
    - Different handling for development vs production
    """
    
    @staticmethod
    def create_error_response(
        status_code: int,
        error_code: str,
        message: str,
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """Create standardized error response."""
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
        
        # Log at appropriate level
        if status_code >= 500:
            logger.error(json.dumps(error_log), exc_info=True)
        elif status_code >= 400:
            logger.warning(json.dumps(error_log))
        else:
            logger.info(json.dumps(error_log))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    error_code = f"http_{exc.status_code}"
    
    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=exc.status_code,
        error_code=error_code,
        user_message=exc.detail
    )
    
    return ProductionExceptionHandler.create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions."""
    error_code = f"http_{exc.status_code}"
    
    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=exc.status_code,
        error_code=error_code,
        user_message=exc.detail
    )
    
    return ProductionExceptionHandler.create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    error_code = "validation_error"
    user_message = "Invalid request data"
    
    # Extract validation details (but sanitize for security)
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


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database-related exceptions."""
    error_code = "database_error"

    # Determine specific error type and user-friendly message
    if isinstance(exc, IntegrityError):
        error_code = "integrity_error"
        user_message = "Data integrity constraint violated"
        status_code = status.HTTP_409_CONFLICT
    else:
        user_message = "Database operation failed"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status_code,
        error_code=error_code,
        user_message=user_message
    )

    return ProductionExceptionHandler.create_error_response(
        status_code=status_code,
        error_code=error_code,
        message=user_message
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
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


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    error_code = "internal_server_error"
    user_message = "An unexpected error occurred"
    
    ProductionExceptionHandler.log_exception(
        request=request,
        exc=exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        user_message=user_message
    )
    
    return ProductionExceptionHandler.create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        message=user_message
    )


# Custom business logic exceptions
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


async def business_logic_exception_handler(request: Request, exc: BusinessLogicError) -> JSONResponse:
    """Handle custom business logic exceptions."""
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