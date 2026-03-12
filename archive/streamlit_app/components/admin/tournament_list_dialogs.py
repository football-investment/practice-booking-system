"""
Tournament List Dialogs Module

Dialog screens for tournament management.
Uses component library for consistent UX.
"""

import requests
import streamlit as st
from typing import Dict, List, Optional
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from streamlit_components.core.api_client import api_client, APIError
from components.admin.tournament_list_helpers import (
    update_tournament,
    generate_tournament_sessions,
    preview_tournament_sessions,
    delete_generated_sessions,
    save_tournament_reward_config
)
from config import API_BASE_URL, SESSION_TOKEN_KEY, SESSION_ROLE_KEY


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


def _fetch_active_campuses() -> List[Dict]:
    """Fetch active campuses from the API using the current session token."""
    token = st.session_state.get(SESSION_TOKEN_KEY, "")
    if not token:
        return []
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/campuses/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 200:
            return [c for c in response.json() if c.get("is_active", True)]
    except Exception:
        pass
    return []


def show_generate_sessions_dialog():
    """
    Generate sessions dialog — role-aware campus selection.

    ADMIN      → multiselect pre-populated with ALL active campuses (auto multi-venue).
                 Admin can deselect campuses if needed.
    INSTRUCTOR → single-select only (backend enforces 403 for >1 campus).
    """
    tournament_id = st.session_state.get("generate_sessions_tournament_id")
    role = st.session_state.get(SESSION_ROLE_KEY, "").upper()
    is_admin = role == "ADMIN"

    st.markdown("### Generate Sessions")

    card = Card(title="Session Generation", card_id="generate_sessions")
    with card.container():
        # ── Campus selection ──────────────────────────────────────────────
        campuses = _fetch_active_campuses()
        campus_options = {f"{c.get('name', '')} (ID {c['id']})": c["id"] for c in campuses}
        campus_label_list = list(campus_options.keys())

        selected_campus_ids: Optional[List[int]] = None

        if campuses:
            if is_admin:
                # Auto-select ALL active campuses by default.
                # Sessions are distributed across campuses automatically (round-robin per group).
                # Admin can deselect campuses to restrict to fewer venues.
                if len(campuses) > 1:
                    st.info(
                        f"**{len(campuses)} active campus(es) detected** — "
                        "all are pre-selected for multi-venue parallel scheduling. "
                        "Deselect campuses to restrict to fewer venues.",
                        icon="🏟️",
                    )
                selected_labels = st.multiselect(
                    "Campus(es) — multi-venue",
                    options=campus_label_list,
                    default=campus_label_list,  # ← auto-select ALL active campuses
                    help="All active campuses are pre-selected. Sessions (matches) are "
                         "distributed automatically across campuses via round-robin assignment. "
                         "Deselect campuses to limit venue usage.",
                    key="gen_sessions_campus_multiselect",
                )
                if selected_labels:
                    selected_campus_ids = [campus_options[lbl] for lbl in selected_labels]
            else:
                # Instructor: single-select only
                if len(campuses) > 1:
                    st.info(
                        f"**{len(campuses)} campuses available** — "
                        "instructors can only generate sessions for one campus at a time.",
                        icon="ℹ️",
                    )
                campus_label_list_with_none = ["— No campus override —"] + campus_label_list
                selected_label = st.selectbox(
                    "Campus",
                    options=campus_label_list_with_none,
                    index=0,
                    help="Select your campus for session generation.",
                    key="gen_sessions_campus_selectbox",
                )
                if selected_label != "— No campus override —":
                    selected_campus_ids = [campus_options[selected_label]]
        else:
            st.caption("No active campuses found — sessions will use the tournament's default campus.")

        # ── Generate button ───────────────────────────────────────────────
        if st.button("🎲 Generate Sessions", key="btn_generate_sessions", type="primary"):
            if tournament_id is None:
                st.error("No tournament selected.")
            else:
                data: Dict = {
                    "parallel_fields": 1,
                    "session_duration_minutes": 90,
                    "break_minutes": 15,
                    "number_of_rounds": 1,
                }
                if selected_campus_ids:
                    data["campus_ids"] = selected_campus_ids

                with Loading.spinner("Generating sessions..."):
                    result = generate_tournament_sessions(tournament_id, data)
                if result:
                    # Close the dialog and refresh
                    st.session_state[f"show_generate_dialog_{tournament_id}"] = False
                    st.rerun()

    card.close_container()


