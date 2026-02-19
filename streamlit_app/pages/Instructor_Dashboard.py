"""
Instructor Dashboard
REBUILT from unified_workflow_dashboard.py (WORKING!)
EXACT API patterns + EXACT UI/UX patterns
"""

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, SPECIALIZATIONS
# api_helpers: get_sessions/get_semesters/get_users → moved to data_loader.py / unused
from session_manager import restore_session_from_url
from datetime import datetime, timedelta
from collections import defaultdict

# Page configuration
from api_helpers_notifications import get_unread_notification_count
from api_helpers_instructors import get_my_master_offers, get_user_licenses
from components.instructor.tabs.tab7_profile import render_profile_tab
from components.instructor.data_loader import load_dashboard_data
from components.instructor.tabs.tab6_inbox import render_inbox_tab
from components.instructor.tabs.tab4_students import render_students_tab
from components.instructor.tabs.tab1_today import render_today_tab
from components.instructor.tournament_applications import (
    render_open_tournaments_tab,
    render_my_applications_tab,
    render_my_tournaments_tab
)
from components.sessions.session_checkin import render_session_checkin
from components.tournaments.instructor.tournament_checkin import render_tournament_checkin
import requests
from config import API_BASE_URL, API_TIMEOUT
import time
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Instructor Dashboard",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# CRITICAL: Restore session from URL params BEFORE checking authentication
if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()

# Check authentication
if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("❌ Not authenticated. Please login first.")
    st.stop()

# Check instructor role
user = st.session_state[SESSION_USER_KEY]
if user.get('role') != 'instructor':
    st.error("❌ Access denied. Instructor role required.")
    st.stop()

# Get token
token = st.session_state[SESSION_TOKEN_KEY]

# ✅ CRITICAL FIX: Validate token expiration BEFORE using it
from session_manager import validate_session
if not validate_session():
    st.error("❌ Your session has expired. Please login again.")
    st.stop()

# DEBUG: Print token info for troubleshooting
print(f"\n🔍 INSTRUCTOR DASHBOARD TOKEN DEBUG:")
print(f"   Token in session_state: {SESSION_TOKEN_KEY in st.session_state}")
print(f"   Token type: {type(token)}")
print(f"   Token length: {len(token) if token else 0}")
print(f"   Token preview: {token[:50] if token else 'EMPTY'}...")

# Test token validity with a simple API call
import requests
from config import API_BASE_URL, API_TIMEOUT
try:
    test_response = requests.get(
        f"{API_BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=API_TIMEOUT
    )
    print(f"   Token validation test: {test_response.status_code}")
    if test_response.status_code != 200:
        print(f"   ERROR: Token is invalid! Response: {test_response.text[:200]}")
        st.error(f"❌ Token validation failed: {test_response.status_code}")
        st.error("Please logout and login again to refresh your session.")
        st.stop()
    else:
        print(f"   ✅ Token is valid!")
except Exception as e:
    print(f"   ERROR: Token validation failed with exception: {e}")
    st.error(f"❌ Cannot connect to API: {str(e)}")
    st.stop()

# Header with Notification Badge
col_title, col_badge = st.columns([4, 1])

with col_title:
    st.title("👨‍🏫 Instructor Dashboard")
    st.caption("LFA Education Center - Instructor Interface")

