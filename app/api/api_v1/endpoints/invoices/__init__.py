"""Invoice management module"""
from fastapi import APIRouter
from . import requests, admin

router = APIRouter()
router.include_router(requests.router)
router.include_router(admin.router)
