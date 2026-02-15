"""
OPS Test Observability Platform
=================================
Live monitoring of automated test tournaments with:
  - OPS Wizard (5-step launch flow)
  - Auto-tracking of launched test tournaments
  - Real-time phase-by-phase execution visibility
  - No production tournament mixing

Architecture: Launch → Auto-Monitor → Live Tracking
"""

from __future__ import annotations

import datetime
import requests
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from config import API_BASE_URL

from api_helpers_monitor import (
    get_all_tournaments_admin,
    get_campus_schedules,
    get_tournament_detail,
    get_tournament_rankings,
    get_tournament_sessions,
    submit_h2h_result,
    trigger_ops_scenario,
)

# Refactored components (Iteration 3)
from .tournament_card.leaderboard import render_leaderboard
from .tournament_card.result_entry import render_manual_result_entry
from .tournament_card.session_grid import (
    render_campus_grid,
    render_session_card,
)
from .ops_wizard import (
    init_wizard_state,
    reset_wizard_state,
    execute_launch,
)


# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_REFRESH_SECONDS = 10
_MIN_REFRESH = 5
_MAX_REFRESH = 120
_SAFETY_CONFIRMATION_THRESHOLD = 128

# Status badge colours (HTML inline)
_STATUS_COLOURS: Dict[str, str] = {
    "IN_PROGRESS":        "#22c55e",   # green
    "DRAFT":              "#f59e0b",   # amber
    "COMPLETED":          "#6b7280",   # grey
    "REWARDS_DISTRIBUTED": "#a855f7",  # purple
    "CANCELLED":          "#ef4444",   # red
}

_RESULT_ICONS = {True: "✅", False: "⏳", None: "⏳"}


# ── Wizard Configuration ─────────────────────────────────────────────────────

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


# ── Helper Functions ─────────────────────────────────────────────────────────

def _badge(label: str, colour: str) -> str:
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 8px;"
        f"border-radius:4px;font-size:0.75rem;font-weight:600'>{label}</span>"
    )


def _progress_bar(done: int, total: int) -> str:
    """Return an HTML mini progress bar."""
    pct = (done / total * 100) if total else 0
    return (
        f"<div style='background:#e5e7eb;border-radius:4px;height:8px;width:100%'>"
        f"<div style='background:#3b82f6;width:{pct:.0f}%;height:8px;border-radius:4px'></div>"
        f"</div>"
        f"<small style='color:#6b7280'>{done}/{total} sessions submitted ({pct:.0f}%)</small>"
    )




def get_group_knockout_config(player_count: int) -> dict | None:
    """Get valid group configuration for group_knockout tournaments"""
    valid_configs = {
        8: {"groups": 2, "players_per_group": 4, "qualifiers": 2},
        12: {"groups": 3, "players_per_group": 4, "qualifiers": 2},
        16: {"groups": 4, "players_per_group": 4, "qualifiers": 2},
        24: {"groups": 6, "players_per_group": 4, "qualifiers": 2},
        32: {"groups": 8, "players_per_group": 4, "qualifiers": 2},
        48: {"groups": 12, "players_per_group": 4, "qualifiers": 2},
        64: {"groups": 16, "players_per_group": 4, "qualifiers": 2},
    }
    return valid_configs.get(player_count)


def estimate_session_count(tournament_type: str, player_count: int) -> int:
    """Estimate total session count"""
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
    """Estimate tournament duration in hours"""
    session_count = estimate_session_count(tournament_type, player_count)
    avg_session_duration_min = 60
    return (session_count * avg_session_duration_min) / 60


def generate_default_tournament_name(scenario: str, tournament_type: str, player_count: int) -> str:
    """Generate default tournament name"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    scenario_short = scenario.upper().replace("_", "-")
    type_short = tournament_type.upper().replace("_", "-")
    return f"OPS-{scenario_short}-{type_short}-{player_count}p-{timestamp}"


# ── Wizard Step Renderers ────────────────────────────────────────────────────

def render_step1_scenario():
    """Step 1: Scenario Selection"""
    st.markdown("### Step 1 of 8: Select Test Scenario")

    st.info("""
🎯 **You are creating a NEW test tournament for observability.**

This wizard launches automated test tournaments that will be **automatically tracked** in the live monitoring panel.

Existing OPS tests are shown in the monitoring panel above.
    """)

    st.markdown("---")

    # Get default value from saved state if available
    default_scenario = st.session_state.get("wizard_scenario_saved")
    default_index = 0
    if default_scenario in ["large_field_monitor", "smoke_test", "scale_test"]:
        default_index = ["large_field_monitor", "smoke_test", "scale_test"].index(default_scenario)

    scenario = st.radio(
        "Choose test scenario",
        options=["large_field_monitor", "smoke_test", "scale_test"],
        format_func=lambda x: SCENARIO_CONFIG[x]["label"],
        key="wizard_scenario_widget",
        index=default_index,
        help="Test scenarios define the operational context and constraints."
    )

    if scenario:
        config = SCENARIO_CONFIG[scenario]
        st.info(f"""
**{config['label']}**

{config['description']}

**Recommended for:** {config['use_case']}
        """)

        st.session_state["wizard_step1_valid"] = True
        st.session_state["wizard_completed_steps"].add(1)
    else:
        st.session_state["wizard_step1_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col2:
        next_enabled = st.session_state["wizard_step1_valid"]
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step1_next"):
            # Save the selection to persistent session state
            st.session_state["wizard_scenario_saved"] = scenario
            st.session_state["wizard_current_step"] = 2
            st.rerun()


def render_step2_format():
    """Step 2: Format Selection — HEAD_TO_HEAD vs INDIVIDUAL_RANKING"""
    st.markdown("### Step 2 of 8: Select Tournament Format")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    st.info(f"**Scenario:** {SCENARIO_CONFIG[scenario]['label']}")
    st.markdown("---")

    default_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    format_options = list(FORMAT_CONFIG.keys())
    default_format_index = format_options.index(default_format) if default_format in format_options else 0

    selected_format = st.radio(
        "Choose tournament format",
        options=format_options,
        format_func=lambda x: FORMAT_CONFIG[x]["label"],
        key="wizard_format_widget",
        index=default_format_index,
        help="This determines whether players compete 1v1 (Head-to-Head) or individually (Individual Ranking)."
    )

    if selected_format:
        cfg = FORMAT_CONFIG[selected_format]
        st.info(f"""
