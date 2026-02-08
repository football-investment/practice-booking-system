"""
Sandbox Tournament Test - Admin-Aligned UI (V3) - REFACTORED

Complete restructure using streamlit_components library:
- SingleColumnForm for all forms
- api_client for all API calls
- Card components for content grouping
- data-testid attributes for E2E testing

Run: streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8502
"""

import streamlit as st
import time
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date

# Configure logging for Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Component library imports
from streamlit_components.core import api_client, auth
from streamlit_components.layouts import SingleColumnForm, Card, InfoCard
from streamlit_components.feedback import Loading, Success, Error

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from app.skills_config import SKILL_CATEGORIES as REAL_SKILL_CATEGORIES
from sandbox_helpers import (
    fetch_locations, fetch_campuses_by_location, fetch_users, fetch_instructors,
    fetch_game_presets, fetch_preset_details, update_preset, create_preset,
    create_game_preset,
    render_mini_leaderboard, get_sandbox_tournaments, calculate_tournament_stats
)
from sandbox_workflow import (
    render_step_create_tournament,
    render_step_manage_sessions,
    render_step_track_attendance,
    render_step_enter_results,
    render_step_view_leaderboard,
    render_step_distribute_rewards,
    render_step_view_rewards
)

# Constants
AGE_GROUPS = ["PRE", "YOUTH", "AMATEUR", "PRO"]
ASSIGNMENT_TYPES = ["OPEN_ASSIGNMENT", "MANUAL_ASSIGNMENT", "INVITE_ONLY"]
TOURNAMENT_FORMATS = ["league", "knockout", "group_knockout"]  # group_knockout = hybrid format (group stage + knockout playoffs)
SCORING_MODES = ["HEAD_TO_HEAD", "INDIVIDUAL"]

# Convert skill categories to display format
SKILL_CATEGORIES = {}
for category in REAL_SKILL_CATEGORIES:
    category_name = f"{category['emoji']} {category['name_en']}"
    SKILL_CATEGORIES[category_name] = [skill['key'] for skill in category['skills']]

