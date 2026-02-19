"""OPS Wizard — Step 3b: Tournament Type Selection (HEAD_TO_HEAD path)"""
import streamlit as st
from ..wizard_config import SCENARIO_CONFIG, TOURNAMENT_TYPE_CONFIG
from streamlit_app.api_helpers_general import get_locations, get_campuses_by_location


def _render_campus_selector(token: str) -> bool:
    """
    Location → campus cascade selector.
    Returns True if at least 1 campus is selected (step valid).
    """
    st.markdown("---")
    st.subheader("Location & Venues")

    ok, locations = get_locations(token, include_inactive=False)
    if not ok or not locations:
        st.error("Failed to load locations.")
        return False

    location_options = {
        loc["id"]: f"{loc.get('city', loc.get('name', str(loc['id'])))} ({loc.get('location_code', '')})"
        for loc in locations
    }

    saved_location = st.session_state.get("wizard_location_id_saved")
    loc_keys = list(location_options.keys())
    default_idx = loc_keys.index(saved_location) if saved_location in loc_keys else 0

    selected_location_id = st.selectbox(
        "Location (city) *",
        options=loc_keys,
        format_func=lambda lid: location_options[lid],
        index=default_idx,
        key="wizard_location_id_widget",
        help="City / location where the tournament is held.",
    )
    st.session_state["wizard_location_id_saved"] = selected_location_id

    ok2, campuses = get_campuses_by_location(token, selected_location_id, include_inactive=False)
    if not ok2 or not campuses:
        st.warning("No active campuses at this location.")
        return False

    campus_options = {c["id"]: f"{c['name']} ({c.get('venue', '-')})" for c in campuses}
    saved_ids = [cid for cid in st.session_state.get("wizard_campus_ids_saved", []) if cid in campus_options]

    selected_campus_ids = st.multiselect(
        "Venues / Campuses *",
        options=list(campus_options.keys()),
        default=saved_ids,
        format_func=lambda cid: campus_options[cid],
        key="wizard_campus_ids_widget",
        help="Select at least 1 campus. Multiple campuses → sessions assigned round-robin.",
    )
    st.session_state["wizard_campus_ids_saved"] = selected_campus_ids
    st.session_state["wizard_campus_labels_saved"] = [campus_options[cid] for cid in selected_campus_ids]

    if not selected_campus_ids:
        st.error("At least 1 campus must be selected.")
        return False

    st.success(f"✅ {len(selected_campus_ids)} campus(es) selected.")
    return True


def render_step3_h2h(token: str = None):
    """Step 3 (HEAD_TO_HEAD): Tournament Type Selection"""
    if token is None:
        token = st.session_state.get("token", "")
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

    # ── Campus / venue selection (required) ──────────────────────────────────
    campus_valid = _render_campus_selector(token)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="step2_back"):
            st.session_state["wizard_current_step"] = 2
            st.rerun()
    with col2:
        next_enabled = st.session_state["wizard_step2_valid"] and campus_valid
        if st.button("Next →", disabled=not next_enabled, use_container_width=True, key="step2_next"):
            st.session_state["wizard_tournament_type_saved"] = tournament_type
            st.session_state["wizard_current_step"] = 4
            st.rerun()