**{cfg['label']}**

{cfg['description']}

**Typical use:** {cfg['use_case']}
        """)

        if selected_format == "HEAD_TO_HEAD":
            st.success("➡️ Next: Select tournament structure (Knockout, League, or Group+Knockout)")
        else:
            st.success("➡️ Next: Select scoring method (Score, Time, Distance, or Placement)")

        st.session_state["wizard_step2_valid"] = True
        st.session_state["wizard_completed_steps"].add(2)
    else:
        st.session_state["wizard_step2_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step2_format_back"):
            st.session_state["wizard_current_step"] = 1
            st.rerun()
    with col2:
        next_enabled = st.session_state.get("wizard_step2_valid", False)
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step2_format_next"):
            st.session_state["wizard_format_saved"] = selected_format
            # If INDIVIDUAL_RANKING, clear any saved tournament_type
            if selected_format == "INDIVIDUAL_RANKING":
                st.session_state.pop("wizard_tournament_type_saved", None)
            st.session_state["wizard_current_step"] = 3
            st.rerun()


def render_step3_individual_scoring():
    """Step 3 (alternate): Individual Scoring Type — only for INDIVIDUAL_RANKING"""
    st.markdown("### Step 3 of 8: Select Scoring Method")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    if not scenario:
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    st.info(f"""
**Scenario:** {SCENARIO_CONFIG[scenario]['label']}
**Format:** 🏃 Individual Ranking
    """)
    st.markdown("---")

    scoring_options = list(INDIVIDUAL_SCORING_CONFIG.keys())
    default_scoring = st.session_state.get("wizard_scoring_type_saved", "SCORE_BASED")
    default_scoring_index = scoring_options.index(default_scoring) if default_scoring in scoring_options else 0

    scoring_type = st.radio(
        "Choose scoring method",
        options=scoring_options,
        format_func=lambda x: INDIVIDUAL_SCORING_CONFIG[x]["label"],
        key="wizard_scoring_type_widget",
        index=default_scoring_index,
    )

    if scoring_type:
        cfg = INDIVIDUAL_SCORING_CONFIG[scoring_type]
        st.info(f"""
**{cfg['label']}**

{cfg['description']}

**Example:** {cfg['example']}
**Ranking:** {"Lowest wins (ASC)" if cfg['ranking_direction'] == 'ASC' else "Highest wins (DESC)" if cfg['ranking_direction'] == 'DESC' else "By finish position"}
        """)
        st.session_state["wizard_step3_valid"] = True
        st.session_state["wizard_completed_steps"].add(3)
    else:
        st.session_state["wizard_step3_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step3_ind_back"):
            st.session_state["wizard_current_step"] = 2
            st.rerun()
    with col2:
        next_enabled = st.session_state.get("wizard_step3_valid", False)
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step3_ind_next"):
            st.session_state["wizard_scoring_type_saved"] = scoring_type
            st.session_state["wizard_ranking_direction_saved"] = INDIVIDUAL_SCORING_CONFIG[scoring_type]["ranking_direction"]
            st.session_state["wizard_current_step"] = 4
            st.rerun()


def render_step2_tournament_type():
    """Step 3 (HEAD_TO_HEAD): Tournament Type Selection"""
    st.markdown("### Step 3 of 8: Select Tournament Type")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")

    # Safeguard: if no scenario, go back to step 1
    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    scenario_config = SCENARIO_CONFIG[scenario]
    allowed_types = scenario_config["allowed_types"]

    st.info(f"**Scenario:** {scenario_config['label']}")
    st.caption(f"Allowed tournament types: {', '.join([TOURNAMENT_TYPE_CONFIG[t]['label'] for t in allowed_types])}")

    st.markdown("---")

    # Get default value from saved state if available
    default_tournament_type = st.session_state.get("wizard_tournament_type_saved")
    default_index = 0
    if default_tournament_type in allowed_types:
        default_index = allowed_types.index(default_tournament_type)

    tournament_type = st.radio(
        "Choose tournament format",
        options=allowed_types,
        format_func=lambda x: TOURNAMENT_TYPE_CONFIG[x]["label"],
        key="wizard_tournament_type_widget",
        index=default_index,
        help="Tournament type determines match structure and progression."
    )

    if tournament_type:
        config = TOURNAMENT_TYPE_CONFIG[tournament_type]
        st.info(f"""
**{config['label']}**

{config['description']}

