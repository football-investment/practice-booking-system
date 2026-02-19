"""
Quiz Management API Endpoints

Refactored into modular components in quiz/ directory

Modules:
- student.py: Student quiz operations (6 routes)
  - GET /available, /category/{category}, /{quiz_id}
  - GET /attempts/my, /statistics/my, /dashboard/overview
- attempts.py: Quiz attempt operations (2 routes)
  - POST /start: Start quiz attempt (complex validation)
  - POST /submit: Submit quiz attempt (scoring + XP)
- admin.py: Admin quiz management (5 routes)
  - POST /: Create quiz
  - GET /admin/{quiz_id}, /admin/all
  - GET /statistics/{quiz_id}, /leaderboard/{quiz_id}
- helpers.py: Quiz service dependency injection

Total: 13 routes, 693 lines → 28 lines (96.0% reduction)
"""
from fastapi import APIRouter
from .quiz import router as quiz_router

router = APIRouter()
router.include_router(quiz_router)
