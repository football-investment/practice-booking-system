"""
Match Structure and Result Models

Defines how tournament sessions are structured and how performance is recorded.
This layer sits between the session and the ranking system, converting
actual performance data into derived rankings.

Architecture:
    Session → MatchStructure → MatchResult → Derived Ranking → Points
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import enum

from ..database import Base


class MatchFormat(str, enum.Enum):
    """
    Match format types - defines HOW participants compete

    INDIVIDUAL_RANKING: All participants compete together, ranked by placement
        Example: League round where all 8 players compete simultaneously

    HEAD_TO_HEAD: 1v1 competition between two participants
        Example: Knockout bracket match

    TEAM_MATCH: Team vs Team competition
        Example: 4v4 match (Team A vs Team B)

    TIME_BASED: Individual performance measured by time
        Example: 100m sprint, fastest completion time

    SKILL_RATING: Individual performance rated by instructor/judges
        Example: Technique assessment, skill demonstration
        ⚠️  EXTENSION POINT: Business logic to be defined later
    """
    INDIVIDUAL_RANKING = "INDIVIDUAL_RANKING"
    HEAD_TO_HEAD = "HEAD_TO_HEAD"
    TEAM_MATCH = "TEAM_MATCH"
    TIME_BASED = "TIME_BASED"
    SKILL_RATING = "SKILL_RATING"  # 🔌 Extension point - logic TBD


class ScoringType(str, enum.Enum):
    """
    Scoring type - defines HOW performance is measured

    PLACEMENT: Direct placement ranking (1st, 2nd, 3rd)
    WIN_LOSS: Binary outcome (winner/loser)
    SCORE_BASED: Numeric score (goals, points)
    TIME_BASED: Time measurement (seconds, milliseconds)
    SKILL_RATING: Instructor/judge rating (1-10 scale)
        ⚠️  EXTENSION POINT: Rating scale and criteria TBD
    """
    PLACEMENT = "PLACEMENT"
    WIN_LOSS = "WIN_LOSS"
    SCORE_BASED = "SCORE_BASED"
    TIME_BASED = "TIME_BASED"
    SKILL_RATING = "SKILL_RATING"  # 🔌 Extension point - criteria TBD


class MatchStructure(Base):
    """
    Defines the structure of a match/session

    Stores metadata about HOW participants are organized and compete.
    This is typically auto-generated during tournament session creation.

    Example configurations:

    1. INDIVIDUAL_RANKING (League):
        {
            "expected_participants": 8,
            "ranking_criteria": "final_placement"
        }

    2. HEAD_TO_HEAD (Knockout):
        {
            "pairing": [player_a_id, player_b_id],
            "bracket_position": "Quarter-Final 1"
        }

    3. TEAM_MATCH:
        {
            "teams": {
                "A": [player1_id, player2_id, player3_id, player4_id],
                "B": [player5_id, player6_id, player7_id, player8_id]
            },
            "team_names": {"A": "Red Team", "B": "Blue Team"}
        }

    4. TIME_BASED:
        {
            "performance_criteria": "100m_sprint_time",
            "expected_participants": 8,
            "time_unit": "seconds"
        }

    5. SKILL_RATING (Extension Point):
        {
            "rating_criteria": "TBD",  # To be defined by business
            "min_score": 1,
            "max_score": 10,
            "judge_ids": [instructor_id]
        }
    """
    __tablename__ = "match_structures"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)

    # Format definition
    match_format = Column(
        SQLAlchemyEnum(MatchFormat),
        nullable=False,
        comment="How participants compete"
    )

    scoring_type = Column(
        SQLAlchemyEnum(ScoringType),
        nullable=False,
        comment="How performance is measured"
    )

    # Structure metadata (flexible JSONB for different formats)
    structure_config = Column(
        JSONB,
        nullable=True,
        comment="Format-specific configuration (pairings, teams, criteria, etc.)"
    )

    # Relationships
    session = relationship("Session", backref="match_structure")
    match_results = relationship("MatchResult", back_populates="match_structure", cascade="all, delete-orphan")


class MatchResult(Base):
    """
    Stores actual performance data from a match

    This is the RAW performance data (scores, times, ratings) that gets
    converted into derived rankings by the ResultProcessor service.

    Example performance_data by format:

    1. INDIVIDUAL_RANKING:
        {"placement": 1}

    2. HEAD_TO_HEAD (WIN_LOSS):
        {"opponent_id": 5, "result": "WIN"}

    3. HEAD_TO_HEAD (SCORE_BASED):
        {"score": 3, "opponent_score": 1, "opponent_id": 5}

    4. TEAM_MATCH:
        {"team": "A", "score": 5, "opponent_score": 3}

    5. TIME_BASED:
        {"time_seconds": 12.45, "time_milliseconds": 12450}

    6. SKILL_RATING (Extension Point):
        {
            "rating": 8.5,
            "judge_id": 1,
            "criteria_scores": {  # TBD - to be defined later
                "technique": 9,
                "speed": 8,
                "accuracy": 8
            }
        }
    """
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    match_structure_id = Column(Integer, ForeignKey("match_structures.id"), nullable=False)

    # Participant identification
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="User ID for individual results"
    )

    team_identifier = Column(
        String(50),
        nullable=True,
        comment="Team identifier for team matches (A, B, etc.)"
    )

    # Performance data (flexible JSONB for different scoring types)
    performance_data = Column(
        JSONB,
        nullable=False,
        comment="Raw performance data (scores, times, ratings, etc.)"
    )

    # Derived ranking (calculated by ResultProcessor)
    derived_rank = Column(
        Integer,
        nullable=True,
        comment="Rank derived from performance data (1=1st place, 2=2nd, etc.)"
    )

    # Metadata
    recorded_at = Column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(),
        comment="When this result was recorded"
    )

    # Relationships
    match_structure = relationship("MatchStructure", back_populates="match_results")
    user = relationship("User")


# ============================================================================
# Example Usage Patterns
# ============================================================================

"""
EXAMPLE 1: League Session (INDIVIDUAL_RANKING)
---------------------------------------------
Session:
    match_format = "INDIVIDUAL_RANKING"
    scoring_type = "PLACEMENT"

