"""
Sandbox Tournament Test - Admin-Aligned UI (V3)

Complete restructure to match admin dashboard tournament creation flow:
- Location → Campus 2-step selection
- Reward Configuration V2 (skill categories + badges)
- Explicit format selection
- All admin fields present
- No sandbox-specific elements

Run: streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8502
"""
import streamlit as st
import requests
import time
import sys
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date

# Add parent directory to path to import skills_config
sys.path.insert(0, str(Path(__file__).parent))
from app.skills_config import SKILL_CATEGORIES as REAL_SKILL_CATEGORIES

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
SANDBOX_ENDPOINT = f"{API_BASE_URL}/sandbox/run-test"
AUTH_ENDPOINT = f"{API_BASE_URL}/auth/login"
USERS_ENDPOINT = f"{API_BASE_URL}/sandbox/users"
INSTRUCTORS_ENDPOINT = f"{API_BASE_URL}/sandbox/instructors"
CAMPUSES_ENDPOINT = f"{API_BASE_URL}/admin/campuses"
LOCATIONS_ENDPOINT = f"{API_BASE_URL}/admin/locations"
GAME_PRESETS_ENDPOINT = f"{API_BASE_URL}/game-presets"

# Available options (Admin-grade - EXACT match from admin dashboard)
TOURNAMENT_TYPES = ["league", "knockout", "hybrid", "None"]  # None = Manual
AGE_GROUPS = ["PRE", "YOUTH", "AMATEUR", "PRO"]  # EXACT from admin
ASSIGNMENT_TYPES = ["OPEN_ASSIGNMENT", "MANUAL_ASSIGNMENT", "INVITE_ONLY"]
FORMATS = ["HEAD_TO_HEAD", "INDIVIDUAL_RANKING"]

# Convert REAL_SKILL_CATEGORIES to display format
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

# Helper Functions
def get_auth_token(email: str, password: str) -> Optional[str]:
    """Authenticate and get token"""
    try:
        response = requests.post(AUTH_ENDPOINT, json={"email": email, "password": password})
        response.raise_for_status()
        auth_data = response.json()
        return auth_data.get("access_token") if auth_data else None
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

def fetch_locations(token: str) -> List[Dict]:
    """Fetch available locations from backend"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(LOCATIONS_ENDPOINT, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch locations: {e}")
        return []

def fetch_campuses_by_location(token: str, location_id: int) -> List[Dict]:
    """Fetch campuses filtered by location"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Use the location-specific endpoint
        url = f"{API_BASE_URL}/admin/locations/{location_id}/campuses"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch campuses for location {location_id}: {e}")
        return []

def fetch_users(token: str, search: str = None, limit: int = 50) -> List[Dict]:
    """Fetch users for selection"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if search:
        params["search"] = search

    try:
        response = requests.get(USERS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch users: {e}")
        return []

def fetch_game_presets() -> List[Dict]:
    """Fetch active game presets (no auth required for read)"""
    try:
        response = requests.get(f"{GAME_PRESETS_ENDPOINT}/")
        response.raise_for_status()
        data = response.json()
        return data.get("presets", [])
    except Exception as e:
        st.error(f"Failed to fetch game presets: {e}")
        return []

def fetch_preset_details(preset_id: int) -> Optional[Dict]:
    """Fetch full preset configuration"""
    try:
        response = requests.get(f"{GAME_PRESETS_ENDPOINT}/{preset_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch preset details: {e}")
        return None

def update_preset(token: str, preset_id: int, update_data: Dict) -> bool:
    """Update game preset"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.patch(
            f"{GAME_PRESETS_ENDPOINT}/{preset_id}",
            headers=headers,
            json=update_data
        )
        if response.status_code == 200:
            st.success("✅ Preset updated successfully!")
            return True
        else:
            st.error(f"Failed to update preset: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error updating preset: {e}")
        return False

def create_preset(token: str, preset_data: Dict) -> bool:
    """Create new game preset"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{GAME_PRESETS_ENDPOINT}/",
            headers=headers,
            json=preset_data
        )
        if response.status_code == 200:
            st.success("✅ Preset created successfully!")
            return True
        else:
            st.error(f"Failed to create preset: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error creating preset: {e}")
        return False

# Quick Test function REMOVED - only Instructor Workflow is supported now

def render_mini_leaderboard(tournament_id: int, token: str, title: str = "🏆 Current Standings"):
    """Render a compact leaderboard view for use in workflow steps"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        leaderboard_response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers=headers
        )

        if leaderboard_response.status_code == 200:
            leaderboard_data = leaderboard_response.json()

            st.markdown(f"### {title}")

            # Display leaderboard table
            if 'leaderboard' in leaderboard_data and leaderboard_data['leaderboard']:
                rankings = leaderboard_data['leaderboard']

                # Build table data
                table_data = []
                for rank_data in rankings[:10]:  # Show top 10
                    player_name = rank_data.get('name') or rank_data.get('username', 'Unknown')
                    gd = rank_data.get('goal_difference', 0)
                    table_data.append({
                        "🏆": f"#{rank_data.get('rank', '?')}",
                        "👤 Player": player_name,
                        "⭐ Pts": rank_data.get('points', 0),
                        "⚽ GF-GA": f"{rank_data.get('goals_for', 0)}-{rank_data.get('goals_against', 0)}",
                        "📈 GD": f"{gd:+d}" if gd != 0 else "0",
                        "📊": f"{rank_data.get('wins', 0)}W-{rank_data.get('draws', 0)}D-{rank_data.get('losses', 0)}L"
                    })

                st.table(table_data)

                # Show completion progress
                total_matches = leaderboard_data.get('total_matches', 0)
                completed_matches = leaderboard_data.get('completed_matches', 0)
                if total_matches > 0:
                    progress = completed_matches / total_matches
                    st.progress(progress)
                    st.caption(f"📊 Progress: {completed_matches}/{total_matches} matches completed ({progress*100:.0f}%)")
            else:
                st.info("ℹ️ No rankings yet. Submit match results to see standings.")

        else:
            st.warning(f"⚠️ Could not fetch leaderboard (Status: {leaderboard_response.status_code})")

    except Exception as e:
        st.error(f"❌ Error fetching leaderboard: {e}")