# Page config
st.set_page_config(
    page_title="Sandbox Tournament Test (Admin-Aligned)",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Session state cleanup for terminology refactor
# Clear old config keys if they exist (FORMATS, format, tournament_type)
if 'config' in st.session_state:
    config = st.session_state['config']
    if isinstance(config, dict):
        # Check if using old terminology
        if 'format' in config or 'tournament_type' in config:
            # Clear entire config to force fresh start
            del st.session_state['config']
            st.rerun()


# ===========================================================================
# NAVIGATION HELPER: Update URL when navigating
# ===========================================================================
def update_url_params(screen: str = None, tournament_id: int = None, step: int = None):
    """
    Update URL query parameters to reflect current navigation state.
    Enables deep linking and page reload recovery.

    Args:
        screen: Screen name (home, history, configuration, instructor_workflow)
        tournament_id: Tournament ID (optional)
        step: Workflow step number (optional, only for instructor_workflow)
    """
    params = {}

    if screen:
        params["screen"] = screen

    if tournament_id is not None:
        params["tournament_id"] = str(tournament_id)

    if step is not None:
        params["step"] = str(step)

    # Only update if params have changed
    current_params = dict(st.query_params)
    if params != current_params:
        st.query_params.update(params)


def render_home_screen():
    """Home dashboard - starting point"""
    st.title("Tournament Sandbox - Home", anchor=False)

    # Auto-login if no token
    if not auth.is_authenticated():
        with Loading.spinner("Auto-authenticating as admin..."):
            if auth.login("admin@lfa.com", "admin123"):
                Success.toast("Authenticated!")
                time.sleep(0.5)
                st.rerun()
            else:
                Error.message("Authentication failed. Please check API server.")
                st.stop()

    st.markdown("### Welcome to the Tournament Testing Sandbox")
    st.markdown("Choose an option to get started:")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        card = Card(
            title="View Tournament History",
            subtitle="Browse past tournaments, view results, and export data",
            card_id="history_card"
        )
        with card.container():
            if st.button(
                "Open History",
                type="primary",
                use_container_width=True,
                key="btn_open_history"
            ):
                st.session_state.screen = "history"
                update_url_params(screen="history")
                st.rerun()
        card.close_container()

    with col2:
        card = Card(
            title="Create New Tournament",
            subtitle="Start the instructor workflow to create and manage a tournament",
            card_id="create_card"
        )
        with card.container():
            if st.button(
                "New Tournament",
                type="primary",
                use_container_width=True,
                key="btn_new_tournament"
            ):
                st.session_state.screen = "configuration"
                st.rerun()
        card.close_container()

    st.markdown("---")

    # Quick stats
    sandbox_tournaments = get_sandbox_tournaments()
    stats = calculate_tournament_stats(sandbox_tournaments)

    st.markdown("### Quick Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sandbox Tournaments", stats['total'])
    with col2:
        st.metric("Completed", stats['completed'])
    with col3:
        st.metric("In Progress", stats['in_progress'])


def render_configuration_screen():
    """Tournament configuration screen with game preset selection"""
    st.title("Sandbox Tournament Test (Admin-Aligned)", anchor=False)

    # ===================================================================
    # TEMPLATE MANAGEMENT FUNCTIONS
    # ===================================================================

    def get_templates() -> Dict[str, Dict]:
        """Get all saved templates from session state"""
        if 'templates' not in st.session_state:
            st.session_state['templates'] = {}
        return st.session_state['templates']

    def save_template(template_name: str, config: Dict):
        """Save tournament config as template"""
        templates = get_templates()
        templates[template_name] = {
            'name': template_name,
            'created_at': datetime.now().isoformat(),
            'config': config
        }
        st.session_state['templates'] = templates

    def load_template(template_name: str) -> Dict:
        """Load template config"""
        templates = get_templates()
        template = templates.get(template_name)
        return template['config'] if template else {}

    def delete_template(template_name: str):
        """Delete template"""
        templates = get_templates()
        if template_name in templates:
            del templates[template_name]
            st.session_state['templates'] = templates

    def list_template_names() -> list:
        """Get list of template names sorted by creation date (newest first)"""
        templates = get_templates()
        return sorted(templates.keys(),
                      key=lambda name: templates[name]['created_at'],
                      reverse=True)

    # Authentication check
    if not auth.is_authenticated():
        st.info("Admin Login Required")
        form = SingleColumnForm("login_form", title="Authenticate")
        with form.container():
            email = st.text_input(
                "Admin Email",
                value="admin@lfa.com",
                key="input_admin_email"
            )
            password = st.text_input(
                "Password",
                value="admin123",
                type="password",
                key="input_admin_password"
            )

            if st.button(
                "Authenticate",
                type="primary",
                use_container_width=True,
                key="btn_authenticate"
            ):
                if auth.login(email, password):
                    Success.message("Authenticated!")
                    st.rerun()
        st.stop()

    st.markdown("---")
    st.session_state.test_mode = "instructor"
    st.info("Instructor Workflow: Manually manage sessions, track attendance, enter results, and view live leaderboard before final rewards.")
    st.markdown("---")

    # Import preset forms module for game preset management
    from streamlit_preset_forms import (
        render_basic_info_editor, render_skill_config_editor,
        render_match_simulation_editor, render_ranking_rules_editor,
        render_metadata_editor, render_simulation_config_editor
    )

    # === GAME TYPE SELECTION (PRESET-BASED) ===
    st.markdown("### Game Type Selection")

    presets = fetch_game_presets()
    if not presets:
        Error.message("No game presets available. Please contact administrator.")
        st.stop()

    # Sort presets
    sorted_presets = sorted(presets, key=lambda x: (not x.get('is_recommended', False), x['name']))

    # Initialize session state
    if 'selected_preset_id' not in st.session_state:
        st.session_state.selected_preset_id = sorted_presets[0]['id']
    if 'editing_preset_id' not in st.session_state:
        st.session_state.editing_preset_id = None
    if 'creating_preset' not in st.session_state:
        st.session_state.creating_preset = False

    # Header with create button
    col_header, col_create = st.columns([3, 1])
    with col_header:
        st.markdown("**Available Game Types:**")
    with col_create:
        if st.button(
            "Create New Preset",
            key="btn_create_preset"
        ):
            st.session_state.creating_preset = True
            st.session_state.editing_preset_id = None
            st.rerun()

    # CREATE NEW PRESET FORM (collapsed for brevity - uses existing preset forms)
    if st.session_state.creating_preset:
        _render_preset_create_form(render_basic_info_editor, render_skill_config_editor,
                                   render_match_simulation_editor, render_ranking_rules_editor,
                                   render_metadata_editor, render_simulation_config_editor)

    # PRESET LIST
    for preset in sorted_presets:
        _render_preset_list_item(preset, render_basic_info_editor, render_skill_config_editor,
                                render_match_simulation_editor, render_ranking_rules_editor,
                                render_metadata_editor, render_simulation_config_editor)

    st.markdown("---")

    # === TOURNAMENT TEMPLATES ===
    st.markdown("### 📋 Tournament Templates")

    template_names = list_template_names()

    if not template_names:
        st.info("⚠️ No saved templates. Templates are stored in this browser session only and will be lost on refresh.")
        st.caption("Fill out the form below and save it as a template for quick reuse.")
    else:
        st.info("⚠️ Templates are stored in this browser session only and will be lost on refresh.")

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            selected_template = st.selectbox(
                "Select a template to load",
                options=["(None - Start Fresh)", *template_names],
                key="template_selector",
                help="Choose a saved template to auto-fill the configuration form"
            )

        with col2:
            load_disabled = selected_template == "(None - Start Fresh)"
            if st.button(
                "Load Template",
                disabled=load_disabled,
                key="btn_load_template",
                use_container_width=True,
                type="primary"
            ):
                config = load_template(selected_template)
                st.session_state['loaded_template_config'] = config
                Success.toast(f"Template '{selected_template}' loaded!")
                st.rerun()

        with col3:
            if st.button(
                "Manage",
                key="btn_manage_templates",
                use_container_width=True
            ):
                st.session_state['show_manage_templates'] = True
                st.rerun()

    # MANAGE TEMPLATES DIALOG
    if st.session_state.get('show_manage_templates', False):
        @st.dialog("📋 Manage Templates", width="large")
        def manage_templates_dialog():
            st.markdown("View and manage your saved tournament templates.")

            templates = get_templates()
            template_names_list = list_template_names()

            if not template_names_list:
                st.info("No templates saved yet.")
            else:
                st.markdown(f"**Total Templates**: {len(template_names_list)}")
                st.markdown("---")

                for template_name in template_names_list:
                    template = templates[template_name]
                    config = template['config']
                    created_at = template['created_at']

                    # Template card
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{template_name}**")
                        st.caption(
                            f"Age: {config.get('age_group', 'N/A')} | "
                            f"Format: {config.get('tournament_format', 'N/A')} | "
                            f"Skills: {len(config.get('skills_to_test', []))} | "
                            f"Created: {created_at[:10]}"
                        )

                    with col2:
                        if st.button(
                            "Load",
                            key=f"btn_load_manage_{template_name}",
                            use_container_width=True,
                            type="primary"
                        ):
                            st.session_state['loaded_template_config'] = config
                            st.session_state['show_manage_templates'] = False
                            Success.toast(f"Template '{template_name}' loaded!")
                            st.rerun()

                    with col3:
                        if st.button(
                            "Delete",
                            key=f"btn_delete_{template_name}",
                            use_container_width=True
                        ):
                            delete_template(template_name)
                            Success.toast(f"Template '{template_name}' deleted")
                            st.rerun()

                    # Expandable details
                    with st.expander("View Details"):
                        st.json(config)

                    st.markdown("---")

            # Close button
            if st.button("Close", key="btn_close_manage_templates", use_container_width=True):
                st.session_state['show_manage_templates'] = False
                st.rerun()

        manage_templates_dialog()

    st.markdown("---")

    # === TOURNAMENT CONFIGURATION ===
    selected_preset = next((p for p in sorted_presets if p['id'] == st.session_state.selected_preset_id), None)

    if selected_preset:
        st.markdown("### Tournament Configuration")

        # Get loaded template config (for pre-filling form fields)
        loaded_config = st.session_state.get('loaded_template_config', {})

        form = SingleColumnForm(
            "tournament_config",
            title="Configure Tournament Details",
            description="Set up your tournament parameters"
        )

        with form.container():
            # Basic Information Section
            form.section("Basic Information")

            tournament_name = st.text_input(
                "Tournament Name",
                value=loaded_config.get('tournament_name', "LFA Sandbox Tournament"),
                key=form.field_key("tournament_name")
            )

            col1, col2 = st.columns(2)
            with col1:
                location_list = fetch_locations()
                location_names = [loc['name'] for loc in location_list]

                # Pre-fill location from template
                loaded_location_id = loaded_config.get('location_id')
                default_location_index = 0
                if loaded_location_id:
                    loaded_location = next((loc for loc in location_list if loc['id'] == loaded_location_id), None)
                    if loaded_location and loaded_location['name'] in location_names:
                        default_location_index = location_names.index(loaded_location['name'])

                selected_location_name = st.selectbox(
                    "Location",
                    location_names,
                    index=default_location_index,
                    key=form.field_key("location")
                )

            with col2:
                if selected_location_name:
                    selected_location = next((loc for loc in location_list if loc['name'] == selected_location_name), None)
                    if selected_location:
                        campus_list = fetch_campuses_by_location(selected_location['id'])
                        campus_names = [c['name'] for c in campus_list]

                        # Pre-fill campus from template
                        loaded_campus_id = loaded_config.get('campus_id')
                        default_campus_index = 0
                        if loaded_campus_id:
                            loaded_campus = next((c for c in campus_list if c['id'] == loaded_campus_id), None)
                            if loaded_campus and loaded_campus['name'] in campus_names:
                                default_campus_index = campus_names.index(loaded_campus['name'])

                        selected_campus = st.selectbox(
                            "Campus",
                            campus_names,
                            index=default_campus_index,
                            key=form.field_key("campus")
                        )

            # Tournament Details Section
            form.section("Tournament Details")

            col1, col2 = st.columns(2)
            with col1:
                # Pre-fill age group from template
                loaded_age_group = loaded_config.get('age_group')
                age_group_index = AGE_GROUPS.index(loaded_age_group) if loaded_age_group in AGE_GROUPS else 0

                age_group = st.selectbox(
                    "Age Group",
                    AGE_GROUPS,
                    index=age_group_index,
                    key=form.field_key("age_group")
                )

            with col2:
                # Pre-fill assignment type from template
                loaded_assignment = loaded_config.get('assignment_type')
                assignment_index = ASSIGNMENT_TYPES.index(loaded_assignment) if loaded_assignment in ASSIGNMENT_TYPES else 0

                assignment_type = st.selectbox(
                    "Assignment Type",
                    ASSIGNMENT_TYPES,
                    index=assignment_index,
                    key=form.field_key("assignment_type")
                )

            # Scoring Mode - CRITICAL: This determines which fields are shown below
            # Pre-fill scoring mode from template
            loaded_scoring = loaded_config.get('scoring_mode')
            scoring_index = SCORING_MODES.index(loaded_scoring) if loaded_scoring in SCORING_MODES else 0

            scoring_mode = st.selectbox(
                "Scoring Mode",
                SCORING_MODES,
                index=scoring_index,
                key=form.field_key("scoring_mode"),
                help="Head-to-Head (1v1 matches) or Individual (performance-based)"
            )

            # ⚠️ CONDITIONAL UI: Show different fields based on scoring mode
            st.markdown("---")  # Visual separator

            # Initialize variables that may be set conditionally
            # (prevents NameError if branches don't execute during reruns)
            tournament_format = None
            number_of_rounds = None
            scoring_type = None
            ranking_direction = None
            measurement_unit = None

            # HEAD_TO_HEAD configuration (league/knockout)
            if scoring_mode == "HEAD_TO_HEAD":
                st.info("🤝 HEAD_TO_HEAD Mode: Players compete in 1v1 matches")

                # Tournament Format (only relevant for HEAD_TO_HEAD)
                loaded_format = loaded_config.get('tournament_format')
                format_index = TOURNAMENT_FORMATS.index(loaded_format) if loaded_format in TOURNAMENT_FORMATS else 0

                tournament_format = st.selectbox(
                    "Tournament Format",
                    TOURNAMENT_FORMATS,
                    index=format_index,
                    key=form.field_key("tournament_format"),
                    help="League (round-robin) or Knockout (elimination)"
                )

                # Set defaults for HEAD_TO_HEAD (not configurable in UI)
                number_of_rounds = None
                scoring_type = None
                ranking_direction = None
                measurement_unit = None

            # INDIVIDUAL scoring configuration
            elif scoring_mode == "INDIVIDUAL":
                st.info("🏃 INDIVIDUAL Mode: Players compete individually for best performance")

                # INDIVIDUAL mode uses "multi_round_ranking" tournament type code
                # (Note: tournament_type.code, not format. Format is INDIVIDUAL_RANKING)
                tournament_format = "multi_round_ranking"
                col1, col2 = st.columns(2)

                with col1:
                    number_of_rounds = st.number_input(
                        "Number of Rounds",
                        min_value=1,
                        max_value=20,
                        value=3,
                        key=form.field_key("number_of_rounds"),
                        help="How many rounds to play (each player competes in each round)"
                    )

                    # Scoring Type - how performance is measured
                    scoring_type = st.selectbox(
                        "Scoring Type",
                        ["TIME_BASED", "SCORE_BASED", "DISTANCE_BASED", "PLACEMENT", "ROUNDS_BASED"],
                        key=form.field_key("scoring_type"),
                        help="How performance is measured"
                    )

                with col2:
                    # Track previous scoring_type to detect changes
                    prev_scoring_key = "prev_scoring_type"
                    if prev_scoring_key not in st.session_state:
                        st.session_state[prev_scoring_key] = scoring_type

                    # Auto-update measurement unit when scoring type changes
                    measurement_unit_key = form.field_key("measurement_unit")
                    if st.session_state[prev_scoring_key] != scoring_type:
                        # Scoring type changed - update measurement unit automatically
                        if scoring_type == "TIME_BASED":
                            st.session_state[measurement_unit_key] = "seconds"
                        elif scoring_type == "DISTANCE_BASED":
                            st.session_state[measurement_unit_key] = "meters"
                        elif scoring_type == "SCORE_BASED":
                            st.session_state[measurement_unit_key] = "points"
                        elif scoring_type == "ROUNDS_BASED":
                            st.session_state[measurement_unit_key] = "rounds"
                        elif scoring_type == "PLACEMENT":
                            st.session_state[measurement_unit_key] = ""

                        st.session_state[prev_scoring_key] = scoring_type

                    # Ranking Direction - which direction wins
                    ranking_direction_option = st.selectbox(
                        "Ranking Direction",
                        ["ASC (Lower is better)", "DESC (Higher is better)"],
                        index=0 if scoring_type == "TIME_BASED" else 1,
                        key=form.field_key("ranking_direction"),
                        help="Which direction determines winner"
                    )
                    ranking_direction = ranking_direction_option.split()[0]  # Extract "ASC" or "DESC"

                    # Measurement Unit (conditional on scoring type)
                    if scoring_type != "PLACEMENT":
                        # Initialize default value if not in session state
                        if measurement_unit_key not in st.session_state:
                            if scoring_type == "TIME_BASED":
                                st.session_state[measurement_unit_key] = "seconds"
                            elif scoring_type == "DISTANCE_BASED":
                                st.session_state[measurement_unit_key] = "meters"
                            elif scoring_type == "ROUNDS_BASED":
                                st.session_state[measurement_unit_key] = "rounds"
                            else:  # SCORE_BASED
                                st.session_state[measurement_unit_key] = "points"

                        measurement_unit = st.text_input(
                            "Measurement Unit",
                            key=measurement_unit_key,
                            help="Unit of measurement (e.g., seconds, meters, points, rounds, repetitions)"
                        )
                    else:
                        measurement_unit = None

            # Pre-fill max players from template
            max_players = st.number_input(
                "Max Players",
                min_value=2,
                max_value=100,
                value=loaded_config.get('max_players', 10),
                key=form.field_key("max_players")
            )

            # Schedule Section
            form.section("Schedule")

            col1, col2 = st.columns(2)
            with col1:
                # Pre-fill start date from template
                loaded_start = loaded_config.get('start_date')
                start_default = datetime.fromisoformat(loaded_start).date() if loaded_start else date.today()
                start_date = st.date_input(
                    "Start Date",
                    value=start_default,
                    key=form.field_key("start_date")
                )
            with col2:
                # Pre-fill end date from template
                loaded_end = loaded_config.get('end_date')
                end_default = datetime.fromisoformat(loaded_end).date() if loaded_end else date.today()
                end_date = st.date_input(
                    "End Date",
                    value=end_default,
                    key=form.field_key("end_date")
                )

            # Participants Section
            form.section("Participants")

            user_list = fetch_users(limit=100)

            # Initialize session state for participant toggles
            # Pre-populate from loaded template
            if "participant_toggles" not in st.session_state:
                loaded_participants = loaded_config.get('selected_users', [])
                st.session_state.participant_toggles = {
                    user['id']: user['id'] in loaded_participants
                    for user in user_list
                }

            # Simple compact list with toggle switches
            for user in user_list:
                user_id = user['id']
                user_email = user['email']
                user_name = user.get('name', 'N/A')
                user_role = user.get('role', 'N/A')

                col1, col2 = st.columns([5, 1])

                with col1:
                    st.caption(f"{user_email} • {user_name} ({user_role})")

                with col2:
                    # Toggle switch (on/off button)
                    # CRITICAL: Label must be VISIBLE for Playwright to find it
                    # Using minimal visible label for E2E test selector
                    toggle_key = f"participant_{user_id}"
                    toggle_label = f"Select {user_id}"  # Visible label for Playwright
                    is_selected = st.toggle(
                        toggle_label,
                        value=st.session_state.participant_toggles.get(user_id, False),
                        key=toggle_key
                        # NO label_visibility - keep default "visible" for Playwright!
                    )

                    # Update toggle state in session_state
                    st.session_state.participant_toggles[user_id] = is_selected

            # ✅ CRITICAL FIX: Rebuild selected_user_ids from participant_toggles EVERY render
            # This is the ONLY source of truth - never maintain a separate list
            selected_user_ids = [
                user_id for user_id, is_selected in st.session_state.participant_toggles.items()
                if is_selected
            ]

            # Display count of selected participants
            st.caption(f"✅ {len(selected_user_ids)} selected")

            # Rewards Section
            form.section("Rewards")

            st.markdown("**Tournament Placement Rewards:**")

            col1, col2, col3 = st.columns(3)
            with col1:
                # Pre-fill rewards from template
                loaded_rewards = loaded_config.get('rewards', {})
                first_xp_default = loaded_rewards.get('first_place', {}).get('xp', 500)
                first_credits_default = loaded_rewards.get('first_place', {}).get('credits', 100)

                first_place_xp = st.number_input(
                    "🥇 1st XP",
                    min_value=0,
                    max_value=2000,
                    value=first_xp_default,
                    step=50,
                    key=form.field_key("first_xp")
                )
                first_place_credits = st.number_input(
                    "1st Credits",
                    min_value=0,
                    max_value=500,
                    value=first_credits_default,
                    step=10,
                    key=form.field_key("first_credits")
                )

            with col2:
                second_xp_default = loaded_rewards.get('second_place', {}).get('xp', 300)
                second_credits_default = loaded_rewards.get('second_place', {}).get('credits', 50)

                second_place_xp = st.number_input(
                    "🥈 2nd XP",
                    min_value=0,
                    max_value=2000,
                    value=second_xp_default,
                    step=50,
                    key=form.field_key("second_xp")
                )
                second_place_credits = st.number_input(
                    "2nd Credits",
                    min_value=0,
                    max_value=500,
                    value=second_credits_default,
                    step=10,
                    key=form.field_key("second_credits")
                )

            with col3:
                third_xp_default = loaded_rewards.get('third_place', {}).get('xp', 200)
                third_credits_default = loaded_rewards.get('third_place', {}).get('credits', 25)

                third_place_xp = st.number_input(
                    "🥉 3rd XP",
                    min_value=0,
                    max_value=2000,
                    value=third_xp_default,
                    step=50,
                    key=form.field_key("third_xp")
                )
                third_place_credits = st.number_input(
                    "3rd Credits",
                    min_value=0,
                    max_value=500,
                    value=third_credits_default,
                    step=5,
                    key=form.field_key("third_credits")
                )

            st.markdown("**Participation Rewards:**")

            col1, col2 = st.columns(2)
            with col1:
                participation_xp_default = loaded_rewards.get('participation', {}).get('xp', 50)
                participation_xp = st.number_input(
                    "Participation XP",
                    min_value=0,
                    max_value=500,
                    value=participation_xp_default,
                    step=10,
                    key=form.field_key("participation_xp"),
                    help="XP for all participants"
                )
            with col2:
                session_base_xp_default = loaded_rewards.get('session_base_xp', 50)
                base_session_xp = st.number_input(
                    "Session Base XP",
                    min_value=0,
                    max_value=200,
                    value=session_base_xp_default,
                    step=10,
                    key=form.field_key("session_base_xp"),
                    help="Base XP per session attendance"
                )

            # Submit Button + Save Template
            st.markdown("---")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    "💾 Save as Template",
                    key="btn_save_template",
                    use_container_width=True,
                    help="Save current configuration as a reusable template"
                ):
                    st.session_state['show_save_template_dialog'] = True
                    # Build current config to save
                    selected_location = next((loc for loc in location_list if loc['name'] == selected_location_name), None)
                    location_id = selected_location['id'] if selected_location else None
                    selected_campus_obj = next((c for c in campus_list if c['name'] == selected_campus), None) if selected_location else None
                    campus_id = selected_campus_obj['id'] if selected_campus_obj else None

                    # Get skills from selected preset (flattened in list API)
                    preset_skills = selected_preset.get('skills_tested', [])

                    st.session_state['config_to_save'] = {
                        'tournament_name': tournament_name,
                        'tournament_format': tournament_format,
                        'scoring_mode': scoring_mode,
                        'number_of_rounds': number_of_rounds if scoring_mode == "INDIVIDUAL" else None,
                        'scoring_type': scoring_type if scoring_mode == "INDIVIDUAL" else None,
                        'ranking_direction': ranking_direction if scoring_mode == "INDIVIDUAL" else None,
                        'measurement_unit': measurement_unit if scoring_mode == "INDIVIDUAL" else None,
                        'age_group': age_group,
                        'assignment_type': assignment_type,
                        'max_players': max_players,
                        'skills_to_test': preset_skills,
                        'location_id': location_id,
                        'campus_id': campus_id,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'game_preset_id': selected_preset['id'],
                        'performance_variation': 'MEDIUM',
                        'ranking_distribution': 'NORMAL',
                        'selected_users': selected_user_ids,
                        'rewards': {
                            'first_place': {'xp': first_place_xp, 'credits': first_place_credits},
                            'second_place': {'xp': second_place_xp, 'credits': second_place_credits},
                            'third_place': {'xp': third_place_xp, 'credits': third_place_credits},
                            'participation': {'xp': participation_xp, 'credits': 0},
                            'session_base_xp': base_session_xp
                        }
                    }
                    st.rerun()

            with col2:
                start_workflow_clicked = st.button(
                    "Start Instructor Workflow",
                    type="primary",
                    use_container_width=True,
                    key="btn_start_workflow"
                )

            # SAVE TEMPLATE DIALOG
            if st.session_state.get('show_save_template_dialog', False):
                @st.dialog("💾 Save as Template")
                def save_template_dialog():
                    st.markdown("Save the current tournament configuration as a reusable template.")

                    template_name = st.text_input(
                        "Template Name",
                        placeholder="e.g., YOUTH Budapest Weekly",
                        key="input_template_name",
                        help="Choose a descriptive name for this template"
                    )

                    # Name validation
                    existing_names = list_template_names()
                    name_exists = template_name in existing_names

                    if name_exists and template_name:
                        Error.message(f"Template '{template_name}' already exists. Choose a different name.")

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("Cancel", key="btn_cancel_save_template", use_container_width=True):
                            st.session_state['show_save_template_dialog'] = False
                            st.rerun()

                    with col2:
                        save_disabled = not template_name or name_exists
                        if st.button(
                            "Save Template",
                            type="primary",
                            disabled=save_disabled,
                            key="btn_confirm_save_template",
                            use_container_width=True
                        ):
                            config_to_save = st.session_state.get('config_to_save', {})
                            save_template(template_name, config_to_save)
                            Success.message(f"Template '{template_name}' saved!")
                            st.session_state['show_save_template_dialog'] = False
                            st.rerun()

                save_template_dialog()

            if start_workflow_clicked:
                # ✅ FIX: Load full preset configuration to get format_config
                from sandbox_helpers import fetch_preset_details
                preset_details = fetch_preset_details(selected_preset['id'])

                if not preset_details:
                    Error.message(f"Failed to load preset configuration (ID: {selected_preset['id']})")
                    st.stop()

                # Extract format configuration from preset
                preset_game_config = preset_details.get('game_config', {})
                format_config_dict = preset_game_config.get('format_config', {})

                # Get the tournament format from preset (not from form widget!)
                # Format config has structure: {"GROUP_KNOCKOUT": {...}, "KNOCKOUT": {...}, etc}
                # We need to find which format is configured
                preset_tournament_format = None
                format_specific_config = {}

                for fmt_key, fmt_config in format_config_dict.items():
                    # The preset uses format keys like "GROUP_KNOCKOUT", "KNOCKOUT", etc.
                    preset_tournament_format = fmt_key
                    format_specific_config = fmt_config
                    break  # Use first format found

                if not preset_tournament_format:
                    # Fallback to form widget value if preset has no format_config
                    preset_tournament_format = tournament_format

                # Get skills from selected preset
                # NOTE: List API returns flattened structure with skills_tested at top level
                preset_skills = selected_preset.get('skills_tested', [])

                # Get location and campus IDs
                selected_location = next((loc for loc in location_list if loc['name'] == selected_location_name), None)
                location_id = selected_location['id'] if selected_location else None
                selected_campus_obj = next((c for c in campus_list if c['name'] == selected_campus), None) if selected_location else None
                campus_id = selected_campus_obj['id'] if selected_campus_obj else None

                # Build configuration - USE PRESET FORMAT, NOT FORM VALUE
                config = {
                    'tournament_name': tournament_name,
                    'tournament_format': preset_tournament_format,  # ✅ FROM PRESET
                    'scoring_mode': scoring_mode,
                    'number_of_rounds': number_of_rounds if scoring_mode == "INDIVIDUAL" else None,
                    'scoring_type': scoring_type if scoring_mode == "INDIVIDUAL" else None,
                    'ranking_direction': ranking_direction if scoring_mode == "INDIVIDUAL" else None,
                    'measurement_unit': measurement_unit if scoring_mode == "INDIVIDUAL" else None,
                    'age_group': age_group,
                    'assignment_type': assignment_type,
                    'max_players': max_players,
                    'skills_to_test': preset_skills,
                    'location_id': location_id,
                    'campus_id': campus_id,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'game_preset_id': selected_preset['id'],
                    'performance_variation': 'MEDIUM',
                    'ranking_distribution': 'NORMAL',
                    'selected_users': selected_user_ids,
                    # Placement Rewards (backend-compatible structure)
                    'rewards': {
                        'first_place': {
                            'xp': first_place_xp,
                            'credits': first_place_credits
                        },
                        'second_place': {
                            'xp': second_place_xp,
                            'credits': second_place_credits
                        },
                        'third_place': {
                            'xp': third_place_xp,
                            'credits': third_place_credits
                        },
                        'participation': {
                            'xp': participation_xp,
                            'credits': 0
                        },
                        'session_base_xp': base_session_xp
                    }
                }

                # ✅ FIX: Add format-specific configuration from preset
                # Merge format-specific fields (group_count, qualifiers_per_group, etc)
                if format_specific_config:
                    config.update(format_specific_config)

                # Store config and move to workflow
                st.session_state.tournament_config = config
                st.session_state.screen = "instructor_workflow"
                st.session_state.workflow_step = 1
                st.rerun()


