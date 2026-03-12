"""
Admin Dashboard - Sessions Tab Component
Sessions management with hierarchical organization
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers import get_sessions, get_locations, get_semesters
from components.session_filters import render_session_filters, apply_session_filters
from components.session_actions import render_session_action_buttons


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


def render_sessions_tab(token, user):
    """
    Render the Sessions tab with hierarchical session organization.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    # Main layout with sidebar filters
    filter_col, main_col = st.columns([1, 3])

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
