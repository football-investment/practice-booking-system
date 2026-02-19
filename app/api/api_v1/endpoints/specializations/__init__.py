"""Specialization system module"""
from fastapi import APIRouter
from . import user, info, progress

router = APIRouter()
router.include_router(user.router)
router.include_router(info.router)
router.include_router(progress.router)
