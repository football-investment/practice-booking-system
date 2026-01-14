"""
Tournament Constants - Shared definitions for tournament management
"""

# ==================================================
# GAME TYPE OPTIONS - Tournament Match Formats
# ==================================================
# All game types support fixed durations: 1, 3, or 5 minutes

GAME_TYPE_OPTIONS = [
    "League Match",
    "King of the Court",
    "Group Stage + Placement Matches",
    "Elimination Bracket"
]

# ==================================================
# GAME TYPE DEFINITIONS - Complete Specifications
# ==================================================

GAME_TYPE_DEFINITIONS = {
    "League Match": {
        "display_name": "⚽ League Match",
        "category": "LEAGUE",
        "description": (
            "All participants play against each other in a round-robin format. "
            "Points awarded: win=3, draw=1, loss=0. "
            "Matches can have fixed durations: 1, 3, or 5 minutes. "
            "Used for season-long competitions with multiple rounds."
        ),
        "scoring_system": "TABLE_BASED",
        "ranking_method": "POINTS",
        "use_case": "Long-term competitions, everyone plays everyone",
        "requires_result": True,
        "allows_draw": True,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "King of the Court": {
        "display_name": "🏆 King of the Court",
        "category": "SPECIAL",
        "description": (
            "Players compete in a challenge format. 1v1, 1v2, or 1v3 setup. "
            "A fixed game time (1, 3, 5 minutes) per round. "
            "Winner stays on the court; losers rotate out. "
            "The goal is to stay on the court as long as possible."
        ),
        "scoring_system": "WIN_STREAK",
        "ranking_method": "SURVIVAL",
        "use_case": "Short, intense challenge competitions",
        "requires_result": True,
        "allows_draw": False,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "Group Stage + Placement Matches": {
        "display_name": "🏆 Group Stage + Placement",
        "category": "GROUP_STAGE",
        "description": (
            "Tournament split into groups. Each group plays round-robin. "
            "After group stage, placement matches determine ranking (1st-4th, 5th-8th, etc.). "
            "Each game has a fixed duration: 1, 3, or 5 minutes. "
            "Used for tournaments needing group stage + knockout-style placement."
        ),
        "scoring_system": "GROUP_TABLE",
        "ranking_method": "POINTS_ADVANCE",
        "use_case": "Tournaments requiring fair group competition and placement",
        "requires_result": True,
        "allows_draw": True,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "Elimination Bracket": {
        "display_name": "🔥 Elimination Bracket",
        "category": "KNOCKOUT",
        "description": (
            "Single or double elimination bracket. Loser is out, winner advances. "
            "Each game has fixed duration: 1, 3, or 5 minutes. "
            "Used for tournaments where final winner is determined by knockout rounds."
        ),
        "scoring_system": "WIN_LOSS",
        "ranking_method": "ADVANCE",
        "use_case": "Direct knockout tournaments, final determines champion",
        "requires_result": True,
        "allows_draw": False,
        "fixed_game_times": [1, 3, 5]  # minutes
    }
}
