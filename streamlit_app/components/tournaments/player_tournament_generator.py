"""
Tournament Generator Component - Admin Dashboard

Allows admins to:
1. Create one-day tournaments
2. Assign master instructors
3. View tournament status
"""
import streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, Any
import requests
from config import API_BASE_URL
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_tournaments import get_reward_policies, get_reward_policy_details, distribute_tournament_rewards


def render_tournament_generator():
    """Render tournament generator UI for admin"""
    st.header("🏆 Tournament Generator")

    # Load tournament templates
    templates = {
        "half_day": {
            "name": "Half-Day Tournament",
            "sessions": [
                {"time": "09:00", "title": "Morning Session", "duration_minutes": 90, "capacity": 20},
                {"time": "11:00", "title": "Late Morning Session", "duration_minutes": 90, "capacity": 20}
            ]
        },
        "full_day": {
            "name": "Full-Day Tournament",
            "sessions": [
                {"time": "09:00", "title": "Morning Session", "duration_minutes": 90, "capacity": 20},
                {"time": "13:00", "title": "Afternoon Session", "duration_minutes": 90, "capacity": 20},
                {"time": "16:00", "title": "Evening Session", "duration_minutes": 90, "capacity": 16}
            ]
        },
        "intensive": {
            "name": "Intensive Tournament",
            "sessions": [
                {"time": "08:00", "title": "Early Morning", "duration_minutes": 90, "capacity": 16},
                {"time": "10:00", "title": "Mid Morning", "duration_minutes": 90, "capacity": 20},
                {"time": "13:00", "title": "Afternoon", "duration_minutes": 90, "capacity": 20},
                {"time": "15:30", "title": "Late Afternoon", "duration_minutes": 90, "capacity": 16},
                {"time": "18:00", "title": "Evening Finals", "duration_minutes": 90, "capacity": 16}
            ]
        }
    }

    # Tabs for create and manage
    tab1, tab2 = st.tabs(["➕ Create Tournament", "📋 Manage Tournaments"])

    with tab1:
        _render_create_tournament_form(templates)

    with tab2:
        _render_manage_tournaments()


