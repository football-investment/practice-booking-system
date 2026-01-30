"""
Streamlit Instructor Workflow Sandbox
Test instructor features (attendance + results submission + live leaderboard) as admin user
"""
import streamlit as st
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"

# Page config
st.set_page_config(
    page_title="Instructor Workflow Sandbox",
    page_icon="👨‍🏫",
    layout="wide"
)

def login(email: str, password: str) -> Optional[str]:
    """Login and return token"""
    try:
        response = requests.post(LOGIN_ENDPOINT, json={"email": email, "password": password})
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def fetch_tournaments(token: str) -> List[Dict]:
    """Fetch available tournaments for instructor"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Get semesters (tournaments) where user is instructor
        response = requests.get(f"{API_BASE_URL}/semesters/", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch tournaments: {e}")
        return []

def fetch_session_schedule(token: str, tournament_id: int) -> List[Dict]:
    """Fetch session schedule for tournament"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_BASE_URL}/sessions/semester/{tournament_id}", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch sessions: {e}")
        return []

def fetch_participants(token: str, tournament_id: int) -> List[Dict]:
    """Fetch enrolled participants for tournament"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_BASE_URL}/semester-enrollments/semesters/{tournament_id}/enrollments", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch participants: {e}")
        return []

def submit_attendance(token: str, session_id: int, attendance_data: List[Dict]) -> bool:
    """Submit attendance for a session"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{API_BASE_URL}/attendance/sessions/{session_id}/bulk",
            json={"attendance_records": attendance_data},
            headers=headers
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Failed to submit attendance: {e}")
        return False

def submit_results(token: str, session_id: int, results_data: List[Dict]) -> bool:
    """Submit performance results for a session"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/submit-results",
            json={"results": results_data},
            headers=headers
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Failed to submit results: {e}")
        return False

def fetch_leaderboard(token: str, tournament_id: int) -> Dict:
    """Fetch live leaderboard for tournament"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch leaderboard: {e}")
        return {}

# Screens
def render_login_screen():
    """Login screen"""
    st.title("👨‍🏫 Instructor Workflow Sandbox")
    st.markdown("### 🔐 Admin Login")

    st.info("💡 **Test instructor features as admin user**")

    col1, col2 = st.columns([2, 1])
    with col1:
        email = st.text_input("Admin Email", value="admin@lfa.com")
        password = st.text_input("Password", value="admin123", type="password")

    if st.button("🔓 Login", type="primary"):
        token = login(email, password)
        if token:
            st.session_state.token = token
            st.session_state.email = email
            st.session_state.screen = "tournament_selection"
            st.success("✅ Login successful!")
            st.rerun()