**Match structure:** {config['structure']}
**Session count:** {config['session_formula']}
{f"**Minimum players:** {config['min_players']}" if config.get('min_players') else ""}
        """)

        st.session_state["wizard_step2_valid"] = True
        st.session_state["wizard_completed_steps"].add(2)
    else:
        st.session_state["wizard_step2_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step2_back"):
            st.session_state["wizard_current_step"] = 2
            st.rerun()
    with col2:
        next_enabled = st.session_state["wizard_step2_valid"]
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step2_next"):
            # Save the selection to persistent session state
            st.session_state["wizard_tournament_type_saved"] = tournament_type
            st.session_state["wizard_current_step"] = 4
            st.rerun()


def validate_step3_detailed() -> Tuple[bool, List[str], List[str], List[str]]:
    """Validate Step 4: Player Count Selection"""
    player_count = st.session_state.get("wizard_player_count_saved") or st.session_state.get("wizard_player_count_widget")
    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")

    if not player_count or not scenario:
        return False, ["Configuration incomplete"], [], []

    # INDIVIDUAL_RANKING doesn't need tournament_type
    if tournament_format == "HEAD_TO_HEAD" and not tournament_type:
        return False, ["No tournament type selected"], [], []

    scenario_config = SCENARIO_CONFIG[scenario]

    # For INDIVIDUAL_RANKING, use generic type_config with min_players=2
    if tournament_format == "INDIVIDUAL_RANKING" or not tournament_type:
        type_config = {"min_players": 2}
    else:
        type_config = TOURNAMENT_TYPE_CONFIG[tournament_type]

    errors = []
    warnings = []
    info = []

    # Check scenario constraints
    if player_count < scenario_config["min_players"]:
        errors.append(f"Player count ({player_count}) below scenario minimum ({scenario_config['min_players']})")
    elif player_count > scenario_config["max_players"]:
        errors.append(f"Player count ({player_count}) exceeds scenario maximum ({scenario_config['max_players']})")
    else:
        info.append(f"Scenario constraint: {scenario_config['min_players']} ≤ count ≤ {scenario_config['max_players']}")

    # Check tournament type constraints
    if player_count < type_config["min_players"]:
        errors.append(f"Player count ({player_count}) below tournament type minimum ({type_config['min_players']})")
    else:
        info.append(f"Tournament type constraint: count ≥ {type_config['min_players']}")

    # Tournament-specific validation
    if tournament_type == "group_knockout":
        valid_config = get_group_knockout_config(player_count)
        if valid_config:
            info.append(
                f"Group configuration valid: {valid_config['groups']} groups × "
                f"{valid_config['players_per_group']} players"
            )
        else:
            errors.append(
                f"No valid group configuration for {player_count} players. "
                f"Valid counts: 8, 12, 16, 24, 32, 48, 64, ..."
            )

    # Estimate session count and duration
    if not errors:
        if tournament_format == "INDIVIDUAL_RANKING":
            warnings.append(f"Expected sessions: ~{player_count} (1 per player)")
            warnings.append("Estimated duration: depends on scoring setup")
        else:
            session_count = estimate_session_count(tournament_type, player_count)
            duration_hours = estimate_duration_hours(tournament_type, player_count)
            warnings.append(f"Expected sessions: ~{session_count} matches")
            warnings.append(f"Estimated duration: ~{duration_hours:.1f} hours")

        if player_count >= _SAFETY_CONFIRMATION_THRESHOLD:
            warnings.append(
                f"LARGE SCALE OPERATION: {player_count} players. "
                f"Safety confirmation will be required."
            )

    is_valid = len(errors) == 0

    return is_valid, errors, warnings, info


def render_step3_player_count():
    """Step 4: Player Count Selection"""
    st.markdown("### Step 5 of 8: Select Player Count")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")

    # Safeguard: if no scenario, go back to step 1
    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    # Safeguard: HEAD_TO_HEAD needs tournament type
    if tournament_format == "HEAD_TO_HEAD" and (not tournament_type or tournament_type not in TOURNAMENT_TYPE_CONFIG):
        st.warning("⚠️ No tournament type selected. Returning to Step 3.")
        st.session_state["wizard_current_step"] = 3
        st.rerun()
        return

    scenario_config = SCENARIO_CONFIG[scenario]

    if tournament_format == "INDIVIDUAL_RANKING":
        scoring_type = st.session_state.get("wizard_scoring_type_saved", "SCORE_BASED")
        st.info(f"""
**Scenario:** {scenario_config['label']}
**Format:** 🏃 Individual Ranking
**Scoring:** {INDIVIDUAL_SCORING_CONFIG.get(scoring_type, {}).get('label', scoring_type)}
        """)
        type_min_players = 2
    else:
        type_config = TOURNAMENT_TYPE_CONFIG[tournament_type]
        st.info(f"""
**Scenario:** {scenario_config['label']}
**Format:** ⚔️ Head-to-Head
**Tournament Type:** {type_config['label']}
        """)
        type_min_players = type_config["min_players"]

    st.markdown("---")

    min_players = max(scenario_config["min_players"], type_min_players)
    max_players = scenario_config["max_players"]
    default_players = scenario_config["default_player_count"]

    # Get default value from saved state, clamped to valid range
    _saved_count = st.session_state.get("wizard_player_count_saved", max(min_players, default_players))
    default_value = max(min_players, min(max_players, _saved_count))

    player_count = st.slider(
        "Number of players to enroll",
        min_value=min_players,
        max_value=max_players,
        value=default_value,
        step=2,
        key="wizard_player_count_widget",
        help=f"Valid range: {min_players} - {max_players} players"
    )

    st.markdown("---")

    is_valid, errors, warnings, info = validate_step3_detailed()

    st.markdown("### ✅ Validation Results")

    if errors:
        for error in errors:
            st.error(f"❌ {error}")

    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")

    if info:
        for i in info:
            st.success(f"✅ {i}")

    st.session_state["wizard_step3_valid"] = is_valid
    st.session_state["wizard_step3_errors"] = errors

    if is_valid:
        st.session_state["wizard_completed_steps"].add(4)

    st.markdown("---")

    # Back: → Step 4 (Game Preset)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step3_back"):
            st.session_state["wizard_current_step"] = 4
            st.rerun()
    with col2:
        next_enabled = is_valid
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step3_next"):
            st.session_state["wizard_player_count_saved"] = player_count
            st.session_state["wizard_current_step"] = 6
            st.rerun()


def render_step4_simulation_mode():
    """Step 5: Simulation Mode Selection"""
    st.markdown("### Step 6 of 8: Select Simulation Mode")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")
    player_count = st.session_state.get("wizard_player_count_saved")
    scoring_type = st.session_state.get("wizard_scoring_type_saved", "SCORE_BASED")

    # Safeguard: if missing data, go back to appropriate step
    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    if tournament_format == "HEAD_TO_HEAD" and (not tournament_type or tournament_type not in TOURNAMENT_TYPE_CONFIG):
        st.warning("⚠️ No tournament type selected. Returning to Step 3.")
        st.session_state["wizard_current_step"] = 3
        st.rerun()
        return

    if not player_count:
        st.warning("⚠️ No player count selected. Returning to Step 4.")
        st.session_state["wizard_current_step"] = 4
        st.rerun()
        return

    if tournament_format == "INDIVIDUAL_RANKING":
        st.info(f"""