def _render_create_tournament_form(templates: Dict[str, Any]):
    """Render tournament creation form"""
    st.subheader("Create New Tournament")

    # ⚠️ CRITICAL FIX: Location & Campus selectors OUTSIDE the form
    # This fixes Streamlit's form state bug where selectbox values don't update properly
    st.write("**Location & Campus**")
    col1, col2 = st.columns(2)

    with col1:
        # Location selector
        locations = _get_locations()
        if locations:
            location_options = {f"{loc['name']} ({loc['city']})": loc['id'] for loc in locations}

            selected_location = st.selectbox(
                "Location *",
                options=list(location_options.keys()),
                help="Select the city/location first",
                key="tourn_location_sel"
            )
            location_id = location_options[selected_location]
            st.caption(f"Selected: {selected_location} (ID: {location_id})")
        else:
            st.error("No locations available. Please create a location first.")
            location_id = None

    with col2:
        # Campus selector (filtered by location)
        campus_id = None
        if location_id:
            campuses = _get_campuses(location_id)
            if campuses:
                campus_list = [camp['name'] for camp in campuses]
                campus_id_map = {camp['name']: camp['id'] for camp in campuses}

                selected_campus = st.selectbox(
                    "Campus *",
                    options=campus_list,
                    index=0,
                    help=f"Campus at this location ({len(campus_list)} available)",
                    key=f"tourn_campus_sel_{location_id}"
                )
                campus_id = campus_id_map[selected_campus]
                st.caption(f"Selected: {selected_campus} (ID: {campus_id})")
            else:
                st.warning(f"⚠️ No campuses at this location")
        else:
            st.info("Select a location first")

    st.divider()

    # NOW the form starts - with location_id and campus_id already selected above
    with st.form("create_tournament_form"):
        # Basic info
        col1, col2 = st.columns(2)

        with col1:
            tournament_name = st.text_input(
                "Tournament Name *",
                placeholder="e.g., Winter Football Cup",
                help="Name of the tournament"
            )

            tournament_date = st.date_input(
                "Tournament Date *",
                min_value=date.today(),
                value=date.today() + timedelta(days=1),
                help="Date when tournament takes place (1-day event)"
            )

        with col2:
            # Age group selector (LFA_FOOTBALL_PLAYER tournaments only)
            age_group = st.selectbox(
                "Age Group *",
                options=["PRE", "YOUTH", "AMATEUR", "PRO"],
                help="Player age group for tournament"
            )

        # Template or custom sessions
        st.divider()
        st.write("**Session Configuration**")

        use_template = st.checkbox("Use Template", value=True)

        sessions = []
        if use_template:
            template_choice = st.selectbox(
                "Select Template",
                options=list(templates.keys()),
                format_func=lambda x: templates[x]["name"]
            )
            sessions = templates[template_choice]["sessions"]

            # Show template preview
            st.info(f"**{templates[template_choice]['name']}** - {len(sessions)} sessions")
            for i, session in enumerate(sessions, 1):
                st.caption(f"{i}. {session['title']} - {session['time']} ({session['duration_minutes']}min, Capacity: {session['capacity']})")
        else:
            # Custom sessions builder
            num_sessions = st.number_input("Number of Sessions", min_value=1, max_value=5, value=2)

            for i in range(num_sessions):
                st.write(f"**Session {i+1}**")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    session_time = st.time_input(f"Time", key=f"time_{i}", value=None)
                with col2:
                    session_title = st.text_input(f"Title", key=f"title_{i}", value=f"Session {i+1}")
                with col3:
                    duration = st.number_input(f"Duration (min)", key=f"duration_{i}", min_value=30, max_value=180, value=90)
                with col4:
                    capacity = st.number_input(f"Capacity", key=f"capacity_{i}", min_value=4, max_value=30, value=20)

                if session_time:
                    sessions.append({
                        "time": session_time.strftime("%H:%M"),
                        "title": session_title,
                        "duration_minutes": duration,
                        "capacity": capacity
                    })

        # Game type (optional)
        st.divider()
        st.write("**Game Type (Optional)**")
        st.caption("Specify what type of game/competition this tournament is")

        game_type = st.text_input(
            "Game Type",
            placeholder="e.g., Skills Challenge, Speed Test, Tactical Match, etc.",
            max_chars=100,
            help="Leave empty for generic tournament games",
            key="tourn_game_type"
        )

        # Reward Policy Selector
        st.divider()
        st.write("**🎁 Reward Policy**")
        st.caption("Select the reward policy for this tournament (immutable after creation)")

        # Get available policies
        success, error, policies = get_reward_policies(st.session_state.get('token', ''))

        if success and policies:
            policy_names = [p['policy_name'] for p in policies]

            # Default to "default" policy
            default_index = 0
            if "default" in policy_names:
                default_index = policy_names.index("default")

            selected_policy_name = st.selectbox(
                "Reward Policy *",
                options=policy_names,
                index=default_index,
                help="Reward policy determines XP and Credits for tournament placements",
                key="reward_policy_selector"
            )

            # Show policy preview
            if selected_policy_name:
                success_detail, error_detail, policy_details = get_reward_policy_details(
                    st.session_state.get('token', ''),
                    selected_policy_name
                )

                if success_detail and policy_details:
                    st.info(f"**Policy Preview: {policy_details.get('policy_name', 'Unknown')}** (v{policy_details.get('version', 'N/A')})")

                    # Placement Rewards
                    placement = policy_details.get('placement_rewards', {})
                    if placement:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            first = placement.get('1ST', {})
                            st.caption(f"🥇 1st: {first.get('xp', 0)} XP + {first.get('credits', 0)} Credits")
                        with col2:
                            second = placement.get('2ND', {})
                            st.caption(f"🥈 2nd: {second.get('xp', 0)} XP + {second.get('credits', 0)} Credits")
                        with col3:
                            third = placement.get('3RD', {})
                            st.caption(f"🥉 3rd: {third.get('xp', 0)} XP + {third.get('credits', 0)} Credits")
                        with col4:
                            participant = placement.get('PARTICIPANT', {})
                            st.caption(f"👤 Participant: {participant.get('xp', 0)} XP + {participant.get('credits', 0)} Credits")

                    # Participation Rewards
                    participation = policy_details.get('participation_rewards', {})
                    if participation:
                        session_reward = participation.get('session_attendance', {})
                        st.caption(f"📅 Session Attendance: {session_reward.get('xp', 0)} XP + {session_reward.get('credits', 0)} Credits")
        else:
            st.warning("⚠️ Could not load reward policies. Using default policy.")
            selected_policy_name = "default"

        # Submit button
        st.divider()
        col1, col2 = st.columns([1, 3])

        with col1:
            submit = st.form_submit_button("🏆 Create Tournament", use_container_width=True)

        with col2:
            st.caption("Tournament will be created with status **SEEKING_INSTRUCTOR**. You'll need to assign a master instructor to activate it.")

    if submit:
        if not tournament_name:
            st.error("Please enter a tournament name")
            return

        if not location_id:
            st.error("Please select a location")
            return

        if not campus_id:
            st.error("Please select a campus (required to specify exact tournament location)")
            return

        if not sessions:
            st.error("Please configure at least one session")
            return

        # Add game_type to each session if provided
        if game_type:
            sessions = [
                {**session, "game_type": game_type}
                for session in sessions
            ]

        # Create tournament
        _create_tournament(
            tournament_date=tournament_date,
            name=tournament_name,
            specialization_type="LFA_FOOTBALL_PLAYER",
            campus_id=campus_id,  # ✅ NEW: Send campus instead of location
            location_id=location_id,
            age_group=age_group,
            sessions=sessions,
            reward_policy_name=selected_policy_name  # ✅ NEW: Reward policy
        )


