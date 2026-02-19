"""
REDIRECT: This file has been refactored into modular structure

Original file (917 lines) split into 6 modules:
- masters/__init__.py       - Router aggregation
- masters/direct_hire.py    - Pathway A: Direct hire offers
- masters/offers.py         - Offer management (list, respond, cancel)
- masters/applications.py   - Pathway B: Hire from job applications
- masters/legacy.py         - Backward compatibility endpoints
- masters/utils.py          - Helper functions (age group validation)

All imports from this file redirect to masters/__init__.py
No breaking changes - all endpoints work unchanged.
"""

from app.api.api_v1.endpoints.instructor_management.masters import router

__all__ = ['router']
