"""
Instructor assignment system module.

- Availability: Instructor availability windows
- Requests: Assignment request workflow
- Discovery: Find available instructors
"""
from fastapi import APIRouter
from . import availability, requests, discovery

router = APIRouter()
router.include_router(availability.router)
router.include_router(requests.router)
router.include_router(discovery.router)
