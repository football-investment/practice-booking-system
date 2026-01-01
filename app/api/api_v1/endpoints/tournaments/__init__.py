"""
Tournament endpoints
"""
from fastapi import APIRouter
from .generator import router as generator_router
from .available import router as available_router
from .enroll import router as enroll_router

# Combine all tournament routers
router = APIRouter()
router.include_router(generator_router)
router.include_router(available_router)
router.include_router(enroll_router)

__all__ = ["router"]
