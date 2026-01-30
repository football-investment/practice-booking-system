"""
Shared services package

Contains reusable service modules that eliminate code duplication across the codebase:
- auth_validator: Authorization decorators and checks
- license_validator: License validation logic
- notification_dispatcher: Notification creation
- status_history_recorder: Status change recording
"""

from .auth_validator import require_role, require_admin, get_current_user_or_403
from .license_validator import LicenseValidator

__all__ = [
    "require_role",
    "require_admin",
    "get_current_user_or_403",
    "LicenseValidator",
]