def render_configuration_screen():
    """Admin-Aligned Configuration Screen"""
    st.title("🧪 Sandbox Tournament Test (Admin-Aligned)")

    # Simple auth
    if "token" not in st.session_state:
        st.info("💡 **Admin Login Required**")
        col1, col2 = st.columns([2, 1])
        with col1:
            email = st.text_input("Admin Email", value="admin@lfa.com")
            password = st.text_input("Password", value="admin123", type="password")
        with col2:
            st.write("")
            st.write("")
            if st.button("🔑 Authenticate", use_container_width=True):
                token = get_auth_token(email, password)
                if token:
                    st.session_state.token = token
                    st.success("✅ Authenticated!")
                    st.rerun()
        st.stop()

    st.markdown("---")

    # Only Instructor Workflow mode (Quick Test removed)
    st.session_state.test_mode = "instructor"
    st.info("👨‍🏫 **Instructor Workflow**: Manually manage sessions, track attendance, enter results, and view live leaderboard before final rewards.")

    st.markdown("---")

    # 0️⃣ GAME TYPE SELECTION (PRESET-BASED)
    st.markdown("### 0️⃣ Game Type Selection")

    # Fetch available game presets
    presets = fetch_game_presets()

    if not presets:
        st.error("❌ No game presets available. Please contact administrator.")
        st.stop()

    # Sort presets: recommended first, then alphabetically
    sorted_presets = sorted(presets, key=lambda x: (not x.get('is_recommended', False), x['name']))

    # Initialize session state for selected preset if not exists
    if 'selected_preset_id' not in st.session_state:
        st.session_state.selected_preset_id = sorted_presets[0]['id']

    # Initialize editing state
    if 'editing_preset_id' not in st.session_state:
        st.session_state.editing_preset_id = None

    # Initialize creating state
    if 'creating_preset' not in st.session_state:
        st.session_state.creating_preset = False

    # Display presets as list with edit buttons
    col_header, col_create = st.columns([3, 1])
    with col_header:
        st.markdown("**Available Game Types:**")
    with col_create:
        if st.button("➕ Create New Preset", key="create_preset_button"):
            st.session_state.creating_preset = True
            st.session_state.editing_preset_id = None  # Close any open edits
            st.rerun()

    # CREATE NEW PRESET FORM
    if st.session_state.creating_preset:
        st.markdown("---")
        with st.container():
            st.markdown("### ➕ Create New Game Preset")

            # Import reusable form components
            from streamlit_preset_forms import (
                render_basic_info_editor,
                render_skill_config_editor,
                render_match_simulation_editor,
                render_ranking_rules_editor,
                render_metadata_editor,
                render_simulation_config_editor
            )

            # Key prefix for unique widgets
            key_prefix = "create_new"
            format_type = "HEAD_TO_HEAD"

            # Empty game config for new preset
            empty_game_config = {
                "skill_config": {},
                "format_config": {},
                "simulation_config": {},
                "metadata": {}
            }

            # === BASIC INFO ===
            with st.expander("📝 Basic Information", expanded=True):
                basic_info = render_basic_info_editor(
                    name="",
                    description="",
                    code="",
                    key_prefix=key_prefix
                )

            # === SKILL CONFIGURATION ===
            with st.expander("⚽ Skill Configuration", expanded=True):
                skill_config_data = render_skill_config_editor(
                    game_config=empty_game_config,
                    preset_id=None,
                    key_prefix=key_prefix
                )

            # === MATCH SIMULATION ===
            with st.expander("🎲 Match Simulation", expanded=False):
                match_sim_data = render_match_simulation_editor(
                    format_config=empty_game_config.get("format_config", {}),
                    format_type=format_type,
                    preset_id=None,
                    key_prefix=key_prefix
                )

            # === RANKING RULES ===
            with st.expander("🏆 Ranking Rules", expanded=False):
                ranking_data = render_ranking_rules_editor(
                    format_config=empty_game_config.get("format_config", {}),
                    format_type=format_type,
                    preset_id=None,
                    key_prefix=key_prefix
                )

            # === METADATA ===
            with st.expander("📋 Metadata", expanded=False):
                metadata_data = render_metadata_editor(
                    game_config=empty_game_config,
                    preset_id=None,
                    key_prefix=key_prefix
                )

            # === SIMULATION CONFIG (Optional) ===
            with st.expander("🎮 Simulation Configuration", expanded=False):
                simulation_data = render_simulation_config_editor(
                    game_config=empty_game_config,
                    preset_id=None,
                    key_prefix=key_prefix
                )

            # === CREATE AND CANCEL BUTTONS ===
            st.markdown("---")
            col_b1, col_b2, col_b3 = st.columns([1, 1, 2])

            with col_b1:
                if st.button("✅ Create Preset", type="primary", key=f"{key_prefix}_create", use_container_width=True):
                    # Validation
                    if not basic_info["code"] or not basic_info["name"]:
                        st.error("❌ Code and Name are required!")
                    elif not skill_config_data["skills_tested"]:
                        st.error("❌ Please select at least one skill!")
                    else:
                        # Build complete game_config
                        new_game_config = {
                            "version": "1.0",
                            "format_config": {
                                format_type: {
                                    "match_simulation": match_sim_data,
                                    "ranking_rules": ranking_data
                                }
                            },
                            "skill_config": skill_config_data,
                            "simulation_config": simulation_data,
                            "metadata": metadata_data
                        }

                        create_data = {
                            "code": basic_info["code"],
                            "name": basic_info["name"],
                            "description": basic_info["description"],
                            "game_config": new_game_config,
                            "is_active": True
                        }

                        if create_preset(st.session_state.token, create_data):
                            st.session_state.creating_preset = False
                            st.rerun()

            with col_b2:
                if st.button("❌ Cancel", type="secondary", key=f"{key_prefix}_cancel", use_container_width=True):
                    st.session_state.creating_preset = False
                    st.rerun()

        st.markdown("---")

    for preset in sorted_presets:
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

        # Create columns: name + info | badges | select button | edit button
        col1, col2, col3, col4 = st.columns([3, 1.5, 1, 1])

        with col1:
            st.markdown(f"**{preset_name}**")
            st.caption(f"🎮 {category} | 📊 {difficulty} | 👥 {player_info}")

        with col2:
            if badges:
                for badge in badges:
                    st.caption(badge)

        with col3:
            # Show "Selected" or "Select" button
            if st.session_state.selected_preset_id == preset_id:
                st.success("✅ Selected")
            else:
                if st.button("Select", key=f"select_preset_{preset_id}"):
                    st.session_state.selected_preset_id = preset_id
                    st.rerun()

        with col4:
            # Edit button - toggle inline edit mode
            if st.session_state.editing_preset_id == preset_id:
                if st.button("❌ Cancel", key=f"cancel_edit_{preset_id}", use_container_width=True):
                    st.session_state.editing_preset_id = None
                    st.rerun()
            else:
                if st.button("✏️ Edit", key=f"edit_preset_{preset_id}", use_container_width=True):
                    st.session_state.editing_preset_id = preset_id
                    st.rerun()

        # Inline edit form (if editing this preset)
        if st.session_state.editing_preset_id == preset_id:
            st.markdown("---")

            with st.container():
                st.markdown("### ✏️ Edit Game Preset")

                # Fetch full preset details
                preset_full = fetch_preset_details(preset_id)

                if preset_full:
                    st.info(f"ℹ️ Editing preset ID: {preset_id} - {preset_full.get('name', 'Unknown')}")

                    # Import reusable form components
                    from streamlit_preset_forms import (
                        render_basic_info_editor,
                        render_skill_config_editor,
                        render_match_simulation_editor,
                        render_ranking_rules_editor,
                        render_metadata_editor,
                        render_simulation_config_editor
                    )

                    # Get existing config
                    game_config = preset_full.get('game_config', {})
                    format_config = game_config.get('format_config', {})
                    simulation_config = game_config.get('simulation_config', {})

                    # Determine format type
                    format_type = list(format_config.keys())[0] if format_config else "HEAD_TO_HEAD"

                    # Key prefix for unique widgets
                    key_prefix = f"edit_{preset_id}"

                    # === BASIC INFO ===
                    with st.expander("📝 Basic Information", expanded=True):
                        basic_info = render_basic_info_editor(
                            name=preset_full.get('name', ''),
                            description=preset_full.get('description', ''),
                            code=preset_full.get('code', ''),
                            key_prefix=key_prefix
                        )

                    # === SKILL CONFIGURATION ===
                    with st.expander("⚽ Skill Configuration", expanded=True):
                        skill_config_data = render_skill_config_editor(
                            game_config=game_config,
                            preset_id=preset_id,
                            key_prefix=key_prefix
                        )

                    # === MATCH SIMULATION ===
                    with st.expander("🎲 Match Simulation", expanded=False):
                        match_sim_data = render_match_simulation_editor(
                            format_config=format_config,
                            format_type=format_type,
                            preset_id=preset_id,
                            key_prefix=key_prefix
                        )

                    # === RANKING RULES ===
                    with st.expander("🏆 Ranking Rules", expanded=False):
                        ranking_data = render_ranking_rules_editor(
                            format_config=format_config,
                            format_type=format_type,
                            preset_id=preset_id,
                            key_prefix=key_prefix
                        )

                    # === METADATA ===
                    with st.expander("📋 Metadata", expanded=False):
                        metadata_data = render_metadata_editor(
                            game_config=game_config,
                            preset_id=preset_id,
                            key_prefix=key_prefix
                        )

                    # === SIMULATION CONFIG (Optional) ===
                    with st.expander("🎮 Simulation Configuration", expanded=False):
                        simulation_data = render_simulation_config_editor(
                            game_config=game_config,
                            preset_id=preset_id,
                            key_prefix=key_prefix
                        )

                    # === SAVE AND CANCEL BUTTONS ===
                    st.markdown("---")
                    col_b1, col_b2, col_b3 = st.columns([1, 1, 2])

                    with col_b1:
                        if st.button("💾 Save Changes", type="primary", key=f"{key_prefix}_save", use_container_width=True):
                            # Build complete game_config
                            updated_game_config = {
                                "version": game_config.get("version", "1.0"),
                                "format_config": {
                                    format_type: {
                                        "match_simulation": match_sim_data,
                                        "ranking_rules": ranking_data
                                    }
                                },
                                "skill_config": skill_config_data,
                                "simulation_config": simulation_data,
                                "metadata": metadata_data
                            }

                            update_data = {
                                "name": basic_info["name"],
                                "description": basic_info["description"],
                                "game_config": updated_game_config
                            }

                            if update_preset(st.session_state.token, preset_id, update_data):
                                st.session_state.editing_preset_id = None
                                st.rerun()

                    with col_b2:
                        if st.button("❌ Cancel", type="secondary", key=f"{key_prefix}_cancel", use_container_width=True):
                            st.session_state.editing_preset_id = None
                            st.rerun()

        st.markdown("---")

    # Get selected preset details
    selected_preset_id = st.session_state.selected_preset_id
    selected_preset = next((p for p in presets if p['id'] == selected_preset_id), None)

    if not selected_preset:
        st.error("❌ Selected preset not found.")
        st.stop()

    # Fetch full preset details
    preset_details = fetch_preset_details(selected_preset_id)

    if preset_details:
        # Display preset preview (read-only)
        with st.expander("📋 Preset Configuration Preview (Read-Only)", expanded=False):
            st.markdown(f"**Description:** {preset_details.get('description', 'N/A')}")

            game_config = preset_details.get('game_config', {})
            skill_config = game_config.get('skill_config', {})
            format_config = game_config.get('format_config', {})

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**⚽ Skills Tested:**")
                skills = skill_config.get('skills_tested', [])
                for skill in skills:
                    st.markdown(f"- {skill.replace('_', ' ').title()}")

                st.markdown("**📊 Skill Weights:**")
                weights = skill_config.get('skill_weights', {})
                for skill, weight in weights.items():
                    st.markdown(f"- {skill.replace('_', ' ').title()}: {weight * 100:.0f}%")

            with col_b:
                st.markdown("**🎲 Match Probabilities:**")
                h2h_config = format_config.get('HEAD_TO_HEAD', {})
                match_sim = h2h_config.get('match_simulation', {})
                if match_sim:
                    st.markdown(f"- Draw: {match_sim.get('draw_probability', 0) * 100:.0f}%")
                    st.markdown(f"- Home Win: {match_sim.get('home_win_probability', 0) * 100:.0f}%")
                    away_prob = 1.0 - match_sim.get('draw_probability', 0) - match_sim.get('home_win_probability', 0)
                    st.markdown(f"- Away Win: {away_prob * 100:.0f}%")

        # Store preset configuration for tournament creation
        st.session_state.preset_overrides = {}  # No overrides - use preset as-is
        st.session_state.preset_skills = skill_config.get('skills_tested', [])
        st.session_state.preset_weights = skill_config.get('skill_weights', {})
        st.session_state.selected_preset_id = selected_preset_id

    else:
        st.error("❌ Failed to load preset details")
        st.stop()

    st.markdown("---")

    # 1️⃣ LOCATION & CAMPUS (Admin exact structure - sequential, not columns!)
    st.markdown("### 1️⃣ Location & Campus")

    st.markdown("**Location ***")
    locations = fetch_locations(st.session_state.token)

    if locations:
        location_options = {f"{loc['name']} ({loc['city']})": loc for loc in locations}
        location_display = st.selectbox(
            "Select location",
            options=list(location_options.keys()),
            key="location_select",
            label_visibility="collapsed"
        )
        selected_location = location_options[location_display]
        location_id = selected_location['id']
        st.caption(f"✓ Selected: {location_display} (ID: {location_id})")
    else:
        st.error("❌ No locations available")
        st.stop()

    st.markdown("**Campus ***")
    # Fetch campuses filtered by the selected location
    campuses = fetch_campuses_by_location(st.session_state.token, location_id)

    if campuses:
        campus_options = {c['name']: c['id'] for c in campuses}
        campus_display = st.selectbox(
            "Select campus",
            options=list(campus_options.keys()),
            key="campus_select",
            label_visibility="collapsed"
        )
        campus_id = campus_options[campus_display]
        st.caption(f"✓ Selected: {campus_display} (ID: {campus_id})")
    else:
        st.error(f"❌ No campuses available for {location_display}")
        st.stop()

    st.markdown("---")

    # 2️⃣ REWARD CONFIGURATION V2 (Admin-grade)
    st.markdown("### 2️⃣ Reward Configuration")

    # Get preset skills and weights (already defined in Game Preset)
    preset_skills = st.session_state.get('preset_skills', [])
    preset_weights_dict = st.session_state.get('preset_weights', {})
    selected_skills = preset_skills
    skill_weights = preset_weights_dict

    # 🎁 REWARD CONFIGURATION - NO EXPANDER, ALWAYS VISIBLE
    st.markdown("### 5️⃣ Reward Configuration")
    st.info("💡 Pre-filled from Game Preset - modify if needed")

    st.markdown("#### 📋 Reward Template")
    reward_template = st.selectbox(
        "Select reward template",
        options=["Standard", "Custom"],
        help="Standard: Pre-configured rewards. Custom: Manual configuration.",
        key="reward_template_select"
    )

    if reward_template == "Standard":
        st.success("✓ Loaded Standard template")

    # Show which preset is being used
    if preset_skills:
        st.info(f"ℹ️ **Skills from Game Preset**: {len(preset_skills)} skills selected from **{selected_preset.get('name', 'Unknown')}** preset")

    st.markdown("---")
    st.markdown("#### 🏆 Badge Configuration")

    # Simplified badge config for MVP
    st.markdown("**🥇 1st Place Rewards**")
    col1, col2 = st.columns(2)
    with col1:
        first_place_credits = st.number_input("💎 Credits", value=500, step=10, key="1st_credits")
    with col2:
        first_place_xp = st.number_input("⭐ XP Multiplier", value=1.5, step=0.1, key="1st_xp")

    st.markdown("**🥈 2nd Place Rewards**")
    col1, col2 = st.columns(2)
    with col1:
        second_place_credits = st.number_input("💎 Credits", value=300, step=10, key="2nd_credits")
    with col2:
        second_place_xp = st.number_input("⭐ XP Multiplier", value=1.2, step=0.1, key="2nd_xp")

    st.markdown("**🥉 3rd Place Rewards**")
    col1, col2 = st.columns(2)
    with col1:
        third_place_credits = st.number_input("💎 Credits", value=200, step=10, key="3rd_credits")
    with col2:
        third_place_xp = st.number_input("⭐ XP Multiplier", value=1.0, step=0.1, key="3rd_xp")

    st.markdown("---")
    st.markdown("#### ✓ Configuration Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Skills", len(selected_skills))
    with col2:
        st.metric("1st Place Badges", 1)  # Simplified
    with col3:
        st.metric("Total Credits (1st)", first_place_credits)
    with col4:
        st.metric("XP Multiplier (1st)", f"{first_place_xp}x")

    st.markdown("---")

    # 3️⃣ TOURNAMENT FORMAT (Admin exact structure)
    st.markdown("### 3️⃣ Tournament Format")

    format_selected = st.selectbox(
        "Format *",
        options=FORMATS,
        format_func=lambda x: "HEAD_TO_HEAD (1v1 matches)" if x == "HEAD_TO_HEAD" else "INDIVIDUAL_RANKING (placement-based)",
        help="Tournament format type"
    )

    tournament_name = st.text_input(
        "Tournament Name *",
        value=f"Sandbox Test {datetime.now().strftime('%Y-%m-%d')}",
        placeholder="e.g., Spring League 2026"
    )

    tournament_date = st.date_input(
        "Tournament Date *",
        value=datetime.now().date(),
        help="Tournament start date"
    )

    age_group = st.selectbox(
        "Age Group *",
        options=AGE_GROUPS,
        index=0,
        help="Target age group for this tournament"
    )

    st.markdown("---")

    # 4️⃣ TOURNAMENT CONFIGURATION (Admin exact structure)
    st.markdown("### 4️⃣ Tournament Configuration")

    assignment_type = st.selectbox(
        "Assignment Type *",
        options=ASSIGNMENT_TYPES,
        help="How players are assigned to this tournament"
    )

    max_players = st.number_input(
        "Max Players *",
        min_value=4,
        max_value=64,
        value=16,
        step=1,
        key="max_players",
        help="Maximum number of participants"
    )

    price_credits = st.number_input(
        "Price (Credits) *",
        min_value=0,
        max_value=10000,
        value=100,
        step=10,
        help="Cost for participants to join"
    )

    st.markdown("---")

    # 5️⃣ TOURNAMENT TYPE CONFIGURATION (Admin exact structure - AT THE END)
    st.markdown("### 5️⃣ Tournament Type Configuration")

    tournament_type = st.selectbox(
        "Tournament Type",
        options=TOURNAMENT_TYPES,
        help="Select tournament type (None = Manual configuration)"
    )

    if tournament_type and tournament_type != "None":
        st.info("📋 Sessions will be auto-generated based on tournament type after creation.")
    else:
        st.info("📋 Sessions will be configured manually in Tournament Management after creation.")

    st.markdown("---")

    # 6️⃣ PARTICIPANT SELECTION - TERV A: SIMPLE CHECKBOXES, SINGLE COLUMN
    st.markdown("### 6️⃣ Participant Selection (Select 4-16 players)")
    st.info("💡 Select users to enroll. Simple checkboxes - click to select.")

    # Search (optional)
    search_users = st.text_input("🔍 Search users", placeholder="Search by name or email...", key="participant_search")
    users = fetch_users(st.session_state.token, search=search_users, limit=50)

    selected_user_ids = []

    if users:
        st.markdown(f"**Available Users** ({len(users)} found)")

        # 🎯 TERV A: Simple single-column checkboxes - PLAYWRIGHT FRIENDLY!
        for user in users:
            # Simple checkbox with clear label format: [ID] Name (email)
            is_selected = st.checkbox(
                f"[{user['id']}] {user['name']} ({user['email']})",
                value=False,
                key=f"participant_{user['id']}"
            )

            if is_selected:
                selected_user_ids.append(user['id'])

        if selected_user_ids:
            st.success(f"✅ Selected: {len(selected_user_ids)} users → IDs: {selected_user_ids}")

    st.markdown("---")

    # 7️⃣ ADVANCED GAME SETTINGS - NO EXPANDERS, ALWAYS VISIBLE
    st.markdown("### 7️⃣ Advanced Game Settings (Optional)")
    st.info("💡 **Game Configuration**: Customize match simulation rules, probabilities, and testing options. Uses default values if not changed.")

    # Initialize default values
    draw_probability = 0.20
    home_win_probability = 0.40
    random_seed = None
    deterministic_mode = False
    performance_variation = "MEDIUM"
    ranking_distribution = "NORMAL"

    # 7️⃣ ADVANCED GAME SETTINGS - ALL REMOVED (use defaults)
    # These settings are not implemented in backend, using defaults
    draw_probability = 0.20
    home_win_probability = 0.40
    away_win_probability = 0.40
    performance_variation = "MEDIUM"
    ranking_distribution = "NORMAL"
    deterministic_mode = False
    random_seed = None

    st.markdown("---")

    # Validation
    validation_errors = []

    if not campus_id:
        validation_errors.append("❌ Please select a campus")
    if not selected_skills:
        validation_errors.append("❌ Please select at least 1 skill")
    if not tournament_name:
        validation_errors.append("❌ Please provide a tournament name")

    if validation_errors:
        for error in validation_errors:
            st.error(error)

    # Run Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_button_disabled = len(validation_errors) > 0

        # Only Instructor Workflow mode
        if st.button(
            "👨‍🏫 Create Tournament & Start Workflow",
            type="primary",
            use_container_width=True,
            disabled=run_button_disabled
        ):
            # Build tournament config (admin-compatible + game_config + preset)
            tournament_config = {
                "tournament_type": tournament_type if tournament_type != "None" else None,
                "tournament_name": tournament_name,
                "tournament_date": tournament_date.isoformat(),
                "age_group": age_group,
                "format": format_selected,
                "assignment_type": assignment_type,
                "max_players": max_players,
                "price_credits": price_credits,
                "campus_id": campus_id,
                "skills_to_test": selected_skills,
                "skill_weights": skill_weights,
                "reward_config": {
                    "template": reward_template,
                    "first_place": {"credits": first_place_credits, "xp_multiplier": first_place_xp},
                    "second_place": {"credits": second_place_credits, "xp_multiplier": second_place_xp},
                    "third_place": {"credits": third_place_credits, "xp_multiplier": third_place_xp}
                },
                "user_ids": selected_user_ids if selected_user_ids else None,
                # Phase 4: Game Preset Integration
                "game_preset_id": st.session_state.get('selected_preset_id'),
                # Game Config parameters (only if overriding preset)
                "draw_probability": st.session_state.get('preset_overrides', {}).get('draw_probability') or draw_probability,
                "home_win_probability": st.session_state.get('preset_overrides', {}).get('home_win_probability') or home_win_probability,
                "performance_variation": performance_variation,
                "ranking_distribution": ranking_distribution
            }

            # Only add random_seed if deterministic mode is enabled
            if random_seed is not None:
                tournament_config["random_seed"] = random_seed

            st.session_state.tournament_config = tournament_config

            # Always go to Instructor Workflow (Quick Test removed)
            st.session_state.screen = "instructor_workflow"

            st.rerun()

