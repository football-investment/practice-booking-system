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

# Combine all tournament routers
router = APIRouter()
router.include_router(lifecycle_router)  # New lifecycle endpoints (create, status, history)
router.include_router(generator_router)
router.include_router(available_router)
router.include_router(enroll_router)
router.include_router(instructor_router)
router.include_router(rewards_router)  # Rewards & ranking endpoints

__all__ = ["router"]
