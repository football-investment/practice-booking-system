"""
Web routes for HTML template rendering
Refactored into modular components in web_routes/ directory

This file now serves as the main entry point that combines:
- Modular web routes (auth, dashboard, profile, etc.) from web_routes/
- Spec-based routes (LFA Player, Gancuju, Internship, Coach) from routes/
"""
from fastapi import APIRouter
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Import spec-based route modules
from .routes import lfa_player_routes, gancuju_routes, internship_routes, lfa_coach_routes

# Import refactored web routes
from .web_routes import router as web_router

# Setup templates (shared across all routes)
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Create main router
router = APIRouter(tags=["web"])

# Include refactored web routes (auth, dashboard, profile, etc.)
router.include_router(web_router)

# Include spec-based routes
router.include_router(lfa_player_routes.router)
router.include_router(gancuju_routes.router)
router.include_router(internship_routes.router)
router.include_router(lfa_coach_routes.router)
