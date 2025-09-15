import logging
import time
import json
from typing import Callable
from uuid import uuid4
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware for production monitoring.
    
    Features:
    - Request/Response logging with performance metrics
    - Unique request ID tracking
    - Error logging with stack traces
    - Security event logging
    - JSON structured logs for easy parsing
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid4())
        request_id_var.set(request_id)
        
        # Extract request details
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        url = str(request.url)
        
        # Log incoming request
        request_log = {
            "event_type": "request_start",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "url": url,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "headers": dict(request.headers) if logger.level <= logging.DEBUG else {}
        }
        
        logger.info(json.dumps(request_log))
        
        # Process request and capture response
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response details
            response_log = {
                "event_type": "request_complete",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "client_ip": client_ip,
                "response_size": self._get_response_size(response)
            }
            
            # Log level based on status code
            if response.status_code >= 500:
                logger.error(json.dumps(response_log))
            elif response.status_code >= 400:
                logger.warning(json.dumps(response_log))
            else:
                logger.info(json.dumps(response_log))
            
            # Add performance warning for slow requests
            if process_time > 2.0:  # 2 second threshold
                performance_log = {
                    "event_type": "performance_warning",
                    "request_id": request_id,
                    "message": "Slow request detected",
                    "process_time_ms": round(process_time * 1000, 2),
                    "threshold_ms": 2000,
                    "url": url,
                    "method": method
                }
                logger.warning(json.dumps(performance_log))
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log unhandled exceptions
            process_time = time.time() - start_time
            error_log = {
                "event_type": "request_error",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "url": url,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "process_time_ms": round(process_time * 1000, 2),
                "client_ip": client_ip
            }
            logger.error(json.dumps(error_log), exc_info=True)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies."""
        # Check for forwarded headers (for reverse proxy setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return getattr(request.client, "host", "unknown")
    
    def _get_response_size(self, response: Response) -> int:
        """Estimate response size in bytes."""
        try:
            if isinstance(response, StreamingResponse):
                return 0  # Cannot determine streaming response size
            
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # For small responses, estimate from body
            if hasattr(response, 'body') and response.body:
                return len(response.body)
                
        except Exception:
            pass
        
        return 0


class SecurityLogger:
    """Security-focused logging utilities."""
    
    @staticmethod
    def log_auth_attempt(request_id: str, email: str, success: bool, client_ip: str):
        """Log authentication attempts."""
        auth_log = {
            "event_type": "auth_attempt",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "email": email,
            "success": success,
            "client_ip": client_ip
        }
        
        if success:
            logger.info(json.dumps(auth_log))
        else:
            logger.warning(json.dumps(auth_log))
    
    @staticmethod
    def log_permission_denied(request_id: str, user_id: int, resource: str, action: str):
        """Log permission denied events."""
        security_log = {
            "event_type": "permission_denied",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action
        }
        logger.warning(json.dumps(security_log))
    
    @staticmethod
    def log_suspicious_activity(request_id: str, client_ip: str, activity: str, details: dict):
        """Log suspicious activities."""
        suspicious_log = {
            "event_type": "suspicious_activity",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "activity": activity,
            "details": details
        }
        logger.error(json.dumps(suspicious_log))


def get_current_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get()


def log_business_event(event_name: str, user_id: int = None, data: dict = None):
    """Log business events for analytics."""
    business_log = {
        "event_type": "business_event",
        "request_id": get_current_request_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        "user_id": user_id,
        "data": data or {}
    }
    logger.info(json.dumps(business_log))