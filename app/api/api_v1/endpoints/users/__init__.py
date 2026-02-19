"""
User endpoints module
Aggregates all user-related routers into a single router
"""
from fastapi import APIRouter

from . import crud, profile, search, credits, instructor_analytics

# Create main router
router = APIRouter()

# Include all sub-routers
# Order matters: more specific routes should come before general ones

# Profile endpoints (must come before /{user_id} to avoid path conflicts)
router.include_router(profile.router, tags=["users"])

# Instructor analytics endpoints (must come before /{user_id})
router.include_router(instructor_analytics.router, tags=["users"])

# Search endpoints
router.include_router(search.router, tags=["users"])

# Credits endpoints
router.include_router(credits.router, tags=["users"])

# CRUD endpoints (should be last due to /{user_id} catch-all)
router.include_router(crud.router, tags=["users"])

# Export router
__all__ = ["router"]
