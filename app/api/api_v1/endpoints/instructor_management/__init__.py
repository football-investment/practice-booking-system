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

# Import specific endpoints for path aliases
from .assignments import update_assignment
from .masters.legacy import update_master_instructor
from .positions import update_position

# Main router for instructor management
router = APIRouter()

# Include sub-routers with resource prefixes
router.include_router(masters_router, prefix="/masters", tags=["Instructor Management - Masters"])
router.include_router(positions_router, prefix="/positions", tags=["Instructor Management - Positions"])
router.include_router(applications_router, prefix="/applications", tags=["Instructor Management - Applications"])
router.include_router(assignments_router, prefix="/assignments", tags=["Instructor Management - Assignments"])

# ── Path Aliases (Backward Compatibility) ──────────────────────────────────
# These aliases enable tests to call /instructor-management/{id} instead of
# /instructor-management/resource/{id} for PATCH endpoints
# Fixes test routing mismatches (BATCH 5 - Phase 3)

router.add_api_route(
    "/{assignment_id}",
    update_assignment,
    methods=["PATCH"],
    tags=["Instructor Management - Assignments"],
    summary="Update Assignment (Alias)",
    description="Alias for /assignments/{assignment_id} - Backward compatibility"
)

router.add_api_route(
    "/{master_id}",
    update_master_instructor,
    methods=["PATCH"],
    tags=["Instructor Management - Masters"],
    summary="Update Master Instructor (Alias)",
    description="Alias for /masters/{master_id} - Backward compatibility"
)

router.add_api_route(
    "/{position_id}",
    update_position,
    methods=["PATCH"],
    tags=["Instructor Management - Positions"],
    summary="Update Position (Alias)",
    description="Alias for /positions/{position_id} - Backward compatibility"
)

__all__ = ["router"]
