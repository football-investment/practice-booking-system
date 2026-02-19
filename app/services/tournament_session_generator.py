"""
Tournament Session Generator Service - Backward Compatibility Facade

This module maintains backward compatibility by importing from the new modular structure.

NEW LOCATION: app.services.tournament.session_generation.TournamentSessionGenerator

The original monolithic implementation (1,294 lines) has been decomposed into:
- session_generator.py (coordinator)
- validators/ (validation logic)
- formats/ (format-specific generators)
- algorithms/ (pairing and distribution algorithms)
- builders/ (session metadata builders)

Usage remains the same:
    from app.services.tournament_session_generator import TournamentSessionGenerator

    generator = TournamentSessionGenerator(db)
    success, message, sessions = generator.generate_sessions(tournament_id)

CRITICAL CONSTRAINT: This service is ONLY called after the enrollment period ends,
ensuring stable player count and preventing mid-tournament enrollment changes.
"""

# Import from new location
from app.services.tournament.session_generation import TournamentSessionGenerator

# Re-export for backward compatibility
__all__ = ["TournamentSessionGenerator"]
