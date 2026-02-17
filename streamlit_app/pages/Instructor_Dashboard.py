"""
Instructor Dashboard
REBUILT from unified_workflow_dashboard.py (WORKING!)
EXACT API patterns + EXACT UI/UX patterns
"""

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, SPECIALIZATIONS
from api_helpers import get_sessions, get_users, get_semesters
from session_manager import restore_session_from_url
from datetime import datetime, timedelta
from collections import defaultdict

# Page configuration
from api_helpers_notifications import get_unread_notification_count
from api_helpers_instructors import get_my_master_offers, get_user_licenses
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
# DATA PREPARATION (Fetch ONCE, use across all tabs)
# ========================================

with st.spinner("Loading your data..."):
    # Fetch ALL sessions (shared across tabs)
    success, all_sessions = get_sessions(token, size=100, specialization_filter=True)

    # Fetch ALL master-led semesters (to show future commitments without sessions)
    semester_success, all_semesters = get_semesters(token)

if not success:
    st.error("❌ Failed to load sessions. Please refresh the page.")
    st.stop()

if not semester_success:
    st.warning("⚠️ Could not load semester data. Some information may be incomplete.")
    all_semesters = []

# Separate seasons vs tournaments
seasons_sessions = [s for s in all_sessions if not s.get('semester', {}).get('code', '').startswith('TOURN-')]
tournament_sessions = [s for s in all_sessions if s.get('semester', {}).get('code', '').startswith('TOURN-')]

# Group by semester_id
seasons_by_semester = defaultdict(list)
for s in seasons_sessions:
    semester_id = s.get('semester_id')
    if semester_id:
        seasons_by_semester[semester_id].append(s)

tournaments_by_semester = defaultdict(list)
for t in tournament_sessions:
    semester_id = t.get('semester_id')
    if semester_id:
        tournaments_by_semester[semester_id].append(t)

# Filter for today and next 7 days
today = datetime.now().date()
next_week = today + timedelta(days=7)

upcoming_sessions = []
for s in all_sessions:
    date_start_str = s.get('date_start')
    if date_start_str:
        try:
            session_date = datetime.fromisoformat(date_start_str.replace('Z', '+00:00')).date()
            if today <= session_date <= next_week:
                upcoming_sessions.append(s)
        except:
            pass  # Skip sessions with invalid date

# Sort upcoming sessions by date
upcoming_sessions.sort(key=lambda x: x.get('date_start', ''))

