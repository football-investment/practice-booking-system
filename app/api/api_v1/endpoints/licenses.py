"""
🏮 GānCuju™️©️ License API Endpoints
Marketing-oriented license progression system API

Refactored into modular components in licenses/ directory

Modules:
- metadata.py: License metadata (3 routes)
  - GET /metadata, /metadata/{specialization}, /metadata/{specialization}/{level}
- student.py: User license operations (7 routes)
  - GET /progression/{specialization}, /my-licenses, /me, /dashboard
  - POST /advance
  - GET /requirements/{specialization}/{level}, /marketing/{specialization}
- instructor.py: Instructor license operations (4 routes)
  - POST /instructor/advance
  - GET /instructor/users/{user_id}/licenses, /instructor/dashboard/{user_id}
  - GET /instructor/{instructor_id}/teachable-specializations
- admin.py: Admin license sync (4 routes)
  - GET /admin/sync/desync-issues
  - POST /admin/sync/user/{user_id}, /admin/sync/user/{user_id}/all, /admin/sync/all
- payment.py: Payment verification (2 routes)
  - POST /{license_id}/verify-payment, /{license_id}/unverify-payment
- skills.py: Football skills assessment (3 routes)
  - GET /{license_id}/football-skills, /user/{user_id}/football-skills
  - PUT /{license_id}/football-skills

Total: 23 routes, 872 lines → 35 lines (96.0% reduction)
"""
from fastapi import APIRouter
from .licenses import router as licenses_router

router = APIRouter()
router.include_router(licenses_router)
