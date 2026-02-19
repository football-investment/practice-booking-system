"""
OPS Wizard Tournament Launch

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Executes tournament launch and auto-tracks the new tournament.
"""

import time
import streamlit as st

# Import API helpers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from api_helpers_monitor import trigger_ops_scenario

# Import wizard state management
from .wizard_state import reset_wizard_state


def execute_launch():
    """Execute tournament launch and auto-track"""
    st.session_state["wizard_launching"] = True

    scenario = st.session_state["wizard_scenario_saved"]
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")  # None for INDIVIDUAL_RANKING
    scoring_type = st.session_state.get("wizard_scoring_type_saved")
    ranking_direction = st.session_state.get("wizard_ranking_direction_saved")
    player_count = st.session_state["wizard_player_count_saved"]
    simulation_mode = st.session_state["wizard_simulation_mode_saved"]
    tournament_name = st.session_state.get("wizard_tournament_name_saved", "").strip() or None
    game_preset_id = st.session_state.get("wizard_game_preset_saved")  # int or None
    reward_config = st.session_state.get("wizard_reward_config_saved")  # dict or None
    number_of_rounds = st.session_state.get("wizard_num_rounds_saved")  # int or None (IR only)
    player_ids = st.session_state.get("wizard_player_ids_saved") or None  # List[int] or None
    campus_ids = st.session_state.get("wizard_campus_ids_saved") or None  # List[int] or None

    with st.spinner("🚀 Launching test tournament..."):
        token = st.session_state.get("token")

        ok, err, data = trigger_ops_scenario(
            token=token,
            scenario=scenario,
            player_count=player_count,
            tournament_type_code=tournament_type,
            tournament_format=tournament_format,
            scoring_type=scoring_type,
            ranking_direction=ranking_direction,
            tournament_name=tournament_name,
            dry_run=False,
            confirmed=True,
            simulation_mode=simulation_mode,
            game_preset_id=game_preset_id,
            reward_config=reward_config,
            number_of_rounds=number_of_rounds,
            player_ids=player_ids,
            campus_ids=campus_ids,
        )

        st.session_state["wizard_launching"] = False

        if ok:
            new_tournament_id = data.get("tournament_id")
            enrolled_count = data.get("enrolled_count", 0)
            session_count = data.get("session_count", 0)

            # Auto-track the new tournament
            if "_ops_tracked_tournaments" not in st.session_state:
                st.session_state["_ops_tracked_tournaments"] = []

            if new_tournament_id not in st.session_state["_ops_tracked_tournaments"]:
                st.session_state["_ops_tracked_tournaments"].append(new_tournament_id)

            # Save launch result — wizard will show success screen until user starts a new one
            st.session_state["wizard_launch_result"] = {
                "tournament_id": new_tournament_id,
                "enrolled_count": enrolled_count,
                "session_count": session_count,
                # snapshot of what was launched
                "scenario": scenario,
                "tournament_format": tournament_format,
                "tournament_type": tournament_type,
                "scoring_type": scoring_type,
                "player_count": player_count,
                "player_ids": player_ids,
                "simulation_mode": simulation_mode,
                "game_preset_id": game_preset_id,
                "tournament_name": tournament_name,
            }

            reset_wizard_state()

            # Clear URL param (we're using session state tracking now)
            if "selected_id" in st.query_params:
                del st.query_params["selected_id"]

            st.toast(f"✅ Tournament #{new_tournament_id} launched!", icon="🚀")
            st.rerun()
        else:
            st.error(f"❌ Launch failed: {err}")
            st.session_state["wizard_launching"] = False
