"""
Admin Dashboard - MODULAR ARCHITECTURE
Compact, reusable components for session, user, and location management
"""

import sys
from pathlib import Path

# Add parent directory to path to import config and other modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY
from api_helpers import get_users, get_sessions, get_locations, get_campuses_by_location, get_semesters
# Financial components (modular)
from components.financial.coupon_management import render_coupon_management
from components.financial.invoice_management import render_invoice_management
from components.financial.invitation_management import render_invitation_management
# Semester components (modular)
from components.semesters import (
    render_location_management,
    render_semester_generation,
    render_semester_management,
    render_semester_overview
)
from session_manager import restore_session_from_url, clear_session
from datetime import datetime

# Import compact components
from components.session_filters import render_session_filters, apply_session_filters
from components.user_filters import render_user_filters, apply_user_filters
from components.session_actions import render_session_action_buttons
from components.user_actions import render_user_action_buttons
from components.location_filters import render_location_filters, apply_location_filters
from components.location_actions import render_location_action_buttons
from components.location_modals import render_create_location_modal
from components.campus_actions import render_campus_action_buttons


# ========================================
# HELPER FUNCTIONS
# ========================================

def _is_upcoming_session(session, now):
    """Check if session is upcoming based on start time"""
    start_time_str = session.get('date_start', '')
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            return start_time > now
        except (ValueError, AttributeError):
            return False
    return False


# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Admin Dashboard",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# SIMPLIFIED SESSION PERSISTENCE: Restore from URL params
if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()

# Check authentication
if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("❌ Not authenticated. Please login first.")
    st.info("💡 **How to login:** Go to Home page and use your credentials.")

    st.markdown("---")
    st.markdown("### Quick Access:")
    st.markdown("1. Click **'🔑 Go to Login'** button below")
    st.markdown("2. Enter your **email** and **password**")
    st.markdown("3. You'll be automatically redirected here")

    # CRITICAL FIX: Redirect to login page (Home is in root, not pages/)
    st.markdown("### 🔗 [Click here to go to Login Page](http://localhost:8505)")

    st.markdown("---")
    st.code("http://localhost:8505", language=None)
    st.caption("Copy-paste this URL to your browser if the link doesn't work")

    st.stop()

# Check admin role
user = st.session_state[SESSION_USER_KEY]
if user.get('role') != 'admin':
    st.error("❌ Access denied. Admin role required.")
    st.stop()

# Get token
token = st.session_state[SESSION_TOKEN_KEY]

