"""
Project management module.

This module aggregates all project-related endpoints:
- Core: Project CRUD operations
- Enrollment: Student enrollment and progress tracking
- Instructor: Instructor project management
- Quizzes: Project quiz system
- Milestones: Milestone submission and approval

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import core
from . import enrollment
from . import instructor
from . import quizzes
from . import milestones

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(core.router, tags=["projects"])
router.include_router(enrollment.router, tags=["projects"])
router.include_router(instructor.router, tags=["projects"])
router.include_router(quizzes.router, tags=["projects"])
router.include_router(milestones.router, tags=["projects"])
