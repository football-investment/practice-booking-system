"""
Curriculum management module.

This module aggregates all curriculum-related endpoints:
- Tracks: Specialization tracks and progress
- Lessons: Lesson content and structure
- Modules: Module viewing and completion
- Exercises: Exercise submission and grading

All endpoints are accessible via the main router exported from this module.
"""
from fastapi import APIRouter

from . import tracks, lessons, modules, exercises

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(tracks.router)
router.include_router(lessons.router)
router.include_router(modules.router)
router.include_router(exercises.router)
