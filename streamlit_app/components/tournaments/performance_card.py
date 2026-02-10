"""
Reusable Tournament Performance Card Component

Can be used in:
- Tournament Achievements Accordion
- Player Profile Page
- Academy Dashboard
- Social Share Export
- Email Digest

Design Philosophy: Status first, data second. User understands in 2 seconds.
"""
import streamlit as st
from typing import Dict, Any, Optional, Literal

from components.tournaments.performance_card_styles import (
    CARD_SIZES,
    PERCENTILE_COLORS,
    BADGE_COLORS,
    SPACING,
    BORDER_RADIUS,
    SHADOWS,
    get_percentile_tier,
    get_percentile_badge_text,
    get_badge_icon,
    get_badge_title
)

# Type hint for size parameter
CardSize = Literal["compact", "normal", "large"]


def render_performance_card(
    tournament_data: Dict[str, Any],
    size: CardSize = "normal",
    show_badges: bool = True,
    show_rewards: bool = True,
    context: str = "accordion"
) -> None:
    """
    Render tournament performance card with status-first design.

    Args:
        tournament_data: {
            'tournament_id': int,
            'tournament_name': str,
            'tournament_status': str,
            'badges': List[Dict],  # User's badges for this tournament
            'metrics': {
                'rank': int,
                'rank_source': str,  # 'current', 'fallback_participation', 'snapshot'
                'points': float,
                'wins': int, 'draws': int, 'losses': int,
                'goals_for': int,
                'total_participants': int,
                'avg_points': float,
                'xp_earned': int,
                'credits_earned': int,
                'badges_earned': int
            }
        }
        size: "compact" | "normal" | "large"
        show_badges: Whether to render badge section
        show_rewards: Whether to render rewards line
        context: Where card is being rendered ("accordion", "profile", "share", etc.)
    """
    metrics = tournament_data.get('metrics')
    if not metrics:
        st.warning("⚠️ No performance data available for this tournament")
        return

    # Extract data
    rank = metrics.get('rank')
    total_participants = metrics.get('total_participants')
    points = metrics.get('points')
    avg_points = metrics.get('avg_points')
    wins = metrics.get('wins')
    draws = metrics.get('draws')
    losses = metrics.get('losses')
    goals_for = metrics.get('goals_for')
    xp_earned = metrics.get('xp_earned')
    credits_earned = metrics.get('credits_earned')
    badges_earned = metrics.get('badges_earned')

    badges = tournament_data.get('badges', [])

    # Fallback: If metrics missing total_participants, try badge metadata
    if not total_participants:
        if badges and len(badges) > 0:
            first_badge = badges[0]
            badge_metadata = first_badge.get('badge_metadata', {})
            if badge_metadata.get('total_participants'):
                total_participants = badge_metadata['total_participants']

    # Compute percentile
    percentile = None
    percentile_badge_text = None
    percentile_tier = None
    if rank and total_participants and total_participants > 0:
        percentile = round((rank / total_participants) * 100, 1)
        percentile_badge_text = get_percentile_badge_text(percentile)
        percentile_tier = get_percentile_tier(percentile)

    # Get primary badge (highest priority)
    primary_badge = _get_primary_badge(tournament_data.get('badges', []))
    badge_type = primary_badge.get('badge_type') if primary_badge else None
    badge_icon = get_badge_icon(badge_type) if badge_type else "🏅"
    badge_title = get_badge_title(badge_type) if badge_type else "PARTICIPANT"

    # CRITICAL PRODUCT RULE: CHAMPION badge MUST have rank (force placement fallback)
    if badge_type == "CHAMPION" and not rank:
        if badges and len(badges) > 0:
            first_badge = badges[0]
            badge_metadata = first_badge.get('badge_metadata', {})
            if badge_metadata.get('placement'):
                rank = badge_metadata['placement']

    # Get size-specific styles
    styles = CARD_SIZES[size]

    # Render based on size
    if size == "compact":
        _render_compact_card(
            badge_icon, badge_title, rank, total_participants,
            percentile_badge_text, percentile_tier, styles
        )
    else:
        _render_normal_card(
            badge_icon, badge_title, rank, total_participants,
            percentile_badge_text, percentile_tier, points, avg_points,
            wins, draws, losses, goals_for, xp_earned, credits_earned,
            badges_earned, show_rewards, show_badges,
            tournament_data.get('badges', []), styles, size
        )


