"""Specialization system module"""
from fastapi import APIRouter
from . import user, info, progress, onboarding

router = APIRouter()
router.include_router(user.router)
router.include_router(info.router)
router.include_router(progress.router)
router.include_router(onboarding.router)
