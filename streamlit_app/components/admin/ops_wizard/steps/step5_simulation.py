"""OPS Wizard — Step 5/6: Simulation Mode Selection"""
import streamlit as st
from ..wizard_config import (
    SCENARIO_CONFIG,
    TOURNAMENT_TYPE_CONFIG,
    SIMULATION_MODE_CONFIG,
    scoring_label,
)


def render_step4_simulation_mode():
    """Step 5: Simulation Mode Selection"""
    st.markdown("### Step 6 of 8: Select Simulation Mode")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")
    player_count = st.session_state.get("wizard_player_count_saved")
    scoring_type = st.session_state.get("wizard_scoring_type_saved", "SCORE_BASED")
    ranking_direction = st.session_state.get("wizard_ranking_direction_saved")

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
**Scoring:** {scoring_label(scoring_type, ranking_direction)}
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
