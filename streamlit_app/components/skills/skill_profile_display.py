"""
Skill Profile Display Component

Displays player's dynamic skill progression with:
- Current skill levels with tier indicators
- Tournament vs Assessment contributions
- Skill growth visualization
- Decay warnings for inactive skills
"""

import streamlit as st
import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.skills_config import SKILL_CATEGORIES

# Optional plotly import with graceful fallback
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Skill tier configuration (matching backend)
SKILL_TIERS = {
    "MASTER": {"emoji": "💎", "color": "#9333ea", "min": 95},
    "ADVANCED": {"emoji": "🔥", "color": "#dc2626", "min": 85},
    "INTERMEDIATE": {"emoji": "⚡", "color": "#f59e0b", "min": 70},
    "DEVELOPING": {"emoji": "📈", "color": "#3b82f6", "min": 50},
    "BEGINNER": {"emoji": "🌱", "color": "#6b7280", "min": 0}
}


def get_skill_tier(level: float) -> str:
    """Get tier name for skill level"""
    if level >= 95:
        return "MASTER"
    elif level >= 85:
        return "ADVANCED"
    elif level >= 70:
        return "INTERMEDIATE"
    elif level >= 50:
        return "DEVELOPING"
    else:
        return "BEGINNER"


def fetch_skill_profile(token: str, api_base_url: str) -> Optional[Dict]:
    """
    Fetch player's skill profile from API

    Returns:
        Skill profile dict or None on error
    """
    try:
        response = requests.get(
            f"{api_base_url}/api/v1/progression/skill-profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load skill profile: {e}")
        return None


def render_skill_card(
    skill_name: str,
    skill_data: Dict,
    show_breakdown: bool = False
):
    """
    Render individual skill card with tier, level, and breakdown

    Args:
        skill_name: Name of the skill
        skill_data: Skill data dict from API
        show_breakdown: Show tournament/assessment breakdown
    """
    current_level = skill_data.get("current_level", 0.0)
    baseline = skill_data.get("baseline", 0.0)
    total_delta = skill_data.get("total_delta", 0.0)
    tournament_delta = skill_data.get("tournament_delta", 0.0)
    assessment_delta = skill_data.get("assessment_delta", 0.0)
    tournament_count = skill_data.get("tournament_count", 0)
    assessment_count = skill_data.get("assessment_count", 0)
    tier = skill_data.get("tier", "BEGINNER")
    tier_emoji = skill_data.get("tier_emoji", "")

    tier_config = SKILL_TIERS.get(tier, SKILL_TIERS["BEGINNER"])

    # Format skill name (get from skills_config if available)
    display_name = skill_name.replace("_", " ").title()

    # Create card
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            # Skill name with tier emoji
            st.markdown(
                f"<h4 style='margin: 0; color: {tier_config['color']};'>"
                f"{tier_emoji} {display_name}</h4>",
                unsafe_allow_html=True
            )

            # Level display
            delta_display = f"+{total_delta:.1f}" if total_delta > 0 else ""
            st.markdown(
                f"<p style='font-size: 1.5rem; margin: 0.25rem 0;'>"
                f"<strong>{current_level:.1f}</strong> / 100 "
                f"<span style='color: #10b981; font-size: 1rem;'>{delta_display}</span>"
                f"</p>",
                unsafe_allow_html=True
            )

            # Tier badge
            st.markdown(
                f"<span style='background: {tier_config['color']}; color: white; "
                f"padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; "
                f"font-weight: bold;'>{tier}</span>",
                unsafe_allow_html=True
            )

        with col2:
            # Progress circle
            progress_percent = min(current_level / 100.0, 1.0)
            st.markdown(
                f"<div style='text-align: center;'>"
                f"<div style='font-size: 2rem;'>{tier_emoji}</div>"
                f"<div style='font-size: 0.875rem; color: #6b7280;'>{progress_percent*100:.0f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        # Progress bar
        st.progress(progress_percent)

        # Breakdown (optional)
        if show_breakdown and total_delta > 0:
            with st.expander("📊 Skill Breakdown", expanded=False):
                st.markdown(f"**Baseline (Onboarding):** {baseline:.1f}")

                if tournament_delta > 0:
                    st.markdown(
                        f"**Tournament Contribution:** +{tournament_delta:.1f} "
                        f"<span style='color: #6b7280;'>({tournament_count} tournaments)</span>",
                        unsafe_allow_html=True
                    )

                if assessment_delta > 0:
                    st.markdown(
                        f"**Assessment Contribution:** +{assessment_delta:.1f} "
                        f"<span style='color: #6b7280;'>({assessment_count} assessments)</span>",
                        unsafe_allow_html=True
                    )

                # Calculate remaining capacity
                tournament_remaining = max(0, 15.0 - tournament_delta)
                assessment_remaining = max(0, 10.0 - assessment_delta)

                if tournament_remaining > 0 or assessment_remaining > 0:
                    st.markdown("**Growth Potential:**")
                    if tournament_remaining > 0:
                        st.markdown(f"- Tournament: +{tournament_remaining:.1f} available")
                    if assessment_remaining > 0:
                        st.markdown(f"- Assessment: +{assessment_remaining:.1f} available")

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)


