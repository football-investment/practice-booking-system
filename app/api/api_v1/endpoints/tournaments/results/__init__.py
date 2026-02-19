"""
Tournament Match Results Endpoints

Modular match results management refactored from match_results.py (1,251 lines).

This module handles:
- Result submission (structured, legacy, round-based)
- Round management (status queries)
- Finalization (group stage, tournament, individual sessions)

Endpoints are organized by responsibility:
- submission.py: 3 endpoints for result submission
- round_management.py: 1 endpoint for round status
- finalization.py: 3 endpoints for finalization

Service layer (app/services/tournament/results/):
- calculators: Standings, rankings, advancement
- finalization: Group stage, session, tournament
- validators: Result validation

Created as part of P2 decomposition (2026-01-30)
"""

from fastapi import APIRouter
from .submission import router as submission_router
from .round_management import router as round_router
from .finalization import router as finalization_router

# Combine all routers
router = APIRouter()
router.include_router(submission_router, tags=["match-results"])
router.include_router(round_router, tags=["match-results"])
router.include_router(finalization_router, tags=["match-results"])

__all__ = ["router"]