def _create_tournament(
    tournament_date: date,
    name: str,
    specialization_type: str,
    campus_id: int,
    location_id: int,
    age_group: Optional[str],
    sessions: list,
    reward_policy_name: str = "default"
):
    """Create tournament via API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            json={
                "date": tournament_date.isoformat(),
                "name": name,
                "specialization_type": specialization_type,
                "campus_id": campus_id,  # ✅ NEW: Send campus_id
                "location_id": location_id,
                "age_group": age_group,
                "sessions": sessions,
                "auto_book_students": False,  # Never auto-book in production
                "reward_policy_name": reward_policy_name  # ✅ NEW: Reward policy
            }
        )

        if response.status_code == 201:
            data = response.json()
            st.success(f"✅ Tournament created successfully! (ID: {data['tournament_id']})")
            st.info(f"**Status:** SEEKING_INSTRUCTOR - Please assign a master instructor to activate")

            # Show summary
            summary = data.get("summary", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sessions", summary.get("session_count", 0))
            with col2:
                st.metric("Total Capacity", summary.get("total_capacity", 0))
            with col3:
                st.metric("Date", tournament_date.strftime("%Y-%m-%d"))

            # Clear form
            st.rerun()
        elif response.status_code == 409:
            st.error(f"❌ Tournament already exists for {tournament_date.strftime('%Y-%m-%d')}. Please choose a different date or delete the existing tournament first.")
        else:
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = f"HTTP {response.status_code}"
            st.error(f"❌ Error creating tournament: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def _render_manage_tournaments():
    """Render tournament management UI"""
    st.subheader("Manage Tournaments")

    # Fetch all semesters with TOURN code prefix
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            data = response.json()

            # API returns {"semesters": [...], "total": N}, so extract the list
            all_semesters = data.get("semesters", []) if isinstance(data, dict) else data

            # Filter tournaments (code starts with TOURN-)
            tournaments = [s for s in all_semesters if s.get("code", "").startswith("TOURN-")]

            if not tournaments:
                st.info("No tournaments found. Create one using the 'Create Tournament' tab.")
                return

            # Display tournaments
            for tournament in tournaments:
                _render_tournament_card(tournament)
        else:
            st.error("Failed to load tournaments")

    except Exception as e:
        st.error(f"Error loading tournaments: {str(e)}")


def _render_tournament_card(tournament: Dict[str, Any]):
    """Render a single tournament card"""
    # Get assignment request status for this tournament
    assignment_request = _get_assignment_request(tournament['id'])

    request_status_display = ""
    if assignment_request:
        status = assignment_request.get('status', 'UNKNOWN')
        if status == "PENDING":
            request_status_display = f" - 📩 Pending Request (Instructor: {assignment_request.get('instructor_id')})"
        elif status == "DECLINED":
            request_status_display = f" - ❌ Declined"
        elif status == "ACCEPTED":
            request_status_display = f" - ✅ Accepted"

    with st.expander(
        f"🏆 {tournament['name']} - {tournament.get('start_date', '')} ({tournament.get('status', 'UNKNOWN')}){request_status_display}",
        expanded=tournament.get("status") == "SEEKING_INSTRUCTOR"
    ):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**Tournament ID:** {tournament['id']}")
            st.write(f"**Code:** {tournament['code']}")
            st.write(f"**Date:** {tournament.get('start_date', 'N/A')}")
            st.write(f"**Status:** {tournament.get('status', 'UNKNOWN')}")
            st.write(f"**Specialization:** {tournament.get('specialization_type', 'N/A')}")

            # Master instructor info
            master_id = tournament.get("master_instructor_id")
            if master_id:
                st.write(f"**Master Instructor ID:** {master_id}")
            else:
                st.warning("⚠️ No master instructor assigned")

            # Reward Policy Info
            st.divider()
            st.write("**🎁 Reward Policy**")
            reward_policy_name = tournament.get('reward_policy_name', 'default')
            st.write(f"- Policy: **{reward_policy_name}**")

            # Show policy snapshot if available
            reward_snapshot = tournament.get('reward_policy_snapshot')
            if reward_snapshot:
                st.caption(f"Version: {reward_snapshot.get('version', 'N/A')}")

                # Show placement rewards in compact format
                placement = reward_snapshot.get('placement_rewards', {})
                if placement:
                    first = placement.get('1ST', {})
                    second = placement.get('2ND', {})
                    third = placement.get('3RD', {})
                    participant = placement.get('PARTICIPANT', {})

                    st.caption(f"🥇 1st: {first.get('xp', 0)} XP + {first.get('credits', 0)} Credits")
                    st.caption(f"🥈 2nd: {second.get('xp', 0)} XP + {second.get('credits', 0)} Credits")
                    st.caption(f"🥉 3rd: {third.get('xp', 0)} XP + {third.get('credits', 0)} Credits")
                    st.caption(f"👤 Participant: {participant.get('xp', 0)} XP + {participant.get('credits', 0)} Credits")
            else:
                st.caption("⚠️ No policy snapshot (legacy tournament)")

            # Assignment request info
            if assignment_request:
                st.divider()
                st.write("**Assignment Request:**")
                st.write(f"- Status: {assignment_request.get('status', 'N/A')}")
                st.write(f"- Instructor ID: {assignment_request.get('instructor_id', 'N/A')}")
                if assignment_request.get('status') == 'DECLINED' and assignment_request.get('decline_reason'):
                    st.caption(f"Decline Reason: {assignment_request['decline_reason']}")

        with col2:
            # Actions based on status
            if tournament.get("status") == "SEEKING_INSTRUCTOR":
                # Check if there's already a pending request
                if assignment_request and assignment_request.get('status') == 'PENDING':
                    st.info("📩 Waiting for instructor response...")
                    st.caption(f"Request sent to Instructor ID: {assignment_request.get('instructor_id')}")
                else:
                    st.write("**Send Instructor Request:**")

                    # Get available instructors
                    instructors = _get_instructors()

                    if instructors:
                        instructor_options = {
                            f"{i['name']} ({i['email']})": i['id']
                            for i in instructors
                        }

                        selected_instructor = st.selectbox(
                            "Select Grandmaster",
                            options=list(instructor_options.keys()),
                            key=f"instructor_select_{tournament['id']}"
                        )

                        message = st.text_area(
                            "Message (Optional)",
                            placeholder="Would you like to lead this tournament?",
                            key=f"message_{tournament['id']}"
                        )

                        if st.button("📩 Send Request", key=f"send_request_btn_{tournament['id']}"):
                            instructor_id = instructor_options[selected_instructor]
                            _send_instructor_request(tournament['id'], instructor_id, message)
                    else:
                        st.info("No instructors available")

            elif tournament.get("status") == "READY_FOR_ENROLLMENT":
                st.success("✅ Tournament is active!")
                st.caption(f"Master Instructor ID: {tournament.get('master_instructor_id')}")

            # Reward Distribution Button (Admin only - for COMPLETED tournaments)
            if tournament.get("status") == "COMPLETED":
                st.divider()
                st.write("**🎁 Reward Distribution**")

                if st.button("🎁 Distribute Rewards", key=f"distribute_rewards_btn_{tournament['id']}", use_container_width=True):
                    st.session_state['distribute_rewards_tournament_id'] = tournament['id']
                    st.session_state['distribute_rewards_tournament_name'] = tournament.get('name', 'Untitled')
                    _show_distribute_rewards_dialog()

            # Delete button
            st.divider()
            if st.button("🗑️ Delete Tournament", key=f"delete_btn_{tournament['id']}"):
                _delete_tournament(tournament['id'])


def _get_locations():
    """Fetch all locations"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/locations/",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def _get_campuses(location_id: Optional[int] = None):
    """Fetch all campuses, optionally filtered by location"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/campuses/",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            campuses = response.json()

            if location_id:
                # Filter by location
                campuses = [c for c in campuses if c.get('location_id') == location_id]
            return campuses
        return []
    except Exception as e:
        st.error(f"❌ Error fetching campuses: {str(e)}")
        return []


def _get_instructors():
    """Fetch all instructors (Grandmasters only)"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/search",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            params={
                "q": "@",  # Search for @ symbol (all emails contain @)
                "role": "instructor",  # ⚠️ CRITICAL: lowercase - API expects lowercase enum values
                "limit": 100  # Get up to 100 instructors
            }
        )

        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"❌ Error fetching instructors: {str(e)}")
        return []