# Header
st.title("📊 Admin Dashboard")
st.caption("LFA Education Center - Complete Admin Interface")

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Admin')}!")
    st.caption(f"Role: **Admin**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    # REFRESH BUTTON - Keep session alive without re-login
    if st.button("🔄 Refresh Page", use_container_width=True, type="secondary"):
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        # Clear session (both session_state and query params)
        clear_session()
        st.switch_page("🏠_Home.py")

# Tab selection (MOVED BEFORE columns for full width)
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'overview'

tab_col1, tab_col2, tab_col3, tab_col4, tab_col5, tab_col6 = st.columns(6)
with tab_col1:
    if st.button("📊 Overview", use_container_width=True, type="primary" if st.session_state.active_tab == 'overview' else "secondary"):
        st.session_state.active_tab = 'overview'
        st.rerun()
with tab_col2:
    if st.button("👥 Users", use_container_width=True, type="primary" if st.session_state.active_tab == 'users' else "secondary"):
        st.session_state.active_tab = 'users'
        st.rerun()
with tab_col3:
    if st.button("📅 Sessions", use_container_width=True, type="primary" if st.session_state.active_tab == 'sessions' else "secondary"):
        st.session_state.active_tab = 'sessions'
        st.rerun()
with tab_col4:
    if st.button("📍 Locations", use_container_width=True, type="primary" if st.session_state.active_tab == 'locations' else "secondary"):
        st.session_state.active_tab = 'locations'
        st.rerun()
with tab_col5:
    if st.button("💳 Financial", use_container_width=True, type="primary" if st.session_state.active_tab == 'financial' else "secondary"):
        st.session_state.active_tab = 'financial'
        st.rerun()
with tab_col6:
    if st.button("📅 Semesters", use_container_width=True, type="primary" if st.session_state.active_tab == 'semesters' else "secondary"):
        st.session_state.active_tab = 'semesters'
        st.rerun()

st.divider()

# Main layout with sidebar filters (AFTER tabs)
filter_col, main_col = st.columns([1, 3])

# ========================================
# OVERVIEW TAB (Location-based overview)
# ========================================
if st.session_state.active_tab == 'overview':
    # Load locations first
    with st.spinner("Loading locations..."):
        success_loc, all_locations = get_locations(token, include_inactive=False)

    # Sidebar: Location selector
    with filter_col:
        st.markdown("### 📍 Select Location")

        if success_loc and all_locations:
            # Location = City level (campuses are venues within the city)
            location_names = {}
            for loc in all_locations:
                city = loc['city']
                country = loc.get('country', '')
                # Display: City, Country (e.g., "Budapest, Hungary")
                display_name = f"{city}, {country}" if country else city
                location_names[display_name] = loc['id']

            selected_location_name = st.selectbox(
                "Choose location",
                options=list(location_names.keys()),
                key="overview_location_selector"
            )
            selected_location_id = location_names[selected_location_name]
            selected_location = next((loc for loc in all_locations if loc['id'] == selected_location_id), None)
        else:
            st.warning("No active locations found")
            selected_location = None
            selected_location_id = None

        st.divider()

        if selected_location:
            st.markdown("### 📋 Location Info")
            st.caption(f"**City:** {selected_location.get('city', 'N/A')}")
            st.caption(f"**Country:** {selected_location.get('country', 'N/A')}")
            # Note: Venue field is deprecated - campuses are now separate entities

    # Main area: Overview content
    with main_col:
        st.markdown("### 📊 Location Overview")

        if not selected_location:
            st.info("📍 Please create a location first in the **Locations** tab")
        else:
            st.caption(f"Overview for: **{selected_location['name']}**")
            st.divider()

            # Load semesters for this location
            with st.spinner("Loading semesters..."):
                success_sem, all_semesters = get_semesters(token)

            if success_sem and all_semesters:
                # Filter semesters by location (we need to check which semesters use this location)
                # For now, show all semesters and filter by specialization

                st.markdown("#### 🎓 Active Semesters by Specialization")

                # Group semesters by specialization
                from collections import defaultdict
                spec_semesters = defaultdict(list)

                for sem in all_semesters:
                    if sem.get('is_active'):
                        spec_type = sem.get('specialization_type', 'Unknown')
                        spec_semesters[spec_type].append(sem)

                if spec_semesters:
                    for spec_type, semesters in spec_semesters.items():
                        with st.expander(f"⚽ {spec_type.replace('_', ' ').title()} ({len(semesters)} semesters)"):
                            for sem in semesters:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.caption(f"**{sem.get('name', 'N/A')}**")
                                with col2:
                                    st.caption(f"📅 {sem.get('start_date', 'N/A')} to {sem.get('end_date', 'N/A')}")
                                with col3:
                                    st.caption(f"ID: {sem.get('id')}")
                else:
                    st.info("No active semesters found")

            st.divider()

            # Load campuses and sessions for this location
            st.markdown("#### 🏫 Campuses & Sessions")

            campus_success, campuses = get_campuses_by_location(token, selected_location_id, include_inactive=False)

            if campus_success and campuses:
                # Load all sessions
                with st.spinner("Loading sessions..."):
                    success_sess, all_sessions = get_sessions(token, size=100, specialization_filter=False)

                # Group sessions by campus
                from datetime import datetime
                from collections import defaultdict

                # For each campus, show its sessions
                for campus in campuses:
                    campus_name = campus.get('name', 'Unknown Campus')
                    campus_venue = campus.get('venue', '')

                    # Filter sessions for this campus
                    # NOTE: Currently sessions use 'location' string field
                    # TODO: When Session model is updated to use campus_id, this filter will be more precise
                    campus_sessions = []
                    if success_sess and all_sessions:
                        # Temporary filtering: match by campus name or venue in session location string
                        for s in all_sessions:
                            session_loc = (s.get('location') or '').lower()
                            if campus_name.lower() in session_loc or (campus_venue and campus_venue.lower() in session_loc):
                                campus_sessions.append(s)

                    # Count upcoming/past
                    now = datetime.now()
                    upcoming = []
                    past = []
                    for s in campus_sessions:
                        if s.get('date_start'):
                            try:
                                start_time = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00'))
                                if start_time > now:
                                    upcoming.append(s)
                                else:
                                    past.append(s)
                            except:
                                pass

                    # Campus expander with session count
                    with st.expander(f"🏫 **{campus_name}** - {len(campus_sessions)} sessions ({len(upcoming)} upcoming, {len(past)} past)", expanded=True):
                        # Campus info
                        col1, col2 = st.columns(2)
                        with col1:
                            if campus_venue:
                                st.caption(f"📍 Venue: {campus_venue}")
                            if campus.get('address'):
                                st.caption(f"📮 Address: {campus['address']}")
                        with col2:
                            st.caption(f"🔢 Total Sessions: {len(campus_sessions)}")
                            st.caption(f"🔜 Upcoming: {len(upcoming)}")

                        st.divider()

                        # Show sessions
                        if campus_sessions:
                            st.markdown("**📅 Sessions:**")

                            # Sort by date
                            sorted_sessions = sorted(
                                campus_sessions,
                                key=lambda x: x.get('date_start', ''),
                                reverse=False
                            )

                            # Show sessions (limit to first 10)
                            for session in sorted_sessions[:10]:
                                start_time_str = session.get('date_start', '')
                                session_title = session.get('title', 'N/A')
                                session_type = session.get('session_type', 'N/A')

                                if start_time_str:
                                    try:
                                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                        time_str = start_time.strftime('%Y-%m-%d %H:%M')
                                        future_emoji = "🔜" if start_time > now else "✅"
                                        st.caption(f"{future_emoji} **{session_title}** - {time_str} ({session_type})")
                                    except:
                                        st.caption(f"• **{session_title}** ({session_type})")
                                else:
                                    st.caption(f"• **{session_title}** ({session_type})")

                            if len(campus_sessions) > 10:
                                st.caption(f"... and {len(campus_sessions) - 10} more sessions")
                        else:
                            st.info("No sessions scheduled at this campus yet")
            else:
                st.warning("⚠️ No campuses found for this location. Add campuses in the **Locations** tab.")

# ========================================
# USERS TAB (with filters and actions)
# ========================================
elif st.session_state.active_tab == 'users':
    # Sidebar: Filters
    with filter_col:
        user_filters = render_user_filters()

    # Main area: User cards
    with main_col:
        st.markdown("### 👥 User Management")
        st.caption("View and manage all users in the system")

        with st.spinner("Loading users..."):
            success, users = get_users(token, limit=100)

        if success and users:
            # Apply filters
            filtered_users = apply_user_filters(users, user_filters)

            # Stats widgets
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

            students_count = len([u for u in filtered_users if u.get("role") == "student"])
            instructors_count = len([u for u in filtered_users if u.get("role") == "instructor"])
            admins_count = len([u for u in filtered_users if u.get("role") == "admin"])
            active_count = len([u for u in filtered_users if u.get("is_active")])

            with stats_col1:
                st.metric("👥 Total", len(filtered_users))
            with stats_col2:
                st.metric("🎓 Students", students_count)
            with stats_col3:
                st.metric("👨‍🏫 Instructors", instructors_count)
            with stats_col4:
                st.metric("✅ Active", active_count)

            st.divider()

            # User cards with action buttons
            if filtered_users:
                st.caption(f"📋 Showing {len(filtered_users)} user(s):")
                for user_item in filtered_users:
                    role = user_item.get("role", "").lower()
                    role_icon = {"student": "🎓", "instructor": "👨‍🏫", "admin": "👑"}.get(role, "👤")
                    status_icon = "✅" if user_item.get('is_active') else "❌"

                    with st.expander(
                        f"{role_icon} **{user_item.get('name', 'Unknown')}** ({user_item.get('email', 'N/A')}) {status_icon}",
                        expanded=False
                    ):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**📋 Basic Info**")
                            st.caption(f"ID: {user_item.get('id')}")
                            st.caption(f"Email: {user_item.get('email', 'N/A')}")
                            st.caption(f"Name: {user_item.get('name', 'N/A')}")

                        with col2:
                            st.markdown("**🔑 Role & Access**")
                            st.caption(f"Role: {role.title()}")
                            st.caption(f"Status: {'✅ Active' if user_item.get('is_active') else '❌ Inactive'}")

                            licenses = user_item.get('licenses', [])
                            if licenses:
                                st.caption(f"📜 Licenses: {len(licenses)}")
                                license_types = {}
                                for lic in licenses:
                                    spec_type = lic.get('specialization_type', 'Unknown')
                                    if spec_type.startswith('LFA_'):
                                        spec_type = spec_type.replace('LFA_', '')
                                    formatted = spec_type.replace('_', ' ').title()
                                    license_types[formatted] = license_types.get(formatted, 0) + 1

                                for spec_type, count in sorted(license_types.items()):
                                    if count > 1:
                                        st.caption(f"  • {spec_type} x{count}")
                                    else:
                                        st.caption(f"  • {spec_type}")
                            else:
                                st.caption("📜 Licenses: None")

                        with col3:
                            st.markdown("**💰 Credits & Stats**")
                            st.metric("Credit Balance", user_item.get('credit_balance', 0))

                        st.divider()
                        # Action buttons (from compact component)
                        render_user_action_buttons(user_item, token)
            else:
                st.info("No users match the selected filters")

        elif success and not users:
            st.info("No users found")
        else:
            st.error("❌ Failed to load users")

# ========================================
# SESSIONS TAB (Hierarchical: Location → Spec → Semester → Sessions)
# ========================================
elif st.session_state.active_tab == 'sessions':
    # Sidebar: Filters
    with filter_col:
        session_filters = render_session_filters(token)

    # Main area: Hierarchical session display
    with main_col:
        st.markdown("### 📅 Session Management")
        st.caption("Sessions organized by location, specialization, and semester")

        # Load all required data
        with st.spinner("Loading data..."):
            success_sess, all_sessions = get_sessions(token, size=100, specialization_filter=False)
            success_loc, all_locations = get_locations(token, include_inactive=False)
            success_sem, all_semesters = get_semesters(token)

        if success_sess and all_sessions and success_loc and all_locations:
            # Apply filters
            filtered_sessions = apply_session_filters(all_sessions, session_filters)

            # Calculate stats
            now = datetime.now()
            upcoming_count = 0
            past_count = 0
            for s in filtered_sessions:
                start_time_str = s.get('date_start', '')
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        if start_time > now:
                            upcoming_count += 1
                        else:
                            past_count += 1
                    except (ValueError, AttributeError):
                        pass

            # Stats widgets
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("📚 Total Sessions", len(filtered_sessions))
            with stats_col2:
                st.metric("🔜 Upcoming", upcoming_count)
            with stats_col3:
                st.metric("📊 Past", past_count)

            st.divider()

            # GROUP BY: Location → Specialization → Semester → Sessions
            if filtered_sessions:
                st.markdown("#### 🗂️ Sessions by Location, Specialization & Semester")

                # Group sessions by location (city name match)
                for location in all_locations:
                    location_city = location.get('city', '').lower()
                    location_id = location.get('id')
                    location_country = location.get('country', '')

                    # Filter sessions for this location (temporary name matching)
                    location_sessions = []
                    for session in filtered_sessions:
                        session_loc = (session.get('location') or '').lower()
                        if location_city in session_loc:
                            location_sessions.append(session)

                    if not location_sessions:
                        continue  # Skip locations with no sessions

                    # Count upcoming/past for this location
                    loc_upcoming = sum(1 for s in location_sessions if _is_upcoming_session(s, now))
                    loc_past = len(location_sessions) - loc_upcoming

                    # LEVEL 1: Location Expander
                    with st.expander(
                        f"📍 **{location_city.title()}, {location_country}** - {len(location_sessions)} sessions ({loc_upcoming} upcoming, {loc_past} past)",
                        expanded=False
                    ):
                        # Group by specialization within this location
                        spec_groups = {}
                        for session in location_sessions:
                            spec = session.get('specialization_type', 'NO_SPEC')
                            if spec not in spec_groups:
                                spec_groups[spec] = []
                            spec_groups[spec].append(session)

                        # LEVEL 2: Specialization Expanders
                        for spec_type, spec_sessions in sorted(spec_groups.items()):
                            # Format specialization name
                            if spec_type.startswith('LFA_'):
                                spec_display = spec_type.replace('LFA_', '').replace('_', ' ').title()
                            else:
                                spec_display = spec_type.replace('_', ' ').title()

                            spec_upcoming = sum(1 for s in spec_sessions if _is_upcoming_session(s, now))
                            spec_past = len(spec_sessions) - spec_upcoming

                            with st.expander(
                                f"🎯 **{spec_display}** - {len(spec_sessions)} sessions ({spec_upcoming} upcoming, {spec_past} past)",
                                expanded=False
                            ):
                                # Group by semester within this specialization
                                semester_groups = {}
                                for session in spec_sessions:
                                    semester_id = session.get('semester_id', 0)
                                    if semester_id not in semester_groups:
                                        semester_groups[semester_id] = []
                                    semester_groups[semester_id].append(session)

                                # LEVEL 3: Semester Expanders
                                for semester_id, semester_sessions in sorted(semester_groups.items()):
                                    # Find semester name
                                    semester_name = "Unknown Semester"
                                    if success_sem and all_semesters:
                                        for sem in all_semesters:
                                            if sem.get('id') == semester_id:
                                                semester_name = sem.get('name', f"Semester {semester_id}")
                                                break
                                    else:
                                        semester_name = f"Semester {semester_id}"

                                    sem_upcoming = sum(1 for s in semester_sessions if _is_upcoming_session(s, now))
                                    sem_past = len(semester_sessions) - sem_upcoming

                                    with st.expander(
                                        f"📚 **{semester_name}** - {len(semester_sessions)} sessions ({sem_upcoming} upcoming, {sem_past} past)",
                                        expanded=False
                                    ):
                                        # LEVEL 4: Sessions sorted by date
                                        sorted_sessions = sorted(
                                            semester_sessions,
                                            key=lambda x: x.get('date_start', ''),
                                            reverse=False
                                        )

                                        for session in sorted_sessions:
                                            start_time_str = session.get('date_start', '')
                                            if not start_time_str:
                                                continue

                                            try:
                                                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                            except (ValueError, AttributeError):
                                                continue

                                            is_upcoming = start_time > now
                                            time_icon = "🔜" if is_upcoming else "✅"
                                            title = session.get('title', 'Untitled Session')
                                            session_type = session.get('session_type', 'N/A')

                                            # Session Card
                                            st.markdown(f"**{time_icon} {title}** ({session_type})")

                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.caption(f"📅 Start: {start_time.strftime('%Y-%m-%d %H:%M')}")
                                            with col2:
                                                end_time_str = session.get('date_end', '')
                                                if end_time_str:
                                                    try:
                                                        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                                                        duration_min = int((end_time - start_time).seconds / 60)
                                                        st.caption(f"⏱️ Duration: {duration_min} min")
                                                    except:
                                                        st.caption(f"⏱️ Duration: N/A")
                                            with col3:
                                                max_participants = session.get('capacity', 0)
                                                current_participants = len(session.get('bookings', []))
                                                st.caption(f"👥 Bookings: {current_participants}/{max_participants}")

                                            # Action buttons
                                            render_session_action_buttons(session, token)
                                            st.divider()

            else:
                st.info("No sessions match the selected filters")

        elif success_sess and not all_sessions:
            st.info("No sessions found")
        else:
            st.error("❌ Failed to load data")

# ========================================
# LOCATIONS TAB (with filters and actions)
# ========================================
elif st.session_state.active_tab == 'locations':
    # Load locations FIRST (before rendering any UI)
    with st.spinner("Loading locations..."):
        success, locations = get_locations(token, include_inactive=True)

    # Sidebar: Filters (render ONCE with loaded data)
    with filter_col:
        # Create button in sidebar
        st.markdown("### ➕ Actions")
        if st.button("➕ Create Location", use_container_width=True, type="primary"):
            st.session_state.create_location_modal = True
            st.rerun()

        st.divider()

        # Filters below create button (render ONCE)
        if success and locations:
            location_filters = render_location_filters(locations)
        else:
            location_filters = render_location_filters([])

    # Main area: Location cards
    with main_col:
        st.markdown("### 📍 Location Management")
        st.caption("Manage LFA Education Center locations")

        if success and locations:
            # Apply filters
            filtered_locations = apply_location_filters(locations, location_filters)

            # Stats widgets
            active_locations = [loc for loc in filtered_locations if loc.get('is_active', False)]
            inactive_locations = [loc for loc in filtered_locations if not loc.get('is_active', False)]

            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("📍 Total", len(filtered_locations))
            with stats_col2:
                st.metric("🟢 Active", len(active_locations))
            with stats_col3:
                st.metric("🔴 Inactive", len(inactive_locations))

            st.divider()

            # Location cards with action buttons
            if filtered_locations:
                st.caption(f"📋 Showing {len(filtered_locations)} location(s):")
                for location in filtered_locations:
                    location_id = location.get('id')
                    is_active = location.get('is_active', False)
                    status_emoji = "🟢" if is_active else "🔴"
                    name = location.get('name', 'Unknown Location')

                    with st.expander(f"{status_emoji} **{name}** (ID: {location_id})"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**📍 Location Info**")
                            st.caption(f"Name: {location.get('name', 'N/A')}")
                            st.caption(f"City: {location.get('city', 'N/A')}")
                            st.caption(f"Country: {location.get('country', 'N/A')}")

                        with col2:
                            st.markdown("**📮 Address Details**")
                            postal_code = location.get('postal_code') or 'N/A'
                            st.caption(f"Postal Code: {postal_code}")
                            venue = location.get('venue') or 'N/A'
                            st.caption(f"Venue: {venue}")

                        with col3:
                            st.markdown("**✅ Status**")
                            st.caption(f"Status: {'✅ Active' if is_active else '❌ Inactive'}")

                            # Address preview
                            address = location.get('address')
                            if address:
                                address_preview = address[:30] + "..." if len(address) > 30 else address
                                st.caption(f"Address: {address_preview}")

                        # Notes preview
                        notes = location.get('notes')
                        if notes:
                            st.markdown("**📝 Notes:**")
                            notes_preview = notes[:80] + "..." if len(notes) > 80 else notes
                            st.caption(notes_preview)

                        st.divider()

                        # CAMPUSES WITHIN THIS LOCATION
                        st.markdown("**🏫 Campuses at this location:**")
                        campus_success, campuses = get_campuses_by_location(token, location_id, include_inactive=True)

                        if campus_success and campuses:
                            # Display each campus in an expander with action buttons
                            for campus in campuses:
                                campus_status_emoji = "🟢" if campus.get('is_active') else "🔴"
                                campus_name = campus.get('name', 'Unknown Campus')
                                campus_id = campus.get('id')

                                # Campus expander
                                with st.expander(f"{campus_status_emoji} **{campus_name}** (Campus ID: {campus_id})"):
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        st.markdown("**📍 Campus Info**")
                                        st.caption(f"Name: {campus.get('name', 'N/A')}")
                                        st.caption(f"Venue: {campus.get('venue', 'N/A')}")

                                    with col2:
                                        st.markdown("**✅ Status**")
                                        st.caption(f"Status: {'🟢 Active' if campus.get('is_active') else '🔴 Inactive'}")
                                        address = campus.get('address')
                                        if address:
                                            address_preview = address[:30] + "..." if len(address) > 30 else address
                                            st.caption(f"Address: {address_preview}")

                                    # Notes preview
                                    notes = campus.get('notes')
                                    if notes:
                                        st.markdown("**📝 Notes:**")
                                        notes_preview = notes[:50] + "..." if len(notes) > 50 else notes
                                        st.caption(notes_preview)

                                    st.divider()
                                    # Action buttons
                                    render_campus_action_buttons(campus, location_id, token)
                        elif campus_success and not campuses:
                            st.caption("  ⚠️ No campuses found for this location")
                        else:
                            st.caption(f"  ❌ Error loading campuses: {campuses}")

                        st.divider()
                        # Action buttons (from compact component)
                        render_location_action_buttons(location, token)
            else:
                st.info("No locations match the selected filters")

        elif success and not locations:
            st.info("📍 No locations found. Create your first location!")
        else:
            st.error("❌ Failed to load locations")

        # Render create modal if open
        render_create_location_modal(token)

# ========================================
# FINANCIAL MANAGEMENT TAB
# ========================================
elif st.session_state.active_tab == 'financial':
    st.markdown("### 💳 Financial Management")
    st.caption("Manage coupons, invoices, and invitation codes")

    # Sub-tabs for financial sections
    financial_tab1, financial_tab2, financial_tab3 = st.tabs([
        "🎫 Coupons",
        "🧾 Invoices",
        "🎟️ Invitation Codes"
    ])

    # ========================================
    # COUPONS SUB-TAB
    # ========================================
    with financial_tab1:
        render_coupon_management(token)

    # ========================================
    # INVOICES SUB-TAB
    # ========================================
    with financial_tab2:
        render_invoice_management(token)

    # ========================================
    # INVITATION CODES SUB-TAB
    # ========================================
    with financial_tab3:
        render_invitation_management(token)

# ========================================
# SEMESTERS TAB (Location, Generation, Management)
# ========================================
elif st.session_state.active_tab == 'semesters':
    st.markdown("### 📅 Semester Generation & Management")
    st.caption("Manage locations, generate semesters, and assign instructors")

    # Sub-tabs for semester features
    semester_tab1, semester_tab2, semester_tab3, semester_tab4 = st.tabs([
        "📊 Overview",
        "📍 Locations",
        "🚀 Generate",
        "🎯 Manage"
    ])

    # ========================================
    # OVERVIEW SUB-TAB
    # ========================================
    with semester_tab1:
        render_semester_overview(token)

    # ========================================
    # LOCATIONS SUB-TAB
    # ========================================
    with semester_tab2:
        render_location_management(token)

    # ========================================
    # GENERATE SEMESTERS SUB-TAB
    # ========================================
    with semester_tab3:
        render_semester_generation(token)

    # ========================================
    # MANAGE SEMESTERS SUB-TAB
    # ========================================
    with semester_tab4:
        render_semester_management(token)
