"""OPS Wizard — Step 1: Scenario Selection"""
import streamlit as st
from ..wizard_config import SCENARIO_CONFIG


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
            st.session_state["wizard_scenario_saved"] = scenario
            st.session_state["wizard_current_step"] = 2
            st.rerun()