def _get_assignment_request(tournament_id: int) -> Optional[Dict[str, Any]]:
    """Get assignment request for tournament"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/instructor-assignments/requests/semester/{tournament_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            requests_list = response.json()
            if requests_list:
                # Return the most recent request
                return requests_list[0]
        return None
    except:
        return None


def _send_instructor_request(tournament_id: int, instructor_id: int, message: str):
    """Send instructor assignment request"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/send-instructor-request",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            json={
                "instructor_id": instructor_id,
                "message": message if message else None
            }
        )

        if response.status_code == 201:
            st.success("✅ Instructor request sent successfully!")
            st.info("📩 Waiting for instructor response...")
            st.rerun()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            st.error(f"❌ Error: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def _delete_tournament(tournament_id: int):
    """Delete tournament"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 204:
            st.success("✅ Tournament deleted successfully!")
            st.rerun()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            st.error(f"❌ Error: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


@st.dialog("🎁 Distribute Tournament Rewards")
def _show_distribute_rewards_dialog():
    """Dialog for distributing tournament rewards with confirmation"""
    tournament_id = st.session_state.get('distribute_rewards_tournament_id')
    tournament_name = st.session_state.get('distribute_rewards_tournament_name', 'Untitled')

    st.warning(f"⚠️ Are you sure you want to distribute rewards for **{tournament_name}**?")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("**This action will:**")
    st.write("✅ Calculate final rankings based on tournament results")
    st.write("✅ Award XP and Credits to participants based on their placements")
    st.write("✅ Use the immutable reward policy snapshot from tournament creation")
    st.write("✅ Create audit trail via CreditTransaction records")

    st.divider()
    st.error("**⚠️ This action can be run multiple times, but rewards should only be distributed once!**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎁 Confirm Distribution", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            if not token:
                st.error("❌ Authentication token not found. Please log in again.")
                return

            # Call reward distribution API
            success, error, stats = distribute_tournament_rewards(token, tournament_id)

            if success:
                st.success(f"✅ Rewards distributed successfully!")
                st.balloons()

                # Show distribution statistics
                st.divider()
                st.write("**📊 Distribution Summary:**")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Participants", stats.get('total_participants', 0))
                with col2:
                    st.metric("XP Distributed", stats.get('xp_distributed', 0))
                with col3:
                    st.metric("Credits Distributed", stats.get('credits_distributed', 0))

                # Clear session state
                if 'distribute_rewards_tournament_id' in st.session_state:
                    del st.session_state['distribute_rewards_tournament_id']
                if 'distribute_rewards_tournament_name' in st.session_state:
                    del st.session_state['distribute_rewards_tournament_name']

                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ Failed to distribute rewards: {error}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'distribute_rewards_tournament_id' in st.session_state:
                del st.session_state['distribute_rewards_tournament_id']
            if 'distribute_rewards_tournament_name' in st.session_state:
                del st.session_state['distribute_rewards_tournament_name']
            st.rerun()