def render_instructor_workflow():
    """Instructor workflow coordinator - 6 main steps + optional step 7 for viewing rewards"""
    import sys
    workflow_step = st.session_state.get('workflow_step', 1)
    logger.info(f"🟡 [WORKFLOW START] render_instructor_workflow() - Step {workflow_step}")

    # Progress indicator (show progress for main workflow steps 1-6, step 7 is standalone)
    max_steps = 6 if workflow_step <= 6 else 7
    st.progress(min(workflow_step, 6) / 6)

    if workflow_step <= 6:
        st.markdown(f"### Step {workflow_step} of 6")
    else:
        st.markdown(f"### Step {workflow_step}: View Distributed Rewards")

    st.markdown("---")

    # ✅ FIX: Removed duplicate import that was shadowing line 34
    # Now using module-level import from sandbox_workflow (line 34)

    # Render appropriate step
    config = st.session_state.get('tournament_config', {})

    if workflow_step == 1:
        logger.info(f"📍 [STEP 1] Calling render_step_create_tournament()")
        render_step_create_tournament(config)
        logger.info(f"✅ [STEP 1] render_step_create_tournament() completed")
    elif workflow_step == 2:
        logger.info(f"📍 [STEP 2] Calling render_step_manage_sessions()")
        render_step_manage_sessions()
        logger.info(f"✅ [STEP 2] render_step_manage_sessions() completed")
    elif workflow_step == 3:
        logger.info(f"📍 [STEP 3] Calling render_step_track_attendance()")
        render_step_track_attendance()
        logger.info(f"✅ [STEP 3] render_step_track_attendance() completed")
    elif workflow_step == 4:
        logger.info(f"📍 [STEP 4] Calling render_step_enter_results()")
        render_step_enter_results()
        logger.info(f"✅ [STEP 4] render_step_enter_results() completed")
    elif workflow_step == 5:
        logger.info(f"📍 [STEP 5] Calling render_step_view_leaderboard()")
        render_step_view_leaderboard()
        logger.info(f"✅ [STEP 5] render_step_view_leaderboard() completed")
    elif workflow_step == 6:
        logger.info(f"📍 [STEP 6] Calling render_step_distribute_rewards()")
        render_step_distribute_rewards()
        logger.info(f"✅ [STEP 6] render_step_distribute_rewards() completed")
    elif workflow_step == 7:
        logger.info(f"📍 [STEP 7] Calling render_step_view_rewards()")
        render_step_view_rewards()
        logger.info(f"✅ [STEP 7] render_step_view_rewards() completed")

    logger.info(f"🟢 [WORKFLOW END] render_instructor_workflow() completed - Step {workflow_step}")


