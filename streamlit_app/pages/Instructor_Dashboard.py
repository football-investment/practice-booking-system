"""
Instructor Dashboard
REBUILT from unified_workflow_dashboard.py (WORKING!)
EXACT API patterns + EXACT UI/UX patterns
"""

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, SPECIALIZATIONS
from api_helpers import get_sessions, get_users
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Instructor Dashboard",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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

# Header
st.title("👨‍🏫 Instructor Dashboard")
st.caption("LFA Education Center - Instructor Interface")

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Instructor')}!")
    st.caption(f"Role: **Instructor**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("🏠_Home.py")

# Main tabs
tab1, tab2 = st.tabs(["📅 My Sessions", "👥 My Students"])

# ========================================
# TAB 1: MY SESSIONS
# ========================================
with tab1:
    st.markdown("### 📅 My Sessions")
    st.caption("Sessions you are teaching")

    with st.spinner("Loading your sessions..."):
        # Get sessions with specialization filter (instructor sees only their specialization)
        success, sessions = get_sessions(token, size=100, specialization_filter=True)

    if success and sessions:
        # WORKING DASHBOARD PATTERN: Metric widgets for session stats
        stats_col1, stats_col2, stats_col3 = st.columns(3)

        now = datetime.now()
        upcoming_sessions = [s for s in sessions if datetime.fromisoformat(s.get('start_time', '').replace('Z', '+00:00')) > now]
        past_sessions = [s for s in sessions if datetime.fromisoformat(s.get('start_time', '').replace('Z', '+00:00')) <= now]

        with stats_col1:
            st.metric("📚 Total Sessions", len(sessions))
        with stats_col2:
            st.metric("🔜 Upcoming", len(upcoming_sessions))
        with stats_col3:
            st.metric("✅ Completed", len(past_sessions))

        st.divider()

        # WORKING DASHBOARD PATTERN: Expandable cards with session details
        for session in sessions:
            try:
                start_time = datetime.fromisoformat(session.get('start_time', '').replace('Z', '+00:00'))
                is_upcoming = start_time > now
                time_icon = "🔜" if is_upcoming else "✅"

                title = session.get('title', 'Untitled Session')
                session_type = session.get('session_type', 'N/A')

                with st.expander(f"{time_icon} **{title}** ({session_type}) - {start_time.strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**📋 Session Info**")
                        st.caption(f"ID: {session.get('id')}")
                        st.caption(f"Title: {session.get('title', 'N/A')}")
                        st.caption(f"Type: {session.get('session_type', 'N/A')}")

                    with col2:
                        st.markdown("**📅 Schedule**")
                        st.caption(f"Start: {start_time.strftime('%Y-%m-%d %H:%M')}")
                        end_time = datetime.fromisoformat(session.get('end_time', '').replace('Z', '+00:00'))
                        st.caption(f"End: {end_time.strftime('%Y-%m-%d %H:%M')}")
                        st.caption(f"Duration: {int((end_time - start_time).seconds / 60)} min")

                    with col3:
                        st.markdown("**👥 Participants**")
                        max_participants = session.get('max_participants', 0)
                        current_participants = len(session.get('bookings', []))
                        st.metric("Bookings", f"{current_participants}/{max_participants}")
            except:
                pass  # Skip sessions with invalid datetime

    elif success and not sessions:
        st.info("No sessions assigned to you yet")
    else:
        st.error("❌ Failed to load sessions")

# ========================================
# TAB 2: MY STUDENTS
# ========================================
with tab2:
    st.markdown("### 👥 My Students")
    st.caption("Students in your sessions")

    with st.spinner("Loading students..."):
        # Get all users and filter students
        success, users = get_users(token, limit=100)

    if success and users:
        # Filter only students
        students = [u for u in users if u.get("role") == "student"]

        if students:
            # WORKING DASHBOARD PATTERN: Metric widgets
            stats_col1, stats_col2 = st.columns(2)

            active_students = len([s for s in students if s.get("is_active")])

            with stats_col1:
                st.metric("🎓 Total Students", len(students))
            with stats_col2:
                st.metric("✅ Active", active_students)

            st.divider()

            # WORKING DASHBOARD PATTERN: Expandable cards
            for student in students:
                status_icon = "✅" if student.get('is_active') else "❌"

                with st.expander(f"🎓 **{student.get('name', 'Unknown')}** ({student.get('email', 'N/A')}) {status_icon}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**📋 Basic Info**")
                        st.caption(f"ID: {student.get('id')}")
                        st.caption(f"Email: {student.get('email', 'N/A')}")
                        st.caption(f"Name: {student.get('name', 'N/A')}")

                    with col2:
                        st.markdown("**🎓 Academic Info**")
                        spec = student.get('specialization')
                        st.caption(f"Specialization: {SPECIALIZATIONS.get(spec, spec) if spec else 'None'}")
                        st.caption(f"Status: {'✅ Active' if student.get('is_active') else '❌ Inactive'}")

                    with col3:
                        st.markdown("**💰 Credits**")
                        st.metric("Credit Balance", student.get('credit_balance', 0))
        else:
            st.info("No students found")
    else:
        st.error("❌ Failed to load students")
