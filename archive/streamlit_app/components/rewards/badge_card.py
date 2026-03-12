"""
Badge Card Component

Displays tournament achievement badges with icon, title, rarity, and description.
Supports different display modes: compact, normal, extended.
"""
import streamlit as st
from typing import Dict, Any, Optional, Literal


# Rarity color palette (subtle, not overly gamified)
RARITY_COLORS = {
    "COMMON": {
        "border": "#9CA3AF",      # Gray-400
        "bg": "#F9FAFB",          # Gray-50
        "text": "#6B7280",        # Gray-500
        "glow": "rgba(156, 163, 175, 0.1)"
    },
    "UNCOMMON": {
        "border": "#10B981",      # Green-500
        "bg": "#ECFDF5",          # Green-50
        "text": "#059669",        # Green-600
        "glow": "rgba(16, 185, 129, 0.15)"
    },
    "RARE": {
        "border": "#3B82F6",      # Blue-500
        "bg": "#EFF6FF",          # Blue-50
        "text": "#2563EB",        # Blue-600
        "glow": "rgba(59, 130, 246, 0.15)"
    },
    "EPIC": {
        "border": "#8B5CF6",      # Purple-500
        "bg": "#F5F3FF",          # Purple-50
        "text": "#7C3AED",        # Purple-600
        "glow": "rgba(139, 92, 246, 0.15)"
    },
    "LEGENDARY": {
        "border": "#F59E0B",      # Amber-500
        "bg": "#FFFBEB",          # Amber-50
        "text": "#D97706",        # Amber-600
        "glow": "rgba(245, 158, 11, 0.2)"
    }
}


def render_badge_card(
    badge: Dict[str, Any],
    size: Literal["compact", "normal", "extended"] = "normal",
    show_metadata: bool = False
) -> None:
    """
    Render a tournament achievement badge card.

    Args:
        badge: Badge dictionary with structure:
            {
                "id": int,
                "icon": str,              # Emoji (🥇, 🥈, 🥉, 🏆, etc.)
                "rarity": str,            # COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
                "title": str,             # "Tournament Champion"
                "description": str,       # "Claimed victory in Speed Test 2026"
                "badge_type": str,        # CHAMPION, RUNNER_UP, etc.
                "badge_category": str,    # PLACEMENT, ACHIEVEMENT, MILESTONE
                "earned_at": str,         # ISO datetime or formatted string
                "metadata": dict          # Optional extra data
            }
        size: Display size - "compact", "normal", or "extended"
        show_metadata: Whether to show metadata (placement, time, etc.)
    """
    rarity = badge.get('rarity', 'COMMON').upper()
    colors = RARITY_COLORS.get(rarity, RARITY_COLORS['COMMON'])

    icon = badge.get('icon', '🏆')
    title = badge.get('title', 'Achievement')
    description = badge.get('description', '')
    earned_at = badge.get('earned_at', '')
    metadata = badge.get('metadata', {})

    # Size-specific styling
    if size == "compact":
        _render_compact_badge(icon, title, rarity, colors)
    elif size == "extended":
        _render_extended_badge(icon, title, description, rarity, colors, earned_at, metadata, show_metadata)
    else:  # normal
        _render_normal_badge(icon, title, description, rarity, colors)