with col_badge:
    # Fetch unread notification count
    unread_count = get_unread_notification_count(token)

    if unread_count > 0:
        st.markdown(
            f"<div style='text-align: center; padding: 15px; margin-top: 10px; background-color: #FF4B4B; "
            f"border-radius: 10px; font-weight: bold; color: white; font-size: 18px;'>"
            f"🔔 {unread_count} New Notification{'s' if unread_count > 1 else ''}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='text-align: center; padding: 15px; margin-top: 10px; background-color: #E8F5E9; "
            f"border-radius: 10px; font-weight: bold; color: #2E7D32; font-size: 18px;'>"
            f"✅ No New Notifications</div>",
            unsafe_allow_html=True
        )

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Instructor')}!")
    st.caption(f"Role: **Instructor**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    if st.button("🏆 Tournament Manager", use_container_width=True, type="primary"):
        st.switch_page("pages/Tournament_Manager.py")

    st.markdown("---")

    # Logout and Refresh buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True, help="Reload dashboard data without logging out"):
            st.rerun()
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("🏠_Home.py")

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_age_group(specialization_type: str) -> str:
    """Extract age group from LFA_PLAYER_X format"""
    if not specialization_type or 'LFA_PLAYER_' not in specialization_type:
        return 'UNKNOWN'
    parts = specialization_type.split('_')
    return parts[-1] if len(parts) > 2 else 'UNKNOWN'

def get_age_group_icon(age_group: str) -> str:
    """Get emoji icon for age group"""
    icons = {
        'PRE': '👶',
        'YOUTH': '👦',
        'AMATEUR': '🧑',
        'PRO': '👨'
    }
    return icons.get(age_group, '❓')

# ========================================
# DATA BOUNDARY (Phase 3 Step 3.4)
# ========================================
# load_dashboard_data() encapsulates all session/semester fetching and
# pre-computation.  Inline data-prep block removed — see data_loader.py.

with st.spinner("Loading your data..."):
    data = load_dashboard_data(token)

if data.load_error:
    st.error(f"❌ {data.load_error}")
    st.stop()

# Local name bindings for remaining inline tab bodies (tabs 2, 3).
# Remove each binding as the corresponding tab is extracted in steps 3.6–3.8.
all_semesters           = data.all_semesters
seasons_by_semester     = data.seasons_by_semester
tournaments_by_semester = data.tournaments_by_semester
today                   = datetime.now().date()      # still needed by inline tab2 body
next_week               = today + timedelta(days=7)  # passed to render_today_tab

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📆 Today & Upcoming",
    "💼 My Jobs",
    "🏆 Tournament Applications",
    "👥 My Students",
    "✅ Check-in & Groups",
    "📬 Inbox",
    "👤 My Profile"
])

# ========================================
# TAB 1: TODAY & UPCOMING (Phase 3 Step 3.5 — extracted)
# ========================================
with tab1:
    render_today_tab(data, token, today, next_week)

