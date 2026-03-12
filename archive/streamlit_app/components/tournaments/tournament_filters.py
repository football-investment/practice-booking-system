"""
Filter controls for tournament achievements section
Handles search, status filter, and sort order
"""
import streamlit as st
from typing import Tuple


def render_tournament_filters() -> Tuple[str, str, str]:
    """
    Render filter controls for tournaments

    Returns:
        Tuple of (search_query, status_filter, sort_order)
    """
    if 'tournament_achievements_state' not in st.session_state:
        st.session_state['tournament_achievements_state'] = {
            'search_query': '',
            'status_filter': 'All',
            'sort_order': 'Recent First'
        }

    state = st.session_state['tournament_achievements_state']

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_query = st.text_input(
            "Search tournaments",
            value=state.get('search_query', ''),
            placeholder="Enter tournament name...",
            key="tournament_search_input",
            label_visibility="collapsed"
        )
        state['search_query'] = search_query

    with col2:
        status_options = ['All', 'COMPLETED', 'REWARDS_DISTRIBUTED', 'IN_PROGRESS', 'UPCOMING']
        status_filter = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(state.get('status_filter', 'All')),
            key="tournament_status_filter",
            label_visibility="collapsed"
        )
        state['status_filter'] = status_filter

    with col3:
        sort_options = ['Recent First', 'Oldest First']
        sort_order = st.selectbox(
            "Sort",
            options=sort_options,
            index=sort_options.index(state.get('sort_order', 'Recent First')),
            key="tournament_sort_order",
            label_visibility="collapsed"
        )
        state['sort_order'] = sort_order

    return search_query, status_filter, sort_order
