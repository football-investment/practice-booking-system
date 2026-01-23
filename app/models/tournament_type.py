"""
Tournament Type Model

Defines tournament formats (League, Knockout, Group+Knockout, Swiss)
Used for auto-generating session structures AFTER enrollment closes
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base


class TournamentType(Base):
    """
    Tournament Type Configuration

    Stores metadata and configuration for different tournament formats.
    Used by session generation service to create tournament structure
    AFTER enrollment period closes.
    """
    __tablename__ = "tournament_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # "league", "knockout", etc.
    display_name = Column(String(100), nullable=False)  # "League (Round Robin)"
    description = Column(Text, nullable=True)

    # Player constraints
    min_players = Column(Integer, default=4, nullable=False)
    max_players = Column(Integer, nullable=True)  # NULL = no limit
    requires_power_of_two = Column(Boolean, default=False, nullable=False)

    # Session timing defaults
    session_duration_minutes = Column(Integer, default=90, nullable=False)
    break_between_sessions_minutes = Column(Integer, default=15, nullable=False)

    # Match format type
    format = Column(
        String(50),
        nullable=False,
        server_default='INDIVIDUAL_RANKING',
        comment='Match format: INDIVIDUAL_RANKING (multi-player ranking) or HEAD_TO_HEAD (1v1 or team vs team score-based)'
    )

    # Full configuration (JSON from config files)
    config = Column(JSON, nullable=False)

    # Relationships
    semesters = relationship("Semester", back_populates="tournament_type_config")

    def __repr__(self):
        return f"<TournamentType(code='{self.code}', display_name='{self.display_name}')>"

    def validate_player_count(self, player_count: int) -> tuple[bool, str]:
        """
        Validate if player_count is compatible with this tournament type

        Returns:
            (is_valid, error_message)
        """
        if player_count < self.min_players:
            return False, f"{self.display_name} requires at least {self.min_players} players (got {player_count})"

        if self.max_players and player_count > self.max_players:
            return False, f"{self.display_name} supports maximum {self.max_players} players (got {player_count})"

        if self.requires_power_of_two:
            # Check if power of 2
            if player_count & (player_count - 1) != 0:
                return False, f"{self.display_name} requires power-of-2 players (4, 8, 16, 32, 64). Got {player_count}"

        return True, ""

    def estimate_duration(self, player_count: int, parallel_fields: int = 1) -> dict:
        """
        Estimate tournament duration based on player count and available fields

        Returns:
            {
                'total_matches': int,
                'total_rounds': int,
                'estimated_duration_minutes': int,
                'estimated_duration_days': float
            }
        """
        import math

        total_matches = 0
        total_rounds = 0

        if self.code == "league":
            # Round robin: n*(n-1)/2 matches
            total_matches = (player_count * (player_count - 1)) // 2
            # Rounds: n-1 if even, n if odd
            total_rounds = player_count - 1 if player_count % 2 == 0 else player_count

        elif self.code == "knockout":
            # Single elimination: n-1 matches
            total_matches = player_count - 1
            total_rounds = math.ceil(math.log2(player_count))
            # Add 3rd place playoff if configured
            if self.config.get("third_place_playoff"):
                total_matches += 1

        elif self.code == "group_knockout":
            # Complex calculation based on group configuration
            group_config = self.config.get("group_configuration", {}).get(f"{player_count}_players")
            if group_config:
                groups = group_config["groups"]
                players_per_group = group_config["players_per_group"]
                qualifiers_per_group = group_config["qualifiers"]

                # Group stage: each group plays round robin
                matches_per_group = (players_per_group * (players_per_group - 1)) // 2
                group_matches = groups * matches_per_group

                # Knockout stage: qualifiers play single elimination
                knockout_players = groups * qualifiers_per_group
                knockout_matches = knockout_players - 1

                total_matches = group_matches + knockout_matches
                group_rounds = players_per_group - 1 if players_per_group % 2 == 0 else players_per_group
                knockout_rounds = math.ceil(math.log2(knockout_players))
                total_rounds = group_rounds + knockout_rounds

        elif self.code == "swiss":
            # Swiss system: typically log2(n) rounds
            total_rounds = math.ceil(math.log2(player_count))
            total_matches = (player_count * total_rounds) // 2

        # Calculate duration
        session_duration = self.session_duration_minutes
        break_duration = self.break_between_sessions_minutes

        # With parallel fields, multiple matches can happen simultaneously
        sessions_per_round = math.ceil(total_matches / total_rounds / parallel_fields) if total_rounds > 0 else 0
        total_time_per_round = sessions_per_round * (session_duration + break_duration)
        total_duration_minutes = total_time_per_round * total_rounds

        return {
            'total_matches': total_matches,
            'total_rounds': total_rounds,
            'estimated_duration_minutes': total_duration_minutes,
            'estimated_duration_days': round(total_duration_minutes / 60 / 24, 2)
        }
