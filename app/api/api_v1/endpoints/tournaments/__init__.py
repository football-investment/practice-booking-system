"""
Tournament endpoints
"""
from fastapi import APIRouter
from .generator import router as generator_router
from .available import router as available_router
from .enroll import router as enroll_router
from .instructor import router as instructor_router
from .lifecycle import router as lifecycle_router
from .rewards import router as rewards_router
from .match_results import router as match_results_router  # ✅ P0-1 Phase 1: Match results extraction
from .instructor_assignment import router as instructor_assignment_router  # ✅ P0-1 Phase 3: Instructor assignment lifecycle
from .cancellation import router as cancellation_router  # ✅ Feature: Tournament cancellation & refund

# Combine all tournament routers
router = APIRouter()
router.include_router(lifecycle_router)  # New lifecycle endpoints (create, status, history)
router.include_router(generator_router)
router.include_router(available_router)
router.include_router(enroll_router)
router.include_router(instructor_router)  # Thin router (queries, debug)
router.include_router(instructor_assignment_router)  # ✅ P0-1 Phase 3: Assignment lifecycle (apply, approve, accept, decline)
router.include_router(match_results_router)  # ✅ P0-1 Phase 1: Match results (submit, finalize)
router.include_router(cancellation_router)  # ✅ Feature: Tournament cancellation & refund
router.include_router(rewards_router)  # Rewards & ranking endpoints

__all__ = ["router"]
