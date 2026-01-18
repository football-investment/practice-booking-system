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

from api_helpers_tournaments import (
    get_reward_policies,
    get_reward_policy_details,
    distribute_tournament_rewards,
    get_tournament_types,
    estimate_tournament_duration
)


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

    # Only show tournament creation form
    # Tournament management is handled in the "📋 View Tournaments" main tab
    st.info("ℹ️ **After creating a tournament**, manage it in the **📋 View Tournaments** tab")
    st.divider()
    _render_create_tournament_form(templates)


def _render_create_tournament_form(templates: Dict[str, Any]):
    """Render tournament creation form"""
    st.subheader("Create New Tournament")

    # ✅ SUCCESS MESSAGE DISPLAY (persists after rerun)
    if 'tournament_created' in st.session_state:
        success_data = st.session_state['tournament_created']

        st.success(f"✅ **Tournament created successfully!**")

        # Show tournament details
        st.info(f"""
        **Tournament Details:**
        - **Name:** {success_data['name']}
        - **Code:** {success_data['code']}
        - **ID:** {success_data['id']}
        - **Date:** {success_data['date']}
        - **Max Players:** {success_data['max_players']}
        - **Price:** {success_data['enrollment_cost']} credits
        """)

        # Show next steps based on assignment type
        if success_data['assignment_type'] == "OPEN_ASSIGNMENT":
            st.warning("**📋 Next Steps:**\n1. Invite a specific instructor via Tournament Management\n2. Add games via ⚙️ Manage Games tab")
        else:
            st.warning("**📋 Next Steps:**\n1. Wait for instructor applications\n2. Select instructor via Tournament Management\n3. Add games via ⚙️ Manage Games tab")

        # Clear button to dismiss success message
        if st.button("✅ Got it! Create another tournament"):
            del st.session_state['tournament_created']
            st.rerun()

        st.divider()

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
            # Get selected location data by location_id to build tournament name
            selected_location_data = None
            if location_id and locations:
                selected_location_data = next((loc for loc in locations if loc['id'] == location_id), None)

            # Build location display part (flag + country code + location code)
            location_prefix = ""
            if selected_location_data:
                country_code = selected_location_data.get('country_code', '')
                location_code_str = selected_location_data.get('location_code', '')
                if country_code and location_code_str:
                    # Generate flag emoji
                    flag = chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397) if len(country_code) == 2 else "🌍"
                    location_prefix = f"{flag} {country_code} - "

            tournament_custom_name = st.text_input(
                "Tournament Name *",
                placeholder="e.g., Winter Football Cup",
                key="tournament_name_input",
                help="Custom name for the tournament (will be prefixed with location)"
            )

            # Show auto-generated full name preview
            if tournament_custom_name and location_prefix and selected_location_data:
                location_code_display = selected_location_data.get('location_code', '')
                full_tournament_name = f"{location_prefix}\"{tournament_custom_name}\" - {location_code_display}"
                st.caption(f"**Full name:** {full_tournament_name}")
            else:
                full_tournament_name = tournament_custom_name  # Fallback if location codes not available

            tournament_date = st.date_input(
                "Tournament Date *",
                min_value=date.today(),
                value=date.today() + timedelta(days=1),
                key="tournament_date_input",
                help="Date when tournament takes place (1-day event)"
            )

        with col2:
            # Age group selector (LFA_FOOTBALL_PLAYER tournaments only)
            age_group = st.selectbox(
                "Age Group *",
                options=["PRE", "YOUTH", "AMATEUR", "PRO"],
                key="age_group_selector",
                help="Player age group for tournament"
            )

        # 🎯 NEW: Tournament Assignment & Capacity
        st.divider()
        st.write("**🎯 Tournament Configuration**")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Assignment Type
            assignment_type = st.selectbox(
                "Assignment Type *",
                options=["OPEN_ASSIGNMENT", "APPLICATION_BASED"],
                key="assignment_type_selector",
                help="OPEN: Admin invites specific instructor. APPLICATION: Instructors apply, admin selects."
            )

        with col2:
            # Max Players
            max_players = st.number_input(
                "Max Players *",
                min_value=1,
                max_value=100,
                value=20,
                key="max_players_input",
                help="Maximum tournament participants (explicit capacity)"
            )

        with col3:
            # Enrollment Cost
            enrollment_cost = st.number_input(
                "Price (Credits) *",
                min_value=0,
                value=500,
                step=50,
                key="enrollment_cost_input",
                help="Enrollment fee in credits"
            )


        # ⚠️ BUSINESS LOGIC: Sessions can be auto-generated OR configured manually
        # 🎯 Tournament Type Selector (NEW - PHASE 3)
        st.divider()
        st.subheader("🎯 Tournament Type Configuration")

        # Fetch tournament types
        success, error, tournament_types = get_tournament_types(st.session_state.token)

        selected_tournament_type = None  # Initialize

        if success and tournament_types:
            # Add "None (Manual Setup)" option
            type_options = ["None (Manual Configuration)"] + [
                f"{tt['display_name']} ({tt['code']})"
                for tt in tournament_types
            ]

            selected_type_display = st.selectbox(
                "Tournament Type",
                options=type_options,
                key="tournament_type_selector",
                help="Select a tournament type for automatic session generation, or choose Manual Configuration to add sessions later"
            )

            # Parse selected tournament type
            if selected_type_display == "None (Manual Configuration)":
                selected_tournament_type = None
                st.info("📋 **Sessions will be configured manually** in Tournament Management after creation.")
            else:
                # Find matching tournament type
                selected_tournament_type = next(
                    (tt for tt in tournament_types
                     if f"{tt['display_name']} ({tt['code']})" == selected_type_display),
                    None
                )

                if selected_tournament_type:
                    # Show tournament type details
                    st.success(f"✅ Selected: **{selected_tournament_type['display_name']}**")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"**Min Players:** {selected_tournament_type['min_players']}")
                        if selected_tournament_type['max_players']:
                            st.caption(f"**Max Players:** {selected_tournament_type['max_players']}")
                        else:
                            st.caption(f"**Max Players:** Unlimited")

                    with col2:
                        if selected_tournament_type['requires_power_of_two']:
                            st.caption("⚠️ **Requires power-of-2 players** (4, 8, 16, 32, 64)")

                    # Show duration estimate if max_players is set
                    if max_players >= selected_tournament_type['min_players']:
                        # Estimate tournament duration
                        est_success, est_error, estimate = estimate_tournament_duration(
                            st.session_state.token,
                            selected_tournament_type['id'],
                            max_players,
                            parallel_fields=1  # Default to 1 field
                        )

                        if est_success:
                            st.info(
                                f"📊 **Estimated Duration:** {estimate['total_matches']} matches, "
                                f"{estimate['total_rounds']} rounds, "
                                f"~{estimate['estimated_duration_minutes']} minutes "
                                f"({estimate['estimated_duration_days']:.2f} days with 1 field)"
                            )
                        else:
                            st.warning(f"⚠️ Could not estimate duration: {est_error}")
                    else:
                        st.warning(
                            f"⚠️ Max players ({max_players}) is below minimum required "
                            f"({selected_tournament_type['min_players']}) for this tournament type"
                        )

                    st.info("🔄 **Sessions will be auto-generated** after enrollment closes (when tournament status changes to IN_PROGRESS)")
        else:
            st.error(f"❌ Failed to load tournament types: {error}")
            selected_tournament_type = None
            st.info("📋 **Sessions will be configured manually** in Tournament Management after creation.")

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

        submit = st.form_submit_button("🏆 Create Tournament", use_container_width=True, type="primary", key="create_tournament_submit")

    if submit:
        if not tournament_custom_name:
            st.error("Please enter a tournament name")
            return

        if not location_id:
            st.error("Please select a location")
            return

        if not campus_id:
            st.error("Please select a campus (required to specify exact tournament location)")
            return

        # Rebuild full_tournament_name in case it wasn't set earlier
        if not full_tournament_name or full_tournament_name == tournament_custom_name:
            selected_location_data = next((loc for loc in locations if loc['id'] == location_id), None) if locations and location_id else None
            if selected_location_data:
                country_code = selected_location_data.get('country_code', '')
                location_code = selected_location_data.get('location_code', '')
                if country_code and location_code:
                    flag = chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397) if len(country_code) == 2 else "🌍"
                    full_tournament_name = f"{flag} {country_code} - \"{tournament_custom_name}\" - {location_code}"
                else:
                    full_tournament_name = tournament_custom_name
            else:
                full_tournament_name = tournament_custom_name

        # Create tournament
        # ⚠️ BUSINESS LOGIC: Instructor assignment happens AFTER creation via Tournament Management
        # - OPEN_ASSIGNMENT: Admin invites specific instructor (via invitation flow)
        # - APPLICATION_BASED: Instructors apply, admin selects one
        _create_tournament(
            tournament_date=tournament_date,
            name=full_tournament_name,
            specialization_type="LFA_FOOTBALL_PLAYER",
            campus_id=campus_id,
            location_id=location_id,
            age_group=age_group,
            reward_policy_name=selected_policy_name,
            # 🎯 NEW: Domain gap resolution fields
            assignment_type=assignment_type,
            max_players=max_players,
            enrollment_cost=enrollment_cost,
            # 🎯 NEW PHASE 3: Tournament type for auto-generation
            tournament_type_id=selected_tournament_type['id'] if selected_tournament_type else None
        )