def _get_primary_badge(badges: list) -> Optional[Dict[str, Any]]:
    """
    Get primary badge (highest priority) from list.

    Priority: CHAMPION > RUNNER_UP > THIRD_PLACE > PODIUM_FINISH > others

    Args:
        badges: List of badge dictionaries

    Returns:
        Primary badge dict or None
    """
    if not badges:
        return None

    priority = {
        'CHAMPION': 1,
        'RUNNER_UP': 2,
        'THIRD_PLACE': 3,
        'PODIUM_FINISH': 4,
        'TRIPLE_CROWN': 5,
        'CONSISTENCY_CHAMPION': 6,
        'PERFECT_ATTENDANCE': 7,
        'TOURNAMENT_PARTICIPANT': 8
    }

    # Sort by priority (lower number = higher priority)
    sorted_badges = sorted(
        badges,
        key=lambda b: priority.get(b.get('badge_type', ''), 999)
    )

    return sorted_badges[0] if sorted_badges else None


def _render_compact_card(
    badge_icon: str,
    badge_title: str,
    rank: Optional[int],
    total_participants: Optional[int],
    percentile_badge_text: Optional[str],
    percentile_tier: Optional[str],
    styles: Dict[str, str]
) -> None:
    """
    Render compact performance card (80px height).

    Layout: [Badge Icon] [Badge Title] | [#X of Y] | [Percentile Badge]
    """
    # Get percentile colors
    tier_colors = PERCENTILE_COLORS.get(percentile_tier, PERCENTILE_COLORS["default"])

    # Compact layout: Single row
    st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: {SPACING['sm']};
            padding: {styles['padding']};
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: {BORDER_RADIUS['medium']};
            height: {styles['height']};
        ">
            <div style="font-size: {styles['badge_icon']};">{badge_icon}</div>
            <div style="flex: 1; min-width: 100px;">
                <div style="font-size: {styles['font_title']}; font-weight: 600; color: #1F2937;">
                    {badge_title}
                </div>
                <div style="font-size: {styles['font_context']}; color: #6B7280;">
                    {f"#{rank} of {total_participants}" if rank and total_participants else "No ranking data"}
                </div>
            </div>
            {f'''
            <div style="
                background: {tier_colors['gradient']};
                color: {tier_colors['text']};
                padding: 4px 12px;
                border-radius: {BORDER_RADIUS['pill']};
                font-size: {styles['font_context']};
                font-weight: 600;
                white-space: nowrap;
            ">
                {percentile_badge_text}
            </div>
            ''' if percentile_badge_text else ''}
        </div>
    """, unsafe_allow_html=True)


def _render_normal_card(
    badge_icon: str,
    badge_title: str,
    rank: Optional[int],
    total_participants: Optional[int],
    percentile_badge_text: Optional[str],
    percentile_tier: Optional[str],
    points: Optional[float],
    avg_points: Optional[float],
    wins: Optional[int],
    draws: Optional[int],
    losses: Optional[int],
    goals_for: Optional[int],
    xp_earned: Optional[int],
    credits_earned: Optional[int],
    badges_earned: Optional[int],
    show_rewards: bool,
    show_badges: bool,
    badges: list,
    styles: Dict[str, str],
    size: CardSize
) -> None:
    """
    Render normal/large performance card (240px+ height).

    Layout:
    [Hero Status Block: Badge Icon, Title, Rank Context, Percentile]
    [Performance Triptych: Points, Goals, Record]
    [Rewards Line: XP, Credits, Badges]
    [Badge Carousel: Badge icons] (if show_badges)
    """
    # Get percentile colors
    tier_colors = PERCENTILE_COLORS.get(percentile_tier, PERCENTILE_COLORS["default"])

    # Hero Status Block
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: {styles['padding']};
            background: linear-gradient(135deg, {tier_colors['primary']}10 0%, white 100%);
            border-radius: {BORDER_RADIUS['medium']};
            margin-bottom: {SPACING['md']};
        ">
            <div style="font-size: {styles['badge_icon']}; margin-bottom: {SPACING['xs']};">{badge_icon}</div>
            <div style="
                font-size: {styles['font_title']};
                font-weight: 700;
                color: #1F2937;
                margin-bottom: {SPACING['xs']};
                letter-spacing: 0.5px;
            ">
                {badge_title}
            </div>
            <div style="
                font-size: {styles['font_context']};
                color: #6B7280;
                margin-bottom: {SPACING['sm']};
            ">
                {f"#{rank} of {total_participants} players" if rank and total_participants else "No ranking data"}
            </div>
            {f'''
            <div style="
                display: inline-block;
                background: {tier_colors['gradient']};
                color: {tier_colors['text']};
                padding: {SPACING['xs']} {SPACING['md']};
                border-radius: {BORDER_RADIUS['pill']};
                font-size: {styles['font_metric']};
                font-weight: 600;
            ">
                {percentile_badge_text}
            </div>
            ''' if percentile_badge_text else ''}
        </div>
    """, unsafe_allow_html=True)

    # Performance Triptych (3 columns)
    if any([points is not None, goals_for is not None, wins is not None]):
        col1, col2, col3 = st.columns(3)

        with col1:
            if points is not None:
                st.metric("💯 Points", f"{points:.0f}")
                if avg_points and avg_points > 0:
                    delta = round(points - avg_points, 1)
                    if delta > 0:
                        st.caption(f"(Avg: {avg_points:.0f}, +{delta})")
                    else:
                        st.caption(f"(Avg: {avg_points:.0f})")

        with col2:
            if goals_for is not None and goals_for > 0:
                st.metric("⚽ Goals", f"{goals_for}")

        with col3:
            if wins is not None or losses is not None or draws is not None:
                w = wins or 0
                d = draws or 0
                l = losses or 0
                record_str = f"{w}-{d}-{l}"
                st.metric("🎯 W-D-L", record_str)

    # Rewards Line
    if show_rewards and any([xp_earned, credits_earned, badges_earned]):
        st.markdown("---")
        rewards_parts = []
        if xp_earned:
            rewards_parts.append(f"+{xp_earned} XP")
        if credits_earned:
            rewards_parts.append(f"+{credits_earned} 💎")
        if badges_earned:
            rewards_parts.append(f"{badges_earned} badges")

        rewards_text = " • ".join(rewards_parts)
        st.markdown(f"""
            <div style="
                text-align: center;
                font-size: {styles['font_context']};
                color: #6B7280;
                padding: {SPACING['xs']};
            ">
                {rewards_text}
            </div>
        """, unsafe_allow_html=True)

    # Badge Carousel (collapsed by default)
    if show_badges and badges and size == "large":
        with st.expander(f"🏅 View {len(badges)} Badges"):
            badge_icons_html = "".join([
                f"<span style='font-size: 32px; margin: 4px;' title='{b.get('title', '')}'>{b.get('icon', '🏅')}</span>"
                for b in badges[:10]  # Limit to 10 for performance
            ])
            st.markdown(f"""
                <div style="text-align: center;">
                    {badge_icons_html}
                </div>
            """, unsafe_allow_html=True)


def export_performance_card_image(tournament_data: Dict[str, Any]) -> bytes:
    """
    Export performance card as PNG image for social sharing.

    STUB: Implementation deferred to future sprint (Week 3).

    Args:
        tournament_data: Tournament data dict

    Returns:
        PNG image bytes

    Raises:
        NotImplementedError: Feature not yet implemented
    """
    raise NotImplementedError(
        "PNG export feature not yet implemented. "
        "This is a stub for future development (Week 3 - Social Share sprint)."
    )
