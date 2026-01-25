"""
Tournament Application Forms - Application dialogs and cards for instructors
"""

import streamlit as st
import requests
import hashlib
import time
from typing import Dict, List
from datetime import datetime
from config import API_BASE_URL, API_TIMEOUT
from components.instructor.tournament_helpers import apply_to_tournament, accept_assignment
from components.admin.tournament_list import get_tournament_sessions_from_db, get_user_names_from_db

def show_apply_dialog(token: str):
    """Dialog for submitting tournament application"""

    tournament_id = st.session_state.get('apply_tournament_id')
    tournament_name = st.session_state.get('apply_tournament_name', 'Unknown')

    st.markdown(f"**Applying to:** {tournament_name}")
    st.caption(f"Tournament ID: {tournament_id}")
    st.divider()

    # Application message
    application_message = st.text_area(
        "Application Message",
        value="I am interested in leading this tournament as the master instructor.",
        height=150,
        key="application_message_input"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Submit Application", use_container_width=True, type="primary", key="submit_application_btn"):
            if not application_message.strip():
                st.error("⚠️ Please provide an application message")
            else:
                if apply_to_tournament(token, tournament_id, application_message):
                    st.success("✅ Application submitted successfully!")
                    st.info("ℹ️ Admin will review your application. Check the 'Inbox' tab for status updates.")
                    time.sleep(2)
                    # Clear dialog state
                    st.session_state['show_apply_dialog'] = False
                    # 🔥 FIX: Clear cache to force refresh on next render
                    if 'tournament_application_statuses' in st.session_state:
                        del st.session_state['tournament_application_statuses']
                    st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state['show_apply_dialog'] = False
            st.rerun()


def render_my_applications_tab(token: str, user: Dict):
    """
    Render the "Inbox" tab - Universal messaging system for assignments, invitations, and direct messages.

    Phase 1: System Messages only (tournament/semester assignments)
    Future: Direct messaging between users
    """
    st.markdown("### 📬 Inbox")
    st.caption("Your messages, invitations, and assignments")

    # Tab structure: System Messages | Direct Messages (Coming Soon)
    inbox_tab1, inbox_tab2 = st.tabs(["🔔 System Messages", "💬 Direct Messages (Coming Soon)"])

    with inbox_tab1:
        render_system_messages_tab(token, user)

    with inbox_tab2:
        render_direct_messages_placeholder()


def render_system_messages_tab(token: str, user: Dict):
    """
    Render System Messages tab - Tournament/Semester assignments and invitations.
    """
    st.markdown("#### 🔔 System Messages")
    st.caption("Tournament invitations, assignment requests, and system notifications")

    # Fetch instructor's applications (these are system messages)
    with st.spinner("Loading your messages..."):
        applications = get_my_applications(token)

    if not applications:
        st.info("📭 No system messages")
        st.caption("Visit the 'Open Tournaments' tab to browse available opportunities")
        return

    # Separate by status
    pending = [a for a in applications if a.get('status') == 'PENDING']
    accepted = [a for a in applications if a.get('status') == 'ACCEPTED']
    declined = [a for a in applications if a.get('status') in ['DECLINED', 'CANCELLED', 'EXPIRED']]

    # Remove duplicate applications by ID (just in case)
    seen_ids = set()
    accepted_unique = []
    for app in accepted:
        app_id = app.get('id')
        if app_id not in seen_ids:
            seen_ids.add(app_id)
            accepted_unique.append(app)
    accepted = accepted_unique

    # Show stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric("🤝 Pending", len(pending))
    with stats_col2:
        st.metric("⏳ Action Required", len(accepted))
    with stats_col3:
        st.metric("📋 Archived", len(declined))

    st.divider()

    # PENDING applications
    if pending:
        st.markdown("##### 🤝 PENDING")
        st.caption("Waiting for admin review")
        for app in pending:
            render_system_message_card(token, app, "PENDING")
        st.divider()

    # ACCEPTED applications (need instructor to accept assignment)
    if accepted:
        st.markdown("##### ⏳ ACTION REQUIRED")
        st.warning("⚠️ These invitations/applications have been approved. Please accept to confirm your assignment!")
        for app in accepted:
            render_system_message_card(token, app, "ACCEPTED")
        st.divider()

    # DECLINED/CANCELLED/EXPIRED applications
    if declined:
        with st.expander(f"📋 Archived Messages ({len(declined)})", expanded=False):
            for app in declined:
                render_system_message_card(token, app, "DECLINED")


def render_direct_messages_placeholder():
    """
    Placeholder for Direct Messages feature (Phase 2).
    """
    st.markdown("#### 💬 Direct Messages")
    st.info("🚧 **Coming Soon!**")
    st.markdown("""
    Direct messaging will allow you to:
    - 📤 Send messages to other instructors
    - 📧 Communicate with admins
    - 💬 Participate in group conversations
    - 🎯 Discuss tournament/semester-specific topics

    This feature is currently under development.
    """)


def render_system_message_card(token: str, application: Dict, status_category: str):
    """
    Render a universal system message card.

    Supports:
    - Tournament invitations (OPEN_ASSIGNMENT)
    - Tournament applications (APPLICATION_BASED)
    - Future: Semester assignments, session requests, etc.
    """

    app_id = application.get('id')
    tournament_id = application.get('tournament_id')
    tournament_name = application.get('tournament_name', 'Unknown Tournament')
    status = application.get('status')
    tournament_status = application.get('tournament_status')
    created_at = application.get('created_at')
    application_message = application.get('application_message', 'N/A')
    response_message = application.get('response_message')
    responded_at = application.get('responded_at')

    # Get tournament details for more context
    age_group = application.get('age_group', 'UNKNOWN')
    assignment_type = application.get('assignment_type', 'APPLICATION_BASED')
    start_date = application.get('start_date', 'N/A')

    # Format dates
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        created_date = 'N/A'

    try:
        event_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        event_date = 'N/A'

    # Age group icon mapping
    age_icons = {
        'PRE': '👶',
        'YOUTH': '👦',
        'AMATEUR': '🧑',
        'PRO': '👨'
    }
    age_icon = age_icons.get(age_group, '❓')

    # Assignment type badge - Dark mode compatible colors
    if assignment_type == 'OPEN_ASSIGNMENT':
        type_badge = "📩 Direct Invitation from Admin"
        type_bg_color = "rgba(33, 150, 243, 0.15)"  # Blue with transparency
        type_text_color = "#42A5F5"  # Bright blue for dark mode
    else:
        type_badge = "📝 Your Application"
        type_bg_color = "rgba(156, 39, 176, 0.15)"  # Purple with transparency
        type_text_color = "#AB47BC"  # Bright purple for dark mode

    # Status badge styling - Dark mode compatible
    if status == 'PENDING':
        status_badge_color = 'rgba(255, 152, 0, 0.2)'  # Orange with transparency
        status_badge_text_color = '#FFB74D'  # Bright orange
        status_icon = '🤝'
        display_status = 'PENDING'
    elif status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
        status_badge_color = 'rgba(255, 152, 0, 0.2)'
        status_badge_text_color = '#FFA726'  # Bright orange
        status_icon = '⏳'
        display_status = 'ACTION REQUIRED'
    elif status == 'ACCEPTED':
        status_badge_color = 'rgba(76, 175, 80, 0.2)'  # Green with transparency
        status_badge_text_color = '#81C784'  # Bright green
        status_icon = '✅'
        display_status = 'CONFIRMED'
    else:
        status_badge_color = 'rgba(244, 67, 54, 0.2)'  # Red with transparency
        status_badge_text_color = '#E57373'  # Bright red
        status_icon = '❌'
        display_status = status

    # Compact inbox-style card - all info in minimal space like email inbox
    card_html = f"""
    <div style='border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 6px; padding: 10px;
                margin-bottom: 6px; background-color: rgba(128, 128, 128, 0.05);'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <div style='display: flex; gap: 10px; align-items: center; flex: 1;'>
                <span style='font-size: 16px;'>🏆</span>
                <span style='background-color: {type_bg_color}; color: {type_text_color};
                            padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 500;'>
                    {type_badge.replace("📩 ", "").replace("📝 ", "")}
                </span>
                <span style='font-weight: 600; font-size: 13px;'>{tournament_name}</span>
            </div>
            <div style='display: flex; gap: 10px; align-items: center;'>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.8);'>📅 {event_date}</span>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.8);'>{age_icon} {age_group}</span>
                <span style='background-color: {status_badge_color}; color: {status_badge_text_color};
                            padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 10px;'>
                    {status_icon} {display_status}
                </span>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.6);'>#{app_id}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Expandable message section (collapsed by default to save space)
    # Handle None application_message for direct assignments
    if application_message and len(application_message) > 60:
        message_preview = application_message[:60] + "..."
    else:
        message_preview = application_message or "Direct assignment - no application message"

    with st.expander(f"💬 {message_preview}", expanded=False):
        if assignment_type == 'OPEN_ASSIGNMENT' and response_message:
            st.markdown(f"**Admin invitation:**")
            st.markdown(f"_{response_message}_")
        elif application_message:
            st.markdown(f"**Your application:**")
            st.markdown(f"_{application_message}_")
        else:
            st.markdown(f"**Direct assignment by admin - no application message**")

        # Admin response (if any)
        if response_message and assignment_type == 'APPLICATION_BASED':
            st.markdown(f"**📧 Admin response:**")
            st.markdown(f"_{response_message}_")

    # Action buttons
    button_col1, button_col2, button_col3 = st.columns([1, 1, 2])

    with button_col1:
        # Accept button for assignments that need instructor action
        if status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
            # Use stable key based on app_id AND tournament_id to ensure uniqueness
            accept_key = f"accept_assignment_btn_{app_id}_{tournament_id}"
            if st.button(f"✅ Accept", key=accept_key, use_container_width=True, type="primary"):
                if accept_assignment(token, tournament_id):
                    st.success("✅ Assignment accepted successfully!")
                    st.info("🎉 You are now the master instructor for this tournament!")
                    time.sleep(2)
                    st.rerun()

    with button_col2:
        # Decline button (future implementation)
        if status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
            # Use stable key based on app_id AND tournament_id to ensure uniqueness
            decline_key = f"decline_btn_{app_id}_{tournament_id}"
            if st.button(f"❌ Decline", key=decline_key, use_container_width=True):
                st.warning("⚠️ Decline functionality coming soon!")

    st.divider()


def render_application_card(token: str, application: Dict, status_category: str):
    """
    DEPRECATED: Use render_system_message_card instead.
    This function is kept for backward compatibility only.
    """
    # Redirect to new universal card renderer
    render_system_message_card(token, application, status_category)



def render_my_tournaments_tab(token: str, user: Dict):
    """
    Render the "My Tournaments" tab showing tournaments where instructor is assigned.
    """
    st.markdown("### 🏆 My Tournaments")
    st.caption("Tournaments where you are the assigned instructor")

    # Fetch all semesters
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters",
            headers={"Authorization": f"Bearer {token}"},
            params={"size": 100},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            all_semesters = response.json().get('semesters', [])

            # Filter for tournaments where current user is master instructor
            my_tournaments = [
                t for t in all_semesters
                if t.get('code', '').startswith('TOURN-') and t.get('master_instructor_id') == user.get('id')
            ]

            if not my_tournaments:
                st.info("📭 You are not currently assigned to any tournaments")
                st.caption("Apply to tournaments in the 'Open Tournaments' tab")
                return

            # Separate by status
            upcoming = [t for t in my_tournaments if t.get('status') in ['INSTRUCTOR_ASSIGNED', 'READY_FOR_ENROLLMENT', 'ENROLLING']]
            ongoing = [t for t in my_tournaments if t.get('status') == 'ONGOING']
            completed = [t for t in my_tournaments if t.get('status') == 'COMPLETED']

            # Stats
            stats_col1, stats_col2, stats_col3 = st.columns(3)

            with stats_col1:
                st.metric("🔜 Upcoming", len(upcoming))
            with stats_col2:
                st.metric("🔴 Ongoing", len(ongoing))
            with stats_col3:
                st.metric("✅ Completed", len(completed))

            st.divider()

            # Display tournaments
            all_tournaments_display = upcoming + ongoing + completed

            for tournament in all_tournaments_display:
                render_my_tournament_card(token, tournament)

        else:
            st.error("Failed to load tournaments")
    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_my_tournament_card(token: str, tournament: Dict):
    """Render tournament card for instructor's assigned tournaments"""

    name = tournament.get('name', 'Unnamed Tournament')
    start_date = tournament.get('start_date', 'TBD')
    status = tournament.get('status', 'N/A')
    tournament_id = tournament.get('id')
    age_group = tournament.get('age_group', 'UNKNOWN')

    # Age group icon
    age_icons = {'PRE': '👶', 'YOUTH': '👦', 'AMATEUR': '🧑', 'PRO': '👨'}
    age_icon = age_icons.get(age_group, '❓')

    # Status styling
    if status in ['READY_FOR_ENROLLMENT', 'ENROLLING']:
        status_color = '#E3F2FD'
        status_text = '#1565C0'
        status_icon = '🔜'
    elif status == 'ONGOING':
        status_color = '#D4EDDA'
        status_text = '#155724'
        status_icon = '🔴'
    else:
        status_color = '#E8E8E8'
        status_text = '#616161'
        status_icon = '✅'

    with st.expander(f"🏆 {name}", expanded=(status == 'ONGOING')):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"📅 **Date:** {start_date}")
            st.caption(f"🎯 **Age Group:** {age_icon} {age_group}")
            st.caption(f"📊 **Status:** {status}")

            # Get enrollment count
            try:
                enroll_response = requests.get(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/enrollments",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT
                )
                if enroll_response.status_code == 200:
                    enrollments = enroll_response.json().get('enrollments', [])
                    st.caption(f"👥 **Enrolled Players:** {len(enrollments)}")
            except:
                pass

        with col2:
            st.markdown(
                f"<div style='text-align: center; padding: 10px; background-color: {status_color}; "
                f"border-radius: 5px; font-weight: bold; color: {status_text};'>"
                f"{status_icon} {status}</div>",
                unsafe_allow_html=True
            )

        st.divider()

        # 🔍 DEBUG PANEL
        with st.expander("🔍 DEBUG: Tournament Status Check", expanded=True):
            st.write(f"**tournament_status**: `{tournament.get('tournament_status')}`")
            st.write(f"**status (old)**: `{tournament.get('status')}`")
            st.write(f"**Check passed**: {tournament.get('tournament_status') in ['COMPLETED', 'REWARDS_DISTRIBUTED']}")

        # ✅ NEW: Show detailed info for COMPLETED tournaments
        if tournament.get('tournament_status') in ['COMPLETED', 'REWARDS_DISTRIBUTED']:
            # Get leaderboard with final standings
            try:
                leaderboard_response = requests.get(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/leaderboard",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT
                )

                st.write(f"**🔍 DEBUG: Leaderboard API Response Status**: {leaderboard_response.status_code}")

                if leaderboard_response.status_code == 200:
                    leaderboard_data = leaderboard_response.json()
                    final_standings = leaderboard_data.get('final_standings')

                    st.write(f"**🔍 DEBUG: final_standings**: {final_standings is not None}")
                    st.write(f"**🔍 DEBUG: leaderboard keys**: {list(leaderboard_data.keys())}")

                    # ========================================
                    # SHOW GROUP STAGE & KNOCKOUT BRACKET
                    # ========================================
                    st.markdown("### 🏆 Tournament Draw & Results")

                    try:
                        # Fetch sessions from database
                        sessions_data = get_tournament_sessions_from_db(tournament_id)

                        if sessions_data:
                            # Separate by phase
                            group_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Group Stage']
                            knockout_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Knockout Stage']

                            # GROUP STAGE
                            if group_sessions:
                                st.markdown("#### ⚽ Group Stage Results")

                                # Organize by group
                                groups = {}
                                for session in group_sessions:
                                    group = session.get('group_identifier', 'Unknown')
                                    if group not in groups:
                                        groups[group] = []
                                    groups[group].append(session)

                                # Fetch all participant names
                                all_participant_ids = set()
                                for group_matches in groups.values():
                                    for match in group_matches:
                                        participant_ids = match.get('participant_user_ids', [])
                                        all_participant_ids.update(participant_ids)

                                user_names = get_user_names_from_db(list(all_participant_ids))

                                # Display groups side-by-side
                                group_cols = st.columns(len(groups))
                                for idx, (group_name, matches) in enumerate(sorted(groups.items())):
                                    with group_cols[idx]:
                                        st.markdown(f"**📍 {group_name}**")

                                        # Show participants
                                        group_participants = set()
                                        for match in matches:
                                            group_participants.update(match.get('participant_user_ids', []))

                                        if group_participants:
                                            st.caption("👥 Participants:")
                                            for pid in sorted(group_participants):
                                                st.caption(f"    • {user_names.get(pid, f'User {pid}')}")

                            # KNOCKOUT BRACKET
                            if knockout_sessions:
                                st.divider()
                                st.markdown("#### 🏆 Knockout Bracket Results")

                                # Organize by round
                                rounds = {}
                                for session in knockout_sessions:
                                    round_name = session.get('session_label', 'Unknown Round')
                                    if round_name not in rounds:
                                        rounds[round_name] = []
                                    rounds[round_name].append(session)

                                # Display rounds
                                for round_name in sorted(rounds.keys(), key=lambda x: len(rounds[x]), reverse=True):
                                    st.markdown(f"**🎯 {round_name}**")

                                    for match in rounds[round_name]:
                                        participants = match.get('participant_user_ids', [])
                                        if len(participants) >= 2:
                                            p1_name = user_names.get(participants[0], f'User {participants[0]}')
                                            p2_name = user_names.get(participants[1], f'User {participants[1]}')
                                            st.caption(f"⚔️ {p1_name} vs {p2_name}")

                    except Exception as e:
                        st.error(f"❌ Error loading tournament draw: {str(e)}")

                    st.divider()

                    # ========================================
                    # FINAL STANDINGS (INDIVIDUAL_RANKING vs HEAD_TO_HEAD)
                    # ========================================
                    tournament_format = leaderboard_data.get('tournament_format', 'HEAD_TO_HEAD')
                    performance_rankings = leaderboard_data.get('performance_rankings')
                    wins_rankings = leaderboard_data.get('wins_rankings')

                    if tournament_format == 'INDIVIDUAL_RANKING' and performance_rankings:
                        # ========================================
                        # INDIVIDUAL_RANKING: Show dual rankings
                        # ========================================
                        st.markdown("### 🏆 Final Rankings")

                        col1, col2 = st.columns(2)

                        # 🏃 Best Performance
                        with col1:
                            st.markdown("#### 🏃 Best Performance")
                            st.caption("Best individual value across all rounds")

                            for rank_entry in performance_rankings[:10]:
                                rank = rank_entry['rank']
                                user_id = rank_entry['user_id']
                                final_value = rank_entry['final_value']
                                unit = rank_entry.get('measurement_unit', '')

                                # Get user name from leaderboard
                                leaderboard = leaderboard_data.get('leaderboard', [])
                                user_name = next((p['name'] for p in leaderboard if p['user_id'] == user_id), f"User {user_id}")

                                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
                                st.markdown(f"**{medal} {user_name}**: {final_value} {unit}")

                        # 🏆 Most Wins
                        with col2:
                            st.markdown("#### 🏆 Most Wins")
                            st.caption("Most 1st place finishes")

                            for rank_entry in wins_rankings[:10]:
                                rank = rank_entry['rank']
                                user_id = rank_entry['user_id']
                                wins = rank_entry['wins']
                                total = rank_entry.get('total_rounds', 0)

                                # Get user name from leaderboard
                                leaderboard = leaderboard_data.get('leaderboard', [])
                                user_name = next((p['name'] for p in leaderboard if p['user_id'] == user_id), f"User {user_id}")

                                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
                                st.markdown(f"**{medal} {user_name}**: {wins}/{total} wins")

                    elif final_standings:
                        st.markdown("### 🏆 Final Standings")

                        # Podium (Top 3)
                        col1, col2, col3 = st.columns(3)

                        champion = next((p for p in final_standings if p['rank'] == 1), None)
                        runner_up = next((p for p in final_standings if p['rank'] == 2), None)
                        third_place = next((p for p in final_standings if p['rank'] == 3), None)

                        with col2:  # Center column for champion
                            if champion:
                                st.markdown(
                                    f"<div style='text-align: center; padding: 15px; background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); "
                                    f"border-radius: 10px; margin: 10px 0;'>"
                                    f"<div style='font-size: 3em;'>🥇</div>"
                                    f"<div style='font-weight: bold; font-size: 1.2em; margin-top: 5px;'>{champion['player_name']}</div>"
                                    f"<div style='font-size: 0.9em; opacity: 0.9;'>Champion</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                        with col1:  # Left column for runner-up
                            if runner_up:
                                st.markdown(
                                    f"<div style='text-align: center; padding: 15px; background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%); "
                                    f"border-radius: 10px; margin: 10px 0; margin-top: 40px;'>"
                                    f"<div style='font-size: 2.5em;'>🥈</div>"
                                    f"<div style='font-weight: bold; font-size: 1.1em; margin-top: 5px;'>{runner_up['player_name']}</div>"
                                    f"<div style='font-size: 0.85em; opacity: 0.9;'>Runner-up</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                        with col3:  # Right column for third place
                            if third_place:
                                st.markdown(
                                    f"<div style='text-align: center; padding: 15px; background: linear-gradient(135deg, #CD7F32 0%, #B87333 100%); "
                                    f"border-radius: 10px; margin: 10px 0; margin-top: 40px;'>"
                                    f"<div style='font-size: 2.5em;'>🥉</div>"
                                    f"<div style='font-weight: bold; font-size: 1.1em; margin-top: 5px;'>{third_place['player_name']}</div>"
                                    f"<div style='font-size: 0.85em; opacity: 0.9;'>Third Place</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )

                        # Complete rankings table
                        st.markdown("#### 📊 Complete Rankings")

                        rankings_data = []
                        for player in final_standings:
                            rank_icon = {1: "🥇", 2: "🥈", 3: "🥉"}.get(player['rank'], f"{player['rank']}.")
                            rankings_data.append({
                                "Rank": rank_icon,
                                "Player": player['player_name'],
                                "Points": player.get('points', 0)
                            })

                        if rankings_data:
                            st.dataframe(rankings_data, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"❌ Failed to load final standings: {str(e)}")

            # Show distributed rewards if available
            if tournament.get('tournament_status') == 'REWARDS_DISTRIBUTED':
                st.markdown("---")
                st.markdown("### 💰 Distributed Rewards")

                try:
                    rewards_response = requests.get(
                        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distributed-rewards",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=API_TIMEOUT
                    )

                    if rewards_response.status_code == 200:
                        rewards_data = rewards_response.json()
                        player_rewards = rewards_data.get('player_rewards', [])

                        if player_rewards:
                            # Summary metrics
                            total_credits = sum(r.get('credits_awarded', 0) for r in player_rewards)
                            total_xp = sum(r.get('xp_awarded', 0) for r in player_rewards)

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("💳 Total Credits", f"{total_credits:,}")
                            with col2:
                                st.metric("⭐ Total XP", f"{total_xp:,}")
                            with col3:
                                st.metric("👥 Players Rewarded", len(player_rewards))

                            # Top 3 rewards detail
                            st.markdown("#### 🏆 Top 3 Rewards")

                            for idx, reward in enumerate(player_rewards[:3], 1):
                                medal = {1: "🥇", 2: "🥈", 3: "🥉"}[idx]
                                with st.container():
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    with col1:
                                        st.markdown(f"**{medal} {reward['player_name']}**")
                                    with col2:
                                        st.markdown(f"💳 {reward.get('credits_awarded', 0):,} credits")
                                    with col3:
                                        st.markdown(f"⭐ {reward.get('xp_awarded', 0):,} XP")
                        else:
                            st.info("ℹ️ No reward data available")
                    else:
                        st.warning("⚠️ Rewards not yet calculated")

                except Exception as e:
                    st.error(f"❌ Failed to load rewards: {str(e)}")

