"""
Tournament achievement accordion component
Groups badges by tournament with collapsible sections
Implements adaptive pagination and virtual scrolling for 1000+ badges
"""
import streamlit as st
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from components.rewards.badge_card import render_badge_grid
from components.tournaments.performance_card import render_performance_card, _get_primary_badge
from api_helpers_tournaments import get_user_tournament_rewards
from config import API_BASE_URL, API_TIMEOUT

# Logger for data integrity monitoring
logger = logging.getLogger(__name__)


def validate_placement_consistency(badge: Dict[str, Any], display_rank: Optional[int], tournament_id: int, user_id: int) -> None:
    """
    Production safety alert: Detect suspicious badge-rank combinations (data drift).

    Alert Trigger: Champion/Runner-Up/Third Place badge but rank > 3
    This indicates:
    - Badge awarded with provisional placement
    - Ranking later recalculated
    - Data integrity issue requiring investigation

    Args:
        badge: Badge data with badge_type
        display_rank: Rank to display (from fallback chain)
        tournament_id: Tournament ID
        user_id: User ID
    """
    placement_badges = {
        'CHAMPION': 1,
        'RUNNER_UP': 2,
        'THIRD_PLACE': 3
    }

    badge_type = badge.get('badge_type')
    if badge_type in placement_badges:
        expected_rank = placement_badges[badge_type]

        if display_rank and display_rank > 3:
            # RED FLAG: Placement badge but rank > 3
            logger.error(
                f"[DATA DRIFT DETECTED] Badge ID: {badge.get('id')} | "
                f"Type: {badge_type} (expects #{expected_rank}) | "
                f"Actual rank: {display_rank} | "
                f"User: {user_id} | "
                f"Tournament: {tournament_id} | "
                f"Severity: HIGH"
            )

            # Visual warning in UI (development/staging only)
            if st.session_state.get('debug_mode', False):
                st.error(
                    f"⚠️ Data Integrity Warning: {badge_type} badge with rank #{display_rank} "
                    f"(expected #{expected_rank})"
                )

        elif display_rank and display_rank != expected_rank:
            # WARNING: Placement badge with mismatched rank (but within top 3)
            logger.warning(
                f"[PLACEMENT MISMATCH] Badge ID: {badge.get('id')} | "
                f"Type: {badge_type} (expects #{expected_rank}) | "
                f"Actual rank: {display_rank} | "
                f"User: {user_id} | "
                f"Tournament: {tournament_id}"
            )


def get_adaptive_page_size(total_tournaments: int) -> int:
    if total_tournaments <= 20:
        return 10
    elif total_tournaments <= 100:
        return 20
    else:
        return 50


