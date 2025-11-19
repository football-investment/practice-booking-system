"""
Audit Middleware

Automatically logs all important API requests to the audit log.
"""
import time
from jose import jwt
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import settings
from ..database import SessionLocal
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log API requests to audit log.

    Logs:
    - All POST, PUT, PATCH, DELETE requests
    - Sensitive GET requests (admin, user data, licenses)
    - Failed requests (4xx, 5xx status codes)
    """

    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()

        # Extract user ID from JWT token (if present)
        user_id = self._extract_user_id(request)

        # Process request
        response = await call_next(request)

        # Calculate process time
        process_time = time.time() - start_time

        # Determine if we should audit this request
        if self._should_audit(request, response):
            # Log to audit (async to not block response)
            try:
                self._log_request(request, response, user_id)
            except Exception as e:
                # Don't let audit logging failures break the app
                print(f"Audit logging error: {e}")

        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _extract_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from JWT token"""
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"]
                )
                # Extract user email/identifier from token
                user_email = payload.get("sub")
                # We'll need to look up user_id from email in the database
                # For now, return None and handle user_id lookup in _log_request
                return user_email
        except Exception:
            pass
        return None

    def _should_audit(self, request: Request, response: Response) -> bool:
        """Determine if request should be audited"""
        method = request.method
        path = str(request.url.path)
        status_code = response.status_code

        # Skip paths that have explicit audit logging in endpoints
        # (to avoid duplicate audit logs)
        skip_paths = [
            "/auth/login",  # Explicitly logged in auth.py with user_id
            "/auth/logout",  # Can be explicitly logged in auth.py
        ]
        if any(skip in path for skip in skip_paths):
            return False

        # Skip health checks and static files
        if path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return False

        # Skip OPTIONS requests
        if method == "OPTIONS":
            return False

        # Always audit write operations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return True

        # Audit failed requests
        if status_code >= 400:
            return True

        # Audit sensitive GET endpoints
        sensitive_paths = [
            "/users",
            "/admin",
            "/licenses",
            "/certificates",
            "/audit",
            "/reports"
        ]
        if any(sensitive in path for sensitive in sensitive_paths):
            return True

        return False

    def _log_request(
        self,
        request: Request,
        response: Response,
        user_identifier: Optional[str]
    ):
        """Log request to audit table"""
        db = SessionLocal()
        try:
            audit_service = AuditService(db)

            # Determine action from request
            action = self._determine_action(request, response)

            # Extract resource info from path
            resource_type, resource_id = self._extract_resource_info(request.url.path)

            # Look up user_id from email if we have an identifier
            user_id = None
            if user_identifier:
                from ..models.user import User
                user = db.query(User).filter(User.email == user_identifier).first()
                if user:
                    user_id = user.id

            # Log the request
            audit_service.log(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_method=request.method,
                request_path=str(request.url.path),
                status_code=response.status_code
            )
        finally:
            db.close()

    def _determine_action(self, request: Request, response: Response) -> str:
        """Determine audit action from request"""
        method = request.method
        path = str(request.url.path)

        # Authentication
        if "/auth/login" in path:
            if response.status_code == 200:
                return AuditAction.LOGIN
            else:
                return AuditAction.LOGIN_FAILED
        if "/auth/logout" in path:
            return AuditAction.LOGOUT

        # Specializations
        if "/specializations" in path and method in ["POST", "PUT", "PATCH"]:
            return AuditAction.SPECIALIZATION_SELECTED

        # Licenses
        if "/licenses" in path:
            if "pdf" in path or "download" in path:
                return AuditAction.LICENSE_DOWNLOADED
            elif "verify" in path:
                return AuditAction.LICENSE_VERIFIED
            elif "upgrade" in path:
                if "approve" in path:
                    return AuditAction.LICENSE_UPGRADE_APPROVED
                elif "reject" in path:
                    return AuditAction.LICENSE_UPGRADE_REJECTED
                else:
                    return AuditAction.LICENSE_UPGRADE_REQUESTED
            elif method == "POST":
                return AuditAction.LICENSE_ISSUED
            elif method == "GET":
                return AuditAction.LICENSE_VIEWED
            elif method == "DELETE":
                return AuditAction.LICENSE_REVOKED

        # Projects
        if "/projects" in path:
            if "enroll" in path:
                if method == "POST":
                    return AuditAction.PROJECT_ENROLLED
                elif method == "DELETE":
                    return AuditAction.PROJECT_UNENROLLED
            elif method == "POST":
                return AuditAction.PROJECT_CREATED
            elif method in ["PUT", "PATCH"]:
                return AuditAction.PROJECT_UPDATED
            elif method == "DELETE":
                return AuditAction.PROJECT_DELETED

        # Quizzes
        if "/quiz" in path:
            if "/start" in path:
                return AuditAction.QUIZ_STARTED
            elif "/submit" in path:
                return AuditAction.QUIZ_SUBMITTED
            elif method == "POST":
                return AuditAction.QUIZ_CREATED
            elif method in ["PUT", "PATCH"]:
                return AuditAction.QUIZ_UPDATED
            elif method == "DELETE":
                return AuditAction.QUIZ_DELETED

        # Certificates
        if "/certificates" in path:
            if "pdf" in path or "download" in path:
                return AuditAction.CERTIFICATE_DOWNLOADED
            elif method == "POST":
                return AuditAction.CERTIFICATE_ISSUED
            elif method == "GET":
                return AuditAction.CERTIFICATE_VIEWED

        # Generic fallback
        return f"{method}_{path}"

    def _extract_resource_info(self, path: str) -> tuple[Optional[str], Optional[int]]:
        """Extract resource type and ID from path"""
        # Simple extraction - matches /resource_type/{id}
        parts = path.strip("/").split("/")

        # Find numeric ID in path
        resource_id = None
        resource_type = None

        for i, part in enumerate(parts):
            if part.isdigit():
                resource_id = int(part)
                # Resource type is usually the segment before the ID
                if i > 0:
                    resource_type = parts[i - 1].rstrip("s")  # Remove plural 's'
                break

        return resource_type, resource_id
