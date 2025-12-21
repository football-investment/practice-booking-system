"""
Booking Management API
Modular route aggregator

Combines:
- student.py: Student booking operations (5 routes)
- admin.py: Admin booking management (4 routes)
- helpers.py: Shared auto-promotion logic
"""
from fastapi import APIRouter

from . import student, admin

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(student.router)
router.include_router(admin.router)
