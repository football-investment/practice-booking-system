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
