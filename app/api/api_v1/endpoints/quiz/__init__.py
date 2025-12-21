"""
Quiz Management API
Modular route aggregator

Combines:
- student.py: Student quiz operations (6 routes)
  - GET /available: Get available quizzes
  - GET /category/{category}: Get quizzes by category
  - GET /{quiz_id}: Get quiz for taking
  - GET /attempts/my: Get my attempts
  - GET /statistics/my: Get my statistics
  - GET /dashboard/overview: Get dashboard overview
- attempts.py: Quiz attempt operations (2 routes)
  - POST /start: Start quiz attempt
  - POST /submit: Submit quiz attempt
- admin.py: Admin quiz management (5 routes)
  - POST /: Create quiz
  - GET /admin/{quiz_id}: Get quiz (admin view)
  - GET /admin/all: Get all quizzes
  - GET /statistics/{quiz_id}: Get quiz statistics
  - GET /leaderboard/{quiz_id}: Get leaderboard
"""
from fastapi import APIRouter

from . import student, attempts, admin

# Create main router
router = APIRouter()

# Include sub-routers
# Order matters: specific routes before path parameter routes
router.include_router(student.router)
router.include_router(attempts.router)
router.include_router(admin.router)
