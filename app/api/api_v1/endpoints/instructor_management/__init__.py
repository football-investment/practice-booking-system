"""
Instructor Management API Endpoints

Two-tier instructor system:
- Master instructors (location-level)
- Assistant instructors (spec/age/period-level)
"""

from fastapi import APIRouter
from .masters import router as masters_router
from .positions import router as positions_router
from .applications import router as applications_router
from .assignments import router as assignments_router

# Main router for instructor management
router = APIRouter()

# Include sub-routers
router.include_router(masters_router, prefix="/masters", tags=["Instructor Management - Masters"])
router.include_router(positions_router, prefix="/positions", tags=["Instructor Management - Positions"])
router.include_router(applications_router, prefix="/applications", tags=["Instructor Management - Applications"])
router.include_router(assignments_router, prefix="/assignments", tags=["Instructor Management - Assignments"])

__all__ = ["router"]
