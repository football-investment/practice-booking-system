"""
Web routes module aggregator
Combines all modular web route files into a single router
"""
from fastapi import APIRouter

from . import (
    auth,
    onboarding,
    profile,
    student_features,
    dashboard,
    specialization,
    sessions,
    attendance,
    quiz,
    instructor,
    instructor_dashboard,
    admin
)

# Create main router with tags
router = APIRouter(tags=["web"])

# Include all sub-routers
router.include_router(auth.router)
router.include_router(onboarding.router)
router.include_router(profile.router)
router.include_router(student_features.router)
router.include_router(dashboard.router)
router.include_router(specialization.router)
router.include_router(sessions.router)
router.include_router(attendance.router)
router.include_router(quiz.router)
router.include_router(instructor.router)
router.include_router(instructor_dashboard.router)
router.include_router(admin.router)
