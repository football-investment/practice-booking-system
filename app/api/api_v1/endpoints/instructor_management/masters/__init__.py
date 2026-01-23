"""
Master Instructor Management Router

Modular structure:
- direct_hire.py: Pathway A (Direct hire offers)
- applications.py: Pathway B (Hire from job applications)
- offers.py: Offer management (list, respond, cancel)
- legacy.py: Backward compatibility endpoints
- utils.py: Helper functions (age group validation)
"""

from fastapi import APIRouter

from .direct_hire import router as direct_hire_router
from .applications import router as applications_router
from .offers import router as offers_router
from .legacy import router as legacy_router

# Main router aggregation
router = APIRouter()

router.include_router(direct_hire_router, tags=["Master Hiring - Direct"])
router.include_router(applications_router, tags=["Master Hiring - Applications"])
router.include_router(offers_router, tags=["Master Hiring - Offers"])
router.include_router(legacy_router, tags=["Master Hiring - Legacy"])

__all__ = ['router']
