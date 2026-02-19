"""
Internship specialization module.

This module aggregates all internship-specific endpoints:
- Licenses: Internship license management
- XP & Renewal: XP tracking and license renewal
- Credits: Credit purchase and spending

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import licenses, xp_renewal, credits

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(licenses.router)
router.include_router(xp_renewal.router)
router.include_router(credits.router)
