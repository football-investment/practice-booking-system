"""
Coach specialization module.

This module aggregates all coach certification endpoints:
- Licenses: Coach license management
- Hours: Theory and practice hours tracking
- Progression: License renewal, promotion and statistics

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import licenses, hours, progression

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(licenses.router)
router.include_router(hours.router)
router.include_router(progression.router)
