"""
Instructor Dashboard — Tab 1: Today & Upcoming
===============================================

Phase 3 extraction Step 3.5.
Renders the time-sensitive landing view: today's sessions and the next-7-day schedule.
Shared session data comes from DashboardData; pending-offers count is fetched inline
(same as the original monolith — one lightweight list call).

Public API:
    render_today_tab(data, token, today, next_week)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import TYPE_CHECKING

import streamlit as st

from api_helpers_instructors import get_my_master_offers

if TYPE_CHECKING:
    from components.instructor.data_loader import DashboardData


def render_today_tab(
    data: "DashboardData",
    token: str,
    today: date,
    next_week: date,
) -> None:
    """Render the 'Today & Upcoming' tab content.

    Args:
        data:      Shared dashboard data snapshot from load_dashboard_data().
        token:     Bearer JWT — needed for the pending-offers count metric.
        today:     Current date (date object).
        next_week: Date 7 days from today (date object).
    """
    st.markdown("### 📆 Today & Upcoming")
    st.caption("Time-sensitive sessions - what needs your attention NOW")

    # Quick Stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric("📅 Today", len(data.todays_sessions))
    with stats_col2:
        st.metric("📅 This Week", len(data.upcoming_sessions))
    with stats_col3:
        try:
            pending_offers = get_my_master_offers(token, include_expired=False)
            pending_offers_count = len([o for o in pending_offers if o.get('status') == 'PENDING'])
        except Exception:
            pending_offers_count = 0
        pending_actions = pending_offers_count
        st.metric("🎯 Pending Actions", pending_actions)

    st.divider()

    # TODAY'S SESSIONS
    if data.todays_sessions:
        st.markdown("### 🚨 TODAY'S SESSIONS")

        for session in data.todays_sessions:
            semester_data = session.get('semester', {})

            try:
                start_dt = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                time_str = start_dt.strftime('%H:%M')
            except Exception:
                time_str = 'N/A'

            title = session.get('title', 'Session')
            capacity = session.get('capacity', 0)
            bookings = session.get('confirmed_bookings', 0)
            semester_name = semester_data.get('name', 'Unknown')

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

    if data.upcoming_sessions:
        sessions_by_day = defaultdict(list)
        for s in data.upcoming_sessions:
            try:
                session_date = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date()
                sessions_by_day[session_date].append(s)
            except Exception:
                pass

        for day in sorted(sessions_by_day.keys()):
            day_sessions = sessions_by_day[day]
            day_name = day.strftime('%A, %B %d')
            is_today = (day == today)

            with st.expander(
                f"**{day_name}** ({len(day_sessions)} sessions)" + (" ⚠️ TODAY" if is_today else ""),
                expanded=is_today
            ):
                for session in sorted(day_sessions, key=lambda x: x.get('date_start', '')):
                    semester_data = session.get('semester', {})

                    try:
                        start_dt = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                        time_str = start_dt.strftime('%H:%M')
                    except Exception:
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

        if data.all_sessions:
            future_sessions = []
            for s in data.all_sessions:
                try:
                    session_date = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date()
                    if session_date > next_week:
                        future_sessions.append((session_date, s))
                except Exception:
                    pass

            if future_sessions:
                future_sessions.sort(key=lambda x: x[0])
                next_session_date, next_session = future_sessions[0]
                st.caption(
                    f"📅 Next session: {next_session_date.strftime('%A, %B %d')} "
                    f"- {next_session.get('title', 'Session')}"
                )

    # ACTION REQUIRED section
    if pending_actions > 0:
        st.divider()
        st.markdown("### ⚠️ ACTION REQUIRED")
        st.warning(
            f"You have **{pending_actions}** pending action(s) in the **📬 Inbox** tab"
        )
        if st.button("Go to Inbox →", use_container_width=True):
            st.session_state['active_tab'] = 'Inbox'
            st.rerun()