def render_category_radar_chart(category_name: str, category_emoji: str, skills: Dict[str, Dict]):
    """
    Render radar chart for a specific skill category

    Args:
        category_name: Name of the category
        category_emoji: Emoji for the category
        skills: Dict of skill_name -> skill_data (filtered for this category)
    """
    if not PLOTLY_AVAILABLE:
        st.info("📊 Radar chart requires plotly package")
        return

    if not skills:
        st.info("No skill data available for this category")
        return

    # Prepare data
    skill_names = []
    current_levels = []
    baselines = []

    for skill_name, skill_data in sorted(skills.items()):
        display_name = skill_name.replace("_", " ").title()
        skill_names.append(display_name)
        current_levels.append(skill_data.get("current_level", 0.0))
        baselines.append(skill_data.get("baseline", 0.0))

    # Close the radar chart (connect last to first)
    skill_names.append(skill_names[0])
    current_levels.append(current_levels[0])
    baselines.append(baselines[0])

    # Create figure
    fig = go.Figure()

    # Add baseline trace
    fig.add_trace(go.Scatterpolar(
        r=baselines,
        theta=skill_names,
        fill='toself',
        name='Baseline',
        line=dict(color='#9ca3af', dash='dash'),
        fillcolor='rgba(156, 163, 175, 0.1)'
    ))

    # Add current level trace
    fig.add_trace(go.Scatterpolar(
        r=current_levels,
        theta=skill_names,
        fill='toself',
        name='Current',
        line=dict(color='#3b82f6', width=2),
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=11, color='#6b7280'),
                gridcolor='#e5e7eb'
            ),
            angularaxis=dict(
                tickfont=dict(
                    size=14,  # ✅ Larger font
                    color='#e5e7eb',  # ✅ Light gray for dark mode visibility
                    family='Arial, sans-serif'
                ),
                rotation=0,  # Prevent rotation for better readability
                gridcolor='rgba(156, 163, 175, 0.3)'  # ✅ Lighter grid for dark mode
            )
        ),
        showlegend=True,
        height=500,  # ✅ Increased height for better spacing
        margin=dict(l=100, r=100, t=40, b=80),  # ✅ Increased bottom margin for legend
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,  # ✅ Move legend below chart
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def render_skill_growth_bar_chart(skills: Dict[str, Dict]):
    """
    Render bar chart showing skill growth (tournament vs assessment)

    Args:
        skills: Dict of skill_name -> skill_data
    """
    if not PLOTLY_AVAILABLE:
        st.info("📈 Growth chart requires plotly package")
        return

    if not skills:
        return

    # Filter skills with growth
    skills_with_growth = {
        name: data for name, data in skills.items()
        if data.get("total_delta", 0.0) > 0
    }

    if not skills_with_growth:
        st.info("No skill growth yet. Participate in tournaments to improve!")
        return

    # Prepare data
    skill_names = []
    tournament_deltas = []
    assessment_deltas = []

    for skill_name, skill_data in sorted(
        skills_with_growth.items(),
        key=lambda x: x[1].get("total_delta", 0.0),
        reverse=True
    ):
        display_name = skill_name.replace("_", " ").title()
        skill_names.append(display_name)
        tournament_deltas.append(skill_data.get("tournament_delta", 0.0))
        assessment_deltas.append(skill_data.get("assessment_delta", 0.0))

    # Create figure
    fig = go.Figure()

    # Add tournament bars
    fig.add_trace(go.Bar(
        name='Tournament',
        x=skill_names,
        y=tournament_deltas,
        marker_color='#3b82f6',
        text=[f"+{v:.1f}" for v in tournament_deltas],
        textposition='auto'
    ))

    # Add assessment bars
    fig.add_trace(go.Bar(
        name='Assessment',
        x=skill_names,
        y=assessment_deltas,
        marker_color='#10b981',
        text=[f"+{v:.1f}" for v in assessment_deltas],
        textposition='auto'
    ))

    # Update layout
    fig.update_layout(
        barmode='stack',
        title="Skill Growth by Source",
        xaxis_title="",
        yaxis_title="Points Gained",
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def render_skill_profile(token: str, api_base_url: str):
    """
    Main component: Render complete skill profile dashboard

    Args:
        token: API authentication token
        api_base_url: Base URL for API
    """
    st.markdown("## ⚡ Your Skill Profile")

    # Fetch data
    with st.spinner("Loading skill profile..."):
        profile = fetch_skill_profile(token, api_base_url)

    if not profile:
        st.error("Unable to load skill profile")
        return

    skills = profile.get("skills", {})
    average_level = profile.get("average_level", 0.0)
    total_tournaments = profile.get("total_tournaments", 0)
    total_assessments = profile.get("total_assessments", 0)

    if not skills:
        st.info("Complete your onboarding to see your skill profile!")
        return

    # Overall stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_tier = get_skill_tier(average_level)
        avg_emoji = SKILL_TIERS[avg_tier]["emoji"]
        st.metric(
            label="Average Level",
            value=f"{avg_emoji} {average_level:.1f}",
            delta=avg_tier
        )

    with col2:
        st.metric(
            label="Total Skills",
            value=len(skills)
        )

    with col3:
        st.metric(
            label="Tournaments",
            value=total_tournaments
        )

    with col4:
        st.metric(
            label="Assessments",
            value=total_assessments
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Skill Radar (by Category)", "📈 Growth Chart", "📋 Detailed List"])

    with tab1:
        st.markdown("### Skill Radar by Category")
        st.caption("Skills grouped by category for better clarity")
        st.markdown("")

        # Render radar chart for each category
        for category in SKILL_CATEGORIES:
            category_key = category["key"]
            category_name = category["name_en"]  # ✅ FIX: Use English name
            category_emoji = category["emoji"]

            # Filter skills for this category
            category_skill_keys = [skill["key"] for skill in category["skills"]]
            category_skills = {
                skill_key: skill_data
                for skill_key, skill_data in skills.items()
                if skill_key in category_skill_keys
            }

            if not category_skills:
                continue

            # Calculate category average
            category_avg = sum(s.get("current_level", 0) for s in category_skills.values()) / len(category_skills)

            # Expander for each category
            with st.expander(f"{category_emoji} **{category_name}** (Avg: {category_avg:.1f}/100)", expanded=True):
                render_category_radar_chart(category_name, category_emoji, category_skills)

                # Show skill count and top skills
                st.caption(f"{len(category_skills)} skills in this category")

    with tab2:
        st.markdown("### Skill Growth")
        render_skill_growth_bar_chart(skills)

    with tab3:
        st.markdown("### Individual Skills by Category")

        # Option to show breakdown
        show_breakdown = st.checkbox("Show detailed breakdown", value=False)

        st.markdown("")

        # Render skills grouped by category in expandable boxes
        for category in SKILL_CATEGORIES:
            category_key = category["key"]
            category_name = category["name_en"]  # ✅ FIX: Use English name
            category_emoji = category["emoji"]

            # Filter skills for this category
            category_skill_keys = [skill["key"] for skill in category["skills"]]
            category_skills = {
                skill_key: skill_data
                for skill_key, skill_data in skills.items()
                if skill_key in category_skill_keys
            }

            if not category_skills:
                continue

            # Calculate category average
            category_avg = sum(s.get("current_level", 0) for s in category_skills.values()) / len(category_skills)

            # ✅ Use expander for collapsible category sections (same as radar charts)
            with st.expander(f"{category_emoji} **{category_name}** (Avg: {category_avg:.1f}/100)", expanded=False):
                st.caption(f"{len(category_skills)} skills in this category")
                st.markdown("")

                # Render each skill in this category
                for skill_key in category_skill_keys:
                    if skill_key in category_skills:
                        render_skill_card(skill_key, category_skills[skill_key], show_breakdown=show_breakdown)
