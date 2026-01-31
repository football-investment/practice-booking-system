"""
Shared Game Preset Form Components
Reusable UI components for creating and editing game presets
"""

import streamlit as st
from typing import Dict, Optional


def render_basic_info_editor(name: str = "", description: str = "", code: str = "", key_prefix: str = "preset") -> Dict:
    """Render basic information editor (name, description, code)"""
    st.subheader("📝 Basic Information")

    col1, col2 = st.columns(2)

    with col1:
        # Only show code input for new presets
        if code == "":
            edit_code = st.text_input(
                "Preset Code (lowercase, underscores only)",
                value=code,
                key=f"{key_prefix}_code",
                help="Unique identifier for the preset (e.g., gan_footvolley)"
            )
        else:
            edit_code = code
            st.text_input(
                "Preset Code (readonly)",
                value=code,
                key=f"{key_prefix}_code_readonly",
                disabled=True,
                help="Code cannot be changed after creation"
            )

        edit_name = st.text_input(
            "Preset Name",
            value=name,
            key=f"{key_prefix}_name"
        )

    with col2:
        edit_description = st.text_area(
            "Description",
            value=description,
            height=120,
            key=f"{key_prefix}_desc"
        )

    return {
        "code": edit_code,
        "name": edit_name,
        "description": edit_description
    }


def render_skill_config_editor(game_config: Dict, preset_id: Optional[int] = None, key_prefix: str = "preset") -> Dict:
    """Render skill configuration editor"""
    st.subheader("⚽ Skill Configuration")

    skill_config = game_config.get("skill_config", {})

    # Import skill categories from skills_config
    from app.skills_config import SKILL_CATEGORIES

    # Use key_prefix if provided, otherwise use preset_id
    if preset_id is not None:
        key_prefix = f"preset_{preset_id}"

    # Skills tested
    st.write("**Skills Tested**")
    st.markdown("Select skills by category:")

    preset_skills = skill_config.get("skills_tested", [])
    skills_tested = []

    skill_multipliers = {}
    total_multiplier = 0.0

    # Get existing weights (already normalized 0.0-1.0)
    existing_weights = skill_config.get("skill_weights", {})

    # Initialize widget state for checkboxes if Edit mode just opened
    # NOTE: Do NOT initialize weight values in session state!
    # Let the widget's value parameter handle defaults to prevent stale values
    for skill_key in preset_skills:
        checkbox_key = f"{key_prefix}_skill_{skill_key}"
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = True

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

                # Create columns for checkbox and weight input
                col_checkbox, col_weight = st.columns([2, 3])

                with col_checkbox:
                    selected = st.checkbox(
                        f"{skill_name}",
                        value=is_default,
                        key=f"{key_prefix}_skill_{skill_key}",
                        help=f"Key: {skill_key}"
                    )

                with col_weight:
                    if selected:
                        # Use existing weight as-is, or default to 1.0
                        default_multiplier = existing_weights.get(skill_key, 1.0)

                        multiplier = st.number_input(
                            f"Weight",
                            min_value=0.0,
                            max_value=10.0,
                            value=float(default_multiplier),
                            step=0.1,
                            key=f"{key_prefix}_weight_{skill_key}",
                            help=f"Relative importance (will be normalized to sum 1.0)",
                            label_visibility="collapsed"
                        )
                        skill_multipliers[skill_key] = multiplier
                        total_multiplier += multiplier
                        skills_tested.append(skill_key)

    # Show normalization summary after all categories
    st.markdown("---")

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
        st.warning("⚠️ No skills selected or total multiplier is 0")

    skill_impact = st.checkbox(
        "Skill impact on matches",
        value=skill_config.get("skill_impact_on_matches", True),
        key=f"{key_prefix}_skill_impact"
    )

    return {
        "skills_tested": skills_tested,
        "skill_weights": skill_weights,
        "skill_impact_on_matches": skill_impact
    }


