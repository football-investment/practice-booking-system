"""
Tournament Reward Configuration Editor

Admin UI component for configuring tournament reward policies.
Features:
- Template selection (Standard, Championship, Friendly)
- Skill mapping checkboxes with weights (NEW: 29 skills from skills_config.py)
- Badge configuration checkboxes per placement
- Credit and XP multiplier inputs
- Save/Load from tournament metadata
"""
import streamlit as st
from typing import Dict, Any, Optional, List
import sys
import os

# Add project root to path to import schemas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.schemas.reward_config import (
    TournamentRewardConfig,
    REWARD_CONFIG_TEMPLATES,
    SkillMappingConfig,
    PlacementRewardConfig,
    BadgeConfig,
    BadgeCondition
)
from app.skills_config import SKILL_CATEGORIES


# ============================================================================
# Constants
# ============================================================================

# ✅ NEW: Build ALL_AVAILABLE_SKILLS from skills_config.py (29 skills)
ALL_AVAILABLE_SKILLS = []
for category in SKILL_CATEGORIES:
    category_key = category["key"].upper()  # OUTFIELD, SET_PIECES, MENTAL, PHYSICAL
    for skill in category["skills"]:
        ALL_AVAILABLE_SKILLS.append({
            "skill": skill["key"],  # e.g., "ball_control", "dribbling"
            "category": category_key,
            "default_weight": 1.0,
            "display_name": skill["name_en"]  # e.g., "Ball Control"
        })

PLACEMENT_BADGE_OPTIONS = {
    "1st_place": [
        {"badge_type": "CHAMPION", "icon": "🥇", "title": "Champion", "rarity": "EPIC", "description": "Won 1st place in {tournament_name}"},
        {"badge_type": "PERFECT_SCORE", "icon": "💯", "title": "Perfect Score", "rarity": "LEGENDARY", "description": "Achieved perfect score", "condition_type": "perfect_score"},
        {"badge_type": "UNDEFEATED", "icon": "🛡️", "title": "Undefeated", "rarity": "LEGENDARY", "description": "Won without losing a match", "condition_type": "always"},
    ],
    "2nd_place": [
        {"badge_type": "RUNNER_UP", "icon": "🥈", "title": "Runner-Up", "rarity": "RARE", "description": "Finished 2nd in {tournament_name}"},
        {"badge_type": "CLOSE_CALL", "icon": "🎯", "title": "Close Call", "rarity": "RARE", "description": "Nearly won the tournament", "condition_type": "always"},
    ],
    "3rd_place": [
        {"badge_type": "THIRD_PLACE", "icon": "🥉", "title": "Third Place", "rarity": "UNCOMMON", "description": "Secured 3rd place in {tournament_name}"},
        {"badge_type": "PODIUM_FINISH", "icon": "🏆", "title": "Podium Finish", "rarity": "UNCOMMON", "description": "Finished on the podium", "condition_type": "always"},
    ],
    "top_25_percent": [
        {"badge_type": "TOP_PERFORMER", "icon": "🌟", "title": "Top Performer", "rarity": "RARE", "description": "Finished in top 25% of {tournament_name}"},
        {"badge_type": "ELITE_PLAYER", "icon": "💎", "title": "Elite Player", "rarity": "RARE", "description": "Among the best performers", "condition_type": "always"},
    ],
    "participation": [
        {"badge_type": "TOURNAMENT_DEBUT", "icon": "⚽", "title": "Tournament Debut", "rarity": "COMMON", "description": "First tournament participation", "condition_type": "first_tournament"},
        {"badge_type": "PARTICIPANT", "icon": "🎖️", "title": "Participant", "rarity": "COMMON", "description": "Participated in {tournament_name}", "condition_type": "always"},
        {"badge_type": "COMEBACK_PLAYER", "icon": "🔥", "title": "Comeback Player", "rarity": "UNCOMMON", "description": "Returned to competition", "condition_type": "always"},
    ]
}


# ============================================================================
# Template Loader
# ============================================================================

def render_template_selector() -> Optional[TournamentRewardConfig]:
    """
    Render template selector dropdown.
    Returns selected template config or None.

    ⚠️ IMPORTANT: Template switching does NOT auto-enable skills.
    All templates have skills disabled by default.
    """
    st.markdown("#### 📋 Reward Template")

    template_options = {
        "Standard": "Standard rewards (500/300/200 credits)",
        "Championship": "Premium rewards (1000/600/400 credits)",
        "Friendly": "Reduced rewards (200/100/50 credits)",
        "Custom": "Create custom configuration"
    }

    selected_template = st.selectbox(
        "Select reward template",
        options=list(template_options.keys()),
        format_func=lambda x: f"{x} - {template_options[x]}",
        key="reward_template_selector"
    )

    if selected_template == "Custom":
        return None

    # Load selected template
    template_key = selected_template.upper()
    if template_key in REWARD_CONFIG_TEMPLATES:
        config = REWARD_CONFIG_TEMPLATES[template_key]
        st.info(f"✓ Loaded {selected_template} template - **Select skills below**")
        return config

    return None


