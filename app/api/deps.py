"""
API Dependencies
Re-exports auth dependencies for API endpoints
"""
from app.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_current_admin_or_instructor_user
)

# Alias for backwards compatibility
require_admin = get_current_admin_user

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_current_admin_or_instructor_user",
    "require_admin"
]
