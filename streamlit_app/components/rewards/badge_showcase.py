"""
Badge Showcase Component

Displays user's tournament achievement badges in an organized showcase format.
Features:
- Featured/pinned badges section
- Recent badges
- Badges by category
- Rarity statistics
"""
import streamlit as st
from typing import Dict, Any, Optional, List
from .badge_card import render_badge_card, render_badge_grid, get_rarity_emoji, get_rarity_sort_value


def render_badge_showcase(
    user_id: int,
    token: str,
    show_stats: bool = True,
    show_categories: bool = True,
    max_featured: int = 3
) -> None:
    """
    Render complete badge showcase for user profile.

    Args:
        user_id: User ID to show badges for
        token: Authentication token
        show_stats: Show badge statistics (rarity counts, total badges)
        show_categories: Show badges grouped by category
        max_featured: Maximum number of featured badges to show
    """
    from api_helpers_tournaments import get_user_badge_showcase

    # Fetch badge showcase data
    success, error, showcase_data = get_user_badge_showcase(token, user_id)

    if not success:
        st.error(f"❌ Failed to load badge showcase: {error}")
        return

    if not showcase_data:
        st.info("🏆 No badges earned yet. Participate in tournaments to earn your first badge!")
        return

    showcase = showcase_data.get('showcase', {})
    total_badges = showcase.get('total_badges', 0)
    rarest_badge_rarity = showcase.get('rarest_badge_rarity')
    featured_badges = showcase.get('featured_badges', [])
    sections = showcase.get('sections', [])
    stats = showcase.get('stats', {})

    # Header with total badge count
    st.markdown(f"### 🏆 Achievement Badges ({total_badges})")

    if rarest_badge_rarity:
        rarity_emoji = get_rarity_emoji(rarest_badge_rarity)
        st.caption(f"Rarest badge: {rarity_emoji} {rarest_badge_rarity}")

    st.divider()

    # Show badge statistics
    if show_stats and stats:
        _render_badge_stats(stats)
        st.divider()

    # Featured badges section
    if featured_badges:
        _render_featured_badges(featured_badges, max_featured)
        st.divider()

    # Badges by category
    if show_categories and sections:
        _render_badge_sections(sections)


