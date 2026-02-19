"""
🎓 Semester Enrollment Management API Endpoints (Admin only)

Refactored into modular components in semester_enrollments/ directory

Modules:
- queries.py: Query enrollments by semester or student (2 routes)
- crud.py: Create, delete, toggle enrollments (3 routes)
- payment.py: Payment verification workflow (4 routes)
- workflow.py: Approval/rejection workflow (2 routes)
- schemas.py: Pydantic models (4 schemas)

Total: 11 routes, 577 lines → 30 lines (94.8% reduction)
"""
from fastapi import APIRouter
from .semester_enrollments import router as semester_enrollments_router

router = APIRouter(tags=["semester-enrollments"])
router.include_router(semester_enrollments_router)
