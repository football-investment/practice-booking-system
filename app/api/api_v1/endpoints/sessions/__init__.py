"""
Session Management API
Modular route aggregator

Combines:
- crud.py: CRUD operations (4 routes)
  - POST /: Create session
  - GET /{session_id}: Get session by ID
  - PATCH /{session_id}: Update session
  - DELETE /{session_id}: Delete session
- queries.py: Query operations (5 routes)
  - GET /: List sessions with complex filtering
  - GET /recommendations: Session recommendations
  - GET /{session_id}/bookings: Get session bookings
  - GET /instructor/my: Get instructor's sessions
  - GET /calendar: Calendar events
"""
from fastapi import APIRouter

from . import crud, queries, checkin

# Create main router
router = APIRouter()

# Include sub-routers
# IMPORTANT: Order matters! CRUD routes with path parameters must come after specific routes
router.include_router(queries.router)  # Includes /recommendations, /instructor/my, /calendar first
router.include_router(checkin.router)  # Includes /{session_id}/check-in (instructor check-in)
router.include_router(crud.router)     # Then includes /{session_id} routes