def _render_badge_stats(stats: Dict[str, int]) -> None:
    """Render badge statistics (rarity breakdown)"""
    st.markdown("#### 📊 Badge Collection")

    # Calculate total
    total = sum(stats.values())

    if total == 0:
        st.info("No badges earned yet")
        return

    # Create columns for rarity stats
    rarity_order = ["LEGENDARY", "EPIC", "RARE", "UNCOMMON", "COMMON"]
    non_zero_rarities = [r for r in rarity_order if stats.get(r, 0) > 0]

    if not non_zero_rarities:
        return

    cols = st.columns(len(non_zero_rarities))

    for idx, rarity in enumerate(non_zero_rarities):
        count = stats.get(rarity, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        emoji = get_rarity_emoji(rarity)

        with cols[idx]:
            st.metric(
                label=f"{emoji} {rarity.title()}",
                value=count,
                delta=f"{percentage:.0f}%" if percentage > 0 else None
            )


def _render_featured_badges(featured_badges: List[Dict[str, Any]], max_count: int) -> None:
    """Render featured/pinned badges section"""
    st.markdown("#### ⭐ Featured Badges")

    # Show up to max_count badges
    badges_to_show = featured_badges[:max_count]

    if not badges_to_show:
        st.info("No featured badges yet")
        return

    # Use grid layout for featured badges
    render_badge_grid(badges_to_show, columns=min(3, len(badges_to_show)), size="extended")


def _render_badge_sections(sections: List[Dict[str, Any]]) -> None:
    """Render badges grouped by category"""
    for section in sections:
        section_title = section.get('section_title', 'Badges')
        section_icon = section.get('section_icon', '🏆')
        badges = section.get('badges', [])
        total_in_category = section.get('total_in_category', len(badges))

        if not badges:
            continue

        # Section header
        st.markdown(f"#### {section_icon} {section_title}")

        if total_in_category > len(badges):
            st.caption(f"Showing {len(badges)} of {total_in_category} badges")

        # Render badges in grid
        render_badge_grid(badges, columns=3, size="normal")

        st.write("")  # Spacing


def render_recent_badges(
    user_id: int,
    token: str,
    limit: int = 5,
    title: str = "🆕 Recent Badges"
) -> None:
    """
    Render user's most recent badges.

    Args:
        user_id: User ID to show badges for
        token: Authentication token
        limit: Maximum number of recent badges to show
        title: Section title
    """
    from api_helpers_tournaments import get_user_badges

    # Fetch recent badges
    success, error, badges_data = get_user_badges(token, user_id, limit=limit)

    if not success:
        st.error(f"❌ Failed to load recent badges: {error}")
        return

    badges = badges_data.get('badges', [])

    if not badges:
        st.info("🏆 No badges earned yet")
        return

    st.markdown(f"#### {title}")

    # Sort by earned_at (newest first)
    sorted_badges = sorted(
        badges,
        key=lambda b: b.get('earned_at', ''),
        reverse=True
    )

    # Take only the most recent
    recent_badges = sorted_badges[:limit]

    # Render in compact grid
    render_badge_grid(recent_badges, columns=min(5, len(recent_badges)), size="compact")


def render_rarest_badges(
    user_id: int,
    token: str,
    limit: int = 3,
    title: str = "💎 Rarest Badges"
) -> None:
    """
    Render user's rarest badges.

    Args:
        user_id: User ID to show badges for
        token: Authentication token
        limit: Maximum number of badges to show
        title: Section title
    """
    from api_helpers_tournaments import get_user_badges

    # Fetch all badges
    success, error, badges_data = get_user_badges(token, user_id, limit=100)

    if not success:
        st.error(f"❌ Failed to load badges: {error}")
        return

    badges = badges_data.get('badges', [])

    if not badges:
        st.info("🏆 No badges earned yet")
        return

    # Sort by rarity (rarest first)
    sorted_badges = sorted(
        badges,
        key=lambda b: get_rarity_sort_value(b.get('rarity', 'COMMON')),
        reverse=True
    )

    # Take only the rarest
    rarest_badges = sorted_badges[:limit]

    st.markdown(f"#### {title}")

    # Render in normal grid
    render_badge_grid(rarest_badges, columns=min(3, len(rarest_badges)), size="normal")


def render_tournament_badges(
    user_id: int,
    tournament_id: int,
    token: str,
    title: Optional[str] = None
) -> None:
    """
    Render badges earned in a specific tournament.

    Args:
        user_id: User ID to show badges for
        tournament_id: Tournament ID to filter by
        token: Authentication token
        title: Optional custom title
    """
    from api_helpers_tournaments import get_user_badges

    # Fetch tournament-specific badges
    success, error, badges_data = get_user_badges(
        token,
        user_id,
        tournament_id=tournament_id
    )

    if not success:
        st.error(f"❌ Failed to load tournament badges: {error}")
        return

    badges = badges_data.get('badges', [])

    if not badges:
        st.info("🏆 No badges earned in this tournament")
        return

    # Use custom title or default
    display_title = title or f"🏆 Tournament Badges ({len(badges)})"
    st.markdown(f"#### {display_title}")

    # Render in grid
    render_badge_grid(badges, columns=3, size="normal")


def render_badge_summary_widget(
    user_id: int,
    token: str,
    show_count: bool = True,
    show_rarest: bool = True,
    compact: bool = False
) -> None:
    """
    Render compact badge summary widget (for dashboard headers/sidebars).

    Args:
        user_id: User ID to show summary for
        token: Authentication token
        show_count: Show total badge count
        show_rarest: Show rarest badge
        compact: Use ultra-compact layout
    """
    from api_helpers_tournaments import get_user_badges

    # Fetch badges
    success, error, badges_data = get_user_badges(token, user_id, limit=100)

    if not success:
        return  # Silent fail for widget

    badges = badges_data.get('badges', [])
    total_badges = len(badges)

    if total_badges == 0:
        if not compact:
            st.caption("🏆 No badges yet")
        return

    # Find rarest badge
    rarest_badge = None
    if show_rarest and badges:
        sorted_badges = sorted(
            badges,
            key=lambda b: get_rarity_sort_value(b.get('rarity', 'COMMON')),
            reverse=True
        )
        rarest_badge = sorted_badges[0]

    if compact:
        # Ultra-compact (single line)
        rarest_info = ""
        if rarest_badge:
            rarity = rarest_badge.get('rarity', 'COMMON')
            emoji = get_rarity_emoji(rarity)
            rarest_info = f" | Rarest: {emoji}"

        st.caption(f"🏆 {total_badges} badges{rarest_info}")
    else:
        # Normal widget
        col1, col2 = st.columns(2)

        with col1:
            if show_count:
                st.metric("🏆 Badges", total_badges)

        with col2:
            if show_rarest and rarest_badge:
                rarity = rarest_badge.get('rarity', 'COMMON')
                emoji = get_rarity_emoji(rarity)
                st.metric("💎 Rarest", f"{emoji} {rarity.title()}")