def group_badges_by_tournament(badges: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    grouped = defaultdict(lambda: {
        'tournament_id': None,
        'tournament_name': 'Unknown Tournament',
        'tournament_code': None,
        'tournament_status': None,
        'start_date': None,
        'badges': [],
        'badge_count': 0,
        'metrics': None
    })

    for badge in badges:
        semester_id = badge.get('semester_id')
        if semester_id:
            if grouped[semester_id]['tournament_id'] is None:
                grouped[semester_id].update({
                    'tournament_id': semester_id,
                    'tournament_name': badge.get('semester_name', 'Unknown Tournament'),
                    'tournament_code': badge.get('tournament_code'),
                    'tournament_status': badge.get('tournament_status'),
                    'start_date': badge.get('tournament_start_date') or badge.get('earned_at'),
                })
            grouped[semester_id]['badges'].append(badge)
            grouped[semester_id]['badge_count'] += 1

    return dict(grouped)


def apply_filters(grouped: Dict[int, Dict[str, Any]], search: str, status: str, sort: str) -> List[Dict[str, Any]]:
    tournaments = list(grouped.values())
    if search:
        search_lower = search.lower()
        tournaments = [t for t in tournaments if search_lower in t['tournament_name'].lower()]
    if status != 'All':
        tournaments = [t for t in tournaments if t.get('tournament_status') == status]
    if sort == 'Recent First':
        tournaments.sort(key=lambda t: t.get('start_date') or '', reverse=True)
    else:
        tournaments.sort(key=lambda t: t.get('start_date') or '', reverse=False)
    return tournaments


def fetch_tournament_metrics(token: str, tournament_id: int, user_id: int, badge_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch tournament metrics with rank fallback chain.

    Rank Source Hierarchy (Data Integrity Strategy):
    1. tournament_rankings.rank (AUTHORITY - current truth)
    2. tournament_participations.placement (FALLBACK - rewards table)
    3. badge_metadata.placement (LAST RESORT - creation snapshot)
    4. None (hide metric if all sources fail)

    Args:
        token: Auth token
        tournament_id: Tournament ID
        user_id: User ID
        badge_data: Optional badge data for fallback rank source

    Returns:
        Dict with metrics including rank, rank_source, points, wins, draws, losses, goals_for, etc.
    """
    try:
        # Initialize metrics
        metrics = {
            'rank': None,
            'rank_source': None,
            'points': None,
            'wins': None,
            'draws': None,
            'losses': None,
            'goals_for': None,
            'goals_against': None,
            'total_participants': None,
            'avg_points': None,
            'xp_earned': None,
            'credits_earned': None,
            'badges_earned': None
        }

        # 1. Try tournament_rankings (AUTHORITY)
        rankings_response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/rankings",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if rankings_response.status_code == 200:
            rankings_data = rankings_response.json().get('rankings', [])
            user_ranking = next((r for r in rankings_data if r.get('user_id') == user_id), None)

            if user_ranking:
                # Use ranking as authority source
                metrics['rank'] = user_ranking.get('rank')
                metrics['rank_source'] = 'current'
                metrics['points'] = user_ranking.get('points', 0)
                metrics['wins'] = user_ranking.get('wins', 0)
                metrics['draws'] = user_ranking.get('draws', 0)
                metrics['losses'] = user_ranking.get('losses', 0)
                metrics['goals_for'] = user_ranking.get('goals_for', 0)
                metrics['goals_against'] = user_ranking.get('goals_against', 0)

            # Compute tournament context (avg_points, total_participants)
            if rankings_data:
                metrics['total_participants'] = len(rankings_data)
                total_points = sum(r.get('points', 0) for r in rankings_data)
                metrics['avg_points'] = round(total_points / len(rankings_data), 2) if len(rankings_data) > 0 else None

        # 2. Get rewards (includes participation.placement fallback)
        success, error, reward_data = get_user_tournament_rewards(token, tournament_id, user_id)
        if success and reward_data:
            participation = reward_data.get('participation', {})
            badges = reward_data.get('badges', {})

            metrics['xp_earned'] = participation.get('total_xp', 0)
            metrics['credits_earned'] = participation.get('credits', 0)
            metrics['badges_earned'] = badges.get('total_badges_earned', 0)

            # Fallback to participation.placement if ranking.rank is None
            if not metrics['rank'] and participation.get('placement'):
                metrics['rank'] = participation.get('placement')
                metrics['rank_source'] = 'fallback_participation'
                logger.warning(f"Tournament {tournament_id}, User {user_id}: Using participation.placement={metrics['rank']} (ranking missing)")

        # 3. Last resort: badge_metadata.placement
        if not metrics['rank'] and badge_data:
            badge_metadata = badge_data.get('badge_metadata', {})
            if badge_metadata.get('placement'):
                metrics['rank'] = badge_metadata['placement']
                metrics['rank_source'] = 'snapshot'
                logger.warning(f"Tournament {tournament_id}, User {user_id}: Using badge_metadata.placement={metrics['rank']} (ranking + participation missing)")

        # 4. Fallback for total_participants (independent of rank)
        if not metrics['total_participants'] and badge_data:
            badge_metadata = badge_data.get('badge_metadata', {})
            if badge_metadata.get('total_participants'):
                metrics['total_participants'] = badge_metadata['total_participants']
                logger.info(f"Tournament {tournament_id}, User {user_id}: Using badge_metadata.total_participants={metrics['total_participants']} (rankings empty)")

        # 5. If still no rank, log error (but don't fail - UI will hide metric)
        if not metrics['rank']:
            logger.error(f"Tournament {tournament_id}, User {user_id}: No rank data from any source (ranking, participation, badge_metadata)")

        return metrics
    except Exception as e:
        logger.error(f"Could not load metrics for tournament {tournament_id}, user {user_id}: {str(e)}")
        st.warning(f"Could not load metrics: {str(e)}")
        return None


def render_tournament_accordion_item(tournament_data: Dict[str, Any], is_expanded: bool, token: str, user_id: int, is_most_recent: bool = False) -> None:
    tournament_id = tournament_data['tournament_id']
    tournament_name = tournament_data['tournament_name']
    tournament_status = tournament_data.get('tournament_status') or 'UNKNOWN'
    start_date = tournament_data.get('start_date')
    badges = tournament_data['badges']
    badge_count = tournament_data['badge_count']
    
    date_str = "Date unknown"
    if start_date:
        try:
            if 'T' in str(start_date):
                dt = datetime.fromisoformat(str(start_date).replace('Z', '+00:00'))
                date_str = dt.strftime("%b %d, %Y")
            else:
                date_str = str(start_date)
        except:
            date_str = str(start_date)
    
    status_badge_color = {
        "COMPLETED": "#10b981",
        "REWARDS_DISTRIBUTED": "#8b5cf6",
        "IN_PROGRESS": "#f59e0b",
        "UPCOMING": "#3b82f6",
    }.get(tournament_status, "#6b7280")
    
    display_name = tournament_name if len(tournament_name) <= 50 else tournament_name[:47] + "..."
    border_style = "border-left: 4px solid #3b82f6;" if is_most_recent else ""
    
    with st.expander(f"🏆 {display_name} ({badge_count} badges)", expanded=is_expanded):
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {status_badge_color}20 0%, white 100%);
                    padding: 12px; border-radius: 8px; margin-bottom: 16px; {border_style}">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="flex: 1; min-width: 200px;">
                    <div style="font-weight: 600; font-size: 16px; color: #1F2937; margin-bottom: 4px;" title="{tournament_name}">
                        {tournament_name}
                    </div>
                    <div style="font-size: 13px; color: #6B7280;">📅 {date_str}</div>
                </div>
                <div>
                    <span style="background: {status_badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                        {str(tournament_status).replace('_', ' ') if tournament_status else 'UNKNOWN'}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if tournament_status in ["COMPLETED", "REWARDS_DISTRIBUTED"]:
            # FORCE REFRESH: Always refetch metrics to get updated total_participants fallback
            # TODO: Remove after cache strategy implemented (version-based)
            if True:  # Force refetch (was: if tournament_data.get('metrics') is None)
                with st.spinner("Loading tournament metrics..."):
                    # Pass PRIMARY badge (highest priority) for fallback metadata
                    # Fix: Use _get_primary_badge instead of badges[0] to avoid reading wrong metadata
                    primary_badge = _get_primary_badge(badges) if badges else None
                    metrics = fetch_tournament_metrics(token, tournament_id, user_id, badge_data=primary_badge)
                    tournament_data['metrics'] = metrics
                    # Debug: Log metrics data
                    logger.info(f"Tournament {tournament_id}: rank={metrics.get('rank')}, total_participants={metrics.get('total_participants')}")
            else:
                metrics = tournament_data['metrics']

            if metrics:
                # Production safety: Validate placement consistency for all badges
                for badge in badges:
                    validate_placement_consistency(badge, metrics.get('rank'), tournament_id, user_id)

                # Render Performance Card (NEW: Reusable component)
                render_performance_card(
                    tournament_data=tournament_data,
                    size="normal",
                    show_badges=False,  # Badges shown separately below
                    show_rewards=True,
                    context="accordion"
                )
                st.markdown("---")
        elif tournament_status == "IN_PROGRESS":
            st.info("⏳ Tournament In Progress - Rewards will be available after completion")
            st.markdown("---")
        elif tournament_status == "UPCOMING":
            st.info("📅 Upcoming Tournament - Metrics will be available after completion")
            st.markdown("---")
        
        st.markdown(f"##### 🏆 Badges Earned ({badge_count})")
        if badge_count > 20:
            st.caption(f"Showing first 20 of {badge_count} badges")
            render_badge_grid(badges[:20], columns=3, size="normal", show_empty_state=False)
            if st.button(f"Show {badge_count - 20} More Badges", key=f"show_more_badges_{tournament_id}", use_container_width=True):
                render_badge_grid(badges[20:], columns=3, size="normal", show_empty_state=False)
        else:
            render_badge_grid(badges, columns=3, size="normal", show_empty_state=False)


def render_tournament_accordion_list(badges: List[Dict[str, Any]], token: str, user_id: int) -> None:
    from components.tournaments.tournament_filters import render_tournament_filters
    
    if 'tournament_achievements_state' not in st.session_state:
        st.session_state['tournament_achievements_state'] = {
            'grouped_tournaments': {},
            'filtered_tournaments': [],
            'page': 0,
            'page_size': 10,
            'total_tournaments': 0,
            'search_query': '',
            'status_filter': 'All',
            'sort_order': 'Recent First',
            'expanded_tournament_ids': set(),
            'auto_expanded_most_recent': False,
            'last_update': None,
            'cache_ttl': 300,
            'last_successful_badges': None,
            'api_error': None
        }
    
    state = st.session_state['tournament_achievements_state']
    
    if not badges or len(badges) == 0:
        st.info("""
🏆 **No Tournament Achievements Yet**

You haven't earned any badges yet. Participate in tournaments to unlock achievements!

**How to get started:**
1. Browse available tournaments in the "🌍 Browse Tournaments" tab
2. Enroll in a tournament that matches your skill level
3. Attend the session and compete
4. Earn badges based on your performance!
        """)
        return
    
    state['last_successful_badges'] = badges
    
    if not state['grouped_tournaments'] or state.get('last_update') is None:
        state['grouped_tournaments'] = group_badges_by_tournament(badges)
        state['last_update'] = datetime.now()
    
    st.markdown("---")
    search_query, status_filter, sort_order = render_tournament_filters()
    
    filtered_tournaments = apply_filters(state['grouped_tournaments'], search_query, status_filter, sort_order)
    state['filtered_tournaments'] = filtered_tournaments
    state['total_tournaments'] = len(filtered_tournaments)
    
    if len(filtered_tournaments) == 0:
        st.info(f"""
🔍 **No Tournaments Found**

No tournaments match your search criteria.

**Current filters:**
- Search: **"{search_query}"** {f'(Status: {status_filter})' if status_filter != 'All' else ''}

**Suggestions:**
- Try a different search term
- Clear filters to see all tournaments
- Check spelling
        """)
        if st.button("Clear Filters", key="clear_filters"):
            state['search_query'] = ''
            state['status_filter'] = 'All'
            st.rerun()
        return
    
    page_size = get_adaptive_page_size(state['total_tournaments'])
    state['page_size'] = page_size
    current_page = state.get('page', 0)
    start_idx = current_page * page_size
    end_idx = min(start_idx + page_size, state['total_tournaments'])
    paginated_tournaments = filtered_tournaments[start_idx:end_idx]
    
    st.caption(f"Showing {start_idx + 1}-{end_idx} of {state['total_tournaments']} tournaments")
    
    if not state['auto_expanded_most_recent'] and len(filtered_tournaments) > 0:
        most_recent_id = filtered_tournaments[0]['tournament_id']
        state['expanded_tournament_ids'].add(most_recent_id)
        state['auto_expanded_most_recent'] = True
    
    for idx, tournament_data in enumerate(paginated_tournaments):
        tournament_id = tournament_data['tournament_id']
        is_expanded = tournament_id in state['expanded_tournament_ids']
        is_most_recent = (idx == 0 and current_page == 0)
        render_tournament_accordion_item(tournament_data, is_expanded, token, user_id, is_most_recent)
    
    remaining = state['total_tournaments'] - end_idx
    if remaining > 0:
        st.markdown("---")
        next_batch = min(page_size, remaining)
        if st.button(f"📥 Load {next_batch} More Tournaments ({remaining} remaining)", key="load_more_tournaments", use_container_width=True):
            state['page'] += 1
            st.rerun()