def render_history_screen():
    """Standalone history browser"""
    st.title("Tournament History", anchor=False)

    if not auth.is_authenticated():
        st.warning("Please log in first")
        if st.button("Go to Login", key="btn_go_to_login"):
            st.session_state.screen = "home"
            st.rerun()
        return

    sandbox_tournaments = get_sandbox_tournaments()

    if not sandbox_tournaments:
        st.info("No sandbox tournaments found")
        return

    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="Search tournaments...",
            key="input_search_tournaments"
        )
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "COMPLETED", "IN_PROGRESS", "DRAFT"],
            key="select_status_filter"
        )
    with col3:
        sort_by = st.selectbox(
            "Sort By",
            ["Newest First", "Oldest First", "Name A-Z"],
            key="select_sort_by"
        )

    # Filter tournaments
    filtered = sandbox_tournaments
    if search_query:
        filtered = [t for t in filtered if search_query.lower() in t.get('name', '').lower()]
    if status_filter != "All":
        filtered = [t for t in filtered if t.get('tournament_status') == status_filter]

    # Sort
    if sort_by == "Newest First":
        filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == "Oldest First":
        filtered.sort(key=lambda x: x.get('created_at', ''))
    else:
        filtered.sort(key=lambda x: x.get('name', ''))

    st.markdown(f"### Results ({len(filtered)} tournaments)")
    st.markdown("---")

    # Display tournaments
    for tournament in filtered:
        _render_tournament_card(tournament)


