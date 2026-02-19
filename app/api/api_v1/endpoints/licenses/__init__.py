"""
License Management API
Modular route aggregator

Combines:
- metadata.py: License metadata (3 routes)
- student.py: User license operations (7 routes)
- instructor.py: Instructor license operations (4 routes)
- admin.py: Admin license sync (4 routes)
- payment.py: Payment verification (2 routes)
- skills.py: Football skills assessment (3 routes)
"""
from fastapi import APIRouter

from . import metadata, student, instructor, admin, payment, skills

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(metadata.router)
router.include_router(student.router)
router.include_router(instructor.router)
router.include_router(admin.router)
router.include_router(payment.router)
router.include_router(skills.router)