def _render_compact_badge(icon: str, title: str, rarity: str, colors: Dict[str, str]) -> None:
    """Render compact badge (for headers, sidebars, tooltips)"""
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 8px 12px;
        border: 1.5px solid {colors['border']};
        border-radius: 12px;
        background: {colors['bg']};
        box-shadow: 0 1px 2px {colors['glow']};
        margin-bottom: 8px;
        width: 100%;
        box-sizing: border-box;
    ">
        <span style="font-size: 18px;">{icon}</span>
        <span style="
            font-size: 12px;
            font-weight: 500;
            color: {colors['text']};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        ">{title}</span>
    </div>
    """, unsafe_allow_html=True)


def _render_normal_badge(
    icon: str,
    title: str,
    description: str,
    rarity: str,
    colors: Dict[str, str]
) -> None:
    """Render normal badge (for profile grids, list views)"""
    st.markdown(f"""
    <div style="
        border: 2px solid {colors['border']};
        border-radius: 12px;
        padding: 16px;
        background: {colors['bg']};
        box-shadow: 0 2px 4px {colors['glow']};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    ">
        <div style="font-size: 48px; margin-bottom: 8px;">{icon}</div>
        <div style="
            font-weight: 600;
            font-size: 16px;
            color: #1F2937;
            margin-bottom: 4px;
        ">{title}</div>
        <div style="
            font-size: 10px;
            font-weight: 600;
            color: {colors['text']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        ">{rarity}</div>
        <div style="
            font-size: 13px;
            color: #6B7280;
            line-height: 1.4;
        ">{description}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_extended_badge(
    icon: str,
    title: str,
    description: str,
    rarity: str,
    colors: Dict[str, str],
    earned_at: str,
    metadata: Dict[str, Any],
    show_metadata: bool
) -> None:
    """Render extended badge (for detail modals, showcase)"""
    # Format earned date
    earned_date = ""
    if earned_at:
        try:
            from datetime import datetime
            if 'T' in earned_at:  # ISO format
                dt = datetime.fromisoformat(earned_at.replace('Z', '+00:00'))
                earned_date = dt.strftime("%B %d, %Y")
            else:
                earned_date = earned_at
        except:
            earned_date = earned_at

    # Build metadata HTML
    metadata_html = ""
    if show_metadata and metadata:
        metadata_items = []
        for key, value in metadata.items():
            # Format key (snake_case → Title Case)
            display_key = key.replace('_', ' ').title()
            metadata_items.append(f"<div style='font-size: 12px; color: #6B7280;'>{display_key}: <strong>{value}</strong></div>")
        metadata_html = "<div style='margin-top: 12px; padding-top: 12px; border-top: 1px solid #E5E7EB;'>" + "".join(metadata_items) + "</div>"

    st.markdown(f"""
    <div style="
        border: 2px solid {colors['border']};
        border-radius: 16px;
        padding: 24px;
        background: linear-gradient(135deg, {colors['bg']} 0%, white 100%);
        box-shadow: 0 4px 6px {colors['glow']}, 0 0 0 1px {colors['glow']};
        text-align: center;
    ">
        <div style="font-size: 64px; margin-bottom: 12px;">{icon}</div>
        <div style="
            font-weight: 700;
            font-size: 20px;
            color: #111827;
            margin-bottom: 6px;
        ">{title}</div>
        <div style="
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            color: {colors['text']};
            background: {colors['border']};
            padding: 4px 12px;
            border-radius: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            color: white;
        ">{rarity}</div>
        <div style="
            font-size: 14px;
            color: #4B5563;
            line-height: 1.5;
            margin-bottom: 8px;
        ">{description}</div>
        <div style="
            font-size: 12px;
            color: #9CA3AF;
            margin-top: 12px;
        ">Earned: {earned_date}</div>
        {metadata_html}
    </div>
    """, unsafe_allow_html=True)


def render_badge_grid(
    badges: list[Dict[str, Any]],
    columns: int = 3,
    size: Literal["compact", "normal", "extended"] = "normal",
    show_empty_state: bool = True
) -> None:
    """
    Render badges in a grid layout.

    Args:
        badges: List of badge dictionaries
        columns: Number of columns in grid
        size: Badge display size
        show_empty_state: Show message if no badges
    """
    if not badges:
        if show_empty_state:
            st.info("🏆 No badges earned yet. Participate in tournaments to earn your first badge!")
        return

    # Create grid
    cols = st.columns(columns)

    for idx, badge in enumerate(badges):
        col_idx = idx % columns
        with cols[col_idx]:
            render_badge_card(badge, size=size)


def render_badge_list(
    badges: list[Dict[str, Any]],
    show_metadata: bool = False,
    show_empty_state: bool = True
) -> None:
    """
    Render badges in a list layout (stacked vertically).

    Args:
        badges: List of badge dictionaries
        show_metadata: Show metadata for each badge
        show_empty_state: Show message if no badges
    """
    if not badges:
        if show_empty_state:
            st.info("🏆 No badges earned yet. Participate in tournaments to earn your first badge!")
        return

    for badge in badges:
        render_badge_card(badge, size="extended", show_metadata=show_metadata)
        st.write("")  # Spacing


def get_rarity_emoji(rarity: str) -> str:
    """Get emoji representing rarity level"""
    rarity_emojis = {
        "COMMON": "⚪",
        "UNCOMMON": "🟢",
        "RARE": "🔵",
        "EPIC": "🟣",
        "LEGENDARY": "🟠"
    }
    return rarity_emojis.get(rarity.upper(), "⚪")


def get_rarity_sort_value(rarity: str) -> int:
    """Get numeric value for sorting badges by rarity (highest first)"""
    rarity_values = {
        "LEGENDARY": 5,
        "EPIC": 4,
        "RARE": 3,
        "UNCOMMON": 2,
        "COMMON": 1
    }
    return rarity_values.get(rarity.upper(), 0)