# ========================================
# TAB 2: MY JOBS (CV-Style Chronological List)
# ========================================
with tab2:
    st.markdown("### 💼 My Jobs")
    st.caption("Your teaching assignments - pending offers, upcoming, active, and completed")

    # Get current user ID for PENDING detection
    current_instructor_id = user.get('id')

    # Collect all jobs (seasons + tournaments) with metadata
    all_jobs = []

    # Add ALL master-led semesters (both with and without sessions)
    # Track which semester IDs we've processed
    processed_semester_ids = set()

    # First, add seasons that have sessions
    for semester_id, sessions in seasons_by_semester.items():
        if sessions:
            semester = sessions[0].get('semester', {})
            spec_type = semester.get('specialization_type', '')
            age_group = get_age_group(spec_type)

            # ✅ NEW: Check if ACCEPTED or PENDING
            master_instructor_id = semester.get('master_instructor_id')
            is_accepted = (master_instructor_id == current_instructor_id)

            # Determine status: pending, upcoming, active, or completed
            if not is_accepted:
                status = 'pending'  # Not accepted yet → PENDING
            else:
                try:
                    start_date = datetime.strptime(semester.get('start_date', ''), '%Y-%m-%d').date()
                    end_date = datetime.strptime(semester.get('end_date', ''), '%Y-%m-%d').date()

                    if start_date > today:
                        status = 'upcoming'
                    elif start_date <= today <= end_date:
                        status = 'active'
                    else:
                        status = 'completed'
                except:
                    status = 'active'  # Default to active if can't parse

            all_jobs.append({
                'type': 'season',
                'semester_id': semester_id,
                'semester': semester,
                'sessions': sessions,
                'age_group': age_group,
                'status': status,
                'start_date': semester.get('start_date', ''),
                'end_date': semester.get('end_date', ''),
                'sort_key': semester.get('start_date', '')  # For sorting
            })
            processed_semester_ids.add(semester_id)

    # Then, add semesters WITHOUT sessions (future commitments)
    for semester in all_semesters:
        semester_id = semester.get('id')
        code = semester.get('code', '')

        # Skip if already processed (has sessions) or is a tournament
        if semester_id in processed_semester_ids or code.startswith('TOURN-'):
            continue

        spec_type = semester.get('specialization_type', '')
        age_group = get_age_group(spec_type)

        # ✅ NEW: Check if ACCEPTED or PENDING
        master_instructor_id = semester.get('master_instructor_id')
        is_accepted = (master_instructor_id == current_instructor_id)

        # Determine status
        if not is_accepted:
            status = 'pending'  # Not accepted yet → PENDING
        else:
            try:
                start_date = datetime.strptime(semester.get('start_date', ''), '%Y-%m-%d').date()
                end_date = datetime.strptime(semester.get('end_date', ''), '%Y-%m-%d').date()

                if start_date > today:
                    status = 'upcoming'
                elif start_date <= today <= end_date:
                    status = 'active'
                else:
                    status = 'completed'
            except:
                status = 'active'

        all_jobs.append({
            'type': 'season',
            'semester_id': semester_id,
            'semester': semester,
            'sessions': [],  # No sessions yet
            'age_group': age_group,
            'status': status,
            'start_date': semester.get('start_date', ''),
            'end_date': semester.get('end_date', ''),
            'sort_key': semester.get('start_date', '')
        })
        processed_semester_ids.add(semester_id)

    # Add tournaments
    for semester_id, sessions in tournaments_by_semester.items():
        if sessions:
            semester = sessions[0].get('semester', {})
            spec_type = semester.get('specialization_type', '')
            age_group = get_age_group(spec_type)

            # ✅ NEW: Check if ACCEPTED or PENDING
            master_instructor_id = semester.get('master_instructor_id')
            is_accepted = (master_instructor_id == current_instructor_id)

            # Determine status: pending, upcoming, active (today or IN_PROGRESS), or completed
            if not is_accepted:
                status = 'pending'  # Not accepted yet → PENDING
            else:
                # Check tournament_status first - if IN_PROGRESS, always mark as active
                tournament_status = semester.get('tournament_status', '')
                if tournament_status == 'IN_PROGRESS':
                    status = 'active'
                elif tournament_status in ['COMPLETED', 'REWARDS_DISTRIBUTED']:
                    status = 'completed'
                else:
                    # Fall back to date-based logic
                    try:
                        tourn_date = datetime.strptime(semester.get('start_date', ''), '%Y-%m-%d').date()

                        if tourn_date > today:
                            status = 'upcoming'
                        elif tourn_date == today:
                            status = 'active'
                        else:
                            status = 'completed'
                    except:
                        status = 'active'

            all_jobs.append({
                'type': 'tournament',
                'semester_id': semester_id,
                'semester': semester,
                'sessions': sessions,
                'age_group': age_group,
                'status': status,
                'tournament_date': semester.get('start_date', ''),
                'sort_key': semester.get('start_date', '')
            })

    # Sort by start date (newest first)
    all_jobs.sort(key=lambda x: x['sort_key'], reverse=True)

    # Separate into 4 categories (NEW: added PENDING)
    pending_jobs = [j for j in all_jobs if j['status'] == 'pending']
    upcoming_jobs = [j for j in all_jobs if j['status'] == 'upcoming']
    active_jobs = [j for j in all_jobs if j['status'] == 'active']
    completed_jobs = [j for j in all_jobs if j['status'] == 'completed']

    # Quick Stats (NEW: added PENDING)
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

    with stats_col1:
        st.metric("⏳ PENDING Offers", len(pending_jobs))
    with stats_col2:
        st.metric("🔜 Upcoming Jobs", len(upcoming_jobs))
    with stats_col3:
        st.metric("🔴 Active Jobs", len(active_jobs))
    with stats_col4:
        st.metric("✅ Completed Jobs", len(completed_jobs))

    st.divider()

    # ✅ NEW SECTION: PENDING OFFERS (Not accepted yet)
    if pending_jobs:
        st.markdown("### ⏳ PENDING OFFERS (Action Required)")
        st.warning(f"⚠️ You have **{len(pending_jobs)}** pending job offers. Review them in the **📬 Inbox** tab!")

        for job in pending_jobs:
            age_icon = get_age_group_icon(job['age_group'])

            if job['type'] == 'season':
                # PENDING SEASON Card
                with st.container():
                    st.markdown(f"#### 📅 SEASON: {job['semester'].get('name', 'Unnamed Season')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Duration:** {job['start_date']} to {job['end_date']}")

                        # Sessions info
                        if len(job['sessions']) > 0:
                            st.caption(f"📊 **Sessions:** {len(job['sessions'])} total")
                        else:
                            st.caption("📝 Sessions will be created after acceptance")

                    with col2:
                        # Status indicator - PENDING
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #FFF3E0; "
                            "border-radius: 5px; font-weight: bold; color: #E65100;'>⏳ PENDING</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

            else:  # tournament
                # PENDING TOURNAMENT Card
                with st.container():
                    st.markdown(f"#### 🏆 TOURNAMENT: {job['semester'].get('name', 'Unnamed Tournament')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Date:** {job['tournament_date']}")

                        # Session summary
                        if len(job['sessions']) > 0:
                            session_times = ", ".join([
                                datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).strftime('%H:%M')
                                for s in job['sessions'][:3]
                            ])
                            st.caption(f"📊 **Sessions:** {len(job['sessions'])} ({session_times}" +
                                     (f", ..." if len(job['sessions']) > 3 else ")"))

                            total_capacity = sum(s.get('capacity', 0) for s in job['sessions'])
                            st.caption(f"👥 **Capacity:** {total_capacity} students")

                    with col2:
                        # Status indicator - PENDING
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #FFF3E0; "
                            "border-radius: 5px; font-weight: bold; color: #E65100;'>⏳ PENDING</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

        st.divider()

    # Display UPCOMING JOBS (Future commitments)
    if upcoming_jobs:
        st.markdown("### 🔜 UPCOMING JOBS (Future Commitments)")

        for job in upcoming_jobs:
            age_icon = get_age_group_icon(job['age_group'])

            if job['type'] == 'season':
                # SEASON Card
                with st.container():
                    st.markdown(f"#### 📅 SEASON: {job['semester'].get('name', 'Unnamed Season')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Duration:** {job['start_date']} to {job['end_date']}")

                        # Calculate days until start
                        try:
                            start_date = datetime.strptime(job['start_date'], '%Y-%m-%d').date()
                            days_until = (start_date - today).days
                            st.info(f"🔜 **Starts in {days_until} day(s)**")
                        except:
                            pass

                        # Sessions info
                        if len(job['sessions']) > 0:
                            st.caption(f"📊 **Sessions:** {len(job['sessions'])} total")
                            st.caption(f"👥 **Students:** TBD (Enrollment data)")
                        else:
                            st.warning("⏳ **Sessions:** Not scheduled yet")
                            st.caption("📝 Sessions will be created closer to the start date")

                    with col2:
                        # Status indicator
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #E3F2FD; "
                            "border-radius: 5px; font-weight: bold; color: #1565C0;'>🔜 UPCOMING</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

            else:  # tournament
                # TOURNAMENT Card
                with st.container():
                    st.markdown(f"#### 🏆 TOURNAMENT: {job['semester'].get('name', 'Unnamed Tournament')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Date:** {job['tournament_date']}")

                        # Calculate days until
                        try:
                            tourn_date = datetime.strptime(job['tournament_date'], '%Y-%m-%d').date()
                            days_until = (tourn_date - today).days
                            st.info(f"🔜 **Upcoming in {days_until} day(s)**")
                        except:
                            pass

                        # Session summary
                        session_times = ", ".join([
                            datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).strftime('%H:%M')
                            for s in job['sessions'][:3]
                        ])
                        st.caption(f"📊 **Sessions:** {len(job['sessions'])} ({session_times}" +
                                 (f", ..." if len(job['sessions']) > 3 else ")"))

                        total_capacity = sum(s.get('capacity', 0) for s in job['sessions'])
                        st.caption(f"👥 **Capacity:** {total_capacity} students")

                    with col2:
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #E3F2FD; "
                            "border-radius: 5px; font-weight: bold; color: #1565C0;'>🔜 UPCOMING</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

        st.divider()

    # Display ACTIVE JOBS
    if active_jobs:
        st.markdown("### 🔴 ACTIVE JOBS")

        for job in active_jobs:
            age_icon = get_age_group_icon(job['age_group'])

            if job['type'] == 'season':
                # SEASON Card
                with st.container():
                    st.markdown(f"#### 📅 SEASON: {job['semester'].get('name', 'Unnamed Season')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # Education Center (TODO: fetch from location/campus)
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Duration:** {job['start_date']} to {job['end_date']}")

                        # Sessions info
                        if len(job['sessions']) > 0:
                            # Find next session
                            future_sessions = [s for s in job['sessions'] if s.get('date_start') and
                                             datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date() >= today]
                            if future_sessions:
                                next_session = min(future_sessions, key=lambda x: x['date_start'])
                                next_date = datetime.fromisoformat(next_session['date_start'].replace('Z', '+00:00'))
                                days_until = (next_date.date() - today).days

                                if days_until == 0:
                                    st.caption(f"📊 **Next session:** Today at {next_date.strftime('%H:%M')} 🚨")
                                else:
                                    st.caption(f"📊 **Next session:** {next_date.strftime('%b %d, %H:%M')} ({days_until} days)")

                            st.caption(f"📊 **Sessions:** {len(job['sessions'])} total")
                            st.caption(f"👥 **Students:** TBD (Enrollment data)")
                        else:
                            st.warning("⏳ **Sessions:** Not scheduled yet")
                            st.caption("📝 Sessions will be created closer to the start date")

                    with col2:
                        # Status indicator
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #D4EDDA; "
                            "border-radius: 5px; font-weight: bold; color: #155724;'>🔴 ACTIVE</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

            else:  # tournament
                # TOURNAMENT Card
                with st.container():
                    st.markdown(f"#### 🏆 TOURNAMENT: {job['semester'].get('name', 'Unnamed Tournament')}")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.caption("📍 **Education Center:** TBD (Location data)")
                        st.caption(f"👤 **Position:** Master Instructor")
                        st.caption(f"🎯 **Age Group:** {age_icon} {job['age_group']}")
                        st.caption(f"📆 **Date:** {job['tournament_date']}")
                        st.caption(f"🔢 **Status:** {job['semester'].get('tournament_status', 'N/A')}")

                        # Calculate days until
                        try:
                            tourn_date = datetime.strptime(job['tournament_date'], '%Y-%m-%d').date()
                            days_until = (tourn_date - today).days

                            if days_until == 0:
                                st.error("🚨 **TODAY!**")
                            elif days_until > 0:
                                st.info(f"🔜 **Upcoming in {days_until} day(s)**")
                        except:
                            pass

                        # Session summary
                        session_times = ", ".join([
                            datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).strftime('%H:%M')
                            for s in job['sessions'][:3]
                        ])
                        st.caption(f"📊 **Sessions:** {len(job['sessions'])} ({session_times}" +
                                 (f", ..." if len(job['sessions']) > 3 else ")"))

                        total_capacity = sum(s.get('capacity', 0) for s in job['sessions'])
                        st.caption(f"👥 **Capacity:** {total_capacity} students")

                    with col2:
                        st.markdown(
                            "<div style='text-align: center; padding: 10px; background-color: #D4EDDA; "
                            "border-radius: 5px; font-weight: bold; color: #155724;'>🔴 ACTIVE</div>",
                            unsafe_allow_html=True
                        )

                    # ACTION BUTTONS for tournament management
                    tournament_id = job['semester'].get('id')
                    tournament_status = job['semester'].get('tournament_status', 'N/A')

                    st.divider()
                    st.markdown("**🎮 Tournament Actions:**")

                    action_col1, action_col2 = st.columns(2)

                    with action_col1:
                        # Record Results button - available for IN_PROGRESS tournaments
                        if tournament_status == "IN_PROGRESS":
                            if st.button(
                                "📝 Record Results",
                                key=f"record_results_{tournament_id}",
                                use_container_width=True,
                                help="Submit final rankings and results"
                            ):
                                st.session_state['record_results_tournament_id'] = tournament_id
                                st.session_state['record_results_tournament'] = job['semester']
                                show_record_results_dialog()

                    with action_col2:
                        # Mark as Completed button - available for IN_PROGRESS tournaments
                        if tournament_status == "IN_PROGRESS":
                            if st.button(
                                "✅ Mark as Completed",
                                key=f"complete_tournament_{tournament_id}",
                                use_container_width=True,
                                type="primary",
                                help="Mark tournament as completed"
                            ):
                                st.session_state['complete_tournament_id'] = tournament_id
                                st.session_state['complete_tournament_name'] = job['semester'].get('name', 'Unknown')
                                show_complete_tournament_dialog()

                    st.divider()
    else:
        st.info("💼 No active jobs")

    # Display COMPLETED JOBS
    if completed_jobs:
        st.divider()
        st.markdown("### ✅ COMPLETED JOBS")

        with st.expander(f"Show {len(completed_jobs)} completed job(s)", expanded=False):
            for job in completed_jobs:
                age_icon = get_age_group_icon(job['age_group'])

                if job['type'] == 'season':
                    st.markdown(f"**📅 SEASON:** {job['semester'].get('name', 'Unnamed Season')}")
                    st.caption(f"📍 Education Center: TBD | 👤 Master Instructor | 🎯 {age_icon} {job['age_group']}")
                    st.caption(f"📆 Duration: {job['start_date']} to {job['end_date']}")
                    st.caption(f"📊 Sessions: {len(job['sessions'])} completed | 👥 Students: TBD")
                else:
                    st.markdown(f"**🏆 TOURNAMENT:** {job['semester'].get('name', 'Unnamed Tournament')}")
                    st.caption(f"📍 Education Center: TBD | 👤 Master Instructor | 🎯 {age_icon} {job['age_group']}")
                    st.caption(f"📆 Date: {job['tournament_date']} ✅ Completed")
                    st.caption(f"📊 Sessions: {len(job['sessions'])} completed | 👥 Participants: TBD")

                st.divider()

    if not active_jobs and not completed_jobs:
        st.info("💼 No jobs assigned yet")
        st.caption("Accept tournament requests or master offers to get started")

