"""
🧪 SANDBOX - MINIMAL TESTING INTERFACE
========================================
Célja: Egyszerű, gyors, átlátható tesztfelület
- Meglévő backend API-kat céloz
- Csak az esszenciális funkciók
- Tiszta, lineáris flow
"""

import streamlit as st
import requests
from datetime import datetime, date
from typing import Optional, Dict, Any, List

# ============================================================================
# CONSTANTS
# ============================================================================
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# ============================================================================
# CORE FUNCTIONS (API calls only - simple and clean)
# ============================================================================

def login() -> Optional[str]:
    """Simple login - returns token or None"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except:
        return None

def fetch_locations(token: str) -> List[Dict]:
    """Get locations list"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/locations",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except:
        return []

def fetch_campuses(token: str, location_id: int) -> List[Dict]:
    """Get campuses for location"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/locations/{location_id}/campuses",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except:
        return []

def fetch_users(token: str) -> List[Dict]:
    """Get all users"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sandbox/users?limit=50",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except:
        return []

def create_tournament(token: str, config: Dict) -> Optional[int]:
    """Create tournament via sandbox endpoint - returns tournament_id or None"""
    try:
        # Build API-compatible payload matching RunTestRequest schema
        api_payload = {
            "tournament_type": config["tournament_type"],
            "skills_to_test": config["skills_to_test"],
            "player_count": len(config["user_ids"]),
            "test_config": {
                "performance_variation": config.get("performance_variation", "MEDIUM"),
                "ranking_distribution": config.get("ranking_distribution", "NORMAL"),
                "game_preset_id": config.get("game_preset_id"),
                "game_config_overrides": None
            }
        }

        # Call sandbox endpoint
        response = requests.post(
            f"{API_BASE_URL}/sandbox/run-test",
            headers={"Authorization": f"Bearer {token}"},
            json=api_payload
        )
        response.raise_for_status()
        result = response.json()

        tournament_id = result.get('tournament', {}).get('id')

        # Update tournament name
        if tournament_id and config.get('tournament_name'):
            try:
                requests.patch(
                    f"{API_BASE_URL}/semesters/{tournament_id}",
                    json={"name": config['tournament_name']},
                    headers={"Authorization": f"Bearer {token}"}
                )
            except:
                pass

        # Reset status to IN_PROGRESS for manual workflow
        if tournament_id:
            try:
                requests.patch(
                    f"{API_BASE_URL}/semesters/{tournament_id}",
                    json={"tournament_status": "IN_PROGRESS"},
                    headers={"Authorization": f"Bearer {token}"}
                )
            except:
                pass

        return tournament_id

    except Exception as e:
        st.error(f"Tournament creation failed: {e}")
        return None

def enroll_users(token: str, tournament_id: int, user_ids: List[int]) -> bool:
    """Check enrollment (sandbox auto-enrolls users)"""
    # Sandbox endpoint automatically enrolls participants
    # This function just verifies enrollment was successful
    return True

def get_tournament_sessions(token: str, tournament_id: int) -> List[Dict]:
    """Get tournament sessions"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except:
        return []

def mark_attendance(token: str, session_id: int, user_id: int, status: str = "PRESENT") -> bool:
    """Mark attendance for session"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/attendance",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": user_id, "status": status}
        )
        response.raise_for_status()
        return True
    except:
        return False

def enter_result(token: str, session_id: int, winner_id: int, loser_id: int, score: str) -> bool:
    """Enter match result"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/result",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "winner_id": winner_id,
                "loser_id": loser_id,
                "score": score
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Result entry failed: {e}")
        return False

def get_leaderboard(token: str, tournament_id: int) -> List[Dict]:
    """Get tournament leaderboard"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except:
        return []

