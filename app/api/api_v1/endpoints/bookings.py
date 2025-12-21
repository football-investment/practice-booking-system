"""
Booking Management API Endpoints

Refactored into modular components in bookings/ directory

Modules:
- student.py: Student booking operations (5 routes)
  - POST /: Create booking
  - GET /me: Get my bookings
  - GET /{booking_id}: Get specific booking
  - DELETE /{booking_id}: Cancel booking
  - GET /my-stats: Get booking statistics
- admin.py: Admin booking management (4 routes)
  - GET /: Get all bookings (admin)
  - POST /{booking_id}/confirm: Confirm booking
  - POST /{booking_id}/cancel: Admin cancel booking
  - PATCH /{booking_id}/attendance: Update attendance
- helpers.py: Auto-promotion logic (DRY principle)

Total: 9 routes (1 duplicate removed), 727 lines → 22 lines (97.0% reduction)
"""
from fastapi import APIRouter
from .bookings import router as bookings_router

router = APIRouter()
router.include_router(bookings_router)
