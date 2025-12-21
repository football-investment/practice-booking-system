"""
Semester Enrollment Management API
Modular route aggregator

Combines:
- queries.py: Query enrollments by semester or student
- crud.py: Create, delete, toggle enrollments
- payment.py: Payment verification workflow
- workflow.py: Approval/rejection workflow
"""
from fastapi import APIRouter

from . import queries, crud, payment, workflow

# Create main router with tags
router = APIRouter(tags=["semester-enrollments"])

# Include all sub-routers
router.include_router(queries.router)
router.include_router(crud.router)
router.include_router(payment.router)
router.include_router(workflow.router)
