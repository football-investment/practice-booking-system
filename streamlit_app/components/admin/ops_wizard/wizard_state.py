"""
OPS Wizard State Management

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Handles wizard session state initialization and reset.
"""

import time
import streamlit as st


def init_wizard_state():
    """Initialize wizard session state"""
    if "wizard_current_step" not in st.session_state:
        st.session_state["wizard_current_step"] = 1

    if "wizard_completed_steps" not in st.session_state:
        st.session_state["wizard_completed_steps"] = set()

    if "wizard_navigation_locked" not in st.session_state:
        st.session_state["wizard_navigation_locked"] = False

    # Step validity flags (8 steps)
    for step in range(1, 9):
        key = f"wizard_step{step}_valid"
        if key not in st.session_state:
            st.session_state[key] = False

    # Launch state
    if "wizard_launching" not in st.session_state:
        st.session_state["wizard_launching"] = False

    if "wizard_initialized" not in st.session_state:
        st.session_state["wizard_initialized"] = True
        st.session_state["wizard_last_modified"] = time.time()


def reset_wizard_state():
    """Reset wizard to initial state (after successful launch)"""
    keys_to_clear = [
        # Legacy widget-bound keys (no longer used but clear just in case)
        "wizard_scenario",
        "wizard_tournament_type",
        "wizard_player_count",
        "wizard_simulation_mode",
        "wizard_tournament_name",
        "wizard_safety_confirm_input",
        # Widget keys (suffixed _widget)
        "wizard_scenario_widget",
        "wizard_format_widget",
        "wizard_tournament_type_widget",
        "wizard_scoring_type_widget",
        "wizard_player_count_widget",
        "wizard_simulation_mode_widget",
        "wizard_tournament_name_widget",
        "wizard_game_preset_widget",
        "wizard_reward_template_widget",
        # Persistent saved values (suffixed _saved)
        "wizard_scenario_saved",
        "wizard_format_saved",
        "wizard_tournament_type_saved",
        "wizard_scoring_type_saved",
        "wizard_ranking_direction_saved",
        "wizard_player_count_saved",
        "wizard_simulation_mode_saved",
        "wizard_tournament_name_saved",
        "wizard_game_preset_saved",
        "wizard_reward_config_saved",
        # Validity flags
        "wizard_completed_steps",
        "wizard_step1_valid",
        "wizard_step2_valid",
        "wizard_step3_valid",
        "wizard_step4_valid",
        "wizard_step5_valid",
        "wizard_step6_valid",
        "wizard_step7_valid",
        "wizard_step8_valid",
        "wizard_step3_errors",
        "wizard_safety_confirmed",
        "wizard_launch_enabled",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state["wizard_current_step"] = 1
    st.session_state["wizard_completed_steps"] = set()
    st.session_state["wizard_last_modified"] = time.time()