# ========================================
# TAB 3: TOURNAMENT APPLICATIONS (NEW!)
# ========================================
with tab3:
    # Sub-tabs for tournament workflow
    tourn_tab1, tourn_tab2, tourn_tab3, tourn_tab4 = st.tabs([
        "🔍 Open Tournaments",
        "🏆 My Tournaments",
        "⚽ Match Command Center",
        "📋 Fixtures (Validation)"
    ])

    with tourn_tab1:
        render_open_tournaments_tab(token, user)

    with tourn_tab2:
        render_my_tournaments_tab(token, user)

    with tourn_tab3:
        st.markdown("### ⚽ Match Command Center")
        st.info(
            "Match management has moved to the unified **Tournament Manager**. "
            "Use the sidebar button or click below.",
            icon="ℹ️",
        )
        if st.button("🏆 Open Tournament Manager", type="primary", use_container_width=True, key="btn_mcc_redirect"):
            st.switch_page("pages/Tournament_Manager.py")

    with tourn_tab4:
        # Fixtures Validation View - ONLY show schedule, NO result entry
        from components.tournaments.instructor.tournament_fixtures_view import render_tournament_fixtures

        st.markdown("### 📋 Tournament Fixtures (Validation)")
        st.caption("View tournament schedule - Backend verification ONLY")

        # Get ALL tournaments (not just IN_PROGRESS) for validation
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/v1/semesters",
                headers={"Authorization": f"Bearer {token}"},
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                all_semesters = response.json().get('semesters', [])
                # Filter for tournaments assigned to this instructor
                tournaments = [
                    t for t in all_semesters
                    if t.get('code', '').startswith('TOURN-') and
                       t.get('master_instructor_id') == user.get('id')
                ]

                if tournaments:
                    # Let user select tournament
                    tournament_options = {
                        f"{t['name']} - {t.get('tournament_status', 'UNKNOWN')} (ID: {t['id']})": t['id']
                        for t in tournaments
                    }

                    selected_tournament_name = st.selectbox(
                        "Select Tournament to View Fixtures",
                        options=list(tournament_options.keys()),
                        key="fixtures_view_tournament_select"
                    )

                    if selected_tournament_name:
                        tournament_id = tournament_options[selected_tournament_name]
                        st.divider()
                        render_tournament_fixtures(token, tournament_id)
                else:
                    st.info("📋 No tournaments found")
            else:
                st.error(f"Failed to load tournaments: {response.status_code}")
        except Exception as e:
            st.error(f"Error loading tournaments: {str(e)}")

