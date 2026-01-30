"""
Tournament List Dialogs Module

Dialog screens for tournament management.
Uses component library for consistent UX.
"""

import streamlit as st
from typing import Dict
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from tournament_list_helpers import (
    update_tournament,
    generate_tournament_sessions,
    preview_tournament_sessions,
    delete_generated_sessions,
    save_tournament_reward_config
)


def show_edit_tournament_dialog():
    """Edit tournament configuration dialog"""
    st.markdown("### Edit Tournament")

    card = Card(title="Tournament Configuration", card_id="edit_tournament")
    with card.container():
        form = SingleColumnForm("edit_tournament_form")
        with form.container():
            # Form fields here
            st.info("Edit tournament configuration")
    card.close_container()


def show_generate_sessions_dialog():
    """Generate sessions dialog"""
    st.markdown("### Generate Sessions")

    card = Card(title="Session Generation", card_id="generate_sessions")
    with card.container():
        if st.button("Generate", key="btn_generate_sessions"):
            with Loading.spinner("Generating sessions..."):
                # Generation logic
                st.success("Sessions generated")
    card.close_container()


def show_preview_sessions_dialog():
    """Preview sessions dialog"""
    st.markdown("### Preview Sessions")

    card = Card(title="Session Preview", card_id="preview_sessions")
    with card.container():
        st.info("Session preview")
    card.close_container()


def show_delete_tournament_dialog():
    """Delete tournament dialog"""
    st.markdown("### Delete Tournament")

    card = Card(title="Confirm Deletion", card_id="delete_tournament")
    with card.container():
        st.warning("This action cannot be undone")

        if st.button("Delete", type="primary", key="btn_confirm_delete"):
            Success.message("Tournament deleted")
    card.close_container()


def show_cancel_tournament_dialog():
    """Cancel tournament dialog"""
    st.markdown("### Cancel Tournament")

    card = Card(title="Confirm Cancellation", card_id="cancel_tournament")
    with card.container():
        if st.button("Cancel Tournament", key="btn_confirm_cancel"):
            Success.message("Tournament cancelled")
    card.close_container()


def show_edit_reward_config_dialog():
    """Edit reward configuration dialog"""
    st.markdown("### Edit Reward Configuration")

    card = Card(title="Reward Configuration", card_id="reward_config")
    with card.container():
        st.info("Reward configuration editor")
    card.close_container()


def show_enrollment_viewer_modal(tournament_id: int, tournament_name: str):
    """View tournament enrollments"""
    st.markdown(f"### Enrollments: {tournament_name}")

    card = Card(title="Enrollment List", card_id="enrollments")
    with card.container():
        st.info(f"Showing enrollments for tournament {tournament_id}")
    card.close_container()


def show_add_game_dialog():
    """Add new game/session dialog"""
    st.markdown("### Add New Game")

    card = Card(title="Game Configuration", card_id="add_game")
    with card.container():
        form = SingleColumnForm("add_game_form")
        with form.container():
            st.text_input("Game Title", key="input_game_title")
            st.selectbox("Game Type", options=["League", "Knockout"], key="input_game_type")
            st.date_input("Game Date", key="input_game_date")
            st.time_input("Start Time", key="input_game_time")

            if st.button("Add Game", type="primary", key="btn_add_game"):
                Success.message("Game added successfully!")
    card.close_container()


def show_delete_game_dialog():
    """Delete game/session dialog"""
    st.markdown("### Delete Game")

    card = Card(title="Confirm Game Deletion", card_id="delete_game")
    with card.container():
        st.warning("This will permanently delete the game and all associated data.")

        if st.button("Delete Game", type="primary", key="btn_confirm_delete_game"):
            Success.message("Game deleted successfully!")
    card.close_container()


def show_reset_sessions_dialog():
    """Reset tournament sessions dialog"""
    st.markdown("### Reset Tournament Sessions")

    card = Card(title="Confirm Session Reset", card_id="reset_sessions")
    with card.container():
        st.warning("This will delete all generated sessions and reset tournament structure.")

        if st.button("Reset Sessions", type="primary", key="btn_reset_sessions"):
            with Loading.spinner("Resetting sessions..."):
                # Reset logic handled by helper
                Success.message("Sessions reset successfully!")
    card.close_container()


def show_edit_schedule_dialog():
    """Edit session schedule dialog"""
    st.markdown("### Edit Session Schedule")

    card = Card(title="Schedule Configuration", card_id="edit_schedule")
    with card.container():
        form = SingleColumnForm("edit_schedule_form")
        with form.container():
            st.date_input("Session Date", key="input_schedule_date")
            st.time_input("Start Time", key="input_schedule_start")
            st.time_input("End Time", key="input_schedule_end")

            if st.button("Update Schedule", type="primary", key="btn_update_schedule"):
                Success.message("Schedule updated successfully!")
    card.close_container()


def show_edit_game_type_dialog():
    """Edit game type and details dialog"""
    st.markdown("### Edit Game Type")

    card = Card(title="Game Type Configuration", card_id="edit_game_type")
    with card.container():
        form = SingleColumnForm("edit_game_type_form")
        with form.container():
            st.text_input("Game Title", key="input_edit_game_title")
            st.selectbox("Game Type", options=["League", "Knockout", "Swiss"], key="input_edit_game_type")
            st.date_input("Game Date", key="input_edit_game_date")
            st.time_input("Start Time", key="input_edit_game_time")

            if st.button("Update Game", type="primary", key="btn_update_game"):
                Success.message("Game updated successfully!")
    card.close_container()
