"""
Tournament List Module - Tournament listing and game management
Refactored following UI_REFACTOR_PATTERN.md
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Dict

# Setup path: add both streamlit_app/ and repo root so streamlit_components is found
_streamlit_app_dir = Path(__file__).parent.parent.parent
_repo_root = _streamlit_app_dir.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_streamlit_app_dir))

from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.core.auth import AuthManager
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error

from components.admin.tournament_list_helpers import (
    get_user_names_from_db,
    get_tournament_sessions_from_db,
    get_campus_schedules_for_tournament,
    get_location_info,
    get_campus_info,
    get_all_tournaments,
    get_tournament_sessions,
    update_tournament,
    get_tournament_enrollment_count,
    generate_tournament_sessions,
    preview_tournament_sessions,
    delete_generated_sessions,
    save_tournament_reward_config
)
from components.admin.tournament_card.session_grid import (
    render_campus_field_grid,
    build_campus_field_map,
)
from components.admin.tournament_list_dialogs import (
    show_edit_tournament_dialog,
    show_generate_sessions_dialog,
    show_preview_sessions_dialog,
    show_delete_tournament_dialog,
    show_cancel_tournament_dialog,
    show_edit_reward_config_dialog,
    show_enrollment_viewer_modal,
    show_add_game_dialog,
    show_delete_game_dialog,
    show_reset_sessions_dialog,
    show_edit_schedule_dialog,
    show_edit_game_type_dialog
)


def render_tournament_list(token=None):
    """Display all tournaments — OPS and manual, all statuses, with audit visibility."""
    st.subheader("📋 All Tournaments")

    with Loading.spinner("Loading tournaments..."):
        tournaments_data = get_all_tournaments()

    if not tournaments_data:
        st.info("No tournaments found")
        return

    # ── Filter controls ───────────────────────────────────────────────────────
    col_src, col_status, col_info = st.columns([2, 3, 2])

    with col_src:
        source_filter = st.selectbox(
            "Source",
            options=["All", "Manual (TOURN-)", "OPS (OPS-)"],
            key="tlist_source_filter",
            label_visibility="collapsed",
        )

    with col_status:
        status_filter = st.selectbox(
            "Status",
            options=["All statuses", "IN_PROGRESS", "COMPLETED", "DRAFT",
                     "ENROLLMENT_OPEN", "CANCELLED", "⚠️ STUCK (0 sessions)"],
            key="tlist_status_filter",
            label_visibility="collapsed",
        )

    # Apply filters
    filtered = tournaments_data
    if source_filter == "Manual (TOURN-)":
        filtered = [t for t in filtered if t.get("code", "").startswith("TOURN-")]
    elif source_filter == "OPS (OPS-)":
        filtered = [t for t in filtered if t.get("code", "").startswith("OPS-")]

    if status_filter == "⚠️ STUCK (0 sessions)":
        filtered = [
            t for t in filtered
            if t.get("tournament_status") == "IN_PROGRESS" and t.get("session_count", -1) == 0
        ]
    elif status_filter != "All statuses":
        filtered = [t for t in filtered if t.get("tournament_status") == status_filter]

    with col_info:
        st.caption(f"{len(filtered)} / {len(tournaments_data)} tournament")

    if not filtered:
        st.info("No tournaments match the selected filters.")
        return

    # Render each tournament
    for tournament in filtered:
        render_tournament_card(tournament)


def _source_badge(tournament: Dict) -> str:
    code = tournament.get("code", "")
    source = tournament.get("source", "")
    if source == "ops" or code.startswith("OPS-"):
        return "🤖 OPS"
    return "🖊️ Manual"


def _status_badge(tournament: Dict) -> str:
    s = tournament.get("tournament_status") or tournament.get("status", "?")
    sc = tournament.get("session_count", -1)
    icons = {
        "IN_PROGRESS":      "🟢",
        "COMPLETED":        "✅",
        "DRAFT":            "📝",
        "ENROLLMENT_OPEN":  "📬",
        "CANCELLED":        "🚫",
    }
    icon = icons.get(s, "❓")
    if s == "IN_PROGRESS" and sc == 0:
        return f"⚠️ STUCK ({s})"
    return f"{icon} {s}"


def _render_stuck_recovery_panel(tournament: Dict):
    """
    Diagnostic + recovery panel for STUCK (IN_PROGRESS, 0 sessions) tournaments.
    Root cause: session generation failed at launch (e.g. old config bug, infra issue).
    Recovery: rollback to ENROLLMENT_CLOSED, then re-generate sessions.
    """
    tournament_id = tournament.get("id")
    tournament_name = tournament.get("name", "")
    tournament_status = tournament.get("tournament_status", "IN_PROGRESS")
    enrolled = tournament.get("enrolled_count", tournament.get("participant_count", 0))

    st.error("🚨 **STUCK TOURNAMENT** — IN_PROGRESS but 0 sessions generated")

    with st.expander("🔍 Root cause & recovery", expanded=True):
        st.markdown(
            f"**What happened:** Session generation failed silently at tournament launch "
            f"({enrolled} players enrolled). The tournament moved to IN_PROGRESS but no "
            f"sessions were created.\n\n"
            f"**All formats** (League, Knockout, Group+Knockout) support up to **1024 players** "
            f"via multi-campus parallel scheduling. This was a backend config bug — now fixed.\n\n"
            f"**Recovery steps:**\n"
            f"1. Click **Rollback → ENROLLMENT_CLOSED** below — resets generation flags\n"
            f"2. Click **▶ Start** in the action buttons above — patches to IN_PROGRESS\n"
            f"   *(the lifecycle auto-generates all sessions on transition to IN_PROGRESS)*"
        )

    # ── Recovery actions ────────────────────────────────────────────────────────
    st.markdown("**Admin recovery options:**")
    rec_col1, rec_col2, rec_col3 = st.columns(3)

    with rec_col1:
        if st.button(
            "🔄 Rollback → ENROLLMENT_CLOSED",
            key=f"stuck_regen_{tournament_id}",
            type="primary",
            help="Reset to ENROLLMENT_CLOSED so sessions can be re-generated",
        ):
            try:
                with Loading.spinner("Rolling back status..."):
                    api_client.patch(
                        f"/api/v1/tournaments/{tournament_id}/status",
                        data={
                            "new_status": "ENROLLMENT_CLOSED",
                            "reason": "Admin rollback — re-generate sessions after stuck IN_PROGRESS"
                        }
                    )
                Success.message(
                    "Status reset to ENROLLMENT_CLOSED. "
                    "Now click the **▶ Start** button above — the lifecycle auto-generates all sessions on transition to IN_PROGRESS."
                )
                st.rerun()
            except APIError as e:
                Error.message(f"Rollback failed (HTTP {e.status_code}): {e.message}")

    with rec_col2:
        if st.button(
            "❌ Cancel Tournament",
            key=f"stuck_cancel_{tournament_id}",
            help="Mark as CANCELLED — players cannot participate",
        ):
            st.session_state["cancel_tournament_id"] = tournament_id
            st.session_state["cancel_tournament_name"] = tournament_name
            st.session_state["cancel_tournament_status"] = tournament_status
            show_cancel_tournament_dialog()

    with rec_col3:
        if st.button(
            "🗑️ Delete Tournament",
            key=f"stuck_delete_{tournament_id}",
            help="Permanently delete — removes all data",
        ):
            st.session_state["delete_tournament_id"] = tournament_id
            st.session_state["delete_tournament_name"] = tournament_name
            show_delete_tournament_dialog()

    st.divider()


def render_tournament_card(tournament: Dict):
    """Render individual tournament card"""
    tournament_id = tournament.get('id')
    tournament_name = tournament.get('name', 'Unknown')
    tournament_code = tournament.get('code', 'N/A')
    sc = tournament.get("session_count", -1)
    src = _source_badge(tournament)
    sbadge = _status_badge(tournament)

    label = f"{tournament_name}  ·  {src}  ·  {sbadge}"
    if sc >= 0:
        label += f"  ·  {sc} sessions"

    with st.expander(f"🏆 {label}  `{tournament_code}`"):
        if tournament.get("tournament_status") == "IN_PROGRESS" and sc == 0:
            _render_stuck_recovery_panel(tournament)
        # Action buttons
        render_tournament_actions(tournament)
        st.divider()

        # Tournament details
        col1, col2 = st.columns(2)

        with col1:
            render_tournament_status(tournament)

        with col2:
            render_tournament_metadata(tournament)

        st.divider()

        # Sessions section
        render_tournament_sessions_section(tournament)


def render_tournament_actions(tournament: Dict):
    """Render tournament action buttons"""
    tournament_id = tournament.get('id')
    tournament_status = tournament.get('tournament_status', 'N/A')

    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5, btn_col6 = st.columns(6)

    with btn_col1:
        if st.button("✏️", key=f"btn_edit_tournament_{tournament_id}", help="Edit tournament"):
            st.session_state['edit_tournament_id'] = tournament_id
            st.session_state['edit_tournament_data'] = tournament
            show_edit_tournament_dialog()

    with btn_col2:
        enrollment_started = tournament_status in ['ENROLLMENT_OPEN', 'IN_PROGRESS', 'COMPLETED']
        if not enrollment_started:
            if st.button("⚙️", key=f"btn_edit_schedule_{tournament_id}", help="Edit match schedule"):
                st.session_state['edit_schedule_tournament_id'] = tournament_id
                st.session_state['edit_schedule_tournament_name'] = tournament.get('name', 'Unknown')
                show_edit_schedule_dialog()

    # ▶ Start → IN_PROGRESS button (ENROLLMENT_CLOSED only)
    # Patching to IN_PROGRESS triggers auto-session-generation in the lifecycle endpoint.
    with btn_col3:
        if tournament_status == 'ENROLLMENT_CLOSED':
            if st.button("▶ Start", key=f"btn_start_tournament_{tournament_id}",
                         help="Advance to IN_PROGRESS — auto-generates sessions", type="primary"):
                try:
                    with st.spinner("Starting tournament..."):
                        api_client.patch(
                            f"/api/v1/tournaments/{tournament_id}/status",
                            data={"new_status": "IN_PROGRESS", "reason": "Admin started tournament"}
                        )
                    st.success("Tournament started — sessions are being generated.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed to start (HTTP {e.status_code}): {e.message}")

    with btn_col4:
        reward_config = tournament.get('reward_config')
        button_label = "🎁" if reward_config else "➕"
        button_help = "Edit reward configuration" if reward_config else "Add reward configuration"
        if st.button(button_label, key=f"btn_reward_config_{tournament_id}", help=button_help):
            st.session_state['edit_reward_config_tournament_id'] = tournament_id
            st.session_state['edit_reward_config_tournament_name'] = tournament.get('name', 'Unknown')
            st.session_state['edit_reward_config_existing'] = reward_config
            st.rerun()

    with btn_col5:
        can_cancel = tournament_status not in ['COMPLETED', 'CANCELLED']
        if can_cancel:
            if st.button("❌", key=f"btn_cancel_tournament_{tournament_id}", help="Cancel tournament"):
                st.session_state['cancel_tournament_id'] = tournament_id
                st.session_state['cancel_tournament_name'] = tournament.get('name', 'Untitled')
                st.session_state['cancel_tournament_status'] = tournament_status
                show_cancel_tournament_dialog()

    with btn_col6:
        if st.button("🗑️", key=f"btn_delete_tournament_{tournament_id}", help="Delete tournament"):
            st.session_state['delete_tournament_id'] = tournament_id
            st.session_state['delete_tournament_name'] = tournament.get('name', 'Untitled')
            show_delete_tournament_dialog()


def render_tournament_status(tournament: Dict):
    """Render tournament status section"""
    st.write(f"**Status**: {tournament.get('status', 'N/A')}")

    tournament_status = tournament.get('tournament_status', 'N/A')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')

    if tournament_status == 'SEEKING_INSTRUCTOR':
        if assignment_type == 'APPLICATION_BASED':
            st.write(f"**Tournament Status**: 📝 {tournament_status}")
            st.caption("Instructors can apply")
        elif assignment_type == 'OPEN_ASSIGNMENT':
            st.write(f"**Tournament Status**: 🔒 {tournament_status}")
            st.caption("Admin will assign instructor")
    else:
        st.write(f"**Tournament Status**: {tournament_status}")

    st.write(f"**Dates**: {tournament.get('start_date', 'N/A')} to {tournament.get('end_date', 'N/A')}")


def render_tournament_metadata(tournament: Dict):
    """Render tournament metadata section"""
    tournament_id = tournament.get('id')
    tournament_type_id = tournament.get('tournament_type_id')
    location_id = tournament.get('location_id')
    campus_id = tournament.get('campus_id')

    if tournament_type_id:
        st.write(f"**Tournament Type ID**: {tournament_type_id}")

    if location_id:
        location_info = get_location_info(location_id)
        location_name = location_info.get('name', 'Unknown')
        st.write(f"**Location**: {location_name}")

    if campus_id:
        campus_info = get_campus_info(campus_id)
        campus_name = campus_info.get('name', 'Unknown')
        st.write(f"**Campus**: {campus_name}")

    enrollment_count = tournament.get('enrolled_count', tournament.get('participant_count', 0))
    st.write(f"**Enrollments**: {enrollment_count}")


def render_tournament_sessions_section(tournament: Dict):
    """Render tournament sessions section"""
    tournament_id = tournament.get('id')
    tournament_status = tournament.get('tournament_status', 'N/A')

    st.markdown("### 🎮 Tournament Sessions")

    # Session generation buttons
    _dialog_key = f"show_generate_dialog_{tournament_id}"
    session_btn_col1, session_btn_col2, session_btn_col3, session_btn_col4 = st.columns(4)

    with session_btn_col1:
        # Backend requires IN_PROGRESS for manual session generation.
        # For ENROLLMENT_CLOSED: use "▶ Start" in the action buttons (lifecycle auto-generates).
        can_generate = tournament_status == 'IN_PROGRESS'
        help_txt = ("Re-generate sessions for an IN_PROGRESS tournament."
                    if can_generate else
                    "Only available for IN_PROGRESS tournaments. For ENROLLMENT_CLOSED, use ▶ Start above.")
        if st.button("🎲 Generate Sessions", key=f"btn_generate_sessions_{tournament_id}",
                     disabled=not can_generate, help=help_txt):
            st.session_state['generate_sessions_tournament_id'] = tournament_id
            st.session_state[_dialog_key] = True

    with session_btn_col2:
        if st.button("👁️ Preview", key=f"btn_preview_sessions_{tournament_id}"):
            st.session_state['preview_sessions_tournament_id'] = tournament_id
            show_preview_sessions_dialog()

    with session_btn_col3:
        if st.button("🔄 Reset", key=f"btn_reset_sessions_{tournament_id}"):
            st.session_state['reset_sessions_tournament_id'] = tournament_id
            show_reset_sessions_dialog()

    with session_btn_col4:
        if st.button("➕ Add Game", key=f"btn_add_game_{tournament_id}"):
            st.session_state['add_game_tournament_id'] = tournament_id
            show_add_game_dialog()

    # Generate sessions dialog — rendered outside the button block so it persists across reruns.
    # The flag _dialog_key keeps it visible until explicitly closed or generation succeeds.
    if st.session_state.get(_dialog_key):
        if st.button("✖ Close", key=f"btn_close_generate_dialog_{tournament_id}", type="secondary"):
            st.session_state[_dialog_key] = False
            st.rerun()
        show_generate_sessions_dialog()

    # Fetch sessions and campus configs
    sessions = get_tournament_sessions_from_db(tournament_id)

    if not sessions:
        st.info("No sessions generated yet")
        return

    st.write(f"**Total Sessions**: {len(sessions)}")

    # Structured campus → field → round view
    campus_configs = get_campus_schedules_for_tournament(tournament_id)
    render_campus_field_grid(sessions, campus_configs)


def render_session_card(session: Dict, tournament_id: int):
    """Render individual session card"""
    session_id = session.get('id')
    session_title = session.get('title', 'Untitled')

    with st.expander(f"📋 {session_title} (ID: {session_id})"):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Phase**: {session.get('tournament_phase', 'N/A')}")
            st.write(f"**Round**: {session.get('tournament_round', 'N/A')}")
            st.write(f"**Group**: {session.get('group_identifier', 'N/A')}")
            st.write(f"**Match Format**: {session.get('match_format', 'N/A')}")

        with col2:
            st.write(f"**Scoring Type**: {session.get('scoring_type', 'N/A')}")
            st.write(f"**Status**: {session.get('session_status', 'N/A')}")

            participant_ids = session.get('participant_user_ids', [])
            st.write(f"**Participants**: {len(participant_ids)}")

        # Session actions
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button("✏️ Edit", key=f"btn_edit_game_{session_id}"):
                st.session_state['edit_game_id'] = session_id
                st.session_state['edit_game_data'] = session
                show_edit_game_type_dialog()

        with action_col2:
            if st.button("🗑️ Delete", key=f"btn_delete_game_{session_id}"):
                st.session_state['delete_game_id'] = session_id
                show_delete_game_dialog()


def main():
    """Main entry point"""
    st.title("🏆 Tournament List")

    # Authentication
    if not AuthManager.is_authenticated():
        st.warning("Please log in to access tournament management")
        return

    # Render tournament list
    render_tournament_list()


if __name__ == "__main__":
    main()