# ========================================
# TAB 4: MY STUDENTS
# ========================================
with tab4:
    render_students_tab(token)


with tab5:
    st.markdown("### ✅ Check-in & Group Assignment")
    st.caption("Mark attendance and create groups for your regular sessions")

    # Note: Tournament check-in moved to Match Command Center
    st.info("💡 **For tournaments:** Use the **⚽ Match Command Center** in the **Tournament Applications** tab!")

    # Regular session check-in only (Present, Absent, Late, Excused)
    render_session_checkin(token, user.get('id'))

# ========================================
# TAB 6: INBOX (Universal Messaging System)
# ========================================
with tab6:
    render_inbox_tab(token, user)


with tab7:
    render_profile_tab(token, user)


# ============================================================================
# TOURNAMENT MANAGEMENT DIALOGS
# ============================================================================

@st.dialog("📝 Record Tournament Results")
def show_record_results_dialog():
    """
    Dialog for recording tournament rankings and results.
    Calls POST /api/v1/tournaments/{tournament_id}/rankings
    """
    tournament_id = st.session_state.get('record_results_tournament_id')
    tournament = st.session_state.get('record_results_tournament', {})
    tournament_name = tournament.get('name', 'Unknown Tournament')

    st.write(f"**Tournament:** {tournament_name}")
    st.write(f"**Tournament ID:** {tournament_id}")
    st.divider()

    # Fetch enrolled players
    token = st.session_state.get('token')
    if not token:
        st.error("❌ Authentication token not found")
        return

    try:
        # Get tournament enrollments
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/{tournament_id}/enrollments",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code != 200:
            st.error(f"❌ Failed to load tournament enrollments: {response.status_code}")
            return

        enrollments = response.json().get('enrollments', [])

        if not enrollments:
            st.warning("⚠️ No enrolled players found")
            return

        st.info(f"📊 **{len(enrollments)} enrolled player(s)**")
        st.divider()

        # Create ranking inputs for each player
        st.markdown("### Enter Rankings")
        st.caption("Assign a unique rank to each player (1 = 1st place, 2 = 2nd place, etc.)")

        rankings = []

        for idx, enrollment in enumerate(enrollments):
            user = enrollment.get('user', {})
            user_id = user.get('id')
            user_name = user.get('name', 'Unknown Player')
            user_email = user.get('email', 'N/A')

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**{user_name}**")
                st.caption(f"{user_email}")

            with col2:
                rank = st.number_input(
                    "Rank",
                    min_value=1,
                    max_value=len(enrollments),
                    value=idx + 1,
                    step=1,
                    key=f"rank_{user_id}",
                    label_visibility="collapsed"
                )

            with col3:
                points = st.number_input(
                    "Points",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    key=f"points_{user_id}",
                    label_visibility="collapsed"
                )

            rankings.append({
                "user_id": user_id,
                "rank": rank,
                "points": points
            })

            st.divider()

        # Notes field
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Add any additional notes about the tournament results...",
            max_chars=500,
            key="ranking_notes"
        )

        st.divider()

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Submit Rankings", use_container_width=True, type="primary"):
                # Validate ranks are unique
                ranks_list = [r['rank'] for r in rankings]
                if len(ranks_list) != len(set(ranks_list)):
                    st.error("❌ Each player must have a unique rank!")
                    return

                # Validate ranks are sequential (1, 2, 3, ...)
                expected_ranks = set(range(1, len(enrollments) + 1))
                actual_ranks = set(ranks_list)
                if expected_ranks != actual_ranks:
                    st.error(f"❌ Ranks must be sequential from 1 to {len(enrollments)}")
                    st.caption(f"Expected: {sorted(expected_ranks)}, Got: {sorted(actual_ranks)}")
                    return

                # Submit rankings to API
                payload = {
                    "rankings": rankings,
                    "notes": notes if notes else None
                }

                try:
                    with st.spinner("Submitting rankings..."):
                        submit_response = requests.post(
                            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/rankings",
                            headers={"Authorization": f"Bearer {token}"},
                            json=payload,
                            timeout=API_TIMEOUT
                        )

                    if submit_response.status_code == 200:
                        result = submit_response.json()
                        st.success(f"✅ Rankings submitted successfully!")
                        st.caption(f"📊 {result.get('rankings_submitted', 0)} rankings recorded")
                        st.balloons()

                        # Clear session state
                        if 'record_results_tournament_id' in st.session_state:
                            del st.session_state['record_results_tournament_id']
                        if 'record_results_tournament' in st.session_state:
                            del st.session_state['record_results_tournament']

                        time.sleep(2)
                        st.rerun()
                    else:
                        error_data = submit_response.json() if submit_response.headers.get('content-type') == 'application/json' else {}
                        error_msg = error_data.get('detail', submit_response.text)
                        st.error(f"❌ Failed to submit rankings: {error_msg}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                # Clear session state
                if 'record_results_tournament_id' in st.session_state:
                    del st.session_state['record_results_tournament_id']
                if 'record_results_tournament' in st.session_state:
                    del st.session_state['record_results_tournament']
                st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading tournament data: {str(e)}")


@st.dialog("✅ Mark Tournament as Completed")
def show_complete_tournament_dialog():
    """
    Dialog for marking a tournament as COMPLETED.
    Calls PATCH /api/v1/tournaments/{tournament_id}/status
    """
    tournament_id = st.session_state.get('complete_tournament_id')
    tournament_name = st.session_state.get('complete_tournament_name', 'Unknown')

    st.warning(f"⚠️ Mark tournament **{tournament_name}** as COMPLETED?")
    st.write(f"**Tournament ID:** {tournament_id}")
    st.divider()

    st.info("ℹ️ This will transition the tournament status from IN_PROGRESS to COMPLETED.")
    st.caption("After completion, you can distribute rewards to players.")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirm", use_container_width=True, type="primary"):
            token = st.session_state.get('token')
            if not token:
                st.error("❌ Authentication token not found")
                return

            try:
                with st.spinner("Marking tournament as completed..."):
                    response = requests.patch(
                        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "new_status": "COMPLETED",
                            "reason": "Tournament finished - marked by instructor"
                        },
                        timeout=API_TIMEOUT
                    )

                if response.status_code == 200:
                    st.success("✅ Tournament marked as COMPLETED!")
                    st.balloons()

                    # Clear session state
                    if 'complete_tournament_id' in st.session_state:
                        del st.session_state['complete_tournament_id']
                    if 'complete_tournament_name' in st.session_state:
                        del st.session_state['complete_tournament_name']

                    time.sleep(2)
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Failed to complete tournament: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'complete_tournament_id' in st.session_state:
                del st.session_state['complete_tournament_id']
            if 'complete_tournament_name' in st.session_state:
                del st.session_state['complete_tournament_name']
            st.rerun()