# ============================================================================
# Skill Mapping Editor
# ============================================================================

def render_skill_mapping_editor(initial_config: Optional[TournamentRewardConfig] = None) -> tuple[List[SkillMappingConfig], bool]:
    """
    Render skill mapping checkboxes with validation (NEW: 29 skills from skills_config.py).
    Returns (list of enabled skill mappings, is_valid).

    🔒 VALIDATION: At least 1 skill must be selected for tournament.
    """
    st.markdown("#### ⚠️ SKILL SELECTION (REQUIRED) ⚠️")
    st.caption("Select at least 1 skill for this tournament:")

    # Get initial enabled skills
    initial_skills = {}
    if initial_config and initial_config.skill_mappings:
        for mapping in initial_config.skill_mappings:
            initial_skills[mapping.skill] = {"enabled": mapping.enabled, "weight": mapping.weight}

    skill_mappings = []

    # Group by category (OUTFIELD, SET_PIECES, MENTAL, PHYSICAL)
    categories = {}
    for skill_info in ALL_AVAILABLE_SKILLS:
        category = skill_info["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(skill_info)

    # Render by category with emoji from SKILL_CATEGORIES
    category_display_names = {
        "OUTFIELD": "🟦 Outfield",
        "SET_PIECES": "🟨 Set Pieces",
        "MENTAL": "🟩 Mental",
        "PHYSICAL": "🟥 Physical Fitness"
    }

    for category_name, category_skills in categories.items():
        display_name = category_display_names.get(category_name, category_name)
        st.markdown(f"**{display_name}:**")

        for skill_info in category_skills:
            skill_name = skill_info["skill"]
            default_weight = skill_info["default_weight"]
            display_label = skill_info["display_name"]

            # Check if enabled in initial config
            is_enabled = initial_skills.get(skill_name, {}).get("enabled", False)
            initial_weight = initial_skills.get(skill_name, {}).get("weight", default_weight)

            # Checkbox for skill
            col1, col2 = st.columns([3, 1])
            with col1:
                enabled = st.checkbox(
                    display_label,
                    value=is_enabled,
                    key=f"skill_{skill_name}"
                )

            with col2:
                if enabled:
                    weight = st.number_input(
                        "Weight",
                        min_value=0.1,
                        max_value=5.0,
                        value=float(initial_weight),
                        step=0.1,
                        key=f"skill_weight_{skill_name}",
                        label_visibility="collapsed"
                    )
                else:
                    weight = default_weight

            if enabled:
                skill_mappings.append(
                    SkillMappingConfig(
                        skill=skill_name,
                        weight=weight,
                        category=category_name,
                        enabled=True
                    )
                )

        st.markdown("")  # Spacing

    # Validation status
    selected_count = len(skill_mappings)
    is_valid = selected_count >= 1

    if is_valid:
        st.success(f"✅ Selected: {selected_count} skill{'s' if selected_count != 1 else ''}")
    else:
        st.error("⚠️ You must select at least 1 skill to continue")

    return skill_mappings, is_valid


# ============================================================================
# Badge Configuration Editor
# ============================================================================

def render_badge_config_editor(
    placement: str,
    title: str,
    initial_config: Optional[PlacementRewardConfig] = None
) -> PlacementRewardConfig:
    """
    Render badge configuration for a specific placement.
    Returns PlacementRewardConfig with selected badges and settings.
    """
    st.markdown(f"#### {title}")

    # Get initial values
    initial_credits = initial_config.credits if initial_config else 0
    initial_xp_mult = initial_config.xp_multiplier if initial_config else 1.0
    initial_badge_types = set()
    if initial_config and initial_config.badges:
        initial_badge_types = {b.badge_type for b in initial_config.badges}

    # Badge selection
    st.caption("Select badges:")
    selected_badges = []

    badge_options = PLACEMENT_BADGE_OPTIONS.get(placement, [])
    for badge_option in badge_options:
        badge_type = badge_option["badge_type"]
        is_enabled = badge_type in initial_badge_types

        # Build condition if exists
        condition = None
        if "condition_type" in badge_option and badge_option["condition_type"] != "always":
            condition = BadgeCondition(type=badge_option["condition_type"])

        # Checkbox
        enabled = st.checkbox(
            f"{badge_option['icon']} {badge_option['title']} ({badge_option['rarity']})",
            value=is_enabled,
            key=f"badge_{placement}_{badge_type}",
            help=badge_option.get("description", "")
        )

        if enabled:
            selected_badges.append(
                BadgeConfig(
                    badge_type=badge_type,
                    icon=badge_option["icon"],
                    title=badge_option["title"],
                    description=badge_option.get("description", ""),
                    rarity=badge_option["rarity"],
                    enabled=True,
                    condition=condition
                )
            )

    # Credits and XP multiplier
    st.caption("Rewards:")
    col1, col2 = st.columns(2)
    with col1:
        credits = st.number_input(
            "💎 Credits",
            min_value=0,
            max_value=10000,
            value=initial_credits,
            step=50,
            key=f"credits_{placement}"
        )
    with col2:
        xp_multiplier = st.number_input(
            "⭐ XP Multiplier",
            min_value=0.0,
            max_value=5.0,
            value=float(initial_xp_mult),
            step=0.1,
            key=f"xp_mult_{placement}"
        )

    return PlacementRewardConfig(
        badges=selected_badges,
        credits=credits,
        xp_multiplier=xp_multiplier
    )


# ============================================================================
# Main Reward Config Editor
# ============================================================================

def render_reward_config_editor(initial_config: Optional[Dict[str, Any]] = None) -> tuple[Optional[TournamentRewardConfig], bool]:
    """
    Main reward configuration editor.

    Args:
        initial_config: Existing reward config dict (from tournament metadata)

    Returns:
        (TournamentRewardConfig if valid, is_valid)
        is_valid indicates if config can be saved (at least 1 skill selected)
    """
    st.markdown("### 🎁 Reward Configuration")
    st.markdown("---")

    # Parse initial config if provided
    parsed_config = None
    if initial_config:
        try:
            parsed_config = TournamentRewardConfig(**initial_config)
            st.info(f"📂 Loaded existing configuration: {parsed_config.template_name or 'Custom'}")
        except Exception as e:
            st.warning(f"⚠️ Could not parse existing config: {str(e)}")

    # Template selector
    template_config = render_template_selector()

    # Use template config as base, or initial config, or fresh config
    base_config = template_config or parsed_config

    st.markdown("---")

    # Skill mapping editor with validation
    skill_mappings, is_valid = render_skill_mapping_editor(base_config)

    st.markdown("---")

    # Badge configuration editors
    st.markdown("### 🏆 Badge Configuration")

    with st.expander("🥇 1st Place Rewards", expanded=True):
        first_place = render_badge_config_editor(
            "1st_place",
            "🥇 1st Place",
            base_config.first_place if base_config else None
        )

    with st.expander("🥈 2nd Place Rewards"):
        second_place = render_badge_config_editor(
            "2nd_place",
            "🥈 2nd Place",
            base_config.second_place if base_config else None
        )

    with st.expander("🥉 3rd Place Rewards"):
        third_place = render_badge_config_editor(
            "3rd_place",
            "🥉 3rd Place",
            base_config.third_place if base_config else None
        )

    with st.expander("🌟 Top 25% Rewards"):
        top_25_percent = render_badge_config_editor(
            "top_25_percent",
            "🌟 Top 25% (Dynamic)",
            base_config.top_25_percent if base_config else None
        )

    with st.expander("⚽ Participation Rewards"):
        participation = render_badge_config_editor(
            "participation",
            "⚽ All Participants",
            base_config.participation if base_config else None
        )

    # Build final config
    try:
        reward_config = TournamentRewardConfig(
            skill_mappings=skill_mappings,
            first_place=first_place,
            second_place=second_place,
            third_place=third_place,
            top_25_percent=top_25_percent,
            participation=participation,
            template_name=template_config.template_name if template_config else "Custom",
            custom_config=template_config is None
        )

        # Validation summary
        st.markdown("---")
        st.markdown("### ✓ Configuration Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Skills", len([s for s in skill_mappings if s.enabled]))
        with col2:
            st.metric("1st Place Badges", len(first_place.badges))
        with col3:
            st.metric("Total Credits (1st)", first_place.credits)
        with col4:
            st.metric("XP Multiplier (1st)", f"{first_place.xp_multiplier}x")

        return reward_config, is_valid

    except Exception as e:
        st.error(f"❌ Invalid configuration: {str(e)}")
        return None, False