# Filter today's sessions
todays_sessions = [s for s in upcoming_sessions if datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date() == today]

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
# TAB 1: TODAY & UPCOMING (PRIMARY LANDING VIEW)
# ========================================
with tab1:
    st.markdown("### 📆 Today & Upcoming")
    st.caption("Time-sensitive sessions - what needs your attention NOW")

    # Quick Stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric("📅 Today", len(todays_sessions))
    with stats_col2:
        st.metric("📅 This Week", len(upcoming_sessions))
    with stats_col3:
        # Count pending actions (tournament requests + master offers)
        try:
            pending_offers = get_my_master_offers(token, include_expired=False)
            pending_offers_count = len([o for o in pending_offers if o.get('status') == 'PENDING'])
        except:
            pending_offers_count = 0

        # TODO: Add tournament requests count when available
        pending_actions = pending_offers_count
        st.metric("🎯 Pending Actions", pending_actions)

    st.divider()

    # TODAY'S SESSIONS
    if todays_sessions:
        st.markdown("### 🚨 TODAY'S SESSIONS")

        for session in todays_sessions:
            semester_data = session.get('semester', {})

            # Extract session details
            try:
                start_dt = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                time_str = start_dt.strftime('%H:%M')
            except:
                time_str = 'N/A'

            title = session.get('title', 'Session')
            capacity = session.get('capacity', 0)
            bookings = session.get('confirmed_bookings', 0)
            semester_name = semester_data.get('name', 'Unknown')

            # Display in red border container
            with st.container():
                st.markdown(
                    f"<div style='border-left: 5px solid #FF4B4B; padding-left: 10px; margin-bottom: 10px;'>"
                    f"<strong>{time_str}</strong> - {title}<br>"
                    f"<small>📍 {semester_name} | 👥 {bookings}/{capacity}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    else:
        st.info("✅ No sessions today")

    st.divider()

    # THIS WEEK (Next 7 Days)
    st.markdown("### 📅 THIS WEEK (Next 7 Days)")

    if upcoming_sessions:
        # Group by day
        sessions_by_day = defaultdict(list)
        for s in upcoming_sessions:
            try:
                session_date = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date()
                sessions_by_day[session_date].append(s)
            except:
                pass

        # Display each day
        for day in sorted(sessions_by_day.keys()):
            day_sessions = sessions_by_day[day]
            day_name = day.strftime('%A, %B %d')
            is_today = (day == today)

            with st.expander(f"**{day_name}** ({len(day_sessions)} sessions)" + (" ⚠️ TODAY" if is_today else ""), expanded=is_today):
                for session in sorted(day_sessions, key=lambda x: x.get('date_start', '')):
                    semester_data = session.get('semester', {})

                    try:
                        start_dt = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                        time_str = start_dt.strftime('%H:%M')
                    except:
                        time_str = 'N/A'

                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.markdown(f"**{session.get('title', 'Session')}**")
                    with col2:
                        st.caption(f"🕐 {time_str} | 📍 {semester_data.get('name', 'Unknown')}")
                    with col3:
                        capacity = session.get('capacity', 0)
                        bookings = session.get('confirmed_bookings', 0)
                        st.caption(f"👥 {bookings}/{capacity}")
    else:
        st.info("📅 No sessions scheduled for the next 7 days")

        # Show next session if any
        if all_sessions:
            future_sessions = []
            for s in all_sessions:
                try:
                    session_date = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date()
                    if session_date > next_week:
                        future_sessions.append((session_date, s))
                except:
                    pass

            if future_sessions:
                future_sessions.sort(key=lambda x: x[0])
                next_session_date, next_session = future_sessions[0]
                st.caption(f"📅 Next session: {next_session_date.strftime('%A, %B %d')} - {next_session.get('title', 'Session')}")

    # ACTION REQUIRED section
    if pending_actions > 0:
        st.divider()
        st.markdown("### ⚠️ ACTION REQUIRED")
        st.warning(f"You have **{pending_actions}** pending action(s) in the **📬 Inbox** tab")
        if st.button("Go to Inbox →", use_container_width=True):
            st.session_state['active_tab'] = 'Inbox'
            st.rerun()

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
    st.markdown("### 👥 My Students")
    st.caption("Students enrolled in your master-led semesters")

    # Check if user is an active Master Instructor
    with st.spinner("Checking master instructor status..."):
        try:
            my_offers = get_my_master_offers(token, include_expired=False)
            active_master_offers = [o for o in my_offers if o.get('offer_status') == 'ACCEPTED' and o.get('is_active')]
        except:
            active_master_offers = []

    if not active_master_offers:
        # Not a Master Instructor - show info message
        st.info("👨‍🏫 **Master Instructor Only**")
        st.markdown("""
        This section is only available when you are an **active Master Instructor** at a training location.

        **How to become a Master Instructor:**
        1. Check the "📩 Master Offers" tab for pending invitations
        2. Accept an offer from a training location
        3. Once accepted, you'll see your students here

        **Current Status:** Not currently serving as Master Instructor
        """)
    else:
        # Active Master Instructor - show students
        master_location = active_master_offers[0].get('location_name', 'Unknown Location')
        master_city = active_master_offers[0].get('location_city', '')

        st.success(f"✅ Master Instructor at: **{master_location}** ({master_city})")

        with st.spinner("Loading students..."):
            # TODO: Implement proper endpoint to get students for master's semesters
            # For now, show placeholder
            st.info("🚧 Student management feature coming soon")
            st.caption("This will show all students enrolled in semesters at your location.")

        # FUTURE: Replace with actual student query
        # success, students = get_master_students(token, location_id)
        # Display students with same pattern as before

# ========================================
# TAB 5: CHECK-IN & GROUPS
# ========================================
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
    # Use the new universal inbox component
    render_my_applications_tab(token, user)

# ========================================
# TAB 7: MY PROFILE
# ========================================
with tab7:
    st.markdown("### 👤 My Profile")
    st.caption("Your licenses, teaching permissions, and instructor status")

    # Fetch instructor's teaching licenses
    instructor_licenses = get_user_licenses(token, user.get('id'))

    # Display instructor profile in 3-column layout (similar to student profile)
    profile_col1, profile_col2, profile_col3 = st.columns([2, 2, 2])

    # ============================================================================
    # COLUMN 1: BASIC INFORMATION
    # ============================================================================
    with profile_col1:
        st.markdown("**📋 Basic Information**")
        st.caption(f"**Name:** {user.get('name', 'N/A')}")
        st.caption(f"**Email:** {user.get('email', 'N/A')}")
        st.caption(f"**Role:** Instructor")

        # Check if user is a Master Instructor
        is_master = user.get('is_master_instructor', False)
        if is_master:
            st.caption("**Status:** ⭐ Master Instructor")
        else:
            st.caption("**Status:** Regular Instructor")

    # ============================================================================
    # COLUMN 2: TEACHING LICENSES
    # ============================================================================
    with profile_col2:
        st.markdown("**📜 Teaching Licenses**")

        if instructor_licenses:
            # ✅ FÁZIS 2: DEDUPLIKÁCIÓ - Csoportosítás specialization_type szerint
            grouped_licenses = {}
            for lic in instructor_licenses:
                spec_type = lic.get('specialization_type')
                current_level = lic.get('current_level', 1)

                if spec_type not in grouped_licenses:
                    grouped_licenses[spec_type] = lic
                else:
                    # Legmagasabb szintet tartjuk meg
                    if current_level > grouped_licenses[spec_type].get('current_level', 0):
                        grouped_licenses[spec_type] = lic

            active_licenses = [lic for lic in grouped_licenses.values() if lic.get('is_active', True)]

            if active_licenses:
                st.caption("**✅ Active Licenses:**")
                for lic in active_licenses:
                    spec_type = lic.get('specialization_type', 'Unknown')
                    current_level = lic.get('current_level', 1)

                    # HELYES mapping migration UTÁN
                    if spec_type == 'GANCUJU_PLAYER':
                        display_name = "GānCuju Player"
                    elif spec_type == 'LFA_COACH':
                        display_name = "LFA Coach"
                    elif spec_type == 'INTERNSHIP':
                        display_name = "Internship"
                    elif spec_type == 'LFA_FOOTBALL_PLAYER':
                        display_name = "LFA Football Player"
                    else:
                        display_name = SPECIALIZATIONS.get(spec_type, spec_type)

                    st.caption(f"• {display_name} (Level {current_level})")
            else:
                st.caption("**No active teaching licenses**")
                st.caption("_Contact admin to get licensed_")
        else:
            st.caption("**No teaching licenses found**")
            st.caption("_You need licenses to accept teaching assignments_")

    # ============================================================================
    # COLUMN 3: TEACHING PERMISSIONS
    # ============================================================================
    with profile_col3:
        st.markdown("**🎯 Teaching Permissions**")

        if instructor_licenses:
            # ✅ FÁZIS 4: SZINT ALAPÚ TEACHING PERMISSIONS
            teaching_permissions = []

            for lic in active_licenses:  # Deduplikált listát használjuk!
                spec_type = lic.get('specialization_type', 'Unknown')
                current_level = lic.get('current_level', 1)

                if spec_type == 'LFA_COACH':
                    # LFA_COACH → can teach LFA Football Player AND coaches!
                    # ALL levels (1-8) authorized (Assistant vs Head distinction)
                    teaching_permissions.append("LFA Football Player programs")
                    teaching_permissions.append("LFA Coach programs")

                elif spec_type == 'INTERNSHIP':
                    # ⚠️ CRITICAL: ONLY Level 5 (Principal) can teach!
                    if current_level == 5:
                        teaching_permissions.append("LFA Internship mentoring")
                    # Level 1-4: NOT authorized

                elif spec_type == 'GANCUJU_PLAYER':
                    # ⚠️ CRITICAL: ONLY Level 5-8 can teach!
                    if current_level >= 5:
                        teaching_permissions.append("GānCuju player training")
                    # Level 1-4: NOT authorized

            # Számláljuk meg a PROGRAMOKAT, nem a licence-eket!
            permission_count = len(teaching_permissions)
            st.metric("Can Teach", f"{permission_count} program type{'s' if permission_count != 1 else ''}")

            st.markdown("---")

            if permission_count > 0:
                st.caption("**You are qualified to teach:**")
                for permission in teaching_permissions:
                    st.caption(f"• {permission}")
            else:
                # Ha nincs teaching permission (pl. GANCUJU L1-4, INTERNSHIP L1-4)
                st.caption("**No instructor authorization**")
                st.caption("_Reach higher levels to gain teaching permissions!_")
        else:
            st.info("⚠️ No teaching licenses - cannot accept assignments")

    st.divider()

    # Show detailed license information
    if instructor_licenses:
        with st.expander("📊 Detailed License Information"):
            for lic in active_licenses:  # ✅ NEM instructor_licenses, hanem DEDUPLIKÁLT active_licenses!
                spec_type = lic.get('specialization_type', 'Unknown')
                current_level = lic.get('current_level', 1)

                # HELYES mapping
                if spec_type == 'GANCUJU_PLAYER':
                    display_name = "GānCuju Player"
                elif spec_type == 'LFA_COACH':
                    display_name = "LFA Coach"
                elif spec_type == 'INTERNSHIP':
                    display_name = "Internship"
                elif spec_type == 'LFA_FOOTBALL_PLAYER':
                    display_name = "LFA Football Player"
                else:
                    display_name = SPECIALIZATIONS.get(spec_type, spec_type)

                is_active = lic.get('is_active', True)

                status_badge = "✅ Active" if is_active else "❌ Inactive"

                st.markdown(f"**{display_name} (Level {current_level})** - {status_badge}")

                # Show license details
                col_a, col_b = st.columns(2)
                with col_a:
                    issued_at = lic.get('issued_at')
                    if issued_at:
                        try:
                            # Handle both datetime objects and ISO strings
                            if isinstance(issued_at, str):
                                issued_date = datetime.fromisoformat(issued_at.replace('Z', '+00:00'))
                            else:
                                issued_date = issued_at
                            st.caption(f"Issued: {issued_date.strftime('%Y-%m-%d')}")
                        except:
                            st.caption("Issued: Unknown")
                    else:
                        # Fallback: use started_at if issued_at missing
                        started_at = lic.get('started_at')
                        if started_at:
                            try:
                                if isinstance(started_at, str):
                                    start_date = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                                else:
                                    start_date = started_at
                                st.caption(f"Started: {start_date.strftime('%Y-%m-%d')}")
                            except:
                                st.caption("Issued: Unknown")
                        else:
                            st.caption("Issued: Unknown")

                with col_b:
                    # Use expires_at (not valid_until - we decided OPTION B)
                    expires_at = lic.get('expires_at')
                    if expires_at:
                        try:
                            # Handle both datetime objects and ISO strings
                            if isinstance(expires_at, str):
                                expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            else:
                                expiry_date = expires_at

                            st.caption(f"Valid until: {expiry_date.strftime('%Y-%m-%d')}")

                            # ⚠️ Expiration warnings
                            days_remaining = (expiry_date - datetime.now()).days
                            if days_remaining < 0:
                                st.error(f"⚠️ EXPIRED {abs(days_remaining)} days ago!")
                            elif days_remaining <= 30:
                                st.warning(f"⚠️ Expires in {days_remaining} days")
                        except:
                            st.caption("Valid until: Unknown")
                    else:
                        st.caption("Valid until: Perpetual")  # NULL = perpetual license

                st.markdown("---")


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