def _render_tournament_card(tournament: Dict):
    """Render a single tournament card in history"""
    status = tournament.get('tournament_status', 'UNKNOWN')
    status_colors = {
        'COMPLETED': 'success',
        'IN_PROGRESS': 'info',
        'DRAFT': 'warning'
    }

    card = InfoCard(
        title=tournament.get('name', 'Unknown Tournament'),
        subtitle=f"Status: {status} | ID: {tournament.get('id')}",
        status=status_colors.get(status, 'info'),
        card_id=f"tournament_{tournament.get('id')}"
    )

    with card.container():
        # UI Testing Contract: Tournament Status
        st.markdown(f'<div data-testid="tournament-status" data-status="{status}">Status: <strong>{status}</strong></div>', unsafe_allow_html=True)
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Participants", tournament.get('participant_count', 0))
        with col2:
            st.metric("Format", tournament.get('format', tournament.get('tournament_format', 'INDIVIDUAL')))
        with col3:
            # Show game preset name or age group
            game_type = tournament.get('game_preset_name', tournament.get('age_group', '—'))
            st.metric("Type", game_type)

        # Action buttons
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

        with col_btn1:
            if st.button("📋 Resume Workflow", key=f"btn_resume_{tournament.get('id')}", use_container_width=True):
                # Load tournament into session state and navigate to instructor workflow
                tournament_id = tournament.get('id')
                st.session_state.tournament_id = tournament_id
                st.session_state.screen = 'instructor_workflow'
                st.session_state.workflow_step = 4  # Default to Step 4 (Enter Results)

                # Update URL for deep linking
                update_url_params(screen='instructor_workflow', tournament_id=tournament_id, step=4)
                st.session_state.workflow_step = 3  # Start at Step 3 (Attendance) by default
                st.rerun()

        with col_btn2:
            if st.button("📊 View Results", key=f"btn_results_{tournament.get('id')}", use_container_width=True):
                st.session_state.tournament_id = tournament.get('id')
                st.session_state.screen = 'instructor_workflow'
                st.session_state.workflow_step = 4  # Jump to Step 4 (Results)
                st.rerun()

        with col_btn3:
            if st.button("🏆 Leaderboard", key=f"btn_leaderboard_{tournament.get('id')}", use_container_width=True):
                st.session_state.tournament_id = tournament.get('id')
                st.session_state.screen = 'instructor_workflow'
                st.session_state.workflow_step = 5  # Jump to Step 5 (Leaderboard)
                st.rerun()

        with col_btn4:
            if st.button("🎁 View Rewards", key=f"btn_rewards_{tournament.get('id')}", use_container_width=True):
                st.session_state.tournament_id = tournament.get('id')
                st.session_state.screen = 'instructor_workflow'
                st.session_state.workflow_step = 7  # Jump to Step 7 (Rewards)
                st.rerun()

        with st.expander("Details"):
            st.json(tournament)

    card.close_container()


