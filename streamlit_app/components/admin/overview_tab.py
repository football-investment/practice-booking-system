"""
Admin Dashboard - Overview Tab Component
Location-based overview with semesters and sessions
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime
from collections import defaultdict

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers import get_locations, get_semesters, get_campuses_by_location, get_sessions
from api_helpers_financial import get_financial_summary


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


def render_overview_tab(token, user):
    """
    Render the Overview tab with location-based dashboard.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    # Main layout with sidebar filters
    filter_col, main_col = st.columns([1, 3])

    # Load locations first
    with st.spinner("Loading locations..."):
        success_loc, all_locations = get_locations(token, include_inactive=False)
        # DEBUG: Show what we received from API
        st.write(f"🔍 DEBUG: API returned {len(all_locations) if all_locations else 0} locations")
        if all_locations:
            for loc in all_locations:
                st.write(f"  - ID {loc.get('id')}: {loc.get('city')}, {loc.get('country', 'N/A')}")

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
        # ── Financial snapshot ────────────────────────────────────
        ok_fin, fin = get_financial_summary(token)
        if ok_fin and fin:
            rev  = fin.get("revenue",  {})
            cred = fin.get("credits",  {})
            inv  = fin.get("invoices", {})

            st.markdown("#### 💶 Financial Snapshot")
            f1, f2, f3, f4, f5 = st.columns(5)
            with f1:
                st.metric("Total Revenue", f"€{rev.get('total_eur', 0):,.0f}")
            with f2:
                pending_eur = rev.get("pending_eur", 0)
                st.metric(
                    "Pending",
                    f"€{pending_eur:,.0f}",
                    delta=f"−€{pending_eur:,.0f}" if pending_eur else None,
                    delta_color="inverse",
                )
            with f3:
                st.metric("Issued Credits", f"{rev.get('total_credits_sold', 0):,} cr")
            with f4:
                st.metric("Active Balance", f"{cred.get('active_balance', 0):,} cr")
            with f5:
                pending_inv = inv.get("pending", 0)
                st.metric(
                    "Open Invoices",
                    pending_inv,
                    delta=f"−{pending_inv}" if pending_inv else None,
                    delta_color="inverse",
                )
            st.divider()

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

                st.markdown("#### 📚 All Semesters by Specialization")

                # Group semesters by specialization
                spec_semesters = defaultdict(list)

                for sem in all_semesters:
                    if sem.get('is_active'):
                        spec_type = sem.get('specialization_type') or 'Unknown'
                        spec_semesters[spec_type].append(sem)

                if spec_semesters:
                    for spec_type, semesters in spec_semesters.items():
                        with st.expander(f"⚽ {spec_type.replace('_', ' ').title()} ({len(semesters)} semesters)"):
                            # Header row
                            header_cols = st.columns([3, 2, 1.5, 1.2, 1.5, 0.8])
                            with header_cols[0]:
                                st.markdown("**Semester Name**")
                            with header_cols[1]:
                                st.markdown("**Dates**")
                            with header_cols[2]:
                                st.markdown("**Status**")
                            with header_cols[3]:
                                st.markdown("**Location**")
                            with header_cols[4]:
                                st.markdown("**Campus**")
                            with header_cols[5]:
                                st.markdown("**ID**")

                            st.divider()

                            for sem in semesters:
                                # Status badge colors
                                status = sem.get('status', 'UNKNOWN')
                                if status == 'DRAFT':
                                    status_badge = "🔵 DRAFT"
                                elif status == 'INSTRUCTOR_ASSIGNED':
                                    status_badge = "🟡 INSTRUCTOR ASSIGNED"
                                elif status == 'READY_FOR_ENROLLMENT':
                                    status_badge = "🟢 READY"
                                elif status == 'ONGOING':
                                    status_badge = "🟢 ONGOING"
                                else:
                                    status_badge = f"⚪ {status}"

                                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1.5, 1.2, 1.5, 0.8])
                                with col1:
                                    st.caption(f"{sem.get('name', 'N/A')}")
                                with col2:
                                    st.caption(f"📅 {sem.get('start_date', 'N/A')} → {sem.get('end_date', 'N/A')}")
                                with col3:
                                    st.caption(status_badge)
                                with col4:
                                    st.caption(f"📍 {sem.get('location_city', 'N/A')}")
                                with col5:
                                    st.caption(f"🏟️ {sem.get('location_venue', 'N/A')}")
                                with col6:
                                    st.caption(f"#{sem.get('id')}")
                else:
                    st.info("No semesters found for this location")

            st.divider()

            # Load campuses and sessions for this location
            st.markdown("#### 🏫 Campuses & Sessions")

            campus_success, campuses = get_campuses_by_location(token, selected_location_id, include_inactive=False)

            if campus_success and campuses:
                # Load all sessions
                with st.spinner("Loading sessions..."):
                    success_sess, all_sessions = get_sessions(token, size=100, specialization_filter=False)

                # Group sessions by campus
                now = datetime.now()

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
                    with st.expander(f"🏫 **{campus_name}** - {len(campus_sessions)} sessions ({len(upcoming)} upcoming, {len(past)} past)", expanded=False):
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
