"""
Shared Tournament Workflow Functions

This module contains reusable E2E workflow functions that work for BOTH:
- INDIVIDUAL tournament tests
- HEAD_TO_HEAD tournament tests

NO DUPLICATION: All test suites import from here.
"""

# Re-export all functions from the original test file for backwards compatibility
# This prevents breaking existing tests while enabling shared usage

from .test_tournament_full_ui_workflow import (
    get_random_participants,
    wait_for_streamlit_load,
    scroll_to_element,
    navigate_to_home,
    click_create_new_tournament,
    fill_tournament_creation_form,
    enroll_players_via_ui,
    start_tournament_via_ui,
    generate_sessions_via_ui,
    submit_results_via_ui,
    finalize_sessions_via_ui,
    complete_tournament_via_ui,
    distribute_rewards_via_ui,
    verify_final_tournament_state,
    verify_skill_rewards,
    ALL_STUDENT_IDS,
)

# Import from streamlit_helpers
from .streamlit_helpers import (
    click_streamlit_button,
    wait_for_streamlit_rerun,
)

__all__ = [
    'get_random_participants',
    'wait_for_streamlit_load',
    'scroll_to_element',
    'navigate_to_home',
    'click_create_new_tournament',
    'fill_tournament_creation_form',
    'enroll_players_via_ui',
    'start_tournament_via_ui',
    'generate_sessions_via_ui',
    'submit_results_via_ui',
    'finalize_sessions_via_ui',
    'complete_tournament_via_ui',
    'distribute_rewards_via_ui',
    'verify_final_tournament_state',
    'verify_skill_rewards',
    'click_streamlit_button',
    'wait_for_streamlit_rerun',
    'ALL_STUDENT_IDS',
]
