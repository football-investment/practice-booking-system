"""
Admin Dashboard Components - Modular Architecture
Exports all admin dashboard rendering functions
"""

from .dashboard_header import render_dashboard_header
from .overview_tab import render_overview_tab
from .users_tab import render_users_tab
from .sessions_tab import render_sessions_tab
from .locations_tab import render_locations_tab
from .financial_tab import render_financial_tab
from .semesters_tab import render_semesters_tab
from .tournaments_tab import render_tournaments_tab
from .system_events_tab import render_system_events_tab
from .game_presets_tab import render_game_presets_tab

__all__ = [
    'render_dashboard_header',
    'render_overview_tab',
    'render_users_tab',
    'render_sessions_tab',
    'render_locations_tab',
    'render_financial_tab',
    'render_semesters_tab',
    'render_tournaments_tab',
    'render_system_events_tab',
    'render_game_presets_tab',
]