**Scenario:** {SCENARIO_CONFIG[scenario]['label']}
**Format:** 🏃 Individual Ranking
**Scoring:** {INDIVIDUAL_SCORING_CONFIG.get(scoring_type, {}).get('label', scoring_type)}
**Player Count:** {player_count}
        """)
    else:
        st.info(f"""
**Scenario:** {SCENARIO_CONFIG[scenario]['label']}
**Format:** ⚔️ Head-to-Head
**Tournament Type:** {TOURNAMENT_TYPE_CONFIG[tournament_type]['label']}
**Player Count:** {player_count}
        """)

    st.markdown("---")

    sim_options = ["manual", "auto_immediate", "accelerated"]
    default_sim = st.session_state.get("wizard_simulation_mode_saved")
    default_sim_index = 0
    if default_sim in sim_options:
        default_sim_index = sim_options.index(default_sim)

    simulation_mode = st.radio(
        "Choose simulation mode",
        options=sim_options,
        format_func=lambda x: SIMULATION_MODE_CONFIG[x]["label"],
        key="wizard_simulation_mode_widget",
        index=default_sim_index,
        help="Simulation mode determines result generation behavior."
    )

    if simulation_mode:
        config = SIMULATION_MODE_CONFIG[simulation_mode]
        st.info(f"""
**{config['label']}**

{config['description']}

**Use for:** {config['use_case']}
        """)

        st.session_state["wizard_step4_valid"] = True
        st.session_state["wizard_completed_steps"].add(4)
    else:
        st.session_state["wizard_step4_valid"] = False

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step4_back"):
            st.session_state["wizard_current_step"] = 5
            st.rerun()
    with col2:
        next_enabled = st.session_state["wizard_step4_valid"]
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step4_next"):
            st.session_state["wizard_simulation_mode_saved"] = simulation_mode
            st.session_state["wizard_current_step"] = 7
            st.rerun()



def render_step5_review_launch():
    """Step 6: Review Configuration & Launch"""
    st.markdown("### Step 8 of 8: Review Configuration & Launch")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")
    scoring_type = st.session_state.get("wizard_scoring_type_saved")
    player_count = st.session_state.get("wizard_player_count_saved")
    simulation_mode = st.session_state.get("wizard_simulation_mode_saved")

    # Safeguard: if missing data, go back to appropriate step
    if not scenario or scenario not in SCENARIO_CONFIG:
        st.warning("⚠️ No scenario selected. Returning to Step 1.")
        st.session_state["wizard_current_step"] = 1
        st.rerun()
        return

    if tournament_format == "HEAD_TO_HEAD" and (not tournament_type or tournament_type not in TOURNAMENT_TYPE_CONFIG):
        st.warning("⚠️ No tournament type selected. Returning to Step 3.")
        st.session_state["wizard_current_step"] = 3
        st.rerun()
        return

    if not player_count:
        st.warning("⚠️ No player count selected. Returning to Step 5.")
        st.session_state["wizard_current_step"] = 5
        st.rerun()
        return

    if not simulation_mode or simulation_mode not in SIMULATION_MODE_CONFIG:
        st.warning("⚠️ No simulation mode selected. Returning to Step 6.")
        st.session_state["wizard_current_step"] = 6
        st.rerun()
        return

    scenario_config = SCENARIO_CONFIG[scenario]
    sim_config = SIMULATION_MODE_CONFIG[simulation_mode]

    if tournament_format == "INDIVIDUAL_RANKING":
        session_count = player_count  # 1 session per player in individual ranking
        duration_hours = 1.0          # rough estimate
    else:
        session_count = estimate_session_count(tournament_type, player_count)
        duration_hours = estimate_duration_hours(tournament_type, player_count)

    st.markdown("### 📋 TOURNAMENT SUMMARY")

    summary_container = st.container(border=True)
    with summary_container:
        if tournament_format == "INDIVIDUAL_RANKING":
            scoring_cfg = INDIVIDUAL_SCORING_CONFIG.get(scoring_type or "SCORE_BASED", {})
            st.markdown(f"""
**Scenario:** {scenario_config['label']}
**Format:** 🏃 Individual Ranking
**Scoring Method:** {scoring_cfg.get('label', scoring_type)}
**Player Count:** {player_count} players
**Simulation Mode:** {sim_config['label']}

---
            """)
        else:
            type_config = TOURNAMENT_TYPE_CONFIG[tournament_type]
            st.markdown(f"""
**Scenario:** {scenario_config['label']}
**Format:** ⚔️ Head-to-Head
**Tournament Type:** {type_config['label']}
**Player Count:** {player_count} players
**Simulation Mode:** {sim_config['label']}

---
            """)

            if tournament_type == "group_knockout":
                group_config = get_group_knockout_config(player_count)
                if group_config:
                    st.markdown(f"""
**Group Configuration:**
- {group_config['groups']} groups × {group_config['players_per_group']} players each
- Top {group_config['qualifiers']} from each group qualify for knockout
                    """)

        st.markdown(f"""
**Expected Sessions:** ~{session_count}

**Estimated Duration:** ~{duration_hours:.1f} hours

**Results:** {sim_config['description']}
        """)

        # Game preset summary
        game_preset_id = st.session_state.get("wizard_game_preset_saved")
        if game_preset_id is not None:
            st.markdown(f"**Game Preset ID:** `{game_preset_id}`")
        else:
            st.markdown("**Game Preset:** *(none)*")

        # Reward config summary
        reward_cfg = st.session_state.get("wizard_reward_config_saved")
        if reward_cfg:
            fp = reward_cfg.get("first_place", {})
            st.markdown(
                f"**Rewards:** 🥇 {fp.get('xp', '?')} XP / {fp.get('credits', '?')} cr  "
                f"*(and lower tiers)*"
            )
        else:
            st.markdown("**Rewards:** OPS Default  *(auto)*")

    st.markdown("---")

    default_name = (
        st.session_state.get("wizard_tournament_name_saved")
        or generate_default_tournament_name(
            scenario,
            tournament_type or (f"INDIVIDUAL-{scoring_type}" if scoring_type else "INDIVIDUAL"),
            player_count,
        )
    )
    tournament_name = st.text_input(
        "Tournament Name (Optional)",
        value=default_name,
        key="wizard_tournament_name_widget",
        help="Leave default or provide custom name",
        placeholder="Auto-generated if empty"
    )
    # Keep name in sync for execute_launch
    st.session_state["wizard_tournament_name_saved"] = tournament_name

    st.markdown("---")

    requires_confirmation = player_count >= _SAFETY_CONFIRMATION_THRESHOLD

    if requires_confirmation:
        st.warning(f"""
