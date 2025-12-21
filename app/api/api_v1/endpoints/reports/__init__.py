"""
Report generation module.

This module aggregates all report-related endpoints:
- Standard: List reports, custom reports, history
- Entity: Semester and user-specific reports
- Export: Data export and system statistics

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import standard, entity, export

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(standard.router)
router.include_router(entity.router)
router.include_router(export.router)
