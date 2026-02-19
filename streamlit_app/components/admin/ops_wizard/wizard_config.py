"""
OPS Wizard — Shared Configuration & Helper Utilities

All wizard-step-level configs and pure helper functions.
Imported by tournament_monitor.py (for the dispatcher) and by each step module.
"""

from __future__ import annotations
import datetime


# ── Constants ─────────────────────────────────────────────────────────────────

_SAFETY_CONFIRMATION_THRESHOLD = 128


# ── Wizard Configs ────────────────────────────────────────────────────────────

SCENARIO_CONFIG = {
    "large_field_monitor": {
        "label": "🏟️ Large Field Monitor",
        "description": "Multi-campus tournament with session scheduling",
        "use_case": "Production monitoring, real-world load testing",
        "min_players": 4,
        "max_players": 1024,
        "default_player_count": 8,
        "allowed_types": ["knockout", "league", "group_knockout"],
    },
    "smoke_test": {
        "label": "🧪 Smoke Test",
        "description": "Quick validation test with minimal players",
        "use_case": "Feature testing, sanity checks",
        "min_players": 2,
        "max_players": 16,
        "default_player_count": 4,
        "allowed_types": ["knockout", "league"],
    },
    "scale_test": {
        "label": "📊 Scale Test",
        "description": "High-volume stress test with large player counts",
        "use_case": "Performance testing, capacity planning",
        "min_players": 64,
        "max_players": 1024,
        "default_player_count": 128,
        "allowed_types": ["knockout", "league", "group_knockout"],
    },
}

FORMAT_CONFIG = {
    "HEAD_TO_HEAD": {
        "label": "⚔️ Head-to-Head (1v1 Matches)",
        "description": "Players compete directly against each other in individual matches. Results determine winners and losers.",
        "use_case": "Standard tournaments: knockout, league, group+knockout",
        "requires_tournament_type": True,
    },
    "INDIVIDUAL_RANKING": {
        "label": "🏃 Individual Ranking (Solo Performance)",
        "description": "All players compete independently. Ranked by their individual score, time, or placement.",
        "use_case": "Athletics, time trials, performance assessments",
        "requires_tournament_type": False,
    },
}

INDIVIDUAL_SCORING_CONFIG = {
    "SCORE_BASED": {
        "label": "🎯 Score Based (highest score wins)",
        "description": "Players are ranked by score. Higher score = better rank.",
        "ranking_direction": "DESC",
        "example": "e.g. goals scored, points accumulated",
    },
    "TIME_BASED": {
        "label": "⏱️ Time Based (fastest wins)",
        "description": "Players are ranked by completion time. Lower time = better rank.",
        "ranking_direction": "ASC",
        "example": "e.g. sprint time, obstacle course",
    },
    "DISTANCE_BASED": {
        "label": "📏 Distance Based (farthest wins)",
        "description": "Players are ranked by distance achieved. Higher distance = better rank.",
        "ranking_direction": "DESC",
        "example": "e.g. long jump, throw distance",
    },
    "PLACEMENT": {
        "label": "🏅 Placement (finish position)",
        "description": "Players are ranked purely by finish position. No numeric scoring.",
        "ranking_direction": None,
        "example": "e.g. race finishing order",
    },
}

TOURNAMENT_TYPE_CONFIG = {
    "knockout": {
        "label": "🏆 Knockout (Single Elimination)",
        "description": "Players compete in bracket-style elimination rounds. Winner advances, loser is eliminated.",
        "structure": "Bracket-style elimination",
        "session_formula": "~N matches (N = player_count - 1)",
        "min_players": 2,
        "requires_power_of_two": False,
    },
    "league": {
        "label": "⚽ League (Round Robin)",
        "description": "Every player competes against every other player. Final rankings based on points and goal difference.",
        "structure": "All-play-all round robin",
        "session_formula": "N×(N-1)/2 matches",
        "min_players": 2,
        "requires_power_of_two": False,
    },
    "group_knockout": {
        "label": "🌍 Group + Knockout (Hybrid)",
        "description": "Phase 1: Group stage (round robin within groups). Phase 2: Knockout (top qualifiers from each group).",
        "structure": "Group stage → Knockout stage",
        "session_formula": "Group matches + knockout matches",
        "min_players": 8,
        "requires_power_of_two": False,
    },
}

