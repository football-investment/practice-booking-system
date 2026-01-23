"""
Student project enrollment management (refactored into modular structure).

This package handles:
- Student enrollment/withdrawal
- Enrollment status tracking
- Progress monitoring
- Enrollment quiz completion
- Enrollment confirmation

Modules:
- enroll: Core enrollment operations (enroll, withdraw, current project)
- status: Status and progress tracking (summary, enrollment-status, progress)
- confirmation: Quiz completion and enrollment confirmation
"""
from fastapi import APIRouter

# Import routers from submodules
from .enroll import router as enroll_router
from .status import router as status_router
from .confirmation import router as confirmation_router

# Create main router and include all sub-routers
router = APIRouter()

# Include all sub-routers with tag for documentation
router.include_router(enroll_router, tags=["enrollment"])
router.include_router(status_router, tags=["enrollment"])
router.include_router(confirmation_router, tags=["enrollment"])

__all__ = ["router"]
