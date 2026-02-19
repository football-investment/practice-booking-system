"""
Shared services package

Contains reusable service modules that eliminate code duplication across the codebase:
- auth_validator: Authorization decorators and checks
- license_validator: License validation logic
- status_history_recorder: Status change recording
"""

from .auth_validator import require_role, require_admin, require_instructor, require_admin_or_instructor, get_current_user_or_403
from .license_validator import LicenseValidator
from .status_history_recorder import StatusHistoryRecorder

__all__ = [
    "require_role",
    "require_admin",
    "require_instructor",
    "require_admin_or_instructor",
    "get_current_user_or_403",
    "LicenseValidator",
    "StatusHistoryRecorder",
]
