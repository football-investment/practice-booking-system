"""
GānCuju™© (Player) specialization module.

This module aggregates all GānCuju player belt system endpoints:
- Licenses: Player license management
- Belts: Belt promotion and demotion
- Activities: Competition participation and teaching hours

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import licenses, belts, activities

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(licenses.router)
router.include_router(belts.router)
router.include_router(activities.router)
