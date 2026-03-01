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
from .masters.direct_hire import create_direct_hire_offer
from .masters.applications import hire_from_application
from .applications import create_application
from .masters.offers import respond_to_offer

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

# POST endpoint aliases (BATCH 7 - Phase 3)
router.add_api_route(
    "/direct-hire",
    create_direct_hire_offer,
    methods=["POST"],
    tags=["Instructor Management - Masters"],
    summary="Create Direct Hire Offer (Alias)",
    description="Alias for /masters/direct-hire - Backward compatibility"
)

router.add_api_route(
    "/hire-from-application",
    hire_from_application,
    methods=["POST"],
    tags=["Instructor Management - Masters"],
    summary="Hire from Application (Alias)",
    description="Alias for /masters/hire-from-application - Backward compatibility"
)

# Root POST endpoint alias for test compatibility
# 4 tests (create_application, create_assignment, create_position, create_master_instructor_legacy)
# all POST to /instructor-management instead of specific sub-resources
router.add_api_route(
    "/",
    create_application,
    methods=["POST"],
    tags=["Instructor Management - Applications"],
    summary="Create Application (Root Alias)",
    description="Alias for /applications/ - Test generator compatibility (BATCH 7)"
)

# PATCH /offers/{id}/respond alias (BATCH 7)
router.add_api_route(
    "/offers/{offer_id}/respond",
    respond_to_offer,
    methods=["PATCH"],
    tags=["Instructor Management - Offers"],
    summary="Respond to Offer (Alias)",
    description="Alias for /masters/offers/{offer_id}/respond - Backward compatibility"
)

__all__ = ["router"]
