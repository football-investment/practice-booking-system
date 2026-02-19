"""OPS Wizard — Step 8: Review Configuration & Launch"""
import streamlit as st
from ..wizard_config import (
    SCENARIO_CONFIG,
    TOURNAMENT_TYPE_CONFIG,
    SIMULATION_MODE_CONFIG,
    _SAFETY_CONFIRMATION_THRESHOLD,
    scoring_label,
    get_group_knockout_config,
    estimate_session_count,
    estimate_duration_hours,
    generate_default_tournament_name,
)
from ..launch import execute_launch


def render_step5_review_launch():
    """Step 8: Review Configuration & Launch"""
    st.markdown("### Step 8 of 8: Review Configuration & Launch")
    st.markdown("---")

    scenario = st.session_state.get("wizard_scenario_saved")
    tournament_format = st.session_state.get("wizard_format_saved", "HEAD_TO_HEAD")
    tournament_type = st.session_state.get("wizard_tournament_type_saved")
    scoring_type = st.session_state.get("wizard_scoring_type_saved")
    player_count = st.session_state.get("wizard_player_count_saved")
    simulation_mode = st.session_state.get("wizard_simulation_mode_saved")

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
    ranking_direction = st.session_state.get("wizard_ranking_direction_saved")

    if tournament_format == "INDIVIDUAL_RANKING":
        session_count = player_count
        duration_hours = 1.0
    else:
        session_count = estimate_session_count(tournament_type, player_count)
        duration_hours = estimate_duration_hours(tournament_type, player_count)

    st.markdown("### 📋 TOURNAMENT SUMMARY")

    campus_ids = st.session_state.get("wizard_campus_ids_saved", [])
    campus_labels = st.session_state.get("wizard_campus_labels_saved", [])
    campus_summary = ", ".join(campus_labels) if campus_labels else (f"{len(campus_ids)} campus(es)" if campus_ids else "Not set")

    summary_container = st.container(border=True)
    with summary_container:
        if tournament_format == "INDIVIDUAL_RANKING":
            st.markdown(f"""
**Scenario:** {scenario_config['label']}
**Format:** 🏃 Individual Ranking
**Scoring Method:** {scoring_label(scoring_type, ranking_direction)}
**Player Count:** {player_count} players
**Simulation Mode:** {sim_config['label']}
**Venues:** {campus_summary}

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
**Venues:** {campus_summary}

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

        game_preset_id = st.session_state.get("wizard_game_preset_saved")
        if game_preset_id is not None:
            st.markdown(f"**Game Preset ID:** `{game_preset_id}`")
        else:
            st.markdown("**Game Preset:** *(none)*")

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