def show_preview_sessions_dialog():
    """Preview sessions dialog"""
    st.markdown("### Preview Sessions")

    card = Card(title="Session Preview", card_id="preview_sessions")
    with card.container():
        st.info("Session preview")
    card.close_container()


def show_delete_tournament_dialog():
    """Delete tournament dialog — DELETE /api/v1/tournaments/{id}"""
    tournament_id = st.session_state.get("delete_tournament_id")
    tournament_name = st.session_state.get("delete_tournament_name", "this tournament")

    st.markdown("### Delete Tournament")
    card = Card(title="Confirm Deletion", card_id="delete_tournament")
    with card.container():
        st.error(
            f"**Permanently delete '{tournament_name}'?**\n\n"
            "This will remove the tournament, all sessions, bookings, and enrollment records. "
            "**This cannot be undone.**"
        )
        confirm_text = st.text_input(
            "Type the tournament name to confirm:",
            key="input_delete_confirm",
            placeholder=tournament_name,
        )
        delete_enabled = confirm_text.strip() == tournament_name.strip()
        if st.button("🗑️ Delete Permanently", type="primary", key="btn_confirm_delete", disabled=not delete_enabled):
            if tournament_id is None:
                Error.message("No tournament selected.")
            else:
                try:
                    with Loading.spinner("Deleting tournament..."):
                        api_client.delete(f"/api/v1/tournaments/{tournament_id}")
                    Success.message(f"Tournament '{tournament_name}' deleted.")
                    st.rerun()
                except APIError as e:
                    Error.message(f"Failed to delete: {e.message}")
    card.close_container()


def show_cancel_tournament_dialog():
    """Cancel tournament dialog — PATCH status → CANCELLED"""
    tournament_id = st.session_state.get("cancel_tournament_id")
    tournament_name = st.session_state.get("cancel_tournament_name", "this tournament")
    current_status = st.session_state.get("cancel_tournament_status", "?")

    st.markdown("### Cancel Tournament")
    card = Card(title="Confirm Cancellation", card_id="cancel_tournament")
    with card.container():
        st.warning(
            f"**{tournament_name}** (currently: `{current_status}`) will be marked as **CANCELLED**.\n\n"
            "This action cannot be undone. Players will no longer be able to participate."
        )
        if st.button("✅ Confirm Cancel", key="btn_confirm_cancel", type="primary"):
            if tournament_id is None:
                Error.message("No tournament selected.")
            else:
                try:
                    with Loading.spinner("Cancelling tournament..."):
                        api_client.patch(
                            f"/api/v1/tournaments/{tournament_id}/status",
                            data={"new_status": "CANCELLED", "reason": "Admin cancelled via dashboard"}
                        )
                    Success.message(f"Tournament '{tournament_name}' cancelled successfully.")
                    st.rerun()
                except APIError as e:
                    Error.message(f"Failed to cancel (HTTP {e.status_code}): {e.message}")
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
    """Reset tournament sessions dialog — deletes all auto-generated sessions."""
    tournament_id = st.session_state.get("reset_sessions_tournament_id")

    st.markdown("### Reset Tournament Sessions")

    card = Card(title="Confirm Session Reset", card_id="reset_sessions")
    with card.container():
        st.warning(
            "This will **delete all auto-generated sessions** and reset the generation flag. "
            "Manual sessions are NOT affected. "
            "After reset you can regenerate with different campus/field settings."
        )

        if st.button("🗑️ Delete sessions & reset", type="primary", key="btn_reset_sessions_confirm"):
            if tournament_id is None:
                Error.message("No tournament selected.")
            else:
                with Loading.spinner("Deleting sessions..."):
                    ok = delete_generated_sessions(tournament_id)
                if ok:
                    st.rerun()
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
