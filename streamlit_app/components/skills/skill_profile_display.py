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

# Add project root to path for accessing app module
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

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


def fetch_skill_timeline(token: str, api_base_url: str, skill_key: str) -> Optional[Dict]:
    """
    Fetch per-tournament skill timeline for one skill from API.

    Returns:
        Timeline dict with 'baseline', 'current_level', 'total_delta', 'timeline' list,
        or None on error.
    """
    try:
        response = requests.get(
            f"{api_base_url}/api/v1/progression/skill-timeline",
            params={"skill": skill_key},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load skill timeline: {e}")
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

            # Level display with color-coded delta (NEW V2: supports negative values)
            if total_delta > 0:
                delta_display = f"+{total_delta:.1f}"
                delta_color = "#10b981"  # Green for positive
                delta_arrow = "🔼"
            elif total_delta < 0:
                delta_display = f"{total_delta:.1f}"  # Already has minus sign
                delta_color = "#ef4444"  # Red for negative
                delta_arrow = "🔻"
            else:
                delta_display = ""
                delta_color = "#6b7280"  # Gray for no change
                delta_arrow = ""

            st.markdown(
                f"<p style='font-size: 1.5rem; margin: 0.25rem 0;'>"
                f"<strong>{current_level:.1f}</strong> / 100 "
                f"<span style='color: {delta_color}; font-size: 1rem;'>{delta_arrow} {delta_display}</span>"
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

        # Breakdown (optional) - NEW V2: shows negative deltas too
        if show_breakdown and total_delta != 0:
            with st.expander("📊 Skill Breakdown", expanded=False):
                st.markdown(f"**Baseline (Onboarding):** {baseline:.1f}")

                if tournament_delta != 0:
                    delta_sign = "+" if tournament_delta > 0 else ""
                    delta_color = "#10b981" if tournament_delta > 0 else "#ef4444"
                    st.markdown(
                        f"**Tournament Contribution:** "
                        f"<span style='color: {delta_color};'>{delta_sign}{tournament_delta:.1f}</span> "
                        f"<span style='color: #6b7280;'>({tournament_count} tournaments)</span>",
                        unsafe_allow_html=True
                    )

                if assessment_delta != 0:
                    delta_sign = "+" if assessment_delta > 0 else ""
                    delta_color = "#10b981" if assessment_delta > 0 else "#ef4444"
                    st.markdown(
                        f"**Assessment Contribution:** "
                        f"<span style='color: {delta_color};'>{delta_sign}{assessment_delta:.1f}</span> "
                        f"<span style='color: #6b7280;'>({assessment_count} assessments)</span>",
                        unsafe_allow_html=True
                    )

                # NEW V2: No growth caps, skills are placement-based
                st.markdown(
                    "<p style='color: #6b7280; font-size: 0.875rem; margin-top: 0.5rem;'>"
                    "💡 Skills reflect your tournament placement. "
                    "Top finishes increase skills, bottom finishes decrease them."
                    "</p>",
                    unsafe_allow_html=True
                )

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

    NEW V2: Shows both positive and negative deltas with color coding

    Args:
        skills: Dict of skill_name -> skill_data
    """
    if not PLOTLY_AVAILABLE:
        st.info("📈 Growth chart requires plotly package")
        return

    if not skills:
        return

    # Filter skills with ANY change (positive or negative)
    skills_with_change = {
        name: data for name, data in skills.items()
        if data.get("total_delta", 0.0) != 0
    }

    if not skills_with_change:
        st.info("No skill changes yet. Participate in tournaments to see your skill progression!")
        return

    # Prepare data (NEW V2: sort by absolute value, supports negative deltas)
    skill_names = []
    tournament_deltas = []
    assessment_deltas = []

    for skill_name, skill_data in sorted(
        skills_with_change.items(),
        key=lambda x: abs(x[1].get("total_delta", 0.0)),
        reverse=True
    ):
        display_name = skill_name.replace("_", " ").title()
        skill_names.append(display_name)
        tournament_deltas.append(skill_data.get("tournament_delta", 0.0))
        assessment_deltas.append(skill_data.get("assessment_delta", 0.0))

    # Create figure
    fig = go.Figure()

    # Add tournament bars with color based on positive/negative
    tournament_colors = ['#3b82f6' if v >= 0 else '#ef4444' for v in tournament_deltas]
    fig.add_trace(go.Bar(
        name='Tournament',
        x=skill_names,
        y=tournament_deltas,
        marker_color=tournament_colors,
        text=[f"+{v:.1f}" if v > 0 else f"{v:.1f}" for v in tournament_deltas],
        textposition='auto'
    ))

    # Add assessment bars with color based on positive/negative
    assessment_colors = ['#10b981' if v >= 0 else '#ef4444' for v in assessment_deltas]
    fig.add_trace(go.Bar(
        name='Assessment',
        x=skill_names,
        y=assessment_deltas,
        marker_color=assessment_colors,
        text=[f"+{v:.1f}" if v > 0 else f"{v:.1f}" for v in assessment_deltas],
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


def render_skill_timeline_chart(token: str, api_base_url: str, skills: Dict[str, Dict]):
    """
    Render a per-tournament line chart for a selected skill.

    Shows how a single skill evolved across tournaments with:
    - Horizontal baseline reference line (onboarding level)
    - Line connecting skill_value_after at each tournament
    - Placement label on every data point
    - Positive/negative delta colour coding per segment

    Args:
        token: API auth token
        api_base_url: Backend base URL
        skills: Aggregated skill profile dict (used to build the selector)
    """
    if not PLOTLY_AVAILABLE:
        st.info("📈 Skill timeline chart requires plotly package")
        return

    if not skills:
        return

    st.markdown("### Tournament Skill Timeline")
    st.caption("Select a skill to see how it changed tournament by tournament")

    # Build selector: only skills that have been touched by tournaments
    skills_with_tournaments = {
        k: v for k, v in skills.items() if v.get("tournament_count", 0) > 0
    }

    if not skills_with_tournaments:
        st.info("Participate in tournaments to see the skill timeline!")
        return

    # Display name → skill key map for the selectbox
    display_to_key = {
        name.replace("_", " ").title(): name
        for name in sorted(skills_with_tournaments.keys())
    }
    display_names = list(display_to_key.keys())

    selected_display = st.selectbox(
        "Select skill",
        options=display_names,
        key="skill_timeline_selector"
    )
    selected_key = display_to_key[selected_display]

    with st.spinner(f"Loading {selected_display} timeline..."):
        timeline_data = fetch_skill_timeline(token, api_base_url, selected_key)

    if timeline_data is None:
        return

    entries = timeline_data.get("timeline", [])
    baseline = timeline_data.get("baseline", 0.0)
    current_level = timeline_data.get("current_level", baseline)
    total_delta = timeline_data.get("total_delta", 0.0)

    if not entries:
        st.info(f"No tournament data for **{selected_display}** yet.")
        return

    # --- Parse timeline entries ---
    x_labels = []       # Tournament name + date
    y_values = []       # skill_value_after
    hover_texts = []    # Rich tooltip per point
    point_colors = []   # Green if improvement, red if decline from baseline

    for entry in entries:
        name = entry.get("tournament_name", f"T#{entry.get('tournament_id', '?')}")
        achieved_at = entry.get("achieved_at") or ""
        date_str = achieved_at[:10] if achieved_at else "?"
        placement = entry.get("placement")
        total_players = entry.get("total_players", 0)
        placement_skill = entry.get("placement_skill", 0.0)
        skill_value_after = entry.get("skill_value_after", baseline)
        delta_prev = entry.get("delta_from_previous", 0.0)
        delta_base = entry.get("delta_from_baseline", 0.0)

        placement_str = f"#{placement}" if placement else "—"
        delta_prev_str = f"+{delta_prev:.1f}" if delta_prev >= 0 else f"{delta_prev:.1f}"
        delta_base_str = f"+{delta_base:.1f}" if delta_base >= 0 else f"{delta_base:.1f}"

        x_labels.append(f"{name}<br>{date_str}")
        y_values.append(skill_value_after)
        hover_texts.append(
            f"<b>{name}</b><br>"
            f"Date: {date_str}<br>"
            f"Placement: {placement_str} / {total_players}<br>"
            f"Placement skill: {placement_skill:.1f}<br>"
            f"Skill after: <b>{skill_value_after:.1f}</b><br>"
            f"vs previous: {delta_prev_str}<br>"
            f"vs baseline: {delta_base_str}"
        )
        point_colors.append("#10b981" if skill_value_after >= baseline else "#ef4444")

    # Build segment colors (per segment between consecutive points)
    segment_colors = []
    for i in range(1, len(y_values)):
        segment_colors.append("#10b981" if y_values[i] >= y_values[i - 1] else "#ef4444")

    # Add a synthetic "Baseline" point at the left edge
    x_with_baseline = ["Baseline"] + x_labels
    y_with_baseline = [baseline] + y_values

    fig = go.Figure()

    # Baseline horizontal reference line
    fig.add_hline(
        y=baseline,
        line_dash="dash",
        line_color="#9ca3af",
        annotation_text=f"Baseline {baseline:.1f}",
        annotation_position="bottom left",
        annotation_font_color="#9ca3af"
    )

    # Main skill value line
    fig.add_trace(go.Scatter(
        x=x_with_baseline,
        y=y_with_baseline,
        mode="lines+markers+text",
        name=selected_display,
        line=dict(color="#3b82f6", width=2),
        marker=dict(
            color=["#9ca3af"] + point_colors,  # Baseline point grey, rest coloured
            size=[8] + [12] * len(entries),
            symbol=["circle"] + [
                "triangle-up" if delta >= 0 else "triangle-down"
                for delta in [e.get("delta_from_previous", 0.0) for e in entries]
            ],
            line=dict(color="white", width=1.5)
        ),
        text=[""] + [
            f"#{e.get('placement', '?')}/{e.get('total_players', 0)}"
            for e in entries
        ],
        textposition="top center",
        textfont=dict(size=11),
        hovertext=["<b>Baseline (Onboarding)</b><br>" + f"Value: {baseline:.1f}"] + hover_texts,
        hoverinfo="text"
    ))

    # Current level annotation at the rightmost point
    total_delta_str = f"+{total_delta:.1f}" if total_delta >= 0 else f"{total_delta:.1f}"
    total_delta_color = "#10b981" if total_delta >= 0 else "#ef4444"

    fig.update_layout(
        xaxis=dict(
            title="",
            tickangle=-30,
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            title="Skill Level",
            range=[
                max(0, min(y_with_baseline) - 10),
                min(100, max(y_with_baseline) + 10)
            ],
            gridcolor="#e5e7eb"
        ),
        height=380,
        margin=dict(l=50, r=20, t=50, b=80),
        showlegend=False,
        hovermode="closest",
        title=dict(
            text=(
                f"{selected_display}  "
                f"<span style='color:{total_delta_color}'>{total_delta_str}</span>"
                f"  (baseline {baseline:.1f} → current {current_level:.1f})"
            ),
            font=dict(size=14)
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary row under the chart
    n = len(entries)
    improvements = sum(1 for e in entries if e.get("delta_from_previous", 0.0) > 0)
    declines = sum(1 for e in entries if e.get("delta_from_previous", 0.0) < 0)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Tournaments", n)
    col_b.metric("Improvements", improvements, delta=f"{improvements}/{n}")
    col_c.metric("Declines", declines, delta=f"-{declines}/{n}" if declines else None,
                 delta_color="inverse")


def fetch_skill_audit(token: str, api_base_url: str) -> Optional[Dict]:
    """Fetch the skill audit log from the API."""
    try:
        response = requests.get(
            f"{api_base_url}/api/v1/progression/skill-audit",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load skill audit: {e}")
        return None


def render_skill_audit_section(token: str, api_base_url: str):
    """
    Render the skill audit table: expected vs actual change per tournament per skill.

    Shows:
    - One row per (tournament × mapped skill)
    - Columns: tournament, placement, skill, weight, dominant?, expected, actual, delta, fair?
    - Color-coded: green = changed & fair, red = unfair, orange = no change
    - Summary: total entries, unfair entries count
    """
    st.markdown("### Skill Audit Log")
    st.caption("Per-tournament validation: did the dominant skill actually change more?")

    with st.spinner("Loading audit data..."):
        audit_data = fetch_skill_audit(token, api_base_url)

    if audit_data is None:
        return

    rows = audit_data.get("audit", [])
    total = audit_data.get("total_entries", 0)
    unfair = audit_data.get("unfair_entries", 0)

    if total == 0:
        st.info("No tournament participation data yet. Participate in tournaments to see the audit log.")
        return

    # Summary metrics
    fair_count = total - unfair
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Entries", total)
    col_b.metric("Fair", fair_count, delta=f"{round(fair_count/total*100)}%")
    col_c.metric("Unfair", unfair,
                 delta=f"-{round(unfair/total*100)}%" if unfair else None,
                 delta_color="inverse" if unfair else "off")

    st.markdown("")

    # Filter controls
    all_skills = sorted({r["skill"] for r in rows})
    all_tournaments = sorted({r["tournament_name"] for r in rows})

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_skill = st.selectbox(
            "Filter by skill",
            options=["All skills"] + all_skills,
            key="audit_filter_skill"
        )
    with col_f2:
        filter_tournament = st.selectbox(
            "Filter by tournament",
            options=["All tournaments"] + all_tournaments,
            key="audit_filter_tournament"
        )

    show_only_unfair = st.checkbox("Show only unfair entries", value=False, key="audit_show_unfair")

    # Apply filters
    filtered = rows
    if filter_skill != "All skills":
        filtered = [r for r in filtered if r["skill"] == filter_skill]
    if filter_tournament != "All tournaments":
        filtered = [r for r in filtered if r["tournament_name"] == filter_tournament]
    if show_only_unfair:
        filtered = [r for r in filtered if not r["fairness_ok"]]

    if not filtered:
        st.info("No entries match the current filter.")
        return

    # Build display table
    import pandas as pd

    display_rows = []
    for r in filtered:
        delta = r["delta_this_tournament"]
        norm = r.get("norm_delta", 0.0)
        delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
        norm_str = f"+{norm*100:.1f}%" if norm > 0 else (f"{norm*100:.1f}%" if norm < 0 else "0% (cap)")
        dominant_str = "🔴 Dominant" if r["is_dominant"] else ("🔵 Support" if r["skill_weight"] < r["avg_weight"] * 0.95 else "⚪ Balanced")
        changed_str = "✅ Yes" if r["actual_changed"] else "⚠️ No"
        fair_str = "✅" if r["fairness_ok"] else "❌ UNFAIR"

        display_rows.append({
            "Tournament": r["tournament_name"],
            "Date": r["achieved_at"][:10] if r["achieved_at"] else "—",
            "Place": f"{r['placement']}/{r['total_players']}",
            "Skill": r["skill"].replace("_", " ").title(),
            "Weight": f"{r['skill_weight']:.2f}×",
            "Role": dominant_str,
            "Changed?": changed_str,
            "Delta": delta_str,
            "Norm. Delta": norm_str,
            "Placement Score": f"{r['placement_skill']:.0f}",
            "Fair?": fair_str,
        })

    df = pd.DataFrame(display_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        "**Norm. Delta** = delta ÷ available headroom toward cap/floor. "
        "Measures what fraction of the possible development range was consumed. "
        "0% (cap) = skill was already at the hard cap (99) — not an unfair outcome."
    )

    if unfair > 0:
        st.warning(
            f"⚠️ {unfair} unfair entr{'y' if unfair == 1 else 'ies'} detected: "
            "a dominant skill consumed a smaller fraction of its headroom than a "
            "lower-weight peer despite having room to grow."
        )
    else:
        st.success("✅ All dominant skills showed equal or larger changes than their lower-weight peers.")


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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Skill Radar (by Category)", "📈 Growth Chart", "📋 Detailed List", "🔍 Skill Audit"])

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

        st.markdown("<hr>", unsafe_allow_html=True)
        render_skill_timeline_chart(token, api_base_url, skills)

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

    with tab4:
        render_skill_audit_section(token, api_base_url)
