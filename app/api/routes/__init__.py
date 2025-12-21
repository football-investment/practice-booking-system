"""
Spec-based route modules

Each specialization has its own route file with spec-specific endpoints:
- lfa_player_routes.py: Skills assessment routes (LFA Player)
- gancuju_routes.py: Belt progression routes (Gancuju)
- internship_routes.py: XP/level progression routes (Internship)
- lfa_coach_routes.py: Certification routes (LFA Coach)
"""

from fastapi import APIRouter
from . import lfa_player_routes, gancuju_routes, internship_routes, lfa_coach_routes

__all__ = [
    'lfa_player_routes',
    'gancuju_routes',
    'internship_routes',
    'lfa_coach_routes'
]