⚠️ **LARGE SCALE OPERATION**

**Player count:** {player_count}
**Expected sessions:** {session_count}
**Estimated duration:** ~{duration_hours:.1f} hours

Type **LAUNCH** below to confirm you want to proceed with this operation.
        """)

        confirm_input = st.text_input(
            "Safety Confirmation",
            key="wizard_safety_confirm_input",
            placeholder="Type LAUNCH to enable the button",
            help="Required for operations with 128+ players"
        )

        safety_confirmed = confirm_input.strip().upper() == "LAUNCH"
        st.session_state["wizard_safety_confirmed"] = safety_confirmed
    else:
        st.info(f"""
Player count: {player_count} (below safety threshold of {_SAFETY_CONFIRMATION_THRESHOLD})
No additional confirmation needed.
        """)
        st.session_state["wizard_safety_confirmed"] = True

    launch_enabled = (
        st.session_state["wizard_safety_confirmed"] and
        not st.session_state.get("wizard_launching", False)
    )

    st.session_state["wizard_launch_enabled"] = launch_enabled

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, disabled=st.session_state.get("wizard_launching", False), key="step5_back"):
            st.session_state["wizard_current_step"] = 7
            st.rerun()

    with col2:
        if st.button(
            "🚀 LAUNCH TOURNAMENT",
            use_container_width=True,
            type="primary",
            disabled=not launch_enabled,
            key="step5_launch"
        ):
            execute_launch()


def render_step_game_preset():
    """Step 4 of 8: Game Preset Selection"""
    st.markdown("### Step 4 of 8: Select Game Preset")
    st.info(
        "Choose a **game preset** to automatically configure which skills this tournament develops. "
        "Select *None* to skip skill configuration entirely."
    )
    st.markdown("---")

    # Fetch presets from API
    @st.cache_data(ttl=60, show_spinner=False)
    def _fetch_presets(token: str) -> list:
        try:
            resp = requests.get(
                f"{API_BASE_URL}/api/v1/game-presets/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else data.get("presets", data.get("items", []))
        except Exception:
            pass
        return []

    token = st.session_state.get("token", "")
    presets = _fetch_presets(token)
    active_presets = [p for p in presets if p.get("is_active", True)]

    # Build options: None first, then each preset
    preset_labels = ["— None (no game preset) —"] + [
        f"{p['name']}  (id={p['id']})" for p in active_presets
    ]
    preset_by_label = {label: preset for label, preset in zip(preset_labels[1:], active_presets)}

    # Restore previous selection
    saved_id = st.session_state.get("wizard_game_preset_saved")
    default_label = "— None (no game preset) —"
    if saved_id is not None:
        for lbl, p in preset_by_label.items():
            if p.get("id") == saved_id:
                default_label = lbl
                break
    default_idx = preset_labels.index(default_label)

    selected_label = st.selectbox(
        "Game Preset",
        options=preset_labels,
        index=default_idx,
        key="wizard_game_preset_widget",
        help="Preset auto-populates skill mappings with the game's skill weights.",
    )

    selected_preset = preset_by_label.get(selected_label)

    # Preview skills
    if selected_preset:
        game_cfg = selected_preset.get("game_config", {})
        skill_cfg = game_cfg.get("skill_config", {})
        skills_tested: list = skill_cfg.get("skills_tested", [])
        skill_weights: dict = skill_cfg.get("skill_weights", {})

        if skills_tested:
            st.success(f"**{selected_preset['name']}** — {len(skills_tested)} skills will be synced:")
            cols = st.columns(min(len(skills_tested), 3))
            for i, skill in enumerate(skills_tested):
                weight = skill_weights.get(skill, 1.0)
                cols[i % 3].metric(skill.replace("_", " ").title(), f"×{weight}")
        elif selected_preset.get("name"):
            st.info(f"**{selected_preset['name']}** selected — no skill config exposed by this preset.")
    else:
        st.caption("No preset selected — tournament will run without automated skill syncing.")

    # Mark step valid (optional step — always valid)
    st.session_state["wizard_step4_valid"] = True
    st.session_state["wizard_completed_steps"].add(4)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="game_preset_back"):
            st.session_state["wizard_current_step"] = 3
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="game_preset_next"):
            st.session_state["wizard_game_preset_saved"] = selected_preset["id"] if selected_preset else None
            st.session_state["wizard_current_step"] = 5
            st.rerun()


def render_step_reward_config():
    """Step 7 of 8: Reward Configuration"""
    st.markdown("### Step 7 of 8: Configure Rewards")
    st.info(
        "Choose a **reward template** or create a custom configuration. "
        "Rewards (XP + Credits) are distributed automatically when the tournament finishes."
    )
    st.markdown("---")

    REWARD_TEMPLATES = {
        "ops_default": {
            "label": "OPS Default  (high XP — ideal for testing)",
            "config": {
                "first_place":   {"xp": 2000, "credits": 1000},
                "second_place":  {"xp": 1200, "credits": 500},
                "third_place":   {"xp": 800,  "credits": 250},
                "participation": {"xp": 100,  "credits": 0},
            },
        },
        "standard": {
            "label": "Standard  (500 / 300 / 200 XP)",
            "config": {
                "first_place":   {"xp": 500, "credits": 100},
                "second_place":  {"xp": 300, "credits": 60},
                "third_place":   {"xp": 200, "credits": 30},
                "participation": {"xp": 50,  "credits": 0},
            },
        },
        "championship": {
            "label": "Championship  (1000 / 600 / 400 XP)",
            "config": {
                "first_place":   {"xp": 1000, "credits": 400},
                "second_place":  {"xp": 600,  "credits": 200},
                "third_place":   {"xp": 400,  "credits": 100},
                "participation": {"xp": 100,  "credits": 0},
            },
        },
        "friendly": {
            "label": "Friendly  (200 / 100 / 50 XP)",
            "config": {
                "first_place":   {"xp": 200, "credits": 50},
                "second_place":  {"xp": 100, "credits": 25},
                "third_place":   {"xp": 50,  "credits": 10},
                "participation": {"xp": 25,  "credits": 0},
            },
        },
        "custom": {
            "label": "Custom  (edit values below)",
            "config": None,
        },
    }

    template_keys = list(REWARD_TEMPLATES.keys())
    template_labels = [REWARD_TEMPLATES[k]["label"] for k in template_keys]

    # Restore previous selection
    saved_config = st.session_state.get("wizard_reward_config_saved")
    default_template_idx = 0  # ops_default

    selected_label = st.radio(
        "Reward Template",
        options=template_labels,
        index=default_template_idx,
        key="wizard_reward_template_widget",
    )

    selected_key = template_keys[template_labels.index(selected_label)]
    template_cfg = REWARD_TEMPLATES[selected_key]["config"]

    if selected_key == "custom":
        st.markdown("#### Custom Reward Values")
        st.caption("Enter XP and Credits per placement tier:")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**XP**")
            xp_1st  = st.number_input("1st Place XP",   min_value=0, value=(saved_config or {}).get("first_place",   {}).get("xp", 1000), step=50, key="wizard_reward_xp1")
            xp_2nd  = st.number_input("2nd Place XP",   min_value=0, value=(saved_config or {}).get("second_place",  {}).get("xp", 600),  step=50, key="wizard_reward_xp2")
            xp_3rd  = st.number_input("3rd Place XP",   min_value=0, value=(saved_config or {}).get("third_place",   {}).get("xp", 400),  step=50, key="wizard_reward_xp3")
            xp_part = st.number_input("Participation XP", min_value=0, value=(saved_config or {}).get("participation",{}).get("xp", 50),  step=10, key="wizard_reward_xp_part")
        with c2:
            st.markdown("**Credits**")
            cr_1st  = st.number_input("1st Place Credits",    min_value=0, value=(saved_config or {}).get("first_place",   {}).get("credits", 200), step=10, key="wizard_reward_cr1")
            cr_2nd  = st.number_input("2nd Place Credits",    min_value=0, value=(saved_config or {}).get("second_place",  {}).get("credits", 100), step=10, key="wizard_reward_cr2")
            cr_3rd  = st.number_input("3rd Place Credits",    min_value=0, value=(saved_config or {}).get("third_place",   {}).get("credits", 50),  step=10, key="wizard_reward_cr3")
            cr_part = st.number_input("Participation Credits", min_value=0, value=(saved_config or {}).get("participation",{}).get("credits", 0),  step=5,  key="wizard_reward_cr_part")

        final_config = {
            "first_place":   {"xp": int(xp_1st),  "credits": int(cr_1st)},
            "second_place":  {"xp": int(xp_2nd),  "credits": int(cr_2nd)},
            "third_place":   {"xp": int(xp_3rd),  "credits": int(cr_3rd)},
            "participation": {"xp": int(xp_part), "credits": int(cr_part)},
        }
    else:
        final_config = template_cfg
        cfg = final_config
        st.markdown("#### Reward Preview")
        tiers = [
            ("🥇 1st Place",     cfg["first_place"]),
            ("🥈 2nd Place",     cfg["second_place"]),
            ("🥉 3rd Place",     cfg["third_place"]),
            ("⚽ Participation", cfg["participation"]),
        ]
        cols = st.columns(4)
        for col, (label, tier) in zip(cols, tiers):
            col.metric(label, f"+{tier['xp']} XP", f"+{tier['credits']} cr")

    st.session_state["wizard_step7_valid"] = True
    st.session_state["wizard_completed_steps"].add(7)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="reward_config_back"):
            st.session_state["wizard_current_step"] = 6
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="reward_config_next"):
            st.session_state["wizard_reward_config_saved"] = final_config
            st.session_state["wizard_current_step"] = 8
            st.rerun()


def render_wizard_progress(current_step: int):
    """Render wizard progress indicator (8 steps)"""
    steps = ["Scenario", "Format", "Type", "Game", "Count", "Simulation", "Reward", "Review"]

    cols = st.columns(8)
    for idx, (col, step_name) in enumerate(zip(cols, steps), start=1):
        with col:
            if idx < current_step:
                st.markdown(f"✅ **{step_name}**")
            elif idx == current_step:
                st.markdown(f"➡️ **{step_name}**")
            else:
                st.markdown(f"⬜ {step_name}")


def render_wizard():
    """Main wizard renderer — 8-step flow with format-aware routing.

    Step 1: Scenario
    Step 2: Format (HEAD_TO_HEAD vs INDIVIDUAL_RANKING)
    Step 3: HEAD_TO_HEAD → Tournament Type  |  INDIVIDUAL_RANKING → Scoring Method
    Step 4: Game Preset (GānFootvolley, GānFoottennis, Custom…)
    Step 5: Player Count
    Step 6: Simulation Mode
    Step 7: Reward Configuration
    Step 8: Review & Launch
    """
    init_wizard_state()

    current_step = st.session_state["wizard_current_step"]

    render_wizard_progress(current_step)

    st.markdown("---")

    if current_step == 1:
        render_step1_scenario()
    elif current_step == 2:
        render_step2_format()
    elif current_step == 3:
        fmt = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
        if fmt == "INDIVIDUAL_RANKING":
            render_step3_individual_scoring()
        else:
            render_step2_tournament_type()
    elif current_step == 4:
        render_step_game_preset()
    elif current_step == 5:
        render_step3_player_count()
    elif current_step == 6:
        render_step4_simulation_mode()
    elif current_step == 7:
        render_step_reward_config()
    elif current_step == 8:
        render_step5_review_launch()
    else:
        st.error(f"Invalid wizard step: {current_step}")
        st.session_state["wizard_current_step"] = 1
        st.rerun()


# ── Monitor Panel Sub-renderers ──────────────────────────────────────────────







def _render_tournament_card(token: str, tournament: Dict[str, Any]) -> None:
    """Render a full monitoring card for one test tournament with phase tracking."""
    tid = tournament.get("id") or tournament.get("tournament_id")
    name = tournament.get("name", f"Tournament {tid}")

    ok_detail, _, fresh = get_tournament_detail(token, tid)
    if ok_detail and fresh:
        status = fresh.get("status", tournament.get("status", "UNKNOWN"))
        enrolled = fresh.get("enrolled_count", fresh.get("participant_count", "?"))
    else:
        status = tournament.get("status", "UNKNOWN")
        enrolled = tournament.get("enrolled_count", tournament.get("participant_count", "?"))

    colour = _STATUS_COLOURS.get(status, "#9ca3af")

    ok_sessions, _, sessions = get_tournament_sessions(token, tid)
    ok_campuses, _, campus_cfg = get_campus_schedules(token, tid)
    ok_rankings, _, rankings = get_tournament_rankings(token, tid)

    sessions = sessions if (ok_sessions and isinstance(sessions, list)) else []
    campus_cfg = campus_cfg if (ok_campuses and isinstance(campus_cfg, list)) else []
    rankings = rankings if (ok_rankings and isinstance(rankings, list)) else []

    total_sessions = len(sessions)
    done_sessions = sum(1 for s in sessions if s.get("result_submitted"))

    # Phase tracking
    phases_present = set(s.get("tournament_phase") for s in sessions if s.get("tournament_phase"))
    phase_progress = {}

    for phase in phases_present:
        phase_sessions = [s for s in sessions if s.get("tournament_phase") == phase]
        phase_done = sum(1 for s in phase_sessions if s.get("result_submitted"))
        phase_total = len(phase_sessions)
        phase_progress[phase] = {
            "done": phase_done,
            "total": phase_total,
            "pct": (phase_done / phase_total * 100) if phase_total else 0
        }

    with st.expander(
        f"🔴 {name}  ·  {status}  ·  {done_sessions}/{total_sessions} submitted",
        expanded=True,
    ):
        # Overall metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Status", status)
        m2.metric("Enrolled", enrolled)
        m3.metric("Total Sessions", total_sessions)
        m4.metric("Submitted", done_sessions)

        st.markdown(_progress_bar(done_sessions, total_sessions), unsafe_allow_html=True)
        st.markdown("---")

        # Phase summary badges (compact row)
        if phase_progress:
            _phase_order_list = ["INDIVIDUAL_RANKING", "GROUP_STAGE", "KNOCKOUT", "FINALS", "PLACEMENT"]
            sorted_phases = sorted(
                phase_progress.keys(),
                key=lambda p: _phase_order_list.index(p) if p in _phase_order_list else 99
            )
            badge_cols = st.columns(len(sorted_phases))
            for idx, phase in enumerate(sorted_phases):
                prog = phase_progress[phase]
                icon = _phase_icon(phase)
                lbl = _phase_label_short(phase)
                done_flag = prog["done"] == prog["total"]
                badge_icon = "✅" if done_flag else "⏳"
                badge_cols[idx].metric(
                    f"{icon} {lbl}",
                    f"{prog['done']}/{prog['total']}",
                    delta=f"{prog['pct']:.0f}%",
                )

            # GROUP_STAGE: per-group breakdown
            if "GROUP_STAGE" in phase_progress:
                gs_sessions = [s for s in sessions if s.get("tournament_phase") == "GROUP_STAGE"]
                groups_seen: Dict[Any, dict] = {}
                for s in gs_sessions:
                    gid = s.get("group_identifier")
                    if gid is None:
                        continue
                    if gid not in groups_seen:
                        groups_seen[gid] = {"done": 0, "total": 0}
                    groups_seen[gid]["total"] += 1
                    if s.get("result_submitted"):
                        groups_seen[gid]["done"] += 1

                if len(groups_seen) > 1:
                    st.caption("**Groups:**")
                    g_cols = st.columns(min(len(groups_seen), 8))
                    for i, (gid, gdata) in enumerate(sorted(groups_seen.items(), key=lambda x: str(x[0]))):
                        gicon = "✅" if gdata["done"] == gdata["total"] else "⏳"
                        g_cols[i % len(g_cols)].metric(
                            f"G{gid}",
                            f"{gdata['done']}/{gdata['total']}",
                            delta=gicon,
                        )

            st.markdown("---")

        # Match Grid (full width) with phase separation
        st.subheader("Tournament Phases")
        st.caption("Each phase displayed as a separate logical unit with parallel campuses.")
        render_campus_grid(sessions, campus_cfg, rankings)

        # Manual result entry (shown when there are pending sessions)
        render_manual_result_entry(token, tid, sessions)

        # Auto-refresh rankings when all sessions are submitted
        has_knockout = any(s.get("tournament_phase") == "KNOCKOUT" for s in sessions)
        knockout_sessions = [s for s in sessions if s.get("tournament_phase") == "KNOCKOUT"]
        all_submitted = total_sessions > 0 and done_sessions == total_sessions
        knockout_complete = has_knockout and knockout_sessions and all(s.get("result_submitted") for s in knockout_sessions)

        # When all sessions are done and tournament is still IN_PROGRESS → auto-finalize
        if all_submitted and status == "IN_PROGRESS":
            try:
                _fin_resp = requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/finalize-tournament",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30,
                )
                if _fin_resp.status_code == 200:
                    ok_detail2, _, fresh2 = get_tournament_detail(token, tid)
                    if ok_detail2 and fresh2:
                        status = fresh2.get("status", status)
            except Exception:
                pass

        # Only call calculate-rankings while still IN_PROGRESS (intermediate refresh).
        # After finalization (COMPLETED/REWARDS_DISTRIBUTED) rankings are already correct.
        if (knockout_complete or all_submitted) and status == "IN_PROGRESS":
            try:
                requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tid}/calculate-rankings",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
            except Exception:
                pass

        ok_rankings2, _, rankings2 = get_tournament_rankings(token, tid)
        if ok_rankings2 and isinstance(rankings2, list) and rankings2:
            rankings = rankings2

        st.subheader("Leaderboard")
        render_leaderboard(rankings, status=status, has_knockout=has_knockout)


# ── Public Entry Point ───────────────────────────────────────────────────────

def render_tournament_monitor(token: str) -> None:
    """Main render function for the OPS Test Observability Platform."""

    # E2E test support: auto-track a specific tournament via ?track_id=N URL param.
    # This allows headless tests to navigate directly to a tournament's monitoring card
    # without going through the OPS Wizard flow.
    _auto_track = st.query_params.get("track_id")
    if _auto_track:
        try:
            _auto_id = int(_auto_track)
            if "_ops_tracked_tournaments" not in st.session_state:
                st.session_state["_ops_tracked_tournaments"] = []
            if _auto_id not in st.session_state["_ops_tracked_tournaments"]:
                st.session_state["_ops_tracked_tournaments"].append(_auto_id)
        except (ValueError, TypeError):
            pass

    with st.sidebar:
        st.markdown("## 🚀 OPS WIZARD")
        st.caption("Launch a new test tournament")

        render_wizard()

        st.markdown("---")
        st.markdown("## ⚙️ MONITORING CONTROLS")
        st.caption("Live tracking of OPS test tournaments")

        # Initialize tracked tournaments list
        if "_ops_tracked_tournaments" not in st.session_state:
            st.session_state["_ops_tracked_tournaments"] = []

        # Fetch OPS tournaments only
        ok, err, all_tournaments = get_all_tournaments_admin(token)
        if not ok:
            st.error(f"Cannot load tournaments: {err}")
            all_tournaments = []

        # Filter: ONLY OPS tournaments (name starts with "OPS-")
        ops_tournaments = [
            t for t in all_tournaments
            if t.get('name', '').startswith('OPS-')
        ]

        # Further filter: IN_PROGRESS + recent COMPLETED/REWARDS_DISTRIBUTED (last 5)
        active_ops = [t for t in ops_tournaments if t.get("status") == "IN_PROGRESS"]
        completed_ops = [t for t in ops_tournaments if t.get("status") in ("COMPLETED", "REWARDS_DISTRIBUTED")]
        completed_ops = sorted(completed_ops, key=lambda x: x.get("id", 0), reverse=True)[:5]

        visible_ops = active_ops + completed_ops

        # Auto-track tournaments from session state
        tracked_ids = st.session_state["_ops_tracked_tournaments"]
        tracked_tournaments = [t for t in visible_ops if (t.get("id") or t.get("tournament_id")) in tracked_ids]

        # Display tracked tournaments count
        st.metric("Tracked Tests", len(tracked_tournaments))

        # Show tracked tournaments list
        if tracked_tournaments:
            st.markdown("**Active Tests:**")
            for t in tracked_tournaments:
                tid = t.get("id") or t.get("tournament_id")
                name = t.get("name", f"T{tid}")
                status = t.get("status", "UNKNOWN")

                status_icon = {
                    "IN_PROGRESS":         "🟢",
                    "COMPLETED":           "⚫",
                    "REWARDS_DISTRIBUTED": "🎁",
                    "DRAFT":               "🟡",
                }.get(status, "")

                # Extract readable name
                clean_name = name
                if name.startswith("OPS-"):
                    parts = name.split("-")
                    if len(parts) >= 4:
                        # OPS-SCENARIO-TYPE-16p-TIMESTAMP → SCENARIO-TYPE-16p
                        clean_name = "-".join(parts[1:4])

                st.caption(f"{status_icon} {clean_name}")

            # Clear all button
            if st.button("🗑️ Clear All Tracked Tests", use_container_width=True):
                st.session_state["_ops_tracked_tournaments"] = []
                st.rerun()
        else:
            st.info("No tests currently tracked.\n\nLaunch a test using the wizard above to start tracking.")

        st.markdown("---")

        # Auto-refresh controls
        # Always sanitize before slider to avoid stale/out-of-range values
        _stored = st.session_state.get("monitor_refresh_sec", _DEFAULT_REFRESH_SECONDS)
        if not isinstance(_stored, (int, float)) or not (_MIN_REFRESH <= _stored <= _MAX_REFRESH):
            st.session_state["monitor_refresh_sec"] = _DEFAULT_REFRESH_SECONDS
        refresh_sec = st.slider(
            "Auto-refresh (seconds)",
            min_value=_MIN_REFRESH,
            max_value=_MAX_REFRESH,
            value=_DEFAULT_REFRESH_SECONDS,
            step=5,
            key="monitor_refresh_sec",
        )

        if st.button("🔄 Refresh now", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.caption(f"Last refresh: {time.strftime('%H:%M:%S')}")

    # Main area: Show tracked tournaments
    if not tracked_tournaments:
        st.info("""
## 🎯 OPS Test Observability Platform

**No active test tournaments to track.**

### How to start:

1. Use the **OPS Wizard** in the sidebar to launch a new test tournament
2. After launch, the test will **automatically appear** in the live tracking view
3. Monitor real-time execution with auto-refresh

### What you'll see:
- ✅ Session progress (group stage, knockout, finals)
- 🏆 Live leaderboards
- 📊 Match results and phase transitions
- ⏱️ Real-time status updates

**Launch a test to begin observability.**
        """)
        return

    # Fragment: Auto-refresh tracked tournaments (always enabled, interval from slider)
    @st.fragment(run_every=int(refresh_sec))
    def _cards_fragment() -> None:
        st.markdown("## 🔴 LIVE TEST TRACKING")
        st.caption(f"Monitoring {len(tracked_tournaments)} active test tournament(s)")
        st.markdown("---")

        for tournament in tracked_tournaments:
            _render_tournament_card(token, tournament)
            st.markdown("---")

        st.caption(f"Data refreshed: {time.strftime('%H:%M:%S')}")

    _cards_fragment()