def render_match_simulation_editor(format_config: Dict, format_type: str, preset_id: Optional[int] = None, key_prefix: str = "preset") -> Dict:
    """Render match simulation editor for HEAD_TO_HEAD format"""
    st.subheader("🎲 Match Simulation")

    if preset_id is not None:
        key_prefix = f"preset_{preset_id}"

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
            "win": {"winner_max": int(winner_max), "loser_max": int(loser_max)},
            "draw": {"min": int(draw_min), "max": int(draw_max)}
        }
    }


def render_ranking_rules_editor(format_config: Dict, format_type: str, preset_id: Optional[int] = None, key_prefix: str = "preset") -> Dict:
    """Render ranking rules editor"""
    st.subheader("🏆 Ranking Rules")

    if preset_id is not None:
        key_prefix = f"preset_{preset_id}"

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
            "win": int(win_points),
            "draw": int(draw_points),
            "loss": int(loss_points)
        },
        "tiebreakers": selected_tiebreakers
    }


def render_metadata_editor(game_config: Dict, preset_id: Optional[int] = None, key_prefix: str = "preset") -> Dict:
    """Render metadata editor"""
    st.subheader("📋 Metadata")

    if preset_id is not None:
        key_prefix = f"preset_{preset_id}"

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
        rec_player_count = metadata.get("recommended_player_count", {"min": 2, "max": 16})
        rec_min = st.number_input("Min Players", value=rec_player_count.get("min", 2), key=f"{key_prefix}_min_players")
        rec_max = st.number_input("Max Players", value=rec_player_count.get("max", 16), key=f"{key_prefix}_max_players")

    return {
        "game_category": game_category,
        "difficulty_level": difficulty,
        "recommended_player_count": {
            "min": int(rec_min),
            "max": int(rec_max)
        }
    }


def render_simulation_config_editor(game_config: Dict, preset_id: Optional[int] = None, key_prefix: str = "preset") -> Dict:
    """Render simulation configuration editor"""
    st.subheader("🎮 Simulation Configuration")

    if preset_id is not None:
        key_prefix = f"preset_{preset_id}"

    simulation_config = game_config.get("simulation_config", {})

    # Ensure simulation_config is a dict (defensive coding)
    if not isinstance(simulation_config, dict):
        simulation_config = {}

    # Player selection
    st.write("**Player Selection**")
    player_selection = simulation_config.get("player_selection", {})

    # Ensure player_selection is a dict
    if not isinstance(player_selection, dict):
        player_selection = {}

    col1, col2 = st.columns(2)
    with col1:
        selection_mode = st.selectbox(
            "Selection Mode",
            options=["random", "skill_based", "balanced"],
            index=["random", "skill_based", "balanced"].index(player_selection.get("mode", "random")),
            key=f"{key_prefix}_selection_mode"
        )

    with col2:
        use_ranking = st.checkbox(
            "Use Ranking Weights",
            value=player_selection.get("use_ranking_weights", False),
            key=f"{key_prefix}_use_ranking"
        )

    # Ranking distribution
    st.write("**Ranking Distribution**")
    ranking_dist = simulation_config.get("ranking_distribution", {})

    # Ensure ranking_dist is a dict
    if not isinstance(ranking_dist, dict):
        ranking_dist = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        dist_type = st.selectbox(
            "Distribution Type",
            options=["normal", "uniform", "custom"],
            index=["normal", "uniform", "custom"].index(ranking_dist.get("type", "normal")),
            key=f"{key_prefix}_dist_type"
        )

    with col2:
        mean = st.number_input(
            "Mean",
            min_value=0.0,
            max_value=1.0,
            value=float(ranking_dist.get("mean", 0.5)),
            step=0.1,
            key=f"{key_prefix}_mean"
        )

    with col3:
        std_dev = st.number_input(
            "Standard Deviation",
            min_value=0.0,
            max_value=1.0,
            value=float(ranking_dist.get("std_dev", 0.2)),
            step=0.05,
            key=f"{key_prefix}_std_dev"
        )

    return {
        "player_selection": {
            "mode": selection_mode,
            "use_ranking_weights": use_ranking
        },
        "ranking_distribution": {
            "type": dist_type,
            "mean": mean,
            "std_dev": std_dev
        }
    }
