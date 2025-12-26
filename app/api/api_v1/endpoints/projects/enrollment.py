"""
REDIRECT: This file has been refactored into modular structure

All endpoints are now available via enrollment/__init__.py

Original endpoints available in:
- enrollment/enroll.py - Enrollment operations (POST /enroll, DELETE /enroll, GET /my/current)
- enrollment/status.py - Status tracking (GET /my/summary, GET /enrollment-status, GET /progress)
- enrollment/confirmation.py - Quiz & confirmation (POST /enrollment-quiz, POST /confirm-enrollment)
"""
from app.api.api_v1.endpoints.projects.enrollment import router

__all__ = ["router"]