# Quick Test screens REMOVED - only Instructor Workflow is supported now

def render_instructor_workflow():
    """Instructor workflow screen - step-by-step tournament management"""
    st.title("👨‍🏫 Instructor Workflow")

    # Initialize workflow state FIRST
    if "workflow_step" not in st.session_state:
        st.session_state.workflow_step = 1
        st.session_state.tournament_id = None

    # Progress indicator (Step 2 removed - sessions auto-generated in Step 1)
    workflow_steps = [
        "1️⃣ Create Tournament",
        "2️⃣ Track Attendance",
        "3️⃣ Enter Results",
        "4️⃣ View Leaderboard",
        "5️⃣ Distribute Rewards",
        "6️⃣ View History"
    ]

    # Display progress
    st.progress(st.session_state.workflow_step / len(workflow_steps))
    st.markdown(f"**Current Step**: {workflow_steps[st.session_state.workflow_step - 1]}")

    st.markdown("---")

    # Get config safely
    config = st.session_state.get('tournament_config', {})

    # Route to current step (Step 2 removed - sessions auto-generated)
    if st.session_state.workflow_step == 1:
        render_step_create_tournament(config)
    elif st.session_state.workflow_step == 2:
        render_step_track_attendance()
    elif st.session_state.workflow_step == 3:
        render_step_enter_results()
    elif st.session_state.workflow_step == 4:
        render_step_view_leaderboard()
    elif st.session_state.workflow_step == 5:
        render_step_distribute_rewards()
    elif st.session_state.workflow_step == 6:
        render_step_tournament_history()

def render_step_create_tournament(config):
    """Step 1: Create tournament"""
    st.markdown("### 1️⃣ Create Tournament")

    st.info("📋 **Tournament Configuration**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tournament Type", config.get('tournament_type', 'N/A'))
    with col2:
        st.metric("Max Players", config.get('max_players', 0))
    with col3:
        st.metric("Skills", len(config.get('skills_to_test', [])))

    with st.expander("📄 Full Configuration"):
        st.json(config)

    # Display Game Config if present
    if any(key in config for key in ["draw_probability", "home_win_probability", "random_seed", "performance_variation"]):
        with st.expander("🎮 Game Configuration (Advanced)", expanded=True):
            st.markdown("**Match Simulation Settings:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                draw_prob = config.get('draw_probability', 0.20)
                st.metric("🤝 Draw Probability", f"{draw_prob:.0%}")
            with col2:
                home_win = config.get('home_win_probability', 0.40)
                st.metric("🏠 Home Win", f"{home_win:.0%}")
            with col3:
                away_win = 1.0 - draw_prob - home_win
                st.metric("✈️ Away Win", f"{away_win:.0%}")

            st.markdown("**Performance Settings (INDIVIDUAL_RANKING):**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Performance Variation", config.get('performance_variation', 'MEDIUM'))
            with col2:
                st.metric("Ranking Distribution", config.get('ranking_distribution', 'NORMAL'))

            st.markdown("**Testing Options:**")
            random_seed = config.get('random_seed')
            if random_seed:
                st.success(f"✅ Deterministic Mode: Seed = {random_seed}")
            else:
                st.info("ℹ️ Random Mode (non-deterministic)")

    st.markdown("---")

    if st.button("✅ Create Tournament", type="primary", use_container_width=True):
        with st.spinner("Creating tournament..."):
            # Call API to create tournament (without running test)
            token = st.session_state.token
            headers = {"Authorization": f"Bearer {token}"}

            try:
                # Build API-compatible payload (matching RunTestRequest schema)
                api_payload = {
                    "tournament_type": config["tournament_type"],
                    "skills_to_test": config["skills_to_test"],
                    "player_count": config["max_players"],
                    "test_config": {
                        "performance_variation": config["performance_variation"],
                        "ranking_distribution": config["ranking_distribution"],
                        "game_preset_id": config.get("game_preset_id"),
                        "game_config_overrides": None  # TODO: Add overrides if needed
                    }
                }

                # 🔍 DEBUG PANEL
                with st.expander("🔍 Debug: Request Payload", expanded=False):
                    st.json(api_payload)

                response = requests.post(
                    f"{API_BASE_URL}/sandbox/run-test",
                    json=api_payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                # Store tournament ID and result
                tournament_id = result.get('tournament', {}).get('id')
                st.session_state.tournament_id = tournament_id
                st.session_state.tournament_result = result

                st.success(f"✅ Tournament created! ID: {tournament_id}")

                # Update tournament name to user's custom name (sandbox uses generic name)
                user_tournament_name = config.get('tournament_name', 'LFA Tournament')
                try:
                    name_update = requests.patch(
                        f"{API_BASE_URL}/semesters/{tournament_id}",
                        json={"name": user_tournament_name},
                        headers=headers
                    )
                    if name_update.status_code == 200:
                        st.success(f"✅ Tournament name set to: {user_tournament_name}")
                except Exception as e:
                    st.warning(f"⚠️ Could not update tournament name: {e}")

                # ✅ Sandbox endpoint automatically:
                # - Creates tournament
                # - Enrolls participants (APPROVED status)
                # - Runs full lifecycle (REWARDS_DISTRIBUTED)
                st.success("✅ Participants automatically enrolled by sandbox!")

                # Reset status to IN_PROGRESS for manual instructor workflow
                st.info("🔄 Resetting tournament to IN_PROGRESS for manual workflow...")
                try:
                    status_reset = requests.patch(
                        f"{API_BASE_URL}/semesters/{tournament_id}",
                        json={"tournament_status": "IN_PROGRESS"},
                        headers=headers
                    )
                    if status_reset.status_code == 200:
                        st.success("✅ Status reset to IN_PROGRESS")
                    else:
                        st.error(f"❌ Status reset failed: {status_reset.text}")
                except Exception as e:
                    st.error(f"❌ Status reset error: {e}")

                # Auto-generate sessions using tournament session generator
                st.info("🔄 Generating tournament sessions (matches/brackets)...")
                try:
                    session_gen_response = requests.post(
                        f"{API_BASE_URL}/tournaments/{tournament_id}/generate-sessions",
                        json={"parallel_fields": 1, "session_duration_minutes": 90, "break_minutes": 15},
                        headers=headers
                    )
                    if session_gen_response.status_code == 200:
                        session_data = session_gen_response.json()
                        sessions_count = session_data.get('sessions_generated_count', 0)
                        st.success(f"✅ {sessions_count} sessions auto-generated!")

                        # Fetch generated sessions for preview
                        st.markdown("---")
                        st.markdown("### 📅 Draw Preview")

                        try:
                            sessions_response = requests.get(
                                f"{API_BASE_URL}/sessions/?semester_id={tournament_id}",
                                headers=headers
                            )
                            if sessions_response.status_code == 200:
                                sessions_data = sessions_response.json()
                                sessions_list = sessions_data.get('sessions', []) if sessions_data else []

                                if sessions_list:
                                    # Display summary
                                    # Map tournament_type code to display name
                                    tournament_type_map = {
                                        'league': 'League (Round Robin)',
                                        'knockout': 'Single Elimination',
                                        'group_knockout': 'Group Stage + Knockout',
                                        'swiss': 'Swiss System',
                                        'multi_round_ranking': 'Multi-Round Ranking'
                                    }

                                    tournament_type_code = config.get('tournament_type', 'unknown')
                                    tournament_type_display = tournament_type_map.get(tournament_type_code, tournament_type_code.upper() if tournament_type_code else 'Unknown')
                                    format_type = config.get('format', 'Unknown').upper()

                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("🎮 Total Matches", len(sessions_list))
                                    with col2:
                                        st.metric("🏆 Tournament Type", tournament_type_display)
                                    with col3:
                                        st.metric("📋 Scoring Format", format_type)

                                    st.markdown("---")

                                    # Group sessions by round
                                    rounds_dict = {}
                                    for session in sessions_list:
                                        round_num = session.get('tournament_round', 0)
                                        if round_num not in rounds_dict:
                                            rounds_dict[round_num] = []
                                        rounds_dict[round_num].append(session)

                                    # Display matches by round
                                    for round_num in sorted(rounds_dict.keys()):
                                        round_sessions = rounds_dict[round_num]

                                        with st.expander(f"🔄 Round {round_num} ({len(round_sessions)} matches)", expanded=(round_num == 1)):
                                            for idx, session in enumerate(round_sessions, 1):
                                                col1, col2, col3 = st.columns([1, 3, 2])

                                                with col1:
                                                    st.markdown(f"**Match {idx}**")

                                                with col2:
                                                    session_title = session.get('title', f"Session {session.get('id')}")
                                                    st.markdown(f"📌 {session_title}")

                                                with col3:
                                                    date_start = session.get('date_start', 'N/A')
                                                    if date_start and date_start != 'N/A':
                                                        # Format datetime
                                                        try:
                                                            from datetime import datetime
                                                            dt = datetime.fromisoformat(date_start.replace('Z', '+00:00'))
                                                            st.markdown(f"🕐 {dt.strftime('%Y-%m-%d %H:%M')}")
                                                        except:
                                                            st.markdown(f"🕐 {date_start}")
                                                    else:
                                                        st.markdown("🕐 TBD")

                                    st.success("✅ Draw details shown above!")
                                else:
                                    st.info("ℹ️ No sessions found yet")
                            else:
                                st.warning("⚠️ Could not fetch session details")
                        except Exception as e:
                            st.warning(f"⚠️ Could not fetch sessions: {e}")

                    else:
                        st.warning(f"⚠️ Session auto-generation skipped: {session_gen_response.text}")
                except Exception as e:
                    st.warning(f"⚠️ Could not auto-generate sessions: {e}")

            except requests.exceptions.HTTPError as e:
                st.error(f"❌ Failed to create tournament: {e.response.status_code} {e.response.reason}")

                # 🔍 DEBUG: Show detailed error
                with st.expander("🔍 Debug: Error Details", expanded=True):
                    st.error(f"**Status Code**: {e.response.status_code}")
                    st.error(f"**Reason**: {e.response.reason}")
                    try:
                        error_detail = e.response.json()
                        st.json(error_detail)
                    except:
                        st.text(e.response.text)

            except Exception as e:
                st.error(f"❌ Failed to create tournament: {e}")

    # Show "View Results" button if tournament was created (sandbox completes full lifecycle)
    st.markdown("---")
    if st.session_state.get('tournament_id'):  # Safe check with .get()
        tournament_result = st.session_state.get('tournament_result')

        # DEBUG: Show what we have in session state
        with st.expander("🔍 DEBUG: Session State", expanded=True):
            st.write("**tournament_id:**", st.session_state.get('tournament_id'))
            st.write("**tournament_result exists:**", tournament_result is not None)
            if tournament_result:
                st.write("**tournament_result keys:**", list(tournament_result.keys()) if isinstance(tournament_result, dict) else "Not a dict")
                st.write("**Has 'final_standings':**", 'final_standings' in tournament_result if isinstance(tournament_result, dict) else False)
                st.json(tournament_result)

        # Check if sandbox returned full results
        if tournament_result and 'final_standings' in tournament_result:
            st.success("✅ Tournament completed automatically by sandbox!")
            if st.button("📊 View Tournament Results", type="primary", use_container_width=True):
                st.session_state.workflow_step = 6  # Jump to results step
                st.rerun()
        else:
            # Manual workflow (not implemented yet for instructor)
            if st.button("➡️ Continue to Step 2: Track Attendance", type="primary", use_container_width=True):
                st.session_state.workflow_step = 2
                st.rerun()

def render_step_manage_sessions():
    """Step 2: Manage sessions"""
    st.markdown("### 2️⃣ Manage Sessions")

    tournament_id = st.session_state.tournament_id
    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    if not tournament_id:
        st.error("❌ Tournament ID not found. Please create tournament first.")
        return

    # Fetch existing sessions for this tournament
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions/?semester_id={tournament_id}",
            headers=headers
        )
        response.raise_for_status()
        sessions_data = response.json()
        sessions = sessions_data.get('sessions', [])
    except Exception as e:
        st.error(f"Failed to fetch sessions: {e}")
        sessions = []

    # Display sessions
    st.markdown(f"#### 📅 Sessions for Tournament {tournament_id}")

    if sessions:
        for session in sessions:
            with st.expander(f"📅 Session {session.get('id')} - {session.get('scheduled_date', 'N/A')}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Time**: {session.get('scheduled_time', 'N/A')}")
                with col2:
                    st.write(f"**Duration**: {session.get('duration_minutes', 0)} min")
                with col3:
                    st.write(f"**Status**: {session.get('status', 'SCHEDULED')}")
    else:
        st.info("ℹ️ No sessions found for this tournament yet.")

    st.markdown("---")

    # Add new session form
    with st.form("add_session_form"):
        st.markdown("#### ➕ Add New Session")

        col1, col2 = st.columns(2)
        with col1:
            session_date = st.date_input("Session Date", value=datetime.now().date())
            session_time = st.time_input("Session Time", value=datetime.now().time())
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=30, max_value=300, value=90, step=15)

        submitted = st.form_submit_button("➕ Create Session", type="primary")

        if submitted:
            # Create session
            session_payload = {
                "semester_id": tournament_id,
                "scheduled_date": session_date.isoformat(),
                "scheduled_time": session_time.strftime("%H:%M:%S"),
                "duration_minutes": duration,
                "location": "TBD",  # Will be inherited from campus
                "session_type": "TRAINING"
            }

            try:
                response = requests.post(
                    f"{API_BASE_URL}/sessions/",
                    json=session_payload,
                    headers=headers
                )
                response.raise_for_status()
                st.success("✅ Session created successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create session: {e}")

    st.markdown("---")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.workflow_step = 1
            st.rerun()
    with col2:
        if len(sessions) > 0:
            if st.button("➡️ Next: Track Attendance", type="primary"):
                st.session_state.workflow_step = 3
                st.rerun()
        else:
            st.warning("⚠️ Please create at least one session before proceeding")

