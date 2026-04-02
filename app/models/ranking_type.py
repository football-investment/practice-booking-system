"""
Ranking Type Domain Enums

RankingType  — how a tournament's standings are determined (stored on TournamentType)
StandingsState — current visibility/readiness of the public standings section (computed)
"""
from enum import Enum


class RankingType(str, Enum):
    """
    Describes what data a tournament's standings are built from.

    SCORING_ONLY — participants are ranked by a single cumulative score / time.
                   No win/draw/loss tracking.  Examples: Swiss System, IR formats
                   (sprint, push-up, relay).  Only the "Pts / Score" column is
                   meaningful in the Full Results table.

    WDL_BASED    — standings are derived from win/draw/loss record across head-to-head
                   matches.  Examples: Round-Robin League, Group Knockout.
                   W / D / L / GF / GA columns are meaningful.
    """
    SCORING_ONLY = "SCORING_ONLY"
    WDL_BASED = "WDL_BASED"


class StandingsState(str, Enum):
    """
    Explicit UI-facing state for the public standings/results section.

    FINAL   — TournamentRanking rows exist AND the event is COMPLETED or
              REWARDS_DISTRIBUTED.  Renders as "📋 Full Results".

    LIVE    — TournamentRanking rows exist but the event is still in progress
              (IN_PROGRESS or CHECK_IN_OPEN).  Renders as "📊 Current Standings".

    PENDING — No TournamentRanking rows yet, but sessions with results exist.
              Rankings have not been calculated.  Renders a placeholder banner.

    NONE    — No ranking data and no session results.  Section is hidden entirely.
    """
    FINAL = "FINAL"
    LIVE = "LIVE"
    PENDING = "PENDING"
    NONE = "NONE"
