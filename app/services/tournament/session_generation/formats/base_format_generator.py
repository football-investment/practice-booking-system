"""
Base Format Generator

Abstract base class for all tournament format generators.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.models.tournament_type import TournamentType


class BaseFormatGenerator(ABC):
    """
    Abstract base class for tournament format generators
    """

    def __init__(self, db: Session):
        """
        Initialize generator with database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    @abstractmethod
    def generate(
        self,
        tournament: Semester,
        tournament_type: TournamentType,
        player_count: int,
        parallel_fields: int,
        session_duration: int,
        break_minutes: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate sessions for this tournament format

        Args:
            tournament: Tournament (Semester) instance
            tournament_type: TournamentType configuration
            player_count: Number of enrolled players
            parallel_fields: Number of fields available for parallel matches
            session_duration: Duration of each session in minutes
            break_minutes: Break time between sessions in minutes
            **kwargs: Additional format-specific parameters

        Returns:
            List of session data dictionaries
        """
        pass