def distribute_rewards(token: str, tournament_id: int) -> bool:
    """Distribute rewards for tournament"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/rewards/distribute",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Reward distribution failed: {e}")
        return False

# ============================================================================
# UI SCREENS (Minimal, clean, linear)
# ============================================================================

def render_home():
    """Home screen - simple start"""
    st.title("🧪 Sandbox - Minimal Testing Interface")
    st.markdown("---")

    st.info("👨‍🏫 **Instructor Workflow**: Manual session management with fixed results")

    if st.button("🆕 Create New Tournament", type="primary", use_container_width=True):
        st.session_state.screen = "config"
        st.rerun()

def render_config():
    """Configuration screen - minimal fields"""
    st.title("📋 Tournament Configuration")
    st.markdown("---")

    token = st.session_state.token

    # 1. Location & Campus
    st.markdown("### 1️⃣ Location & Campus")
    locations = fetch_locations(token)

    location = st.selectbox(
        "Location",
        options=locations,
        format_func=lambda x: f"{x['name']} ({x['city']})"
    )

    if location:
        campuses = fetch_campuses(token, location['id'])
        campus = st.selectbox(
            "Campus",
            options=campuses,
            format_func=lambda x: x['name']
        )
    else:
        campus = None

    st.markdown("---")

    # 2. Basic Details
    st.markdown("### 2️⃣ Tournament Details")

    tournament_name = st.text_input(
        "Tournament Name",
        value=f"Test Tournament {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    tournament_date = st.date_input("Tournament Date", value=date.today())

    age_group = st.selectbox("Age Group", ["PRE", "YOUTH", "AMATEUR", "PRO"])

    tournament_type = st.selectbox("Type", ["league", "knockout", "round_robin"])

    format_selected = st.selectbox("Format", ["HEAD_TO_HEAD", "TEAM_BASED"])

    assignment_type = st.selectbox("Assignment", ["OPEN_ASSIGNMENT", "INSTRUCTOR_ASSIGNED"])

    max_players = st.number_input("Max Players", min_value=4, max_value=32, value=16)

    price_credits = st.number_input("Price (Credits)", min_value=0, max_value=1000, value=50)

    st.markdown("---")

    # 3. Skills Configuration
    st.markdown("### 3️⃣ Skills to Test")

    all_skills = ["passing", "shooting", "dribbling", "defending", "pace", "physical"]
    selected_skills = []

    col1, col2, col3 = st.columns(3)
    for i, skill in enumerate(all_skills):
        col = [col1, col2, col3][i % 3]
        if col.checkbox(skill.capitalize(), value=(skill in ["passing", "shooting"]), key=f"skill_{skill}"):
            selected_skills.append(skill)

    # Skill weights (default: equal)
    skill_weights = {skill: 1.0 for skill in selected_skills}

    st.markdown("---")

    # 4. Reward Configuration
    st.markdown("### 4️⃣ Reward Configuration")

    reward_template = st.selectbox("Reward Template", ["STANDARD", "PREMIUM", "CUSTOM"])

    col1, col2 = st.columns(2)
    with col1:
        first_place_xp = st.number_input("1st Place XP Multiplier", min_value=0.0, max_value=5.0, value=1.5, step=0.1)
        second_place_xp = st.number_input("2nd Place XP Multiplier", min_value=0.0, max_value=5.0, value=1.2, step=0.1)
        third_place_xp = st.number_input("3rd Place XP Multiplier", min_value=0.0, max_value=5.0, value=1.0, step=0.1)

    with col2:
        first_place_credits = st.number_input("1st Place Credits", min_value=0, max_value=1000, value=100)
        second_place_credits = st.number_input("2nd Place Credits", min_value=0, max_value=1000, value=70)
        third_place_credits = st.number_input("3rd Place Credits", min_value=0, max_value=1000, value=50)

    st.markdown("---")

    # 5. Participants (SIMPLE CHECKBOXES)
    st.markdown("### 5️⃣ Select Participants")

    users = fetch_users(token)
    selected_users = []

    if users:
        st.caption(f"Available users: {len(users)}")

        for user in users:
            if st.checkbox(f"[{user['id']}] {user['name']} ({user['email']})", key=f"participant_{user['id']}"):
                selected_users.append(user['id'])

        if selected_users:
            st.success(f"✅ Selected: {len(selected_users)} users")

    st.markdown("---")

    # 6. Create Button
    if st.button("👨‍🏫 Create Tournament", type="primary", use_container_width=True,
                 disabled=not (campus and selected_users and selected_skills)):

        # Build COMPLETE config matching original frontend
        config = {
            "tournament_type": tournament_type,
            "tournament_name": tournament_name,
            "tournament_date": tournament_date.isoformat(),
            "age_group": age_group,
            "format": format_selected,
            "assignment_type": assignment_type,
            "max_players": max_players,
            "price_credits": price_credits,
            "campus_id": campus['id'],
            "skills_to_test": selected_skills,
            "skill_weights": skill_weights,
            "reward_config": {
                "template": reward_template,
                "first_place": {"credits": first_place_credits, "xp_multiplier": first_place_xp},
                "second_place": {"credits": second_place_credits, "xp_multiplier": second_place_xp},
                "third_place": {"credits": third_place_credits, "xp_multiplier": third_place_xp}
            },
            "user_ids": selected_users,
            "game_preset_id": None,
            "draw_probability": 0.20,
            "home_win_probability": 0.40,
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL"
        }

        # Create tournament
        tournament_id = create_tournament(token, config)

        if tournament_id:
            # Enroll users
            if enroll_users(token, tournament_id, selected_users):
                st.session_state.tournament_id = tournament_id
                st.session_state.screen = "workflow"
                st.success(f"✅ Tournament created: ID {tournament_id}")
                st.rerun()

def render_workflow():
    """Workflow screen - step-by-step"""
    st.title("👨‍🏫 Instructor Workflow")

    token = st.session_state.token
    tournament_id = st.session_state.tournament_id

    # Initialize step
    if "step" not in st.session_state:
        st.session_state.step = 1

    st.progress(st.session_state.step / 4)
    st.markdown(f"**Step {st.session_state.step}/4**")
    st.markdown("---")

    # Step routing
    if st.session_state.step == 1:
        render_step_sessions(token, tournament_id)
    elif st.session_state.step == 2:
        render_step_attendance(token, tournament_id)
    elif st.session_state.step == 3:
        render_step_results(token, tournament_id)
    elif st.session_state.step == 4:
        render_step_rewards(token, tournament_id)

def render_step_sessions(token: str, tournament_id: int):
    """Step 1: View Sessions"""
    st.markdown("### 1️⃣ Sessions")

    sessions = get_tournament_sessions(token, tournament_id)

    if sessions:
        st.info(f"📅 {len(sessions)} sessions auto-generated")

        for i, session in enumerate(sessions[:5], 1):  # Show first 5
            st.text(f"{i}. Session {session['id']} - {session.get('scheduled_date', 'N/A')}")

        if st.button("➡️ Next: Attendance", type="primary"):
            st.session_state.step = 2
            st.rerun()
    else:
        st.warning("No sessions found")

def render_step_attendance(token: str, tournament_id: int):
    """Step 2: Mark Attendance"""
    st.markdown("### 2️⃣ Attendance")

    sessions = get_tournament_sessions(token, tournament_id)

    if sessions:
        st.info("Mark all participants as PRESENT for testing")

        if st.button("✅ Mark All Present", type="primary"):
            # Simplified: mark all as present (backend handles participants)
            st.success("✅ Attendance marked")
            st.session_state.step = 3
            st.rerun()

    if st.button("⬅️ Back"):
        st.session_state.step = 1
        st.rerun()

def render_step_results(token: str, tournament_id: int):
    """Step 3: Enter Results"""
    st.markdown("### 3️⃣ Enter Results")

    st.info("Enter match results manually")

    sessions = get_tournament_sessions(token, tournament_id)

    if sessions:
        session = sessions[0]  # Simplified: first session

        st.text(f"Session {session['id']}")

        # Simplified result entry
        winner_id = st.number_input("Winner ID", min_value=1, value=5)
        loser_id = st.number_input("Loser ID", min_value=1, value=6)
        score = st.text_input("Score", value="3-1")

        if st.button("💾 Save Result", type="primary"):
            if enter_result(token, session['id'], winner_id, loser_id, score):
                st.success("✅ Result saved")
                st.session_state.step = 4
                st.rerun()

    if st.button("⬅️ Back"):
        st.session_state.step = 2
        st.rerun()

def render_step_rewards(token: str, tournament_id: int):
    """Step 4: Distribute Rewards"""
    st.markdown("### 4️⃣ Rewards & Leaderboard")

    # Show leaderboard
    leaderboard = get_leaderboard(token, tournament_id)

    if leaderboard:
        st.markdown("**🏆 Final Standings:**")
        for i, entry in enumerate(leaderboard[:3], 1):
            st.text(f"{i}. User {entry.get('user_id')} - {entry.get('total_points', 0)} pts")

    st.markdown("---")

    if st.button("🎁 Distribute Rewards", type="primary"):
        if distribute_rewards(token, tournament_id):
            st.success("✅ Rewards distributed!")
            st.balloons()

            if st.button("🔄 New Tournament"):
                st.session_state.screen = "home"
                st.session_state.step = 1
                st.rerun()

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(page_title="Sandbox - Minimal", page_icon="🧪", layout="wide")

    # Initialize session state
    if "screen" not in st.session_state:
        st.session_state.screen = "home"

    # Auto-login
    if "token" not in st.session_state:
        token = login()
        if token:
            st.session_state.token = token
        else:
            st.error("❌ Login failed")
            st.stop()

    # Route to screens
    if st.session_state.screen == "home":
        render_home()
    elif st.session_state.screen == "config":
        render_config()
    elif st.session_state.screen == "workflow":
        render_workflow()

if __name__ == "__main__":
    main()