def _render_preset_create_form(*form_components):
    """Render preset creation form with all components"""
    (render_basic_info_editor, render_skill_config_editor,
     render_match_simulation_editor, render_ranking_rules_editor,
     render_metadata_editor, render_simulation_config_editor) = form_components

    st.markdown("---")
    card = Card(title="Create New Game Preset", card_id="create_preset")
    with card.container():
        # Empty config for new preset
        empty_config = {
            "version": "1.0",
            "metadata": {},
            "skill_config": {},
            "format_config": {"HEAD_TO_HEAD": {}},
            "simulation_config": {}
        }

        # Basic info
        basic_info = render_basic_info_editor(name="", description="", code="", key_prefix="new_preset")

        # Metadata
        with st.expander("📋 Metadata", expanded=False):
            metadata = render_metadata_editor(empty_config, key_prefix="new_preset")

        # Skill config
        with st.expander("⚽ Skill Configuration", expanded=True):
            skill_config = render_skill_config_editor(empty_config, preset_id=None, key_prefix="new_preset")

        # Match simulation
        with st.expander("🎮 Match Simulation", expanded=False):
            match_sim = render_match_simulation_editor(empty_config.get("format_config", {}), format_type="HEAD_TO_HEAD", preset_id=None, key_prefix="new_preset")

        # Ranking rules
        with st.expander("🏆 Ranking Rules", expanded=False):
            ranking = render_ranking_rules_editor(empty_config.get("format_config", {}), format_type="HEAD_TO_HEAD", preset_id=None, key_prefix="new_preset")

        # Simulation config
        with st.expander("⚙️ Simulation Configuration", expanded=False):
            sim_config = render_simulation_config_editor(empty_config, key_prefix="new_preset")

        # Action buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Save New Preset", key="btn_save_new_preset", type="primary", use_container_width=True):
                # Validate
                if not basic_info["code"] or not basic_info["name"]:
                    Error.message("Preset code and name are required!")
                elif not skill_config.get("skills_tested"):
                    Error.message("At least one skill must be selected!")
                else:
                    # Build game_config
                    game_config = {
                        "version": "1.0",
                        "metadata": metadata,
                        "skill_config": skill_config,
                        "format_config": {"HEAD_TO_HEAD": {
                            "ranking_rules": ranking,
                            "match_simulation": match_sim
                        }},
                        "simulation_config": sim_config
                    }

                    # Save to API
                    response = create_game_preset(
                        code=basic_info["code"],
                        name=basic_info["name"],
                        description=basic_info["description"],
                        game_config=game_config
                    )

                    if response:
                        Success.toast(f"Preset '{basic_info['name']}' created successfully!")
                        st.session_state.creating_preset = False
                        st.session_state.selected_preset_id = response.get("id")
                        st.rerun()
                    else:
                        Error.message("Failed to create preset. Check if code already exists.")

        with col2:
            if st.button("Cancel", key="btn_cancel_create_preset", use_container_width=True):
                st.session_state.creating_preset = False
                st.rerun()

    card.close_container()
    st.markdown("---")


