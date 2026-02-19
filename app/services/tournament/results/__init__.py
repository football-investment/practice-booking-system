"""
Tournament Results Services

Provides business logic services for tournament results management:
- Calculators: Standings, rankings, advancement
- Finalizers: Group stage, session, tournament
- Validators: Result validation

This module was created as part of P2 decomposition to extract
business logic from the 1,251-line match_results.py endpoint file.
"""

from .calculators import (
    StandingsCalculator,
    RankingAggregator,
    AdvancementCalculator
)
from .finalization import (
    GroupStageFinalizer,
    SessionFinalizer,
    TournamentFinalizer
)
from .validators import ResultValidator

__all__ = [
    # Calculators
    "StandingsCalculator",
    "RankingAggregator",
    "AdvancementCalculator",
    # Finalizers
    "GroupStageFinalizer",
    "SessionFinalizer",
    "TournamentFinalizer",
    # Validators
    "ResultValidator",
]