def _create_tournament(
    tournament_date: date,
    name: str,
    specialization_type: str,
    campus_id: int,
    location_id: int,
    age_group: Optional[str],
    reward_policy_name: str = "default",
    # 🎯 NEW: Domain gap resolution fields
    assignment_type: str = "APPLICATION_BASED",
    max_players: int = 20,
    enrollment_cost: int = 500,
    # 🎯 NEW PHASE 3: Tournament type for auto-generation
    tournament_type_id: Optional[int] = None
):
    """
    Create tournament via API

    BUSINESS LOGIC:
    - Instructor assignment happens AFTER creation via Tournament Management
    - Sessions can be auto-generated (if tournament_type_id provided) OR manually configured
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            json={
                "date": tournament_date.isoformat(),
                "name": name,
                "specialization_type": specialization_type,
                "campus_id": campus_id,
                "location_id": location_id,
                "age_group": age_group,
                # ⚠️ BUSINESS LOGIC: Sessions added later via Tournament Management
                "sessions": [],
                "auto_book_students": False,
                "reward_policy_name": reward_policy_name,
                # 🎯 NEW: Domain gap resolution fields
                "assignment_type": assignment_type,
                "max_players": max_players,
                "enrollment_cost": enrollment_cost,
                # 🎯 NEW PHASE 3: Tournament type for auto-generation
                "tournament_type_id": tournament_type_id,
                # ⚠️ BUSINESS LOGIC: instructor_id is None at creation
                # Instructor assignment happens AFTER via Tournament Management:
                # - OPEN_ASSIGNMENT: Admin invites specific instructor
                # - APPLICATION_BASED: Instructors apply, admin selects
                "instructor_id": None
            }
        )

        if response.status_code == 201:
            data = response.json()
            tournament_id = data['tournament_id']
            tournament_code = data.get('tournament_code', 'N/A')

            # Store success message in session state to persist across rerun
            st.session_state['tournament_created'] = {
                'id': tournament_id,
                'code': tournament_code,
                'name': name,
                'date': tournament_date.strftime("%Y-%m-%d"),
                'assignment_type': assignment_type,
                'max_players': max_players,
                'enrollment_cost': enrollment_cost
            }

            # Rerun to show success message
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


# Tournament management functions removed - now handled in tournaments_tab.py
# Use the "📋 View Tournaments" main tab for all tournament management operations


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


# Instructor management functions removed - now handled in tournaments_tab.py


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
