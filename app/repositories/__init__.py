"""
Repository package

Contains data access layer logic following the Repository pattern.
Eliminates duplicated database queries across endpoints.

Repositories:
- TournamentRepository: Tournament CRUD and queries
"""

from .tournament_repository import TournamentRepository

__all__ = ["TournamentRepository"]
