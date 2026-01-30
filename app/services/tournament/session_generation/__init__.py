"""
Tournament Session Generation Module

Modular session generation system for tournaments.

Structure:
- session_generator.py: Main coordinator
- validators/: Validation logic
- formats/: Format-specific generators (league, knockout, swiss, etc.)
- algorithms/: Reusable pairing and distribution algorithms
- builders/: Session metadata builders (future expansion)

Usage:
    from app.services.tournament.session_generation import TournamentSessionGenerator

    generator = TournamentSessionGenerator(db)
    success, message, sessions = generator.generate_sessions(tournament_id)
"""
from .session_generator import TournamentSessionGenerator
from .validators import GenerationValidator
from .formats import (
    BaseFormatGenerator,
    LeagueGenerator,
    KnockoutGenerator,
    SwissGenerator,
    GroupKnockoutGenerator,
    IndividualRankingGenerator,
)
from .algorithms import (
    RoundRobinPairing,
    GroupDistribution,
    KnockoutBracket,
)

__all__ = [
    # Main coordinator
    "TournamentSessionGenerator",

    # Validators
    "GenerationValidator",

    # Format generators
    "BaseFormatGenerator",
    "LeagueGenerator",
    "KnockoutGenerator",
    "SwissGenerator",
    "GroupKnockoutGenerator",
    "IndividualRankingGenerator",

    # Algorithms
    "RoundRobinPairing",
    "GroupDistribution",
    "KnockoutBracket",
]
