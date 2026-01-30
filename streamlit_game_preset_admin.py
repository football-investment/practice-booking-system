"""
🎮 Game Preset Admin UI
Streamlit interface for managing game presets
"""

import streamlit as st
import requests
import json
from typing import Dict, Any, List, Optional

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


def login() -> Optional[str]:
    """Login and get access token"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception as e:
        st.error(f"Login failed: {e}")
    return None


def get_headers(token: str) -> Dict[str, str]:
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}"}


def fetch_presets(token: str, active_only: bool = False) -> List[Dict]:
    """Fetch all game presets"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/game-presets/",
            params={"active_only": active_only}
        )
        if response.status_code == 200:
            return response.json()["presets"]
    except Exception as e:
        st.error(f"Failed to fetch presets: {e}")
    return []


def fetch_preset_detail(preset_id: int) -> Optional[Dict]:
    """Fetch detailed preset configuration"""
    try:
        response = requests.get(f"{API_BASE_URL}/game-presets/{preset_id}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch preset: {e}")
    return None


def create_preset(token: str, preset_data: Dict) -> bool:
    """Create new game preset"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/game-presets/",
            headers=get_headers(token),
            json=preset_data
        )
        if response.status_code == 201:
            st.success("✅ Preset created successfully!")
            return True
        else:
            st.error(f"Failed to create preset: {response.text}")
    except Exception as e:
        st.error(f"Error creating preset: {e}")
    return False


def update_preset(token: str, preset_id: int, preset_data: Dict) -> bool:
    """Update existing game preset"""
    try:
        response = requests.patch(
            f"{API_BASE_URL}/game-presets/{preset_id}",
            headers=get_headers(token),
            json=preset_data
        )
        if response.status_code == 200:
            st.success("✅ Preset updated successfully!")
            return True
        else:
            st.error(f"Failed to update preset: {response.text}")
    except Exception as e:
        st.error(f"Error updating preset: {e}")
    return False


def delete_preset(token: str, preset_id: int, hard_delete: bool = False) -> bool:
    """Delete game preset"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/game-presets/{preset_id}",
            headers=get_headers(token),
            params={"hard_delete": hard_delete}
        )
        if response.status_code == 204:
            st.success("✅ Preset deleted successfully!")
            return True
        else:
            st.error(f"Failed to delete preset: {response.text}")
    except Exception as e:
        st.error(f"Error deleting preset: {e}")
    return False


def render_skill_config_editor(game_config: Dict, preset_id: Optional[int] = None) -> Dict:
    """Render skill configuration editor"""
    st.subheader("⚽ Skill Configuration")

    skill_config = game_config.get("skill_config", {})

    # Import skill categories from skills_config
    from app.skills_config import SKILL_CATEGORIES

    # Generate unique key prefix based on preset_id or create mode
    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"

    # Skills tested
    st.write("**Skills Tested**")
    st.markdown("Select skills by category:")

    preset_skills = skill_config.get("skills_tested", [])
    skills_tested = []

    for category in SKILL_CATEGORIES:
        category_emoji = category["emoji"]
        category_name = category["name_en"]
        category_skills = category["skills"]

        with st.expander(f"{category_emoji} {category_name}", expanded=False):
            for skill_def in category_skills:
                skill_key = skill_def["key"]
                skill_name = skill_def["name_en"]

                # Check if skill is in preset defaults
                is_default = skill_key in preset_skills

                selected = st.checkbox(
                    f"{skill_name}",
                    value=is_default,
                    key=f"{key_prefix}_skill_{skill_key}",
                    help=f"Key: {skill_key}"
                )

                if selected:
                    skills_tested.append(skill_key)

    # Skill weights with multipliers
    st.write("**Skill Weights** (relative multipliers, auto-normalized)")
    st.caption("💡 Enter relative importance (e.g., 5, 3, 2) - will be auto-normalized to sum to 1.0")

    skill_multipliers = {}
    total_multiplier = 0.0

    # Get existing weights as multipliers (scale up from 0.0-1.0 to easier numbers)
    existing_weights = skill_config.get("skill_weights", {})

    for skill in skills_tested:
        # Convert existing weight to multiplier (scale by 10 for easier input)
        default_multiplier = existing_weights.get(skill, 1.0 / len(skills_tested)) * 10.0

        multiplier = st.number_input(
            f"{skill.replace('_', ' ').title()}",
            min_value=0.0,
            max_value=100.0,
            value=float(default_multiplier),
            step=0.5,
            key=f"{key_prefix}_weight_{skill}",
            help=f"Relative importance (will be normalized)"
        )
        skill_multipliers[skill] = multiplier
        total_multiplier += multiplier

    # Normalize to sum to 1.0
    skill_weights = {}
    if total_multiplier > 0:
        for skill, multiplier in skill_multipliers.items():
            skill_weights[skill] = multiplier / total_multiplier

        # Show normalized weights
        st.success(f"✅ Total multiplier: {total_multiplier:.2f} → Normalized to 1.0")

        with st.expander("📊 Normalized Weights Preview"):
            for skill, weight in skill_weights.items():
                st.write(f"- {skill.replace('_', ' ').title()}: **{weight:.3f}** ({weight * 100:.1f}%)")
    else:
        st.error("⚠️ Total multiplier is 0, please assign weights")

    skill_impact = st.checkbox(
        "Skill impact on matches",
        value=skill_config.get("skill_impact_on_matches", True)
    )

    return {
        "skills_tested": skills_tested,
        "skill_weights": skill_weights,
        "skill_impact_on_matches": skill_impact
    }


