"""OPS Wizard — Step 2: Format Selection (HEAD_TO_HEAD vs INDIVIDUAL_RANKING)"""
import streamlit as st
from ..wizard_config import SCENARIO_CONFIG, FORMAT_CONFIG


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