def render_step_track_attendance():
    """Step 2: Track attendance"""
    st.markdown("### 2️⃣ Track Attendance")

    tournament_id = st.session_state.tournament_id
    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch sessions for this tournament
    try:
        sessions_response = requests.get(
            f"{API_BASE_URL}/sessions/?semester_id={tournament_id}",
            headers=headers
        )
        sessions_data = sessions_response.json()
        sessions = sessions_data.get('sessions', []) if sessions_data else []
    except Exception as e:
        st.error(f"❌ Failed to fetch sessions: {e}")
        sessions = []

    if not sessions:
        st.warning("⚠️ No sessions found. Please create sessions in Step 2 first.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Sessions"):
                st.session_state.workflow_step = 2
                st.rerun()
        return

    # Show progress summary
    total_matches = len(sessions)
    matches_with_attendance = sum(1 for s in sessions if s.get('attendance_count', 0) > 0)
    progress = matches_with_attendance / total_matches if total_matches > 0 else 0

    st.markdown("#### 📊 Tournament Progress")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Matches", total_matches)
    with col2:
        st.metric("Completed", matches_with_attendance)
    with col3:
        st.metric("Remaining", total_matches - matches_with_attendance)

    st.progress(progress)
    st.caption(f"Attendance recorded for {matches_with_attendance}/{total_matches} matches ({progress*100:.0f}%)")

    # ✅ Check if all attendance is complete
    if matches_with_attendance == total_matches:
        st.success("✅ All attendance recorded! Ready to enter results.")
        st.info("➡️ Click the button below to continue to results entry:")
        if st.button("🎯 Go to Enter Results", type="primary", use_container_width=True):
            st.session_state.workflow_step = 3  # Jump to Enter Results
            st.rerun()
        # ⛔ STOP HERE - Don't show session selector if all complete
        return

    st.markdown("---")

    # Select session with status indicators
    st.markdown("#### 📅 Select Session")
    session_options = {}
    for session in sessions:
        session_id = session.get('id')
        session_title = session.get('title', f'Session {session_id}')
        date_start = session.get('date_start', 'N/A')

        # Status indicators based on attendance_count
        attendance_count = session.get('attendance_count', 0)
        expected_participants = len(session.get('participant_user_ids', []))

        if attendance_count == 0:
            status_icon = "⚪"  # Not started
        elif attendance_count < expected_participants:
            status_icon = "🟡"  # Partial attendance
        else:
            status_icon = "✅"  # Complete attendance

        session_options[f"{status_icon} {session_title} - {date_start}"] = session_id

    selected_session_label = st.selectbox("Choose a session to mark attendance:", list(session_options.keys()))
    selected_session_id = session_options[selected_session_label]

    # Get selected session object
    selected_session = next((s for s in sessions if s['id'] == selected_session_id), None)
    if not selected_session:
        st.error(f"❌ Session {selected_session_id} not found")
        return

    st.markdown("---")

    # ✅ CRITICAL: Use participant_user_ids from session (not all tournament enrollments!)
    # For HEAD_TO_HEAD matches, this will be exactly 2 players
    participant_user_ids = selected_session.get('participant_user_ids', [])

    if not participant_user_ids:
        st.warning(f"⚠️ No participants assigned to this match yet")
        st.info("💡 This session doesn't have participant_user_ids. It may need to be regenerated.")
        return

    # Fetch ONLY the participants in this specific match
    try:
        enrollments_response = requests.get(
            f"{API_BASE_URL}/semester-enrollments/semesters/{tournament_id}/enrollments",
            headers=headers
        )
        all_enrollments = enrollments_response.json()

        # Filter to only participants in THIS match
        enrollments = [e for e in all_enrollments if e.get('user_id') in participant_user_ids]

    except Exception as e:
        st.error(f"❌ Failed to fetch participants: {e}")
        enrollments = []

    if not enrollments:
        st.warning("⚠️ No participants found for this match")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.workflow_step = 1
                st.rerun()
        return

    # Attendance form
    st.markdown(f"#### ✅ Mark Attendance")
    st.markdown(f"**Match**: {selected_session['title']}")
    st.info(f"👥 Participants in this match: {len(enrollments)}")

    attendance_records = []

    # Create attendance form for each participant
    for enrollment in enrollments:
        user_id = enrollment.get('user_id')
        # Prefer nickname, fallback to name, then email
        user_nickname = enrollment.get('user_nickname')
        user_name = enrollment.get('user_name')
        user_email = enrollment.get('user_email')
        display_name = user_nickname or user_name or user_email or f'User {user_id}'

        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"**👤 {display_name}**")

            with col2:
                # Simple checkbox: checked = PRESENT, unchecked = ABSENT
                is_present = st.checkbox(
                    "Present",
                    value=True,  # Default to PRESENT
                    key=f"attendance_status_{user_id}_{selected_session_id}",
                    label_visibility="collapsed"
                )

            status = "PRESENT" if is_present else "ABSENT"

            attendance_records.append({
                "user_id": user_id,
                "status": status,
                "notes": None  # Simplified - no notes field for speed
            })

    st.markdown("---")

    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Back"):
            st.session_state.workflow_step = 2
            st.rerun()

    with col2:
        if st.button("💾 Submit Attendance", type="primary", use_container_width=True):
            with st.spinner("Submitting attendance..."):
                success_count = 0
                failed_count = 0

                for record in attendance_records:
                    try:
                        # Individual POST for each user (no bulk endpoint exists)
                        attendance_response = requests.post(
                            f"{API_BASE_URL}/attendance/",
                            json={
                                "session_id": selected_session_id,
                                "user_id": record["user_id"],
                                "status": record["status"].lower(),  # "PRESENT" -> "present"
                                "notes": record.get("notes")
                            },
                            headers=headers
                        )

                        if attendance_response.status_code in [200, 201]:
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1

                if failed_count == 0:
                    st.success(f"✅ Attendance submitted for {success_count} participants!")
                    st.info("➡️ Moving to Step 3: Enter Results for this match...")
                    time.sleep(1)
                    # Save the selected session ID so Step 3 can pre-select it
                    st.session_state.last_attendance_session_id = selected_session_id
                    st.session_state.workflow_step = 3  # Move to Enter Results
                    st.rerun()
                else:
                    st.warning(f"⚠️ Submitted {success_count} successful, {failed_count} failed")

    with col3:
        if st.button("➡️ Next: Enter Results", type="secondary"):
            st.session_state.workflow_step = 4
            st.rerun()

    # Show current standings below the form
    st.markdown("---")
    render_mini_leaderboard(tournament_id, token, title="🏆 Current Standings")

def render_step_enter_results():
    """Step 3: Enter results"""
    st.markdown("### 3️⃣ Enter Results")

    tournament_id = st.session_state.tournament_id
    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch sessions for this tournament
    try:
        sessions_response = requests.get(
            f"{API_BASE_URL}/sessions/?semester_id={tournament_id}",
            headers=headers
        )
        sessions_response.raise_for_status()
        response_data = sessions_response.json()
        sessions = response_data.get('sessions', [])

        # Debug
        st.success(f"✅ API Response: {len(sessions)} matches found (Total: {response_data.get('total', 0)})")

    except Exception as e:
        st.error(f"❌ Failed to fetch sessions: {e}")
        st.code(f"URL: {API_BASE_URL}/sessions/?semester_id={tournament_id}")
        sessions = []

    if not sessions:
        st.warning("⚠️ No sessions found. Sessions should have been auto-generated in Step 1.")
        st.info("💡 Try going back to Step 1 and creating a new tournament, or check if sessions were generated.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Track Attendance"):
                st.session_state.workflow_step = 2
                st.rerun()
        return

    # Show progress summary
    total_matches = len(sessions)
    matches_with_attendance = sum(1 for s in sessions if s.get('attendance_count', 0) > 0)
    progress = matches_with_attendance / total_matches if total_matches > 0 else 0

    st.markdown("#### 📊 Tournament Progress")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Matches", total_matches)
    with col2:
        st.metric("Completed", matches_with_attendance)
    with col3:
        st.metric("Remaining", total_matches - matches_with_attendance)

    st.progress(progress)
    st.caption(f"Attendance recorded for {matches_with_attendance}/{total_matches} matches ({progress*100:.0f}%)")

    # ✅ Check if all results are complete via leaderboard API
    try:
        leaderboard_response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers=headers
        )
        if leaderboard_response.status_code == 200:
            leaderboard_data = leaderboard_response.json()
            completed_matches = leaderboard_data.get('completed_matches', 0)
            total_matches_lb = leaderboard_data.get('total_matches', total_matches)

            if completed_matches == total_matches_lb and completed_matches > 0:
                st.success("✅ All results recorded! Tournament complete.")
                st.info("➡️ Click the button below to view final standings and distribute rewards:")
                if st.button("🏆 View Final Leaderboard", type="primary", use_container_width=True):
                    st.session_state.workflow_step = 4  # Jump to View Leaderboard
                    st.rerun()
                # ⛔ STOP HERE - Don't show session selector if all complete
                return
    except Exception as e:
        pass  # Silently ignore if leaderboard check fails

    st.markdown("---")

    # Select session with status indicators
    st.markdown("#### 📅 Select Session")
    session_options = {}
    for session in sessions:
        session_id = session.get('id')
        session_title = session.get('title', f'Session {session_id}')
        date_start = session.get('date_start', 'N/A')

        # Status indicators based on attendance_count
        attendance_count = session.get('attendance_count', 0)
        expected_participants = len(session.get('participant_user_ids', []))

        if attendance_count == 0:
            status_icon = "⚪"  # Not started
        elif attendance_count < expected_participants:
            status_icon = "🟡"  # Partial attendance
        else:
            status_icon = "✅"  # Complete attendance

        session_options[f"{status_icon} {session_title} - {date_start}"] = session_id

    # Pre-select the session from attendance if available
    default_index = 0
    if 'last_attendance_session_id' in st.session_state:
        last_session_id = st.session_state.last_attendance_session_id
        # Find the index of this session in the options
        for idx, (label, sid) in enumerate(session_options.items()):
            if sid == last_session_id:
                default_index = idx
                break
        # Clear it after using once
        del st.session_state.last_attendance_session_id

    selected_session_label = st.selectbox(
        "Choose a session to enter results:",
        list(session_options.keys()),
        index=default_index,
        key="results_session_select"
    )
    selected_session_id = session_options[selected_session_label]

    # Get selected session object
    selected_session = next((s for s in sessions if s['id'] == selected_session_id), None)
    if not selected_session:
        st.error(f"❌ Session {selected_session_id} not found")
        return

    st.markdown("---")

    # ✅ CRITICAL: Use participant_user_ids from session (not all tournament enrollments!)
    # For HEAD_TO_HEAD matches, this will be exactly 2 players
    participant_user_ids = selected_session.get('participant_user_ids', [])

    if not participant_user_ids:
        st.warning(f"⚠️ No participants assigned to this match yet")
        st.info("💡 This session doesn't have participant_user_ids. It may need to be regenerated.")
        return

    st.info(f"👥 Match participants: {len(participant_user_ids)} players")

    # Fetch ONLY the participants in this specific match
    try:
        from app.models.user import User
        # We'll need to fetch user details for the participant_user_ids
        # Use the users API or enrollment API filtered by user_ids
        enrollments_response = requests.get(
            f"{API_BASE_URL}/semester-enrollments/semesters/{tournament_id}/enrollments",
            headers=headers
        )
        all_enrollments = enrollments_response.json()

        # Filter to only participants in THIS match
        enrollments = [e for e in all_enrollments if e.get('user_id') in participant_user_ids]

    except Exception as e:
        st.error(f"❌ Failed to fetch participants: {e}")
        enrollments = []

    if not enrollments:
        st.warning("⚠️ No participants found for this match")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.workflow_step = 2
                st.rerun()
        return

    # Results entry form - HEAD_TO_HEAD format
    st.markdown(f"#### ⚽ Enter Match Result")
    st.markdown(f"**Session**: {selected_session['title']}")

    match_format = selected_session.get('match_format', 'HEAD_TO_HEAD')
    st.caption(f"Format: {match_format}")

    results_records = []

    # HEAD_TO_HEAD: Simple 2-player score entry
    if len(enrollments) == 2:
        st.markdown("---")
        col1, col2 = st.columns(2)

        for idx, enrollment in enumerate(enrollments):
            user_id = enrollment.get('user_id')
            user_nickname = enrollment.get('user_nickname')
            user_name = enrollment.get('user_name')
            display_name = user_nickname or user_name or f'User {user_id}'

            with [col1, col2][idx]:
                st.markdown(f"### 👤 {display_name}")
                score = st.number_input(
                    "Goals/Points",
                    min_value=0,
                    max_value=50,
                    value=0,
                    step=1,
                    key=f"score_{user_id}_{selected_session_id}",
                    label_visibility="visible"
                )

                results_records.append({
                    "user_id": user_id,
                    "score": score
                })

    else:
        # Fallback for non-HEAD_TO_HEAD or incorrect participant count
        st.warning(f"⚠️ Expected 2 participants for HEAD_TO_HEAD, found {len(enrollments)}")
        for idx, enrollment in enumerate(enrollments):
            user_id = enrollment.get('user_id')
            user_nickname = enrollment.get('user_nickname')
            user_name = enrollment.get('user_name')
            display_name = user_nickname or user_name or f'User {user_id}'

            st.markdown(f"**{display_name}**")
            score = st.number_input(
                "Score",
                min_value=0,
                value=0,
                key=f"score_{user_id}_{selected_session_id}"
            )
            results_records.append({"user_id": user_id, "score": score})

    st.markdown("---")

    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Back"):
            st.session_state.workflow_step = 2
            st.rerun()

    with col2:
        if st.button("💾 Submit Results", type="primary", use_container_width=True):
            with st.spinner("Submitting results..."):
                try:
                    # Use the correct tournament API endpoint
                    results_response = requests.post(
                        f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{selected_session_id}/submit-results",
                        json={"results": results_records},
                        headers=headers
                    )

                    if results_response.status_code == 200:
                        st.success("✅ Results submitted successfully!")
                        st.info("➡️ Returning to Step 2: Track Attendance for next match...")
                        time.sleep(1)
                        st.session_state.workflow_step = 2  # Return to Track Attendance
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to submit results: {results_response.text}")
                except Exception as e:
                    st.error(f"❌ Error submitting results: {e}")

    with col3:
        if st.button("➡️ Next: View Leaderboard", type="secondary"):
            st.session_state.workflow_step = 5
            st.rerun()

    # Show current standings below the form
    st.markdown("---")
    render_mini_leaderboard(tournament_id, token, title="🏆 Current Standings")