def render_match_simulation_editor(format_config: Dict, format_type: str, preset_id: Optional[int] = None) -> Dict:
    """Render match simulation editor for HEAD_TO_HEAD format"""
    st.subheader("🎲 Match Simulation")

    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"
    match_sim = format_config.get(format_type, {}).get("match_simulation", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        home_win_prob = st.number_input(
            "Home Win Probability",
            min_value=0.0,
            max_value=1.0,
            value=float(match_sim.get("home_win_probability", 0.45)),
            step=0.05,
            key=f"{key_prefix}_home_win_prob"
        )

    with col2:
        draw_prob = st.number_input(
            "Draw Probability",
            min_value=0.0,
            max_value=1.0,
            value=float(match_sim.get("draw_probability", 0.15)),
            step=0.05,
            key=f"{key_prefix}_draw_prob"
        )

    with col3:
        away_win_prob = st.number_input(
            "Away Win Probability",
            min_value=0.0,
            max_value=1.0,
            value=float(match_sim.get("away_win_probability", 0.40)),
            step=0.05,
            key=f"{key_prefix}_away_win_prob"
        )

    total_prob = home_win_prob + draw_prob + away_win_prob
    if abs(total_prob - 1.0) > 0.01:
        st.warning(f"⚠️ Total probability is {total_prob:.2f}, should be 1.0")

    st.write("**Score Ranges**")

    score_ranges = match_sim.get("score_ranges", {
        "win": {"winner_max": 3, "loser_max": 2},
        "draw": {"min": 0, "max": 2}
    })

    col1, col2 = st.columns(2)
    with col1:
        winner_max = st.number_input("Winner Max Score", value=score_ranges.get("win", {}).get("winner_max", 3), key=f"{key_prefix}_winner_max")
        loser_max = st.number_input("Loser Max Score", value=score_ranges.get("win", {}).get("loser_max", 2), key=f"{key_prefix}_loser_max")

    with col2:
        draw_min = st.number_input("Draw Min Score", value=score_ranges.get("draw", {}).get("min", 0), key=f"{key_prefix}_draw_min")
        draw_max = st.number_input("Draw Max Score", value=score_ranges.get("draw", {}).get("max", 2), key=f"{key_prefix}_draw_max")

    return {
        "home_win_probability": home_win_prob,
        "draw_probability": draw_prob,
        "away_win_probability": away_win_prob,
        "score_ranges": {
            "win": {"winner_max": winner_max, "loser_max": loser_max},
            "draw": {"min": draw_min, "max": draw_max}
        }
    }


def render_ranking_rules_editor(format_config: Dict, format_type: str, preset_id: Optional[int] = None) -> Dict:
    """Render ranking rules editor"""
    st.subheader("🏆 Ranking Rules")

    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"
    ranking = format_config.get(format_type, {}).get("ranking_rules", {})

    # Points system
    st.write("**Points System**")
    points_system = ranking.get("points_system", {"win": 3, "draw": 1, "loss": 0})

    col1, col2, col3 = st.columns(3)
    with col1:
        win_points = st.number_input("Win Points", value=points_system.get("win", 3), key=f"{key_prefix}_win_points")
    with col2:
        draw_points = st.number_input("Draw Points", value=points_system.get("draw", 1), key=f"{key_prefix}_draw_points")
    with col3:
        loss_points = st.number_input("Loss Points", value=points_system.get("loss", 0), key=f"{key_prefix}_loss_points")

    # Tiebreakers
    st.write("**Tiebreakers** (in order of priority)")
    tiebreakers = ranking.get("tiebreakers", ["goal_difference", "goals_for", "user_id"])

    available_tiebreakers = ["goal_difference", "goals_for", "goals_against", "user_id", "head_to_head"]
    selected_tiebreakers = st.multiselect(
        "Select tiebreakers",
        options=available_tiebreakers,
        default=tiebreakers,
        key=f"{key_prefix}_tiebreakers"
    )

    return {
        "primary": ranking.get("primary", "points"),
        "points_system": {
            "win": win_points,
            "draw": draw_points,
            "loss": loss_points
        },
        "tiebreakers": selected_tiebreakers
    }


def render_metadata_editor(game_config: Dict, preset_id: Optional[int] = None) -> Dict:
    """Render metadata editor"""
    st.subheader("📋 Metadata")

    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"
    metadata = game_config.get("metadata", {})

    col1, col2 = st.columns(2)

    with col1:
        game_category = st.selectbox(
            "Game Category",
            options=["beach_sports", "racquet_sports", "small_sided_games", "training_drills", "general"],
            index=["beach_sports", "racquet_sports", "small_sided_games", "training_drills", "general"].index(
                metadata.get("game_category", "general")
            ),
            key=f"{key_prefix}_game_category"
        )

        difficulty = st.selectbox(
            "Difficulty Level",
            options=["beginner", "intermediate", "advanced", "expert"],
            index=["beginner", "intermediate", "advanced", "expert"].index(
                metadata.get("difficulty_level", "intermediate")
            ),
            key=f"{key_prefix}_difficulty"
        )

    with col2:
        player_count = metadata.get("recommended_player_count", {"min": 4, "max": 16})
        min_players = st.number_input("Min Players", value=player_count.get("min", 4), min_value=2, key=f"{key_prefix}_min_players")
        max_players = st.number_input("Max Players", value=player_count.get("max", 16), min_value=min_players, key=f"{key_prefix}_max_players")

    return {
        "game_category": game_category,
        "difficulty_level": difficulty,
        "recommended_player_count": {"min": min_players, "max": max_players}
    }


def render_simulation_config_editor(game_config: Dict, preset_id: Optional[int] = None) -> Dict:
    """Render simulation configuration editor"""
    st.subheader("🧪 Simulation Configuration")

    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"
    sim_config = game_config.get("simulation_config", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        player_selection = st.selectbox(
            "Player Selection",
            options=["auto", "manual", "random"],
            index=["auto", "manual", "random"].index(sim_config.get("player_selection", "auto")),
            key=f"{key_prefix}_player_selection"
        )

    with col2:
        ranking_dist = st.selectbox(
            "Ranking Distribution",
            options=["NORMAL", "UNIFORM", "EXPONENTIAL"],
            index=["NORMAL", "UNIFORM", "EXPONENTIAL"].index(sim_config.get("ranking_distribution", "NORMAL")),
            key=f"{key_prefix}_ranking_dist"
        )

    with col3:
        perf_variation = st.selectbox(
            "Performance Variation",
            options=["LOW", "MEDIUM", "HIGH"],
            index=["LOW", "MEDIUM", "HIGH"].index(sim_config.get("performance_variation", "MEDIUM")),
            key=f"{key_prefix}_perf_variation"
        )

    return {
        "player_selection": player_selection,
        "ranking_distribution": ranking_dist,
        "performance_variation": perf_variation
    }


def render_preset_editor(preset: Optional[Dict] = None, token: str = None):
    """Render game preset editor form"""

    is_edit_mode = preset is not None

    st.subheader("🎮 Game Preset Editor")

    # Basic Info
    st.write("### Basic Information")

    preset_id = preset.get("id") if preset else None
    key_prefix = f"preset_{preset_id}" if preset_id else "new_preset"

    col1, col2 = st.columns(2)

    with col1:
        code = st.text_input(
            "Preset Code *",
            value=preset.get("code", "") if preset else "",
            disabled=is_edit_mode,
            help="Lowercase, underscores only (e.g., gan_footvolley)",
            key=f"{key_prefix}_code"
        )

        name = st.text_input(
            "Preset Name *",
            value=preset.get("name", "") if preset else "",
            key=f"{key_prefix}_name"
        )

    with col2:
        description = st.text_area(
            "Description",
            value=preset.get("description", "") if preset else "",
            height=100,
            key=f"{key_prefix}_description"
        )

        is_active = st.checkbox(
            "Active",
            value=preset.get("is_active", True) if preset else True,
            key=f"{key_prefix}_is_active"
        )

    # Game Configuration
    st.write("### Game Configuration")

    game_config = preset.get("game_config", {}) if preset else {}

    # Version
    version = st.text_input("Version", value=game_config.get("version", "1.0"), key=f"{key_prefix}_version")

    # Skill Configuration
    skill_config = render_skill_config_editor(game_config, preset_id=preset_id)

    # Format Configuration
    st.write("---")
    format_type = st.selectbox(
        "Tournament Format",
        options=["HEAD_TO_HEAD", "INDIVIDUAL_RANKING"],
        index=0,  # Default to HEAD_TO_HEAD
        key=f"{key_prefix}_format_type"
    )

    if format_type == "HEAD_TO_HEAD":
        match_simulation = render_match_simulation_editor(
            game_config.get("format_config", {}),
            format_type,
            preset_id=preset_id
        )
        ranking_rules = render_ranking_rules_editor(
            game_config.get("format_config", {}),
            format_type,
            preset_id=preset_id
        )

        format_config = {
            format_type: {
                "match_simulation": match_simulation,
                "ranking_rules": ranking_rules
            }
        }
    else:
        # INDIVIDUAL_RANKING configuration (simplified for now)
        st.info("INDIVIDUAL_RANKING format configuration coming soon")
        format_config = {format_type: {}}

    # Simulation Configuration
    st.write("---")
    simulation_config = render_simulation_config_editor(game_config, preset_id=preset_id)

    # Metadata
    st.write("---")
    metadata = render_metadata_editor(game_config, preset_id=preset_id)

    # Build final game_config
    final_game_config = {
        "version": version,
        "skill_config": skill_config,
        "format_config": format_config,
        "simulation_config": simulation_config,
        "metadata": metadata
    }

    # Preview
    with st.expander("📄 Preview JSON Configuration"):
        st.json(final_game_config)

    # Save buttons
    st.write("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if is_edit_mode:
            if st.button("💾 Update Preset", type="primary", use_container_width=True):
                update_data = {
                    "name": name,
                    "description": description if description else None,
                    "game_config": final_game_config,
                    "is_active": is_active
                }
                if update_preset(token, preset["id"], update_data):
                    st.rerun()
        else:
            if st.button("✅ Create Preset", type="primary", use_container_width=True):
                create_data = {
                    "code": code,
                    "name": name,
                    "description": description if description else None,
                    "game_config": final_game_config,
                    "is_active": is_active
                }
                if create_preset(token, create_data):
                    st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.selected_preset_id = None
            st.session_state.create_mode = False
            st.rerun()

    with col3:
        if is_edit_mode:
            if st.button("🗑️ Delete Preset", type="secondary", use_container_width=True):
                if st.session_state.get("confirm_delete", False):
                    if delete_preset(token, preset["id"], hard_delete=False):
                        st.session_state.selected_preset_id = None
                        st.session_state.confirm_delete = False
                        st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.warning("Click again to confirm deletion")


def main():
    st.set_page_config(
        page_title="Game Preset Admin",
        page_icon="🎮",
        layout="wide"
    )

    st.title("🎮 Game Preset Administration")

    # Login
    if "token" not in st.session_state:
        st.session_state.token = login()

    if not st.session_state.token:
        st.error("Failed to authenticate. Please check API connection.")
        return

    # Sidebar - Preset List
    st.sidebar.title("📋 Game Presets")

    if st.sidebar.button("➕ Create New Preset", use_container_width=True):
        st.session_state.create_mode = True
        st.session_state.selected_preset_id = None

    active_only = st.sidebar.checkbox("Show active only", value=False)

    presets = fetch_presets(st.session_state.token, active_only=active_only)

    st.sidebar.write(f"**{len(presets)} presets found**")

    # Preset selection
    for preset in presets:
        status_icon = "✅" if preset["is_active"] else "❌"
        rec_icon = "⭐" if preset.get("is_recommended", False) else ""

        if st.sidebar.button(
            f"{status_icon} {rec_icon} {preset['name']}",
            key=f"preset_{preset['id']}",
            use_container_width=True
        ):
            st.session_state.selected_preset_id = preset["id"]
            st.session_state.create_mode = False

    # Main content
    if st.session_state.get("create_mode", False):
        render_preset_editor(preset=None, token=st.session_state.token)

    elif st.session_state.get("selected_preset_id"):
        preset_detail = fetch_preset_detail(st.session_state.selected_preset_id)
        if preset_detail:
            render_preset_editor(preset=preset_detail, token=st.session_state.token)

    else:
        st.info("👈 Select a preset from the sidebar or create a new one")

        # Show summary
        if presets:
            st.write("### Preset Summary")

            for preset in presets:
                with st.expander(f"{preset['name']} ({preset['code']})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Status:** {'Active' if preset['is_active'] else 'Inactive'}")
                        st.write(f"**Recommended:** {'Yes' if preset.get('is_recommended') else 'No'}")

                    with col2:
                        st.write(f"**Category:** {preset.get('game_category', 'N/A')}")
                        st.write(f"**Difficulty:** {preset.get('difficulty_level', 'N/A')}")

                    with col3:
                        player_count = preset.get('recommended_player_count', {})
                        st.write(f"**Players:** {player_count.get('min', 'N/A')}-{player_count.get('max', 'N/A')}")
                        skills = preset.get('skills_tested', [])
                        st.write(f"**Skills:** {', '.join(skills) if skills else 'N/A'}")

                    if preset.get('description'):
                        st.write(f"*{preset['description']}*")


if __name__ == "__main__":
    main()
