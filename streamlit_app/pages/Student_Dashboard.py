"""
Student Dashboard
REBUILT from unified_workflow_dashboard.py (WORKING!)
EXACT API patterns + EXACT UI/UX patterns
"""

import streamlit as st
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, SPECIALIZATIONS
from api_helpers import get_sessions
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title=f"{PAGE_TITLE} - Student Dashboard",
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Apply CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Check authentication
if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("❌ Not authenticated. Please login first.")
    st.stop()

# Check student role
user = st.session_state[SESSION_USER_KEY]
if user.get('role') != 'student':
    st.error("❌ Access denied. Student role required.")
    st.stop()

# Get token
token = st.session_state[SESSION_TOKEN_KEY]

# Header
st.title("🎓 Student Dashboard")
st.caption("LFA Education Center - Student Interface")

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Student')}!")
    st.caption(f"Role: **Student**")
    st.caption(f"Email: {user.get('email', 'N/A')}")

    spec = user.get('specialization')
    if spec:
        st.caption(f"Specialization: {SPECIALIZATIONS.get(spec, spec)}")

    st.markdown("---")

    # Credits display
    st.markdown("**💰 My Credits**")
    st.metric("Credit Balance", user.get('credit_balance', 0))

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("🏠_Home.py")

# Main tabs
tab1, tab2 = st.tabs(["📅 Available Sessions", "📚 My Bookings"])

# ========================================
# TAB 1: AVAILABLE SESSIONS
# ========================================
with tab1:
    st.markdown("### 📅 Available Sessions")
    st.caption("Browse and book training sessions")

    with st.spinner("Loading available sessions..."):
        # Get sessions with specialization filter (student sees their specialization)
        success, sessions = get_sessions(token, size=100, specialization_filter=True)

    if success and sessions:
        # Filter only upcoming sessions
        now = datetime.now()
        upcoming_sessions = []
        for s in sessions:
            try:
                start_time = datetime.fromisoformat(s.get('start_time', '').replace('Z', '+00:00'))
                if start_time > now:
                    upcoming_sessions.append(s)
            except:
                pass

        if upcoming_sessions:
            # WORKING DASHBOARD PATTERN: Metric widget
            st.metric("🔜 Upcoming Sessions", len(upcoming_sessions))

            st.divider()

            # WORKING DASHBOARD PATTERN: Expandable cards
            for session in upcoming_sessions:
                try:
                    start_time = datetime.fromisoformat(session.get('start_time', '').replace('Z', '+00:00'))

                    title = session.get('title', 'Untitled Session')
                    session_type = session.get('session_type', 'N/A')
                    max_participants = session.get('max_participants', 0)
                    current_participants = len(session.get('bookings', []))

                    # Availability check
                    is_full = current_participants >= max_participants
                    availability_icon = "❌" if is_full else "✅"

                    with st.expander(f"{availability_icon} **{title}** ({session_type}) - {start_time.strftime('%Y-%m-%d %H:%M')}"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**📋 Session Info**")
                            st.caption(f"ID: {session.get('id')}")
                            st.caption(f"Title: {session.get('title', 'N/A')}")
                            st.caption(f"Type: {session.get('session_type', 'N/A')}")

                        with col2:
                            st.markdown("**📅 When**")
                            st.caption(f"Date: {start_time.strftime('%Y-%m-%d')}")
                            st.caption(f"Time: {start_time.strftime('%H:%M')}")
                            end_time = datetime.fromisoformat(session.get('end_time', '').replace('Z', '+00:00'))
                            st.caption(f"Duration: {int((end_time - start_time).seconds / 60)} min")

                        with col3:
                            st.markdown("**👥 Availability**")
                            st.metric("Spots", f"{current_participants}/{max_participants}")
                            if is_full:
                                st.warning("Session is full")
                            else:
                                st.success(f"{max_participants - current_participants} spots left")

                        st.divider()

                        # Book button
                        if not is_full:
                            if st.button("📝 Book This Session", key=f"book_{session.get('id')}", use_container_width=True):
                                st.info("Booking functionality coming soon!")
                        else:
                            st.button("❌ Full", key=f"full_{session.get('id')}", disabled=True, use_container_width=True)
                except:
                    pass  # Skip sessions with invalid datetime

        else:
            st.info("No upcoming sessions available in your specialization")
    else:
        st.error("❌ Failed to load sessions")

# ========================================
# TAB 2: MY BOOKINGS
# ========================================
with tab2:
    st.markdown("### 📚 My Bookings")
    st.caption("Your booked sessions")

    # TODO: Implement get_my_bookings API call
    st.info("My bookings functionality coming soon!")

    st.markdown("""
    **Features to be implemented:**
    - ✅ View all your booked sessions
    - ✅ Cancel bookings
    - ✅ View attendance history
    - ✅ Download certificates
    """)
