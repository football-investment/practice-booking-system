"""
E2E Test Configuration

This file makes fixtures from fixtures.py available to all E2E tests.
"""

# Import all fixtures to make them available
from tests.e2e.fixtures import (
    admin_token,
    test_instructor,
    test_players,
    create_tournament,
    tournament_in_draft,
    tournament_with_instructor,
    complete_tournament_setup
)

# Make pytest aware of the fixtures
__all__ = [
    "admin_token",
    "test_instructor",
    "test_players",
    "create_tournament",
    "tournament_in_draft",
    "tournament_with_instructor",
    "complete_tournament_setup"
]
