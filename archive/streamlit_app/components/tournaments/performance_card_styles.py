"""
Performance Card Style Presets
Centralized styling for reusable tournament performance card component
"""

# Percentile tier color palettes
PERCENTILE_COLORS = {
    "top_5": {
        "primary": "#FFD700",
        "secondary": "#FFA500",
        "gradient": "linear-gradient(135deg, #FFD700 0%, #FFA500 100%)",
        "text": "#000000"
    },
    "top_10": {
        "primary": "#FF8C00",
        "secondary": "#FF6347",
        "gradient": "linear-gradient(135deg, #FF8C00 0%, #FF6347 100%)",
        "text": "#FFFFFF"
    },
    "top_25": {
        "primary": "#1E90FF",
        "secondary": "#00BFFF",
        "gradient": "linear-gradient(135deg, #1E90FF 0%, #00BFFF 100%)",
        "text": "#FFFFFF"
    },
    "default": {
        "primary": "#A9A9A9",
        "secondary": "#D3D3D3",
        "gradient": "linear-gradient(135deg, #A9A9A9 0%, #D3D3D3 100%)",
        "text": "#FFFFFF"
    }
}

# Badge type colors
BADGE_COLORS = {
    "CHAMPION": "#FFD700",
    "RUNNER_UP": "#C0C0C0",
    "THIRD_PLACE": "#CD7F32",
    "PODIUM_FINISH": "#8B4513",
    "TOURNAMENT_PARTICIPANT": "#4A90E2",
    "PERFECT_ATTENDANCE": "#10B981",
    "CONSISTENCY_CHAMPION": "#8B5CF6",
}

# Card size presets (matching 8px grid system)
CARD_SIZES = {
    "compact": {
        "width": "100%",
        "height": "80px",
        "padding": "8px",
        "badge_icon": "32px",
        "font_title": "14px",
        "font_context": "11px",
        "font_metric": "12px",
        "gap": "4px"
    },
    "normal": {
        "width": "100%",
        "height": "240px",
        "padding": "12px",
        "badge_icon": "48px",
        "font_title": "18px",
        "font_context": "13px",
        "font_metric": "14px",
        "gap": "8px"
    },
    "large": {
        "width": "100%",
        "height": "320px",
        "padding": "16px",
        "badge_icon": "64px",
        "font_title": "24px",
        "font_context": "16px",
        "font_metric": "16px",
        "gap": "12px"
    }
}

# Typography scale
TYPOGRAPHY = {
    "hero_badge": {
        "compact": "20px",
        "normal": "28px",
        "large": "36px"
    },
    "percentile": {
        "compact": "14px",
        "normal": "20px",
        "large": "24px"
    }
}

# Spacing scale (8px grid)
SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px"
}

# Border radius
BORDER_RADIUS = {
    "small": "4px",
    "medium": "8px",
    "large": "12px",
    "pill": "999px"
}

# Shadow presets
SHADOWS = {
    "none": "none",
    "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "md": "0 4px 6px -1px rgb(0 0 0 / 0.1)",
    "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1)"
}


def get_percentile_tier(percentile: float) -> str:
    """
    Get percentile tier key based on percentage.

    Args:
        percentile: Percentile value (0-100)

    Returns:
        Tier key: 'top_5', 'top_10', 'top_25', or 'default'
    """
    if percentile <= 5:
        return "top_5"
    elif percentile <= 10:
        return "top_10"
    elif percentile <= 25:
        return "top_25"
    else:
        return "default"


def get_percentile_badge_text(percentile: float) -> str:
    """
    Get percentile badge display text with icon.

    Args:
        percentile: Percentile value (0-100)

    Returns:
        Formatted text: "🔥 TOP 5%", "⚡ TOP 10%", etc.
    """
    if percentile <= 5:
        return "🔥 TOP 5%"
    elif percentile <= 10:
        return "⚡ TOP 10%"
    elif percentile <= 25:
        return "🎯 TOP 25%"
    else:
        return "📊 TOP 50%"


def get_badge_icon(badge_type: str) -> str:
    """
    Get icon for badge type.

    Args:
        badge_type: Badge type string

    Returns:
        Unicode emoji icon
    """
    icons = {
        "CHAMPION": "🥇",
        "RUNNER_UP": "🥈",
        "THIRD_PLACE": "🥉",
        "PODIUM_FINISH": "🏆",
        "TOURNAMENT_PARTICIPANT": "⚽",
        "PERFECT_ATTENDANCE": "✨",
        "CONSISTENCY_CHAMPION": "🌟",
        "TRIPLE_CROWN": "👑",
    }
    return icons.get(badge_type, "🏅")


def get_badge_title(badge_type: str) -> str:
    """
    Get human-readable title for badge type.

    Args:
        badge_type: Badge type string

    Returns:
        Formatted title
    """
    titles = {
        "CHAMPION": "CHAMPION",
        "RUNNER_UP": "RUNNER-UP",
        "THIRD_PLACE": "3RD PLACE",
        "PODIUM_FINISH": "PODIUM FINISH",
        "TOURNAMENT_PARTICIPANT": "PARTICIPANT",
        "PERFECT_ATTENDANCE": "PERFECT ATTENDANCE",
        "CONSISTENCY_CHAMPION": "CONSISTENCY CHAMPION",
        "TRIPLE_CROWN": "TRIPLE CROWN",
    }
    return titles.get(badge_type, badge_type.replace('_', ' ').title())
