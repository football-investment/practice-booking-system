"""
Session Management API Endpoints

Refactored into modular components in sessions/ directory

Modules:
- crud.py: CRUD operations (4 routes)
  - POST /: Create session with instructor authorization
  - GET /{session_id}: Get session by ID with statistics
  - PATCH /{session_id}: Update session with validation
  - DELETE /{session_id}: Delete session with relationship checks
- queries.py: Query operations (5 routes)
  - GET /: List sessions with complex filtering (241 lines!)
  - GET /recommendations: Personalized session recommendations
  - GET /{session_id}/bookings: Get session bookings
  - GET /instructor/my: Get instructor's sessions
  - GET /calendar: Calendar events for FullCalendar

Total: 9 routes, 697 lines → 29 lines (95.8% reduction)
"""
from fastapi import APIRouter
from .sessions import router as sessions_router

router = APIRouter()
router.include_router(sessions_router)