def _clear_preset_widget_state(preset_id: int):
    """Clear all widget state for a preset to force reload from JSON"""
    from app.skills_config import SKILL_CATEGORIES

    key_prefix = f"preset_{preset_id}"

    # Clear all skill checkbox and weight widget keys
    for category in SKILL_CATEGORIES:
        for skill_def in category["skills"]:
            skill_key = skill_def["key"]
            checkbox_key = f"{key_prefix}_skill_{skill_key}"
            weight_key = f"{key_prefix}_weight_{skill_key}"

            if checkbox_key in st.session_state:
                del st.session_state[checkbox_key]
            if weight_key in st.session_state:
                del st.session_state[weight_key]


def _render_preset_list_item(preset: Dict, *form_components):
    """Render a single preset in the list"""
    preset_id = preset['id']
    preset_name = preset['name']

    # Build display badges
    badges = []
    if preset.get('is_recommended'):
        badges.append("⭐ Recommended")
    if preset.get('is_locked'):
        badges.append("🔒 Locked")

    difficulty = (preset.get('difficulty_level') or 'N/A').title()
    category = (preset.get('game_category') or 'N/A').replace('_', ' ').title()
    player_range = preset.get('recommended_player_count', {})
    player_info = f"{player_range.get('min', 'N/A')}-{player_range.get('max', 'N/A')} players" if player_range else "N/A"

    col1, col2, col3, col4 = st.columns([3, 1.5, 1, 1])

    with col1:
        st.markdown(f"**{preset_name}**")
        st.caption(f"{category} | {difficulty} | {player_info}")

    with col2:
        if badges:
            for badge in badges:
                st.caption(badge)

    with col3:
        if st.session_state.selected_preset_id == preset_id:
            st.success("Selected")
        else:
            if st.button("Select", key=f"btn_select_preset_{preset_id}"):
                st.session_state.selected_preset_id = preset_id
                st.rerun()

    with col4:
        if st.session_state.editing_preset_id == preset_id:
            if st.button("Cancel", key=f"btn_cancel_edit_{preset_id}"):
                _clear_preset_widget_state(preset_id)
                st.session_state.editing_preset_id = None
                st.rerun()
        else:
            if st.button("Edit", key=f"btn_edit_preset_{preset_id}"):
                # Clear widget state to load fresh values from JSON
                _clear_preset_widget_state(preset_id)
                st.session_state.editing_preset_id = preset_id
                st.rerun()

    # EDIT MODE: Show skill configuration editor when editing
    if st.session_state.editing_preset_id == preset_id:
        st.markdown("---")
        st.markdown(f"### Editing: {preset_name}")

        # Reload preset from JSON to get latest data
        from sandbox_helpers import fetch_preset_details
        fresh_preset = fetch_preset_details(preset_id)
        if not fresh_preset:
            st.error(f"Failed to reload preset {preset_id}")
            return

        # Render skill configuration editor if provided
        if len(form_components) >= 2:
            render_skill_config_editor = form_components[1]
            updated_config = render_skill_config_editor(fresh_preset.get('game_config', {}), preset_id=preset_id)

            # Save button
            st.markdown("---")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 Save Changes", key=f"btn_save_preset_{preset_id}", type="primary", use_container_width=True):
                    # Update preset with new skill configuration
                    update_data = {
                        "skill_config": updated_config
                    }
                    if update_preset(preset_id, update_data):
                        # Clear widget state for this preset to force reload from JSON
                        _clear_preset_widget_state(preset_id)
                        st.session_state.editing_preset_id = None
                        st.rerun()
            with col2:
                if st.button("Cancel", key=f"btn_cancel_save_{preset_id}", use_container_width=True):
                    # Clear widget state to discard changes
                    _clear_preset_widget_state(preset_id)
                    st.session_state.editing_preset_id = None
                    st.rerun()