MatchStructure:
    structure_config = {
        "expected_participants": 8,
        "ranking_criteria": "final_placement"
    }

MatchResults (4 present players):
    [
        {user_id: 1, performance_data: {"placement": 1}, derived_rank: 1},
        {user_id: 2, performance_data: {"placement": 2}, derived_rank: 2},
        {user_id: 3, performance_data: {"placement": 3}, derived_rank: 3},
        {user_id: 4, performance_data: {"placement": 4}, derived_rank: 4}
    ]


EXAMPLE 2: Knockout Match (HEAD_TO_HEAD)
-----------------------------------------
Session:
    match_format = "HEAD_TO_HEAD"
    scoring_type = "SCORE_BASED"

MatchStructure:
    structure_config = {
        "pairing": [player_a_id, player_b_id],
        "bracket_position": "Semi-Final 1"
    }

MatchResults:
    [
        {user_id: player_a_id, performance_data: {"score": 3, "opponent_score": 1}, derived_rank: 1},
        {user_id: player_b_id, performance_data: {"score": 1, "opponent_score": 3}, derived_rank: 2}
    ]


EXAMPLE 3: Team Match (TEAM_MATCH)
-----------------------------------
Session:
    match_format = "TEAM_MATCH"
    scoring_type = "SCORE_BASED"

MatchStructure:
    structure_config = {
        "teams": {
            "A": [1, 2, 3, 4],
            "B": [5, 6, 7, 8]
        }
    }

MatchResults:
    [
        # Team A members (winners)
        {user_id: 1, team_identifier: "A", performance_data: {"team_score": 5, "opponent_score": 3}, derived_rank: 1},
        {user_id: 2, team_identifier: "A", performance_data: {"team_score": 5, "opponent_score": 3}, derived_rank: 1},
        {user_id: 3, team_identifier: "A", performance_data: {"team_score": 5, "opponent_score": 3}, derived_rank: 1},
        {user_id: 4, team_identifier: "A", performance_data: {"team_score": 5, "opponent_score": 3}, derived_rank: 1},
        # Team B members (losers)
        {user_id: 5, team_identifier: "B", performance_data: {"team_score": 3, "opponent_score": 5}, derived_rank: 2},
        {user_id: 6, team_identifier: "B", performance_data: {"team_score": 3, "opponent_score": 5}, derived_rank: 2},
        {user_id: 7, team_identifier: "B", performance_data: {"team_score": 3, "opponent_score": 5}, derived_rank: 2},
        {user_id: 8, team_identifier: "B", performance_data: {"team_score": 3, "opponent_score": 5}, derived_rank: 2}
    ]


EXAMPLE 4: Time-Based Performance (TIME_BASED)
-----------------------------------------------
Session:
    match_format = "TIME_BASED"
    scoring_type = "TIME_BASED"

MatchStructure:
    structure_config = {
        "performance_criteria": "100m_sprint",
        "time_unit": "seconds"
    }

MatchResults:
    [
        {user_id: 1, performance_data: {"time_seconds": 11.23}, derived_rank: 1},  # Fastest
        {user_id: 2, performance_data: {"time_seconds": 11.45}, derived_rank: 2},
        {user_id: 3, performance_data: {"time_seconds": 11.89}, derived_rank: 3},
        {user_id: 4, performance_data: {"time_seconds": 12.01}, derived_rank: 4}
    ]


EXAMPLE 5: Skill Rating (SKILL_RATING) - EXTENSION POINT
---------------------------------------------------------
Session:
    match_format = "SKILL_RATING"
    scoring_type = "SKILL_RATING"

MatchStructure:
    structure_config = {
        "rating_criteria": "TBD",  # ⚠️  Business logic to be defined
        "min_score": 1,
        "max_score": 10,
        "judge_ids": [instructor_id]
    }

MatchResults:
    [
        {
            user_id: 1,
            performance_data: {
                "rating": 9.5,
                "judge_id": instructor_id,
                # ⚠️  Additional criteria TBD by business
                "criteria_scores": {
                    "technique": null,  # To be defined
                    "speed": null,
                    "accuracy": null
                }
            },
            derived_rank: 1  # Calculated by future SKILL_RATING processor
        },
        ...
    ]
"""
