"""LFA Player specialization module"""
from fastapi import APIRouter
from . import licenses, skills, credits

router = APIRouter()
router.include_router(licenses.router)
router.include_router(skills.router)
router.include_router(credits.router)