def render_step_view_leaderboard():
    """Step 5: View leaderboard"""
    st.markdown("### 4️⃣ View Leaderboard")

    tournament_id = st.session_state.tournament_id
    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    # Debug info
    st.info(f"🔍 Tournament ID: {tournament_id}")

    # Check if sessions exist
    try:
        sessions_check = requests.get(
            f"{API_BASE_URL}/sessions/?semester_id={tournament_id}",
            headers=headers
        )
        sessions_data = sessions_check.json()
        sessions_count = len(sessions_data.get('sessions', [])) if sessions_data else 0
        st.success(f"✅ {sessions_count} matches found in tournament")
    except Exception as e:
        st.error(f"❌ Error checking sessions: {e}")

    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("#### 🏆 Tournament Leaderboard")
    with col2:
        auto_refresh = st.toggle("🔄 Auto-refresh", value=False, help="Refresh leaderboard every 5 seconds")

    # Manual refresh button
    if st.button("🔄 Refresh Now") or auto_refresh:
        if auto_refresh:
            time.sleep(5)
            st.rerun()

    st.markdown("---")

    # Fetch leaderboard
    try:
        leaderboard_response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers=headers
        )

        if leaderboard_response.status_code == 200:
            leaderboard_data = leaderboard_response.json()
        else:
            st.error(f"❌ Failed to fetch leaderboard: {leaderboard_response.text}")
            leaderboard_data = {}
    except Exception as e:
        st.error(f"❌ Error fetching leaderboard: {e}")
        leaderboard_data = {}

    if not leaderboard_data:
        st.warning("⚠️ No leaderboard data available yet. Submit some results first!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Enter Results"):
                st.session_state.workflow_step = 3  # Step 3 = Enter Results
                st.rerun()
        return

    # Extract leaderboard entries
    entries = leaderboard_data.get('leaderboard', [])

    if not entries:
        st.info("ℹ️ No entries in leaderboard yet. Submit some results first!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Enter Results"):
                st.session_state.workflow_step = 3  # Step 3 = Enter Results
                st.rerun()
        with col2:
            if st.button("➡️ Next: Distribute Rewards", type="secondary"):
                st.session_state.workflow_step = 5  # Step 5 = Distribute Rewards
                st.rerun()
        return

    # Create DataFrame for leaderboard with more details
    leaderboard_df = pd.DataFrame([
        {
            "🏆 Rank": f"#{entry.get('rank', 'N/A')}",
            "👤 Player": entry.get('name', 'Unknown'),
            "⭐ Points": entry.get('points', 0),
            "📊 W-D-L": f"{entry.get('wins', 0)}-{entry.get('draws', 0)}-{entry.get('losses', 0)}",
            "⚽ GF": entry.get('goals_for', 0),
            "🥅 GA": entry.get('goals_against', 0),
            "📈 GD": f"{entry.get('goal_difference', 0):+d}",
            "🎯 Win %": f"{(entry.get('wins', 0) / max(entry.get('wins', 0) + entry.get('losses', 0) + entry.get('draws', 0), 1) * 100):.0f}%"
        }
        for entry in entries
    ])

    # Display leaderboard table
    st.dataframe(
        leaderboard_df,
        hide_index=True,
        use_container_width=True,
        height=min(400, len(entries) * 40 + 50)  # Dynamic height based on entries
    )

    st.markdown("---")

    # Top 3 Performers Highlight
    st.markdown("#### 🏅 Top 3 Performers")
    col1, col2, col3 = st.columns(3)

    if len(entries) >= 1:
        with col1:
            player_name = entries[0].get('name', entries[0].get('email', 'Unknown'))
            wins = entries[0].get('wins', 0)
            losses = entries[0].get('losses', 0)
            st.metric(
                "🥇 1st Place",
                player_name,
                f"{entries[0].get('points', 0):.0f} pts"
            )
            st.caption(f"Record: {wins}W-{losses}L")

    if len(entries) >= 2:
        with col2:
            player_name = entries[1].get('name', entries[1].get('email', 'Unknown'))
            wins = entries[1].get('wins', 0)
            losses = entries[1].get('losses', 0)
            st.metric(
                "🥈 2nd Place",
                player_name,
                f"{entries[1].get('points', 0):.0f} pts"
            )
            st.caption(f"Record: {wins}W-{losses}L")

    if len(entries) >= 3:
        with col3:
            player_name = entries[2].get('name', entries[2].get('email', 'Unknown'))
            wins = entries[2].get('wins', 0)
            losses = entries[2].get('losses', 0)
            st.metric(
                "🥉 3rd Place",
                player_name,
                f"{entries[2].get('points', 0):.0f} pts"
            )
            st.caption(f"Record: {wins}W-{losses}L")

    st.markdown("---")

    # Check if all matches are complete
    completed_matches = leaderboard_data.get('completed_matches', 0)
    total_matches_lb = leaderboard_data.get('total_matches', 0)

    if completed_matches == total_matches_lb and completed_matches > 0:
        st.success(f"✅ Tournament Complete! All {total_matches_lb} matches finished.")
        st.info("🎁 Ready to distribute rewards to top performers!")
        if st.button("🎁 Distribute Rewards Now", type="primary", use_container_width=True):
            st.session_state.workflow_step = 6
            st.rerun()
        st.markdown("---")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Results"):
            st.session_state.workflow_step = 4
            st.rerun()
    with col2:
        if st.button("➡️ Distribute Rewards", type="secondary"):
            st.session_state.workflow_step = 6
            st.rerun()

