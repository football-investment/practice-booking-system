"""
Tournament System Enums

Enums for tournament types and participant types.
"""
import enum


class TournamentType(str, enum.Enum):
    """Tournament format types"""
    LEAGUE = "LEAGUE"  # League format - all play all, ranked by points
    KNOCKOUT = "KNOCKOUT"  # Single/double elimination bracket
    ROUND_ROBIN = "ROUND_ROBIN"  # Round robin - everyone plays everyone
    CUSTOM = "CUSTOM"  # Custom tournament format


class ParticipantType(str, enum.Enum):
    """Participant types in tournaments"""
    INDIVIDUAL = "INDIVIDUAL"  # Individual players
    TEAM = "TEAM"  # Teams only
    MIXED = "MIXED"  # Both individuals and teams


class TeamMemberRole(str, enum.Enum):
    """Roles within a team"""
    CAPTAIN = "CAPTAIN"
    PLAYER = "PLAYER"


class TournamentPhase(str, enum.Enum):
    """
    Canonical tournament phase values

    These are the ONLY valid values for Session.tournament_phase in the domain model.
    UI display strings should be derived from these canonical values, not stored in the database.
    """
    GROUP_STAGE = "GROUP_STAGE"  # Group stage / League round robin
    KNOCKOUT = "KNOCKOUT"  # Knockout stage / Elimination rounds
    FINALS = "FINALS"  # Finals / Championship match
    PLACEMENT = "PLACEMENT"  # Placement matches (3rd place, etc.)
    INDIVIDUAL_RANKING = "INDIVIDUAL_RANKING"  # Individual ranking format
    SWISS = "SWISS"  # Swiss system format