SIMULATION_MODE_CONFIG = {
    "manual": {
        "label": "🎮 Manual Results",
        "description": "Tournament created with sessions scheduled. Results must be entered manually by admin later.",
        "use_case": "Real tournaments with actual players",
        "auto_simulate": False,
        "complete_lifecycle": False,
    },
    "auto_immediate": {
        "label": "🤖 Auto-Simulation (Immediate)",
        "description": "Tournament created AND results auto-generated now. Random scores simulated for all matches.",
        "use_case": "Testing, monitoring, load validation",
        "auto_simulate": True,
        "complete_lifecycle": False,
    },
    "accelerated": {
        "label": "⚡ Accelerated Simulation",
        "description": "Entire tournament lifecycle simulated instantly. All phases completed, final rankings calculated.",
        "use_case": "End-to-end testing, ranking algorithm validation",
        "auto_simulate": True,
        "complete_lifecycle": True,
    },
}

_SCORING_DIR_LABELS = {
    ("TIME_BASED",     "ASC"):  "⏱️ Time Based (fastest wins)",
    ("TIME_BASED",     "DESC"): "⏱️ Time Based (longest wins)",
    ("SCORE_BASED",    "ASC"):  "🎯 Score Based (lowest score wins)",
    ("SCORE_BASED",    "DESC"): "🎯 Score Based (highest score wins)",
    ("DISTANCE_BASED", "ASC"):  "📏 Distance Based (shortest wins)",
    ("DISTANCE_BASED", "DESC"): "📏 Distance Based (farthest wins)",
}


# ── Helper Functions ──────────────────────────────────────────────────────────

def scoring_label(scoring_type: str, ranking_direction: str | None = None) -> str:
    """Return scoring label that reflects the actual ranking direction."""
    if ranking_direction:
        override = _SCORING_DIR_LABELS.get((scoring_type, ranking_direction))
        if override:
            return override
    return INDIVIDUAL_SCORING_CONFIG.get(scoring_type, {}).get("label", scoring_type)


def get_group_knockout_config(player_count: int) -> dict | None:
    """Get valid group configuration for group_knockout tournaments."""
    valid_configs = {
        8:  {"groups": 2,  "players_per_group": 4, "qualifiers": 2},
        12: {"groups": 3,  "players_per_group": 4, "qualifiers": 2},
        16: {"groups": 4,  "players_per_group": 4, "qualifiers": 2},
        24: {"groups": 6,  "players_per_group": 4, "qualifiers": 2},
        32: {"groups": 8,  "players_per_group": 4, "qualifiers": 2},
        48: {"groups": 12, "players_per_group": 4, "qualifiers": 2},
        64: {"groups": 16, "players_per_group": 4, "qualifiers": 2},
    }
    return valid_configs.get(player_count)


def estimate_session_count(tournament_type: str, player_count: int) -> int:
    """Estimate total session count."""
    if tournament_type == "knockout":
        return player_count - 1
    elif tournament_type == "league":
        return (player_count * (player_count - 1)) // 2
    elif tournament_type == "group_knockout":
        config = get_group_knockout_config(player_count)
        if config:
            group_matches = config["groups"] * (config["players_per_group"] * (config["players_per_group"] - 1)) // 2
            knockout_participants = config["groups"] * config["qualifiers"]
            knockout_matches = knockout_participants - 1
            return group_matches + knockout_matches
    return 0


def estimate_duration_hours(tournament_type: str, player_count: int) -> float:
    """Estimate tournament duration in hours."""
    session_count = estimate_session_count(tournament_type, player_count)
    avg_session_duration_min = 60
    return (session_count * avg_session_duration_min) / 60


def generate_default_tournament_name(scenario: str, tournament_type: str, player_count: int) -> str:
    """Generate default tournament name."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    scenario_short = scenario.upper().replace("_", "-")
    type_short = tournament_type.upper().replace("_", "-")
    return f"OPS-{scenario_short}-{type_short}-{player_count}p-{timestamp}"