def render_step_distribute_rewards():
    """Step 5: Distribute final rewards"""
    st.markdown("### 5️⃣ Distribute Rewards")

    tournament_id = st.session_state.tournament_id
    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    st.warning("⚠️ **Final Step**: This will finalize the tournament and distribute rewards!")
    st.markdown("Once rewards are distributed:")
    st.markdown("- ✅ Tournament status becomes REWARDS_DISTRIBUTED")
    st.markdown("- 🔒 Results can no longer be edited")
    st.markdown("- 💰 Credits and XP awarded to players")

    st.markdown("---")

    # Fetch final leaderboard for preview
    st.markdown("#### 📋 Final Standings Preview")
    try:
        leaderboard_response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers=headers
        )

        if leaderboard_response.status_code == 200:
            leaderboard_data = leaderboard_response.json()
            entries = leaderboard_data.get('leaderboard', [])

            if entries:
                # Display top 5 finishers
                preview_df = pd.DataFrame([
                    {
                        "Rank": f"#{entry.get('rank', 'N/A')}",
                        "Player": entry.get('username', 'Unknown'),
                        "Points": entry.get('points', 0),
                    }
                    for entry in entries[:5]
                ])

                st.dataframe(
                    preview_df,
                    hide_index=True,
                    use_container_width=True,
                    height=200
                )
            else:
                st.info("ℹ️ No leaderboard entries yet")
        else:
            st.warning("⚠️ Could not fetch final standings")
    except Exception as e:
        st.error(f"❌ Error fetching standings: {e}")

    st.markdown("---")

    # Confirmation checkbox
    confirm = st.checkbox("✅ I confirm that I want to distribute rewards and complete this tournament", value=False)

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Back to Leaderboard"):
            st.session_state.workflow_step = 4
            st.rerun()

    with col2:
        if st.button("🎁 Distribute Rewards & Complete", type="primary", use_container_width=True, disabled=not confirm):
            # 🐛 DEBUG: Log button click event
            st.write("🐛 **DEBUG: Button clicked!**")
            st.write(f"🐛 Tournament ID: {tournament_id}")
            st.write(f"🐛 Confirm checkbox: {confirm}")
            st.write(f"�� Button disabled: {not confirm}")

            with st.spinner("Distributing rewards..."):
                try:
                    # 🐛 DEBUG: Log API call start
                    st.write("🐛 **DEBUG: Starting API calls...**")

                    # First, ensure tournament status is COMPLETED
                    st.info("🔄 Setting tournament to COMPLETED status...")

                    # 🐛 DEBUG: Log PATCH request details
                    patch_url = f"{API_BASE_URL}/semesters/{tournament_id}"
                    st.write(f"🐛 PATCH URL: {patch_url}")
                    st.write(f"🐛 PATCH body: {{'tournament_status': 'COMPLETED'}}")

                    status_update = requests.patch(
                        patch_url,
                        json={"tournament_status": "COMPLETED"},
                        headers=headers
                    )

                    # 🐛 DEBUG: Log PATCH response
                    st.write(f"🐛 PATCH response status: {status_update.status_code}")
                    st.write(f"🐛 PATCH response body: {status_update.text[:200]}")

                    if status_update.status_code != 200:
                        st.error(f"❌ Failed to update tournament status: {status_update.text}")
                        st.stop()

                    st.success("✅ Tournament status set to COMPLETED")

                    # Now distribute rewards using V2 endpoint (includes skills)
                    st.info("💰 Distributing rewards (credits, XP, and skills)...")

                    # 🐛 DEBUG: Log POST request details
                    post_url = f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards-v2"
                    post_body = {
                        "tournament_id": tournament_id,
                        "force_redistribution": False
                    }
                    st.write(f"🐛 POST URL: {post_url}")
                    st.write(f"🐛 POST body: {post_body}")

                    rewards_response = requests.post(
                        post_url,
                        json=post_body,
                        headers=headers
                    )

                    # 🐛 DEBUG: Log POST response
                    st.write(f"🐛 POST response status: {rewards_response.status_code}")
                    st.write(f"🐛 POST response body: {rewards_response.text[:500]}")

                    if rewards_response.status_code == 200:
                        rewards_data = rewards_response.json()
                        st.success("✅ Rewards distributed successfully!")

                        # Show summary
                        if rewards_data.get('summary'):
                            st.json(rewards_data['summary'])

                        # Verify tournament status was updated to REWARDS_DISTRIBUTED
                        verify_url = f"{API_BASE_URL}/semesters/{tournament_id}"
                        st.write(f"🐛 GET verify URL: {verify_url}")

                        verify_response = requests.get(
                            verify_url,
                            headers=headers
                        )

                        st.write(f"🐛 GET verify status: {verify_response.status_code}")

                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            updated_status = verify_data.get('tournament_status') if verify_data else None
                            st.write(f"🐛 Verified tournament status: {updated_status}")

                            if updated_status == 'REWARDS_DISTRIBUTED':
                                st.success(f"✅ Tournament status: {updated_status}")
                            else:
                                st.warning(f"⚠️ Tournament status: {updated_status} (expected REWARDS_DISTRIBUTED)")

                        st.balloons()
                        time.sleep(2)

                        # Clear any cached tournament data
                        if 'selected_tournament_id' in st.session_state:
                            del st.session_state['selected_tournament_id']
                            st.write("🐛 Cleared cached tournament ID")

                        # Move to history step
                        st.write("🐛 Moving to workflow step 6 (History)")
                        st.session_state.workflow_step = 6
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to distribute rewards: {rewards_response.text}")
                        st.write(f"🐛 ERROR: Status {rewards_response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error distributing rewards: {e}")
                    st.write(f"🐛 EXCEPTION: {type(e).__name__}: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

    with col3:
        if st.button("📜 Skip to History", type="secondary"):
            st.session_state.workflow_step = 6
            st.rerun()

def render_step_tournament_history():
    """Step 6: View tournament results and history"""
    st.markdown("### 🏆 Tournament Results")

    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    # Check if we have a fresh tournament result from sandbox
    current_tournament_id = st.session_state.get('tournament_id')
    current_result = st.session_state.get('tournament_result')

    if current_tournament_id and current_result:
        st.success(f"✅ Displaying results for Tournament #{current_tournament_id}")

        # Show execution summary
        execution = current_result.get('execution_summary', {})
        verdict = current_result.get('verdict', 'UNKNOWN')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⚖️ Verdict", verdict)
        with col2:
            duration = execution.get('duration_seconds', 0)
            st.metric("⏱️ Duration", f"{duration:.2f}s")
        with col3:
            steps = len(execution.get('steps_completed', []))
            st.metric("✅ Steps", steps)

        # Fetch and display full tournament data from API
        try:
            tournament_detail = requests.get(
                f"{API_BASE_URL}/semesters/{current_tournament_id}",
                headers=headers
            ).json()

            # Tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(["�� Leaderboard", "🎯 Match Results", "🎁 Rewards", "📈 Skill Impact"])

            with tab1:
                # Fetch leaderboard
                leaderboard_response = requests.get(
                    f"{API_BASE_URL}/tournaments/{current_tournament_id}/leaderboard",
                    headers=headers
                )

                if leaderboard_response.status_code == 200:
                    leaderboard_data = leaderboard_response.json()
                    entries = leaderboard_data.get('leaderboard', [])

                    if entries:
                        leaderboard_df = pd.DataFrame([
                            {
                                "🏆 Rank": f"#{entry.get('rank', 'N/A')}",
                                "👤 Player": entry.get('name', 'Unknown'),
                                "⭐ Points": entry.get('points', 0),
                                "📊 W-D-L": f"{entry.get('wins', 0)}-{entry.get('draws', 0)}-{entry.get('losses', 0)}",
                                "⚽ GF": entry.get('goals_for', 0),
                                "🥅 GA": entry.get('goals_against', 0),
                                "📈 GD": f"{entry.get('goal_difference', 0):+d}",
                            }
                            for entry in entries
                        ])

                        st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("ℹ️ No leaderboard data yet")
                else:
                    st.error(f"❌ Failed to fetch leaderboard: {leaderboard_response.status_code}")

            with tab2:
                # Fetch all sessions/matches
                sessions_response = requests.get(
                    f"{API_BASE_URL}/sessions/?semester_id={current_tournament_id}",
                    headers=headers
                )

                if sessions_response.status_code == 200:
                    sessions_data = sessions_response.json()
                    sessions = sessions_data.get('sessions', [])

                    if sessions:
                        st.markdown(f"**Total Matches:** {len(sessions)}")

                        matches_df = pd.DataFrame([
                            {
                                "Match": s.get('title', 'N/A'),
                                "Home": s.get('home_user', {}).get('name', 'N/A'),
                                "Score": f"{s.get('home_score', '-')} - {s.get('away_score', '-')}",
                                "Away": s.get('away_user', {}).get('name', 'N/A'),
                                "Status": s.get('status', 'N/A')
                            }
                            for s in sessions
                        ])

                        st.dataframe(matches_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("ℹ️ No matches found")
                else:
                    st.error("❌ Failed to fetch matches")

            with tab3:
                st.info("🎁 Rewards data (coming soon)")

            with tab4:
                # Skill progression from sandbox result
                skill_progression = current_result.get('skill_progression', {})

                if skill_progression:
                    st.markdown("**Skill Changes:**")

                    skill_data = []
                    for user_id_str, skills in skill_progression.items():
                        for skill, change in skills.items():
                            if change != 0:
                                skill_data.append({
                                    "User ID": user_id_str,
                                    "Skill": skill.replace('_', ' ').title(),
                                    "Change": f"{change:+.2f}"
                                })

                    if skill_data:
                        skill_df = pd.DataFrame(skill_data)
                        st.dataframe(skill_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("ℹ️ No skill changes recorded")
                else:
                    st.info("ℹ️ No skill progression data available")

        except Exception as e:
            st.error(f"❌ Error fetching tournament data: {e}")

        st.markdown("---")

        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Run Another Test", use_container_width=True):
                # Clear session state and return to config
                st.session_state.workflow_step = 1
                st.session_state.tournament_id = None
                st.session_state.tournament_result = None
                st.rerun()

        with col2:
            if st.button("📚 View Tournament History", use_container_width=True):
                # Clear current result to show history view
                st.session_state.tournament_result = None
                st.rerun()

        return

    # Otherwise show tournament history browser
    st.info("📚 View past tournaments and export data for batch testing")

    # Fetch all tournaments
    try:
        tournaments_response = requests.get(
            f"{API_BASE_URL}/semesters/",
            headers=headers
        )

        if tournaments_response.status_code == 200:
            response_data = tournaments_response.json()

            # Check for None response
            if response_data is None:
                st.error("❌ Failed to fetch tournaments: Empty response")
                all_tournaments = []
            # Handle both dict {'semesters': [...]} and list [...] formats
            elif isinstance(response_data, dict):
                all_tournaments = response_data.get('semesters', [])
            else:
                all_tournaments = response_data

            # Filter sandbox tournaments
            sandbox_tournaments = [
                t for t in all_tournaments
                if 'SANDBOX' in t.get('code', '') or 'sandbox' in t.get('code', '').lower()
            ]

            st.markdown(f"#### 🏆 Found {len(sandbox_tournaments)} Sandbox Tournaments")

            if not sandbox_tournaments:
                st.warning("⚠️ No sandbox tournaments found yet. Create one first!")
            else:
                # Tournament selector
                tournament_options = {}
                for t in sorted(sandbox_tournaments, key=lambda x: x.get('created_at', ''), reverse=True):
                    # Safe date extraction - handle None values
                    created_at = t.get('created_at') or 'N/A'
                    date_str = created_at[:10] if created_at != 'N/A' else 'N/A'
                    label = f"{t.get('name', 'Unknown')} - {date_str} (ID: {t.get('id')})"
                    tournament_options[label] = t.get('id')

                selected_tournament_label = st.selectbox(
                    "Select tournament to view:",
                    list(tournament_options.keys())
                )
                selected_tournament_id = tournament_options[selected_tournament_label]

                st.markdown("---")

                # Wrap entire section in try-except for debugging
                try:
                    # Fetch tournament details
                    st.info(f"🔍 Fetching tournament details for ID: {selected_tournament_id}")

                    tournament_detail_response = requests.get(
                        f"{API_BASE_URL}/semesters/{selected_tournament_id}",
                        headers=headers
                    )

                    st.write(f"🔍 Response status: {tournament_detail_response.status_code}")

                    tournament_detail_response.raise_for_status()
                    tournament_detail = tournament_detail_response.json()

                    st.write(f"🔍 tournament_detail type: {type(tournament_detail)}")
                    st.write(f"🔍 tournament_detail is None: {tournament_detail is None}")

                    if tournament_detail is None:
                        st.error("❌ Tournament detail data is empty")
                        return

                    # Tournament summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tournament Name", tournament_detail.get('name', 'N/A'))
                    with col2:
                        st.metric("Status", tournament_detail.get('tournament_status', 'N/A'))
                    with col3:
                        st.metric("Format", tournament_detail.get('format', 'N/A'))
                except Exception as e:
                    st.error(f"❌ CRITICAL ERROR at line: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    return

                st.markdown("---")

                # 🔍 DEBUG PANEL - Show all tournament data
                with st.expander("🔍 DEBUG: Tournament Data", expanded=True):
                    st.write("**Tournament Detail Object:**")
                    st.json(tournament_detail)

                    st.write("**Key Values:**")
                    st.write(f"- tournament_status: `{tournament_detail.get('tournament_status')}`")
                    st.write(f"- tournament_type: `{tournament_detail.get('tournament_type')}`")
                    st.write(f"- format: `{tournament_detail.get('format')}`")
                    st.write(f"- code: `{tournament_detail.get('code')}`")
                    st.write(f"- id: `{tournament_detail.get('id')}`")

                    st.write("**API Endpoints to try:**")
                    st.code(f"GET {API_BASE_URL}/tournaments/{selected_tournament_id}/leaderboard")
                    st.code(f"GET {API_BASE_URL}/sessions/?semester_id={selected_tournament_id}")
                    st.code(f"GET {API_BASE_URL}/semester-enrollments/?semester_id={selected_tournament_id}")

                st.markdown("---")

                # Tabs - conditionally show Skill Impact only for REWARDS_DISTRIBUTED
                if tournament_detail.get('tournament_status') == 'REWARDS_DISTRIBUTED':
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Leaderboard", "🎯 Match Results", "🎁 Rewards", "📈 Skill Impact", "💾 Export JSON"])
                else:
                    # Skip Skill Impact tab for IN_PROGRESS tournaments
                    tab1, tab2, tab3, tab5 = st.tabs(["📊 Leaderboard", "🎯 Match Results", "🎁 Rewards", "💾 Export JSON"])
                    tab4 = None  # No Skill Impact tab

                with tab1:
                    # Check tournament status first
                    tournament_status = tournament_detail.get('tournament_status')

                    if tournament_status == 'DRAFT':
                        st.warning("⚠️ Tournament in DRAFT status")
                        st.info("📋 Sessions need to be generated before leaderboard is available")

                        # Show enrolled players instead
                        enrollments_response = requests.get(
                            f"{API_BASE_URL}/semester-enrollments/?semester_id={selected_tournament_id}",
                            headers=headers
                        )

                        if enrollments_response.status_code == 200:
                            enrollments_data = enrollments_response.json()
                            if enrollments_data is None:
                                st.warning("⚠️ Enrollments data is empty")
                                enrollments = []
                            else:
                                enrollments = enrollments_data.get('enrollments', [])

                            if enrollments:
                                st.markdown(f"**👥 Enrolled Players: {len(enrollments)}**")
                                enrollments_df = pd.DataFrame([
                                    {
                                        "👤 Player": (e.get('user') or {}).get('name', 'Unknown'),
                                        "📧 Email": (e.get('user') or {}).get('email', 'N/A'),
                                        "✅ Status": "Enrolled"
                                    }
                                    for e in enrollments
                                ])
                                st.dataframe(enrollments_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("ℹ️ No players enrolled yet")
                    else:
                        # Fetch leaderboard for non-DRAFT tournaments
                        st.info(f"🔍 DEBUG: Fetching leaderboard for tournament #{selected_tournament_id} (status: {tournament_status})")

                        leaderboard_response = requests.get(
                            f"{API_BASE_URL}/tournaments/{selected_tournament_id}/leaderboard",
                            headers=headers
                        )

                        # 🔍 DEBUG: Show response details
                        with st.expander("🔍 DEBUG: Leaderboard API Response", expanded=True):
                            st.write(f"**Status Code**: {leaderboard_response.status_code}")
                            st.write(f"**URL**: {leaderboard_response.url}")
                            st.write(f"**Headers**: {dict(leaderboard_response.headers)}")

                            try:
                                response_json = leaderboard_response.json()
                                st.write("**Response JSON**:")
                                st.json(response_json)
                            except Exception as e:
                                st.error(f"**Cannot parse JSON**: {e}")
                                st.write("**Raw Response Text**:")
                                st.code(leaderboard_response.text)

                        if leaderboard_response.status_code == 200:
                            leaderboard_data = leaderboard_response.json()
                            if leaderboard_data is None:
                                st.warning("⚠️ Leaderboard data is empty")
                                entries = []
                            else:
                                entries = leaderboard_data.get('leaderboard', [])

                            if entries:
                                leaderboard_df = pd.DataFrame([
                                    {
                                        "🏆 Rank": f"#{entry.get('rank', 'N/A')}",
                                        "👤 Player": entry.get('name', 'Unknown'),
                                        "⭐ Points": entry.get('points', 0),
                                        "📊 W-D-L": f"{entry.get('wins', 0)}-{entry.get('draws', 0)}-{entry.get('losses', 0)}",
                                        "⚽ GF": entry.get('goals_for', 0),
                                        "🥅 GA": entry.get('goals_against', 0),
                                        "📈 GD": f"{entry.get('goal_difference', 0):+d}",
                                    }
                                    for entry in entries
                                ])

                                st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("ℹ️ No leaderboard data yet")
                        else:
                            st.error(f"❌ Failed to fetch leaderboard")

                with tab2:
                    # Fetch all sessions/matches
                    sessions_response = requests.get(
                        f"{API_BASE_URL}/sessions/?semester_id={selected_tournament_id}",
                        headers=headers
                    )

                    if sessions_response.status_code == 200:
                        sessions_data = sessions_response.json()
                        if sessions_data is None:
                            st.warning("⚠️ Sessions data is empty")
                            sessions = []
                        else:
                            sessions = sessions_data.get('sessions', [])

                        if sessions:
                            st.markdown(f"**Total Matches:** {len(sessions)}")

                            matches_df = pd.DataFrame([
                                {
                                    "Match": s.get('title', 'N/A'),
                                    "Date": (s.get('date_start') or 'N/A')[:10] if s.get('date_start') else 'N/A',
                                    "Attendance": f"{s.get('attendance_count', 0)}/{len(s.get('participant_user_ids', []))}",
                                    "Status": "✅ Complete" if s.get('attendance_count', 0) > 0 else "⚪ Pending"
                                }
                                for s in sessions[:20]  # Show first 20
                            ])

                            st.dataframe(matches_df, hide_index=True, use_container_width=True)
                        else:
                            st.info("ℹ️ No matches found")
                    else:
                        st.error("❌ Failed to fetch matches")

                with tab3:
                    st.markdown("#### 🎁 Rewards Distribution Summary")

                    # Fetch rewards from tournament_participations table
                    import psycopg2
                    import json as json_lib

                    try:
                        conn = psycopg2.connect(
                            dbname="lfa_intern_system",
                            user="postgres",
                            password="postgres",
                            host="localhost",
                            port="5432"
                        )
                        cur = conn.cursor()

                        # Query tournament_participations
                        query = """
                        SELECT
                            u.name,
                            tp.placement,
                            tp.xp_awarded,
                            tp.credits_awarded,
                            tp.skill_points_awarded
                        FROM tournament_participations tp
                        JOIN users u ON tp.user_id = u.id
                        WHERE tp.semester_id = %s
                        ORDER BY tp.placement
                        """
                        cur.execute(query, (selected_tournament_id,))
                        participations = cur.fetchall()

                        cur.close()
                        conn.close()

                        if participations:
                            rewards_data = []
                            for name, placement, xp, credits, skills_json in participations:
                                # Count total skill points awarded
                                skill_points = skills_json if isinstance(skills_json, dict) else {}
                                total_skill_points = sum(skill_points.values()) if skill_points else 0

                                rewards_data.append({
                                    "Rank": f"#{placement}" if placement else "N/A",
                                    "Player": name,
                                    "XP Awarded": xp,
                                    "Credits Awarded": credits,
                                    "Total Skill Points": round(total_skill_points, 1)
                                })

                            rewards_df = pd.DataFrame(rewards_data)
                            st.dataframe(rewards_df, hide_index=True, use_container_width=True)

                            # Summary stats
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("💰 Total XP", sum([p[2] for p in participations]))
                            with col2:
                                st.metric("💳 Total Credits", sum([p[3] for p in participations]))
                            with col3:
                                st.metric("⚽ Participants", len(participations))
                        else:
                            st.warning("⚠️ No rewards have been distributed yet")

                    except Exception as e:
                        st.error(f"❌ Failed to load rewards: {str(e)}")
                        st.info("💡 Make sure rewards have been distributed using the V2 endpoint")

                # Only show Skill Impact tab if it exists (REWARDS_DISTRIBUTED tournaments)
                if tab4 is not None:
                    with tab4:
                        st.markdown("#### 📈 Skill Impact Analysis")
                        st.info("Track skill points awarded from THIS tournament")

                        # Get tournament reward config to see which skills were targeted
                        reward_config = tournament_detail.get('reward_config') or {}
                        tournament_skills = reward_config.get('skill_mappings', []) if isinstance(reward_config, dict) else []
                        enabled_skills = [s.get('skill', 'unknown') for s in tournament_skills if isinstance(s, dict) and s.get('enabled', True)]

                        st.markdown(f"**Tournament targeted {len(enabled_skills)} skills:** {', '.join(enabled_skills)}")
                        st.markdown("---")

                        # Fetch skill rewards from tournament_participations
                        import psycopg2
                        import json as json_lib

                        try:
                            conn = psycopg2.connect(
                                dbname="lfa_intern_system",
                                user="postgres",
                                password="postgres",
                                host="localhost",
                                port="5432"
                            )
                            cur = conn.cursor()

                            # Query tournament_participations for skill points awarded
                            query = """
                            SELECT
                                u.name,
                                tp.placement,
                                tp.skill_points_awarded
                            FROM tournament_participations tp
                            JOIN users u ON tp.user_id = u.id
                            WHERE tp.semester_id = %s
                            ORDER BY tp.placement
                            """
                            cur.execute(query, (selected_tournament_id,))
                            participations = cur.fetchall()

                            cur.close()
                            conn.close()

                            if participations:
                                st.markdown("### 📊 Skill Points Awarded by Player")

                                # Build data for visualization
                                skill_data = []
                                for name, placement, skills_json in participations:
                                    if skills_json:
                                        for skill_name, points in skills_json.items():
                                            # Only show enabled skills
                                            if skill_name in enabled_skills:
                                                skill_data.append({
                                                    'Player': name,
                                                    'Placement': placement,
                                                    'Skill': skill_name.replace('_', ' ').title(),
                                                    'Points Awarded': points
                                                })

                                if skill_data:
                                    df_skills = pd.DataFrame(skill_data)

                                    # Player selector
                                    selected_player = st.selectbox(
                                        "Select player to view skill points:",
                                        options=sorted(df_skills['Player'].unique().tolist())
                                    )

                                    # Show selected player's skills
                                    player_data = df_skills[df_skills['Player'] == selected_player].copy()

                                    st.markdown(f"### 👤 {selected_player}")
                                    placement = player_data['Placement'].iloc[0] if len(player_data) > 0 else 'N/A'
                                    st.markdown(f"**Placement:** #{placement}")
                                    st.markdown(f"**Skills rewarded:** {len(player_data)} skills")
                                    st.markdown("---")

                                    # Prepare display data with visual indicator
                                    display_rows = []
                                    for _, row in player_data.iterrows():
                                        points = row['Points Awarded']
                                        if points > 0:
                                            indicator = f"🟢 +{points:.1f}"
                                        else:
                                            indicator = "⚪ 0.0"

                                        display_rows.append({
                                            "Skill": row['Skill'],
                                            "Points Awarded": indicator
                                        })

                                    display_df = pd.DataFrame(display_rows)
                                    st.dataframe(display_df, hide_index=True, use_container_width=True)

                                    # Total summary
                                    total_points = player_data['Points Awarded'].sum()
                                    st.metric("💫 Total Skill Points", f"{total_points:.1f}")

                                else:
                                    st.warning("⚠️ No skill points found for enabled skills")

                            else:
                                st.warning("⚠️ No tournament participations found. Rewards may not have been distributed yet.")

                        except Exception as e:
                            st.error(f"❌ Database error: {e}")
                            st.info("Make sure PostgreSQL is running and rewards have been distributed")

                with tab5:
                    st.markdown("#### 💾 Export Tournament Data")

                    st.info("📦 Export complete tournament data as JSON for batch testing")

                    if st.button("📥 Generate JSON Export", type="primary"):
                        with st.spinner("Generating export..."):
                            # Compile all data
                            export_data = {
                                "tournament": tournament_detail,
                                "leaderboard": leaderboard_data if 'leaderboard_data' in locals() else {},
                                "sessions": sessions if 'sessions' in locals() else [],
                                "export_timestamp": datetime.now().isoformat()
                            }

                            # Display JSON
                            st.json(export_data)

                            # Download button
                            json_str = json.dumps(export_data, indent=2, default=str)
                            st.download_button(
                                label="⬇️ Download JSON",
                                data=json_str,
                                file_name=f"tournament_{selected_tournament_id}_export.json",
                                mime="application/json"
                            )
        else:
            st.error("❌ Failed to fetch tournaments")

    except Exception as e:
        st.error(f"❌ Error: {e}")

    st.markdown("---")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Rewards"):
            st.session_state.workflow_step = 5
            st.rerun()
    with col2:
        if st.button("🏠 New Tournament", type="primary"):
            st.session_state.screen = "configuration"
            st.session_state.workflow_step = 1
            st.rerun()

# Main App
def render_home_screen():
    """Home dashboard - starting point"""
    st.title("🏠 Tournament Sandbox - Home")

    # Auto-login if no token
    if "token" not in st.session_state:
        st.info("💡 **Auto-authenticating as admin...**")
        token = get_auth_token("admin@lfa.com", "admin123")
        if token:
            st.session_state.token = token
            st.success("✅ Authenticated!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Authentication failed. Please check API server.")
            st.stop()

    st.markdown("### Welcome to the Tournament Testing Sandbox")
    st.markdown("Choose an option to get started:")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 View Tournament History")
        st.markdown("Browse past tournaments, view results, and export data")
        st.markdown("")
        if st.button("📚 Open History", type="primary", use_container_width=True):
            st.session_state.screen = "history"
            st.rerun()

    with col2:
        st.markdown("### 🆕 Create New Tournament")
        st.markdown("Start the instructor workflow to create and manage a tournament")
        st.markdown("")
        if st.button("➕ New Tournament", type="primary", use_container_width=True):
            st.session_state.screen = "configuration"
            st.rerun()

    st.markdown("---")

    # Quick stats
    token = st.session_state.get('token')
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            tournaments_response = requests.get(f"{API_BASE_URL}/semesters/", headers=headers)
            if tournaments_response.status_code == 200:
                response_data = tournaments_response.json()
                # Handle both dict {'semesters': [...]} and list [...] formats
                all_tournaments = response_data.get('semesters', []) if isinstance(response_data, dict) else response_data
                sandbox_tournaments = [
                    t for t in all_tournaments
                    if 'SANDBOX' in t.get('code', '') or 'sandbox' in t.get('code', '').lower()
                ]

                st.markdown("### 📈 Quick Stats")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Sandbox Tournaments", len(sandbox_tournaments))
                with col2:
                    completed = sum(1 for t in sandbox_tournaments if t.get('tournament_status') == 'COMPLETED')
                    st.metric("Completed", completed)
                with col3:
                    in_progress = sum(1 for t in sandbox_tournaments if t.get('tournament_status') == 'IN_PROGRESS')
                    st.metric("In Progress", in_progress)
        except:
            pass

def render_history_screen():
    """Standalone history browser"""
    st.title("📚 Tournament History")

    # Check if token exists, if not redirect to login
    if 'token' not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Please log in first")
        if st.button("🔑 Go to Login"):
            st.session_state.screen = "home"
            st.rerun()
        return

    token = st.session_state.token
    headers = {"Authorization": f"Bearer {token}"}

    # This is essentially the same as Step 6 history, but as a standalone page
    try:
        tournaments_response = requests.get(f"{API_BASE_URL}/semesters/", headers=headers)

        if tournaments_response.status_code == 200:
            response_data = tournaments_response.json()

            # Check for None response
            if response_data is None:
                st.error("❌ Failed to fetch tournaments: Empty response")
                all_tournaments = []
            # Handle both dict {'semesters': [...]} and list [...] formats
            elif isinstance(response_data, dict):
                all_tournaments = response_data.get('semesters', [])
            else:
                all_tournaments = response_data
            sandbox_tournaments = [
                t for t in all_tournaments
                if 'SANDBOX' in t.get('code', '') or 'sandbox' in t.get('code', '').lower()
            ]

            st.markdown(f"#### 🏆 Found {len(sandbox_tournaments)} Sandbox Tournaments")

            if not sandbox_tournaments:
                st.warning("⚠️ No sandbox tournaments found yet. Create one first!")
                if st.button("🆕 Create New Tournament"):
                    st.session_state.screen = "configuration"
                    st.rerun()
            else:
                # Tournament selector
                tournament_options = {}
                for t in sorted(sandbox_tournaments, key=lambda x: x.get('created_at', ''), reverse=True):
                    # Safe date extraction - handle None values
                    created_at = t.get('created_at') or 'N/A'
                    date_str = created_at[:10] if created_at != 'N/A' else 'N/A'
                    label = f"{t.get('name', 'Unknown')} - {date_str} (ID: {t.get('id')})"
                    tournament_options[label] = t.get('id')

                selected_tournament_label = st.selectbox(
                    "Select tournament to view:",
                    list(tournament_options.keys())
                )
                selected_tournament_id = tournament_options[selected_tournament_label]

                st.markdown("---")

                # Fetch tournament details
                try:
                    tournament_detail_response = requests.get(
                        f"{API_BASE_URL}/semesters/{selected_tournament_id}",
                        headers=headers
                    )
                    tournament_detail_response.raise_for_status()
                    tournament_detail = tournament_detail_response.json()

                    if tournament_detail is None:
                        st.error("❌ Tournament detail data is empty")
                        return
                except Exception as e:
                    st.error(f"❌ Failed to fetch tournament details: {e}")
                    return

                # Tournament summary
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                with col1:
                    st.metric("Tournament Name", tournament_detail.get('name', 'N/A'))
                with col2:
                    st.metric("Status", tournament_detail.get('tournament_status', 'N/A'))
                with col3:
                    st.metric("Format", tournament_detail.get('format', 'N/A'))
                with col4:
                    # Add "Continue Tournament" button for DRAFT and IN_PROGRESS tournaments
                    if tournament_detail.get('tournament_status') == 'DRAFT':
                        st.markdown("")
                        st.markdown("")
                        if st.button("▶️ Continue Setup", type="primary", use_container_width=True):
                            # Load tournament into workflow
                            st.session_state.tournament_id = selected_tournament_id
                            st.session_state.screen = "instructor_workflow"
                            st.session_state.workflow_step = 1  # Start from Step 1 (Generate Sessions)

                            # Load tournament config from tournament detail
                            st.session_state.tournament_config = {
                                "tournament_type": tournament_detail.get('tournament_type'),
                                "tournament_name": tournament_detail.get('name'),
                                "tournament_date": tournament_detail.get('start_date'),
                                "age_group": tournament_detail.get('age_group'),
                                "format": tournament_detail.get('format'),
                                "assignment_type": tournament_detail.get('assignment_type'),
                                "max_players": tournament_detail.get('max_participants'),
                                "price_credits": tournament_detail.get('price_credits', 0),
                                "campus_id": tournament_detail.get('campus_id'),
                                "skills_to_test": [s['skill'] for s in (tournament_detail.get('reward_config') or {}).get('skill_mappings', []) if s.get('enabled', True)]
                            }

                            st.success("✅ Loaded tournament into workflow!")
                            time.sleep(0.5)
                            st.rerun()
                    elif tournament_detail.get('tournament_status') == 'IN_PROGRESS':
                        st.markdown("")
                        st.markdown("")
                        if st.button("▶️ Continue Tournament", type="primary", use_container_width=True):
                            # Check if tournament was auto-completed by sandbox (has final_standings in leaderboard)
                            has_final_standings = False
                            try:
                                leaderboard_check = requests.get(
                                    f"{API_BASE_URL}/tournaments/{selected_tournament_id}/leaderboard",
                                    headers=headers
                                )
                                if leaderboard_check.status_code == 200:
                                    leaderboard_data = leaderboard_check.json()
                                    if leaderboard_data and 'final_standings' in leaderboard_data:
                                        has_final_standings = True
                                        # Store tournament result for Step 6 display
                                        st.session_state.tournament_result = leaderboard_data
                            except:
                                pass

                            # Load tournament into workflow
                            st.session_state.tournament_id = selected_tournament_id
                            st.session_state.screen = "instructor_workflow"

                            # If tournament has final standings (sandbox completed it), jump to Step 6 (Results)
                            # Otherwise start from Step 2 (Manage Sessions for manual workflow)
                            st.session_state.workflow_step = 6 if has_final_standings else 2

                            # Load tournament config from tournament detail
                            st.session_state.tournament_config = {
                                "tournament_type": tournament_detail.get('tournament_type'),
                                "tournament_name": tournament_detail.get('name'),
                                "tournament_date": tournament_detail.get('start_date'),
                                "age_group": tournament_detail.get('age_group'),
                                "format": tournament_detail.get('format'),
                                "assignment_type": tournament_detail.get('assignment_type'),
                                "max_players": tournament_detail.get('max_participants'),
                                "price_credits": tournament_detail.get('price_credits', 0),
                                "campus_id": tournament_detail.get('campus_id'),
                                "skills_to_test": [s['skill'] for s in (tournament_detail.get('reward_config') or {}).get('skill_mappings', []) if s.get('enabled', True)]
                            }

                            st.success("✅ Loaded tournament into workflow!")
                            time.sleep(0.5)
                            st.rerun()

                st.markdown("---")

                # Tabs - conditionally show Skill Impact only for REWARDS_DISTRIBUTED
                if tournament_detail.get('tournament_status') == 'REWARDS_DISTRIBUTED':
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Leaderboard", "🎯 Match Results", "🎁 Rewards", "📈 Skill Impact", "💾 Export JSON"])
                else:
                    # Skip Skill Impact tab for IN_PROGRESS tournaments
                    tab1, tab2, tab3, tab5 = st.tabs(["📊 Leaderboard", "🎯 Match Results", "🎁 Rewards", "💾 Export JSON"])
                    tab4 = None  # No Skill Impact tab

                with tab1:
                    # Check tournament status first
                    tournament_status = tournament_detail.get('tournament_status')

                    if tournament_status == 'DRAFT':
                        st.warning("⚠️ Tournament in DRAFT status")
                        st.info("📋 Sessions need to be generated before leaderboard is available")

                        # Show enrolled players instead
                        enrollments_response = requests.get(
                            f"{API_BASE_URL}/semester-enrollments/?semester_id={selected_tournament_id}",
                            headers=headers
                        )

                        if enrollments_response.status_code == 200:
                            enrollments_data = enrollments_response.json()
                            if enrollments_data is None:
                                st.warning("⚠️ Enrollments data is empty")
                                enrollments = []
                            else:
                                enrollments = enrollments_data.get('enrollments', [])

                            if enrollments:
                                st.markdown(f"**👥 Enrolled Players: {len(enrollments)}**")
                                enrollments_df = pd.DataFrame([
                                    {
                                        "👤 Player": (e.get('user') or {}).get('name', 'Unknown'),
                                        "📧 Email": (e.get('user') or {}).get('email', 'N/A'),
                                        "✅ Status": "Enrolled"
                                    }
                                    for e in enrollments
                                ])
                                st.dataframe(enrollments_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("ℹ️ No players enrolled yet")
                    else:
                        # Fetch leaderboard for non-DRAFT tournaments
                        st.info(f"🔍 DEBUG: Fetching leaderboard for tournament #{selected_tournament_id} (status: {tournament_status})")

                        leaderboard_response = requests.get(
                            f"{API_BASE_URL}/tournaments/{selected_tournament_id}/leaderboard",
                            headers=headers
                        )

                        # 🔍 DEBUG: Show response details
                        with st.expander("🔍 DEBUG: Leaderboard API Response", expanded=True):
                            st.write(f"**Status Code**: {leaderboard_response.status_code}")
                            st.write(f"**URL**: {leaderboard_response.url}")
                            st.write(f"**Headers**: {dict(leaderboard_response.headers)}")

                            try:
                                response_json = leaderboard_response.json()
                                st.write("**Response JSON**:")
                                st.json(response_json)
                            except Exception as e:
                                st.error(f"**Cannot parse JSON**: {e}")
                                st.write("**Raw Response Text**:")
                                st.code(leaderboard_response.text)

                        if leaderboard_response.status_code == 200:
                            leaderboard_data = leaderboard_response.json()
                            if leaderboard_data is None:
                                st.warning("⚠️ Leaderboard data is empty")
                                entries = []
                            else:
                                entries = leaderboard_data.get('leaderboard', [])

                            if entries:
                                leaderboard_df = pd.DataFrame([
                                    {
                                        "🏆 Rank": f"#{entry.get('rank', 'N/A')}",
                                        "👤 Player": entry.get('name', 'Unknown'),
                                        "⭐ Points": entry.get('points', 0),
                                        "📊 W-D-L": f"{entry.get('wins', 0)}-{entry.get('draws', 0)}-{entry.get('losses', 0)}",
                                        "⚽ GF": entry.get('goals_for', 0),
                                        "🥅 GA": entry.get('goals_against', 0),
                                        "📈 GD": f"{entry.get('goal_difference', 0):+d}",
                                    }
                                    for entry in entries
                                ])

                                st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("ℹ️ No leaderboard data yet")
                        else:
                            st.error(f"❌ Failed to fetch leaderboard")

                with tab2:
                    sessions_response = requests.get(
                        f"{API_BASE_URL}/sessions/?semester_id={selected_tournament_id}",
                        headers=headers
                    )

                    if sessions_response.status_code == 200:
                        sessions_data = sessions_response.json()
                        if sessions_data is None:
                            st.warning("⚠️ Sessions data is empty")
                            sessions = []
                        else:
                            sessions = sessions_data.get('sessions', [])

                        if sessions:
                            st.markdown(f"**Total Matches:** {len(sessions)}")

                            matches_df = pd.DataFrame([
                                {
                                    "Match": s.get('title', 'N/A'),
                                    "Date": (s.get('date_start') or 'N/A')[:10] if s.get('date_start') else 'N/A',
                                    "Attendance": f"{s.get('attendance_count', 0)}/{len(s.get('participant_user_ids', []))}",
                                    "Status": "✅ Complete" if s.get('attendance_count', 0) > 0 else "⚪ Pending"
                                }
                                for s in sessions[:20]
                            ])

                            st.dataframe(matches_df, hide_index=True, use_container_width=True)

                with tab3:
                    st.markdown("#### 🎁 Rewards Distribution Summary")

                    # Fetch rewards from tournament_participations table
                    import psycopg2
                    import json as json_lib

                    try:
                        conn = psycopg2.connect(
                            dbname="lfa_intern_system",
                            user="postgres",
                            password="postgres",
                            host="localhost",
                            port="5432"
                        )
                        cur = conn.cursor()

                        # Query tournament_participations
                        query = """
                        SELECT
                            u.name,
                            tp.placement,
                            tp.xp_awarded,
                            tp.credits_awarded,
                            tp.skill_points_awarded
                        FROM tournament_participations tp
                        JOIN users u ON tp.user_id = u.id
                        WHERE tp.semester_id = %s
                        ORDER BY tp.placement
                        """
                        cur.execute(query, (selected_tournament_id,))
                        participations = cur.fetchall()

                        cur.close()
                        conn.close()

                        if participations:
                            rewards_data = []
                            for name, placement, xp, credits, skills_json in participations:
                                # Count total skill points awarded
                                skill_points = skills_json if isinstance(skills_json, dict) else {}
                                total_skill_points = sum(skill_points.values()) if skill_points else 0

                                rewards_data.append({
                                    "Rank": f"#{placement}" if placement else "N/A",
                                    "Player": name,
                                    "XP Awarded": xp,
                                    "Credits Awarded": credits,
                                    "Total Skill Points": round(total_skill_points, 1)
                                })

                            rewards_df = pd.DataFrame(rewards_data)
                            st.dataframe(rewards_df, hide_index=True, use_container_width=True)

                            # Summary stats
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("💰 Total XP", sum([p[2] for p in participations]))
                            with col2:
                                st.metric("💳 Total Credits", sum([p[3] for p in participations]))
                            with col3:
                                st.metric("⚽ Participants", len(participations))
                        else:
                            st.warning("⚠️ No rewards have been distributed yet")

                    except Exception as e:
                        st.error(f"❌ Failed to load rewards: {str(e)}")
                        st.info("💡 Make sure rewards have been distributed using the V2 endpoint")

                # Only show Skill Impact tab if it exists (REWARDS_DISTRIBUTED tournaments)
                if tab4 is not None:
                    with tab4:
                        st.markdown("#### 📈 Skill Impact Analysis")
                        st.info("Track skill points awarded from THIS tournament")

                        # Get tournament reward config to see which skills were targeted
                        reward_config = tournament_detail.get('reward_config') or {}
                        tournament_skills = reward_config.get('skill_mappings', []) if isinstance(reward_config, dict) else []
                        enabled_skills = [s.get('skill', 'unknown') for s in tournament_skills if isinstance(s, dict) and s.get('enabled', True)]

                        st.markdown(f"**Tournament targeted {len(enabled_skills)} skills:** {', '.join(enabled_skills)}")
                        st.markdown("---")

                        # Fetch skill rewards from tournament_participations
                        import psycopg2
                        import json as json_lib

                        try:
                            conn = psycopg2.connect(
                                dbname="lfa_intern_system",
                                user="postgres",
                                password="postgres",
                                host="localhost",
                                port="5432"
                            )
                            cur = conn.cursor()

                            # Query tournament_participations for skill points awarded
                            query = """
                            SELECT
                                u.name,
                                tp.placement,
                                tp.skill_points_awarded
                            FROM tournament_participations tp
                            JOIN users u ON tp.user_id = u.id
                            WHERE tp.semester_id = %s
                            ORDER BY tp.placement
                            """
                            cur.execute(query, (selected_tournament_id,))
                            participations = cur.fetchall()

                            cur.close()
                            conn.close()

                            if participations:
                                st.markdown("### 📊 Skill Points Awarded by Player")

                                # Build data for visualization
                                skill_data = []
                                for name, placement, skills_json in participations:
                                    if skills_json:
                                        for skill_name, points in skills_json.items():
                                            # Only show enabled skills
                                            if skill_name in enabled_skills:
                                                skill_data.append({
                                                    'Player': name,
                                                    'Placement': placement,
                                                    'Skill': skill_name.replace('_', ' ').title(),
                                                    'Points Awarded': points
                                                })

                                if skill_data:
                                    df_skills = pd.DataFrame(skill_data)

                                    # Player selector
                                    selected_player = st.selectbox(
                                        "Select player to view skill points:",
                                        options=sorted(df_skills['Player'].unique().tolist()),
                                        key="history_player_selector"
                                    )

                                    # Show selected player's skills
                                    player_data = df_skills[df_skills['Player'] == selected_player].copy()

                                    st.markdown(f"### 👤 {selected_player}")
                                    placement = player_data['Placement'].iloc[0] if len(player_data) > 0 else 'N/A'
                                    st.markdown(f"**Placement:** #{placement}")
                                    st.markdown(f"**Skills rewarded:** {len(player_data)} skills")
                                    st.markdown("---")

                                    # Prepare display data with visual indicator
                                    display_rows = []
                                    for _, row in player_data.iterrows():
                                        points = row['Points Awarded']
                                        if points > 0:
                                            indicator = f"🟢 +{points:.1f}"
                                        else:
                                            indicator = "⚪ 0.0"

                                        display_rows.append({
                                            "Skill": row['Skill'],
                                            "Points Awarded": indicator
                                        })

                                    display_df = pd.DataFrame(display_rows)
                                    st.dataframe(display_df, hide_index=True, use_container_width=True)

                                    # Total summary
                                    total_points = player_data['Points Awarded'].sum()
                                    st.metric("💫 Total Skill Points", f"{total_points:.1f}")

                                else:
                                    st.warning("⚠️ No skill points found for enabled skills")

                            else:
                                st.warning("⚠️ No tournament participations found. Rewards may not have been distributed yet.")

                        except Exception as e:
                            st.error(f"❌ Database error: {e}")
                            st.info("Make sure PostgreSQL is running and rewards have been distributed")

                with tab5:
                    st.markdown("#### 💾 Export Tournament Data")

                    if st.button("📥 Generate JSON Export", type="primary"):
                        with st.spinner("Generating export..."):
                            export_data = {
                                "tournament": tournament_detail,
                                "leaderboard": leaderboard_data if 'leaderboard_data' in locals() else {},
                                "sessions": sessions if 'sessions' in locals() else [],
                                "export_timestamp": datetime.now().isoformat()
                            }

                            st.json(export_data)

                            json_str = json.dumps(export_data, indent=2, default=str)
                            st.download_button(
                                label="⬇️ Download JSON",
                                data=json_str,
                                file_name=f"tournament_{selected_tournament_id}_export.json",
                                mime="application/json"
                            )
        else:
            st.error("❌ Failed to fetch tournaments")

    except Exception as e:
        st.error(f"❌ Error: {e}")

    st.markdown("---")

    if st.button("🏠 Back to Home"):
        st.session_state.screen = "home"
        st.rerun()

def main():
    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "home"
    if "test_mode" not in st.session_state:
        st.session_state.test_mode = "quick"

    # ========== SIDEBAR: Fresh Start Button ==========
    with st.sidebar:
        st.markdown("### 🧪 Sandbox Controls")

        # Show current screen info
        current_screen = st.session_state.screen
        if current_screen == "home":
            st.info("🏠 Home")
        elif current_screen == "history":
            st.info("📚 History Browser")
        elif current_screen == "configuration":
            st.info("📋 Configuration")
        elif current_screen == "instructor_workflow":
            workflow_step = st.session_state.get('workflow_step', 1)
            st.info(f"👨‍🏫 Workflow: Step {workflow_step}/6")

        st.markdown("---")

        # Refresh Current Page button
        if st.button("🔄 Refresh Page", use_container_width=True, help="Reload current page (stays on same step)"):
            st.rerun()

        # Home button (go back to home screen)
        if st.button("🏠 Back to Home", use_container_width=True, help="Return to home screen"):
            # Keep authentication but reset workflow
            keys_to_clear = [
                'test_mode', 'workflow_step',
                'tournament_id', 'tournament_result', 'tournament_config',
                'test_result', 'test_error'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            # Go to home
            st.session_state.screen = "home"
            st.session_state.workflow_step = 1

            st.success("✅ Returning home...")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")

        # Additional info
        st.markdown("**💡 Quick Tips:**")
        st.markdown("- Refresh Page: reload current step")
        st.markdown("- Back to Home: return to start")
        st.markdown("- No browser refresh needed")

        st.markdown("---")
        st.caption(f"🧪 Sandbox v3 | Screen: {current_screen}")

    # ========== MAIN CONTENT ==========
    # Route to screens
    if st.session_state.screen == "home":
        render_home_screen()
    elif st.session_state.screen == "history":
        render_history_screen()
    elif st.session_state.screen == "configuration":
        render_configuration_screen()
    elif st.session_state.screen == "instructor_workflow":
        render_instructor_workflow()
    # Quick Test screens ("progress", "results") REMOVED

if __name__ == "__main__":
    main()
