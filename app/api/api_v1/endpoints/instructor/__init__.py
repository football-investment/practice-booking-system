"""
Instructor API Endpoints
========================

Instructor-specific endpoints for student assessment and management.
"""
from fastapi import APIRouter

from . import student_assessment

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(student_assessment.router)  # /instructor/students/{id}/skills/... endpoints