def render_tournament_selection():
    """Tournament selection screen"""
    st.title("👨‍🏫 Instructor Workflow Sandbox")
    st.markdown(f"### 📋 Select Tournament")
    st.markdown(f"**Logged in as**: {st.session_state.email}")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")

    # Fetch tournaments
    tournaments = fetch_tournaments(st.session_state.token)

    if not tournaments:
        st.warning("⚠️ No tournaments found. Create a tournament first!")
        return

    # Display tournaments
    st.markdown("#### 🏆 Available Tournaments")

    for tournament in tournaments:
        with st.expander(f"🏆 {tournament.get('name', 'Unknown')} (ID: {tournament.get('id')})"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Status", tournament.get('tournament_status', 'Unknown'))
            with col2:
                st.metric("Type", tournament.get('tournament_type_id', 'N/A'))
            with col3:
                st.metric("Max Players", tournament.get('max_players', 0))

            if st.button(f"📝 Manage This Tournament", key=f"select_{tournament.get('id')}"):
                st.session_state.selected_tournament = tournament
                st.session_state.screen = "instructor_dashboard"
                st.rerun()

def render_instructor_dashboard():
    """Main instructor dashboard (attendance + results + leaderboard)"""
    tournament = st.session_state.selected_tournament
    tournament_id = tournament.get('id')

    st.title(f"👨‍🏫 Instructor Dashboard: {tournament.get('name')}")

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**Tournament ID**: {tournament_id} | **Status**: {tournament.get('tournament_status')}")
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.screen = "tournament_selection"
            st.rerun()

    st.markdown("---")

    # Tabs for workflow steps
    tab1, tab2, tab3 = st.tabs(["📋 Attendance", "🎯 Results Submission", "🏆 Live Leaderboard"])

    with tab1:
        render_attendance_tab(tournament_id)

    with tab2:
        render_results_tab(tournament_id)

    with tab3:
        render_leaderboard_tab(tournament_id)

def render_attendance_tab(tournament_id: int):
    """Attendance tracking interface"""
    st.markdown("### 📋 Mark Attendance")

    # Fetch sessions
    sessions = fetch_session_schedule(st.session_state.token, tournament_id)

    if not sessions:
        st.warning("⚠️ No sessions found for this tournament")
        return

    # Select session
    session_options = {f"Session {s.get('id')} - {s.get('scheduled_date', 'N/A')}": s.get('id') for s in sessions}
    selected_session_name = st.selectbox("Select Session", list(session_options.keys()))
    selected_session_id = session_options[selected_session_name]

    st.markdown("---")

    # Fetch participants
    participants = fetch_participants(st.session_state.token, tournament_id)

    if not participants:
        st.warning("⚠️ No participants enrolled in this tournament")
        return

    st.markdown(f"#### ✅ Mark Attendance (Session {selected_session_id})")

    # Attendance form
    attendance_records = []

    for participant in participants:
        user_id = participant.get('user_id')
        username = participant.get('user', {}).get('email', 'Unknown')

        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.write(f"👤 {username}")

        with col2:
            status = st.selectbox(
                "Status",
                ["PRESENT", "ABSENT", "LATE", "EXCUSED"],
                key=f"attendance_status_{user_id}",
                label_visibility="collapsed"
            )

        with col3:
            notes = st.text_input(
                "Notes",
                key=f"attendance_notes_{user_id}",
                placeholder="Optional notes...",
                label_visibility="collapsed"
            )

        attendance_records.append({
            "user_id": user_id,
            "status": status,
            "notes": notes if notes else None
        })

    st.markdown("---")

    if st.button("💾 Submit Attendance", type="primary"):
        with st.spinner("Submitting attendance..."):
            success = submit_attendance(st.session_state.token, selected_session_id, attendance_records)
            if success:
                st.success("✅ Attendance submitted successfully!")
                time.sleep(1)
                st.rerun()

def render_results_tab(tournament_id: int):
    """Results submission interface"""
    st.markdown("### 🎯 Submit Performance Results")

    # Fetch sessions
    sessions = fetch_session_schedule(st.session_state.token, tournament_id)

    if not sessions:
        st.warning("⚠️ No sessions found for this tournament")
        return

    # Select session
    session_options = {f"Session {s.get('id')} - {s.get('scheduled_date', 'N/A')}": s.get('id') for s in sessions}
    selected_session_name = st.selectbox("Select Session", list(session_options.keys()), key="results_session")
    selected_session_id = session_options[selected_session_name]

    st.markdown("---")

    # Fetch participants
    participants = fetch_participants(st.session_state.token, tournament_id)

    if not participants:
        st.warning("⚠️ No participants enrolled in this tournament")
        return

    st.markdown(f"#### 🎯 Enter Results (Session {selected_session_id})")

    # Results form
    results_records = []

    for participant in participants:
        user_id = participant.get('user_id')
        username = participant.get('user', {}).get('email', 'Unknown')

        with st.expander(f"👤 {username}"):
            col1, col2 = st.columns(2)

            with col1:
                score = st.number_input(
                    "Score/Points",
                    min_value=0.0,
                    max_value=100.0,
                    value=50.0,
                    step=1.0,
                    key=f"result_score_{user_id}"
                )

            with col2:
                rank = st.number_input(
                    "Rank",
                    min_value=1,
                    max_value=len(participants),
                    value=1,
                    step=1,
                    key=f"result_rank_{user_id}"
                )

            notes = st.text_area(
                "Performance Notes",
                key=f"result_notes_{user_id}",
                placeholder="Optional performance notes..."
            )

            results_records.append({
                "user_id": user_id,
                "score": score,
                "rank": rank,
                "notes": notes if notes else None
            })

    st.markdown("---")

    if st.button("💾 Submit Results", type="primary"):
        with st.spinner("Submitting results..."):
            success = submit_results(st.session_state.token, selected_session_id, results_records)
            if success:
                st.success("✅ Results submitted successfully!")
                time.sleep(1)
                st.rerun()

def render_leaderboard_tab(tournament_id: int):
    """Live leaderboard display"""
    st.markdown("### 🏆 Live Leaderboard")

    # Auto-refresh toggle
    auto_refresh = st.toggle("🔄 Auto-refresh (5s)", value=False)

    if st.button("🔄 Refresh Now") or auto_refresh:
        if auto_refresh:
            time.sleep(5)
            st.rerun()

    # Fetch leaderboard
    leaderboard_data = fetch_leaderboard(st.session_state.token, tournament_id)

    if not leaderboard_data:
        st.warning("⚠️ No leaderboard data available yet")
        return

    # Display leaderboard
    st.markdown("---")

    # Extract leaderboard entries
    entries = leaderboard_data.get('leaderboard', [])

    if not entries:
        st.info("ℹ️ No entries in leaderboard yet. Submit some results first!")
        return

    # Create DataFrame
    leaderboard_df = pd.DataFrame([
        {
            "Rank": f"#{entry.get('rank', 'N/A')}",
            "Player": entry.get('username', 'Unknown'),
            "Points": entry.get('points', 0),
            "Wins": entry.get('wins', 0),
            "Losses": entry.get('losses', 0),
        }
        for entry in entries
    ])

    # Display table
    st.dataframe(
        leaderboard_df,
        hide_index=True,
        use_container_width=True,
        height=400
    )

    # Top 3 highlight
    st.markdown("#### 🥇 Top 3 Performers")
    col1, col2, col3 = st.columns(3)

    if len(entries) >= 1:
        with col1:
            st.metric(
                "🥇 1st Place",
                entries[0].get('username', 'Unknown'),
                f"{entries[0].get('points', 0)} pts"
            )

    if len(entries) >= 2:
        with col2:
            st.metric(
                "🥈 2nd Place",
                entries[1].get('username', 'Unknown'),
                f"{entries[1].get('points', 0)} pts"
            )

    if len(entries) >= 3:
        with col3:
            st.metric(
                "🥉 3rd Place",
                entries[2].get('username', 'Unknown'),
                f"{entries[2].get('points', 0)} pts"
            )

# Main app
def main():
    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "login"

    # Route to screens
    if st.session_state.screen == "login":
        render_login_screen()
    elif st.session_state.screen == "tournament_selection":
        render_tournament_selection()
    elif st.session_state.screen == "instructor_dashboard":
        render_instructor_dashboard()

if __name__ == "__main__":
    main()