def main():
    """Main application entry point"""
    import sys
    logger.info("🔵 [SCRIPT START] main() entered")
    logger.info(f"🔍 [LOAD] workflow_step ON ENTRY: {st.session_state.get('workflow_step', 'NOT SET')}")

    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "home"
    if "test_mode" not in st.session_state:
        st.session_state.test_mode = "quick"

    # E2E Testing: Always auto-authenticate for testing
    # This ensures API calls have valid Bearer tokens
    # Use direct token injection (no rerun) to avoid race conditions in headless tests
    if not st.session_state.get("auth_token"):
        import requests
        print("🔐 [AUTO-LOGIN] No auth_token in session_state, attempting login...")
        try:
            login_response = requests.post(
                "http://localhost:8000/api/v1/auth/login",
                json={"email": "admin@lfa.com", "password": "admin123"},
                timeout=5
            )
            print(f"🔐 [AUTO-LOGIN] Login response status: {login_response.status_code}")
            if login_response.status_code == 200:
                token_data = login_response.json()
                st.session_state.auth_token = token_data["access_token"]
                st.session_state.user_id = token_data.get("user_id", 1)
                st.session_state.user_email = "admin@lfa.com"
                st.session_state.user_role = token_data.get("role", "ADMIN")
                print(f"🔐 [AUTO-LOGIN] ✅ SUCCESS: Token set (len={len(st.session_state.auth_token)})")
            else:
                print(f"🔐 [AUTO-LOGIN] ❌ FAIL: Status {login_response.status_code}, response: {login_response.text[:200]}")
        except Exception as e:
            # If login fails, log error but continue (home screen will show error)
            print(f"🔐 [AUTO-LOGIN] ❌ EXCEPTION: {type(e).__name__}: {str(e)}")
    else:
        print(f"🔐 [AUTO-LOGIN] Token already exists (len={len(st.session_state.auth_token)})")

    # ===========================================================================
    # PHASE 1: URL-BASED ROUTING - State Restoration from Query Params
    # ===========================================================================
    # Read query parameters and restore session state
    # This enables deep linking, page reload, and browser back/forward navigation
    query_params = st.query_params

    # Auto-login for E2E testing if query params present
    if any(key in query_params for key in ["screen", "tournament_id", "step"]):
        if not st.session_state.get("auth_token"):
            import requests
            try:
                login_response = requests.post(
                    "http://localhost:8000/api/v1/auth/login",
                    json={"email": "admin@lfa.com", "password": "admin123"}
                )
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    st.session_state.auth_token = token_data["access_token"]
                    st.session_state.user_id = token_data.get("user_id")
                    st.session_state.user_email = "admin@lfa.com"
                    st.session_state.user_role = token_data.get("role", "ADMIN")
            except Exception:
                pass  # Fail silently

    # Restore navigation state from URL
    # All params (screen, tournament_id, workflow_step) applied immediately without rerun
    # This allows deep linking to work on first page load

    if "screen" in query_params:
        desired_screen = query_params["screen"]
        if st.session_state.get("screen") != desired_screen:
            logger.info(f"🔍 [QUERY RESTORE] Setting screen from URL: {desired_screen}")
            st.session_state.screen = desired_screen

    if "tournament_id" in query_params:
        try:
            desired_tournament_id = int(query_params["tournament_id"])
            if st.session_state.get("tournament_id") != desired_tournament_id:
                logger.info(f"🔍 [QUERY RESTORE] Setting tournament_id from URL: {desired_tournament_id}")
                st.session_state.tournament_id = desired_tournament_id
        except (ValueError, TypeError):
            pass  # Invalid tournament_id, ignore

    # Restore workflow_step from URL (deep linking support)
    # URL is source of truth for navigation - allows mid-workflow deep links
    if "step" in query_params:
        try:
            desired_step = int(query_params["step"])
            current_step = st.session_state.get("workflow_step")
            if current_step != desired_step:
                logger.info(f"🔍 [QUERY RESTORE] Syncing workflow_step from URL: {current_step} → {desired_step}")
                st.session_state.workflow_step = desired_step
        except (ValueError, TypeError):
            pass  # Invalid step, ignore

    # NO RERUN - query params applied immediately and render proceeds
    # This ensures deep links work on first page load without extra script runs

    # Sidebar
    with st.sidebar:
        st.markdown("### Sandbox Controls")

        current_screen = st.session_state.screen
        if current_screen == "home":
            st.info("Home")
        elif current_screen == "history":
            st.info("History Browser")
        elif current_screen == "configuration":
            st.info("Configuration")
        elif current_screen == "instructor_workflow":
            workflow_step = st.session_state.get('workflow_step', 1)
            st.info(f"Workflow: Step {workflow_step}/6")

        st.markdown("---")

        if st.button(
            "Refresh Page",
            use_container_width=True,
            key="btn_refresh_page"
        ):
            st.rerun()

        if st.button(
            "Back to Home",
            use_container_width=True,
            key="btn_back_to_home"
        ):
            # Clear workflow state
            keys_to_clear = [
                'test_mode', 'workflow_step', 'tournament_id',
                'tournament_result', 'tournament_config', 'test_result', 'test_error'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            st.session_state.screen = "home"
            st.session_state.workflow_step = 1

            # Update URL to reflect navigation
            update_url_params(screen="home")

            Success.toast("Returning home...")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")
        st.markdown("**Quick Tips:**")
        st.markdown("- Refresh Page: reload current step")
        st.markdown("- Back to Home: return to start")
        st.markdown("---")
        st.caption(f"Sandbox v3 | Screen: {current_screen}")

    # Route to screens (with explicit returns to prevent multi-screen rendering)
    if st.session_state.screen == "home":
        render_home_screen()
        logger.info("🟢 [SCRIPT END] main() completed (home screen)")
        return
    elif st.session_state.screen == "history":
        render_history_screen()
        logger.info("🟢 [SCRIPT END] main() completed (history screen)")
        return
    elif st.session_state.screen == "configuration":
        render_configuration_screen()
        logger.info("🟢 [SCRIPT END] main() completed (configuration screen)")
        return
    elif st.session_state.screen == "instructor_workflow":
        render_instructor_workflow()
        logger.info("🟢 [SCRIPT END] main() completed (instructor_workflow screen)")
        return


if __name__ == "__main__":
    main()
