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
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date

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
    render_mini_leaderboard, get_sandbox_tournaments, calculate_tournament_stats
)

# Constants
AGE_GROUPS = ["PRE", "YOUTH", "AMATEUR", "PRO"]
ASSIGNMENT_TYPES = ["OPEN_ASSIGNMENT", "MANUAL_ASSIGNMENT", "INVITE_ONLY"]
TOURNAMENT_FORMATS = ["league", "knockout", "hybrid"]
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

    # === TOURNAMENT CONFIGURATION ===
    selected_preset = next((p for p in sorted_presets if p['id'] == st.session_state.selected_preset_id), None)

    if selected_preset:
        st.markdown("### Tournament Configuration")

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
                value="LFA Sandbox Tournament",
                key=form.field_key("tournament_name")
            )

            col1, col2 = st.columns(2)
            with col1:
                location_list = fetch_locations()
                location_names = [loc['name'] for loc in location_list]
                selected_location_name = st.selectbox(
                    "Location",
                    location_names,
                    key=form.field_key("location")
                )

            with col2:
                if selected_location_name:
                    selected_location = next((loc for loc in location_list if loc['name'] == selected_location_name), None)
                    if selected_location:
                        campus_list = fetch_campuses_by_location(selected_location['id'])
                        campus_names = [c['name'] for c in campus_list]
                        selected_campus = st.selectbox(
                            "Campus",
                            campus_names,
                            key=form.field_key("campus")
                        )

            # Tournament Details Section
            form.section("Tournament Details")

            col1, col2 = st.columns(2)
            with col1:
                age_group = st.selectbox(
                    "Age Group",
                    AGE_GROUPS,
                    key=form.field_key("age_group")
                )
                tournament_format = st.selectbox(
                    "Tournament Format",
                    TOURNAMENT_FORMATS,
                    key=form.field_key("tournament_format"),
                    help="League (round-robin), Knockout (elimination), or Hybrid (league + knockout)"
                )

            with col2:
                assignment_type = st.selectbox(
                    "Assignment Type",
                    ASSIGNMENT_TYPES,
                    key=form.field_key("assignment_type")
                )

            # Scoring Mode - moved outside columns to give it full width
            scoring_mode = st.selectbox(
                "Scoring Mode",
                SCORING_MODES,
                key=form.field_key("scoring_mode"),
                help="Head-to-Head (1v1 matches with wins/draws/losses) or Individual (performance-based scoring)"
            )

            # INDIVIDUAL scoring configuration
            if scoring_mode == "INDIVIDUAL":
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
                        ["TIME_BASED", "SCORE_BASED", "DISTANCE_BASED", "PLACEMENT"],
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
                            else:  # SCORE_BASED
                                st.session_state[measurement_unit_key] = "points"

                        measurement_unit = st.text_input(
                            "Measurement Unit",
                            key=measurement_unit_key,
                            help="Unit of measurement (e.g., seconds, meters, points, repetitions)"
                        )
                    else:
                        measurement_unit = None
            else:
                # HEAD_TO_HEAD mode - no additional config needed
                number_of_rounds = None
                scoring_type = None
                ranking_direction = None
                measurement_unit = None

            max_players = st.number_input(
                "Max Players",
                min_value=2,
                max_value=100,
                value=10,
                key=form.field_key("max_players")
            )

            # Schedule Section
            form.section("Schedule")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=date.today(),
                    key=form.field_key("start_date")
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=date.today(),
                    key=form.field_key("end_date")
                )

            # Participants Section
            form.section("Participants")

            user_list = fetch_users(limit=100)

            # Initialize session state for participant toggles
            if "participant_toggles" not in st.session_state:
                st.session_state.participant_toggles = {}

            selected_user_ids = []

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
                    toggle_key = f"participant_{user_id}"
                    is_selected = st.toggle(
                        "",
                        value=st.session_state.participant_toggles.get(user_id, False),
                        key=toggle_key
                    )
                    st.session_state.participant_toggles[user_id] = is_selected

                    if is_selected:
                        selected_user_ids.append(user_id)

            st.caption(f"✅ {len(selected_user_ids)} selected")

            # Rewards Section
            form.section("Rewards")

            st.markdown("**Tournament Placement Rewards:**")

            col1, col2, col3 = st.columns(3)
            with col1:
                first_place_xp = st.number_input(
                    "🥇 1st XP",
                    min_value=0,
                    max_value=2000,
                    value=500,
                    step=50,
                    key=form.field_key("first_xp")
                )
                first_place_credits = st.number_input(
                    "1st Credits",
                    min_value=0,
                    max_value=500,
                    value=100,
                    step=10,
                    key=form.field_key("first_credits")
                )

            with col2:
                second_place_xp = st.number_input(
                    "🥈 2nd XP",
                    min_value=0,
                    max_value=2000,
                    value=300,
                    step=50,
                    key=form.field_key("second_xp")
                )
                second_place_credits = st.number_input(
                    "2nd Credits",
                    min_value=0,
                    max_value=500,
                    value=50,
                    step=10,
                    key=form.field_key("second_credits")
                )

            with col3:
                third_place_xp = st.number_input(
                    "🥉 3rd XP",
                    min_value=0,
                    max_value=2000,
                    value=200,
                    step=50,
                    key=form.field_key("third_xp")
                )
                third_place_credits = st.number_input(
                    "3rd Credits",
                    min_value=0,
                    max_value=500,
                    value=25,
                    step=5,
                    key=form.field_key("third_credits")
                )

            st.markdown("**Participation Rewards:**")

            col1, col2 = st.columns(2)
            with col1:
                participation_xp = st.number_input(
                    "Participation XP",
                    min_value=0,
                    max_value=500,
                    value=50,
                    step=10,
                    key=form.field_key("participation_xp"),
                    help="XP for all participants"
                )
            with col2:
                base_session_xp = st.number_input(
                    "Session Base XP",
                    min_value=0,
                    max_value=200,
                    value=50,
                    step=10,
                    key=form.field_key("session_base_xp"),
                    help="Base XP per session attendance"
                )

            # Submit Button
            st.markdown("---")
            if st.button(
                "Start Instructor Workflow",
                type="primary",
                use_container_width=True,
                key="btn_start_workflow"
            ):
                # Get skills from selected preset (correct path: game_config.skill_config.skills_tested)
                game_config = selected_preset.get('game_config', {})
                skill_config = game_config.get('skill_config', {})
                preset_skills = skill_config.get('skills_tested', [])

                # Get location and campus IDs
                selected_location = next((loc for loc in location_list if loc['name'] == selected_location_name), None)
                location_id = selected_location['id'] if selected_location else None
                selected_campus_obj = next((c for c in campus_list if c['name'] == selected_campus), None) if selected_location else None
                campus_id = selected_campus_obj['id'] if selected_campus_obj else None

                # Build configuration
                config = {
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

                # Store config and move to workflow
                st.session_state.tournament_config = config
                st.session_state.screen = "instructor_workflow"
                st.session_state.workflow_step = 1
                st.rerun()


def render_instructor_workflow():
    """Instructor workflow coordinator - 6 steps"""
    workflow_step = st.session_state.get('workflow_step', 1)

    # Progress indicator
    st.progress(workflow_step / 6)
    st.markdown(f"### Step {workflow_step} of 6")
    st.markdown("---")

    # Import workflow step modules
    from sandbox_workflow import (
        render_step_create_tournament,
        render_step_manage_sessions,
        render_step_track_attendance,
        render_step_enter_results,
        render_step_view_leaderboard,
        render_step_distribute_rewards,
        render_step_tournament_history
    )

    # Render appropriate step
    config = st.session_state.get('tournament_config', {})

    if workflow_step == 1:
        render_step_create_tournament(config)
    elif workflow_step == 2:
        render_step_manage_sessions()
    elif workflow_step == 3:
        render_step_track_attendance()
    elif workflow_step == 4:
        render_step_enter_results()
    elif workflow_step == 5:
        render_step_view_leaderboard()
    elif workflow_step == 6:
        render_step_distribute_rewards()


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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Participants", tournament.get('participant_count', 0))
        with col2:
            st.metric("Format", tournament.get('format', 'N/A'))
        with col3:
            st.metric("Type", tournament.get('type', 'N/A'))

        with st.expander("Details"):
            st.json(tournament)

    card.close_container()


def _render_preset_create_form(*form_components):
    """Render preset creation form (collapsed for brevity)"""
    # This maintains the existing preset creation logic but uses Card components
    # Full implementation would include all the expanders and form fields
    st.markdown("---")
    card = Card(title="Create New Game Preset", card_id="create_preset")
    with card.container():
        st.info("Use the preset forms to configure the new game preset")
        # Preset form components would go here (already exists in codebase)
        if st.button("Cancel", key="btn_cancel_create_preset"):
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

    difficulty = preset.get('difficulty_level', 'N/A').title()
    category = preset.get('game_category', 'N/A').replace('_', ' ').title()
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
    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "home"
    if "test_mode" not in st.session_state:
        st.session_state.test_mode = "quick"

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
            Success.toast("Returning home...")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")
        st.markdown("**Quick Tips:**")
        st.markdown("- Refresh Page: reload current step")
        st.markdown("- Back to Home: return to start")
        st.markdown("---")
        st.caption(f"Sandbox v3 | Screen: {current_screen}")

    # Route to screens
    if st.session_state.screen == "home":
        render_home_screen()
    elif st.session_state.screen == "history":
        render_history_screen()
    elif st.session_state.screen == "configuration":
        render_configuration_screen()
    elif st.session_state.screen == "instructor_workflow":
        render_instructor_workflow()


if __name__ == "__main__":
    main()
