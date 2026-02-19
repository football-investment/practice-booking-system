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
        reward_config_status = "✅ Configured" if success_data.get('reward_config_saved', False) else "⚠️ Not configured"
        st.info(f"""
        **Tournament Details:**
        - **Name:** {success_data['name']}
        - **Code:** {success_data['code']}
        - **ID:** {success_data['id']}
        - **Date:** {success_data['date']}
        - **Max Players:** {success_data['max_players']}
        - **Price:** {success_data['enrollment_cost']} credits
        - **Reward Config:** {reward_config_status}
        """)

        # Show next steps based on assignment type
        if success_data['assignment_type'] == "OPEN_ASSIGNMENT":
            st.warning("**📋 Next Steps:**\n1. Invite a specific instructor via Tournament Management\n2. Add games via ⚙️ Manage Games tab")
        else:
            st.warning("**📋 Next Steps:**\n1. Wait for instructor applications\n2. Select instructor via Tournament Management\n3. Add games via ⚙️ Manage Games tab")

        # Clear button to dismiss success message
        if st.button("✅ Got it! Create another tournament"):
            del st.session_state['tournament_created']
            if 'tournament_reward_config' in st.session_state:
                del st.session_state['tournament_reward_config']
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

    # 🎁 NEW V2: Reward Configuration Editor (OUTSIDE form for immediate UI updates)
    st.write("**🎁 Reward Configuration (V2)**")
    st.caption("Configure badges, skill points, credits, and XP multipliers for this tournament")

    # Import reward config editor
    from components.admin.reward_config_editor import render_reward_config_editor

    # Render the reward config editor with validation
    reward_config, is_valid = render_reward_config_editor(initial_config=None)

    # Store in session state for form submission
    if reward_config and is_valid:
        st.session_state['tournament_reward_config'] = reward_config
        st.session_state['tournament_reward_config_valid'] = True
    else:
        st.session_state['tournament_reward_config_valid'] = False
        if 'tournament_reward_config' in st.session_state:
            del st.session_state['tournament_reward_config']

    st.divider()

    # 🎯 Tournament Format Selector (OUTSIDE form for real-time updates)
    st.subheader("🎯 Tournament Format")
    tournament_format = st.selectbox(
        "Format *",
        options=["HEAD_TO_HEAD", "INDIVIDUAL_RANKING"],
        index=0,
        key="tournament_format_selector",
        help="INDIVIDUAL_RANKING: All players compete, ranked by result. HEAD_TO_HEAD: 1v1 matches with tournament structure."
    )

    # ============================================================================
    # INDIVIDUAL_RANKING: Scoring Configuration (OUTSIDE form for real-time updates)
    # ============================================================================
    scoring_type = "PLACEMENT"
    measurement_unit = None
    ranking_direction = None

    if tournament_format == "INDIVIDUAL_RANKING":
        st.divider()
        st.subheader("📊 Scoring Configuration")

        # Scoring Type selector
        scoring_type = st.selectbox(
            "Scoring Type *",
            options=["PLACEMENT", "TIME_BASED", "DISTANCE_BASED", "SCORE_BASED"],
            index=0,
            key="scoring_type_selector",
            help="""INDIVIDUAL_RANKING measurement types:
• PLACEMENT: Manual ranking (1st, 2nd, 3rd...)
• TIME_BASED: Timed events (100m sprint, plank hold)
• DISTANCE_BASED: Distance events (long jump, shot put)
• SCORE_BASED: Point-based events (push-ups, accuracy score)

Winner determined by Ranking Direction (ASC/DESC) configured below."""
        )

        # Measurement Unit selector (only for non-PLACEMENT)
        if scoring_type != "PLACEMENT":
            unit_options = {
                'TIME_BASED': ['seconds', 'minutes', 'hours'],
                'DISTANCE_BASED': ['meters', 'centimeters', 'kilometers'],
                'SCORE_BASED': ['points', 'repetitions', 'goals']
            }

            available_units = unit_options.get(scoring_type, [])
            measurement_unit = st.selectbox(
                "Measurement Unit *",
                options=available_units,
                index=0,
                key="measurement_unit_selector",
                help=f"Select the unit for measuring {scoring_type.replace('_', ' ').lower()} results"
            )

            # Ranking Direction selector
            ranking_direction = st.selectbox(
                "Winner Determination *",
                options=["ASC", "DESC"],
                index=1,  # Default to DESC
                key="ranking_direction_selector",
                format_func=lambda x: "ASC (Lowest wins)" if x == "ASC" else "DESC (Highest wins)",
                help="ASC: Lowest value wins (e.g., 100m sprint). DESC: Highest value wins (e.g., plank hold)"
            )

            # Show example based on selection
            if ranking_direction == "ASC":
                st.caption("⬇️ **Lowest wins**: 10.5s beats 11.2s, 4.8m loses to 4.2m")
            else:
                st.caption("⬆️ **Highest wins**: 120s beats 90s, 5.2m beats 4.8m")
        else:
            st.caption("🏆 **Manual ranking** (1st place beats 2nd place)")
            measurement_unit = None
            ranking_direction = None

    st.divider()

    # ============================================================================
    # 🎮 GAME PRESET SELECTOR + SKILL PREVIEW
    # OUTSIDE the form so the preview updates immediately on preset selection.
    # ============================================================================
    st.subheader("🎮 Game Preset")
    st.caption(
        "Select a game preset to automatically configure which skills this tournament develops. "
        "The preset's skill weights are converted to reactivity multipliers — dominant skills "
        "produce proportionally larger skill changes after the tournament."
    )

    def _fetch_game_presets(token: str) -> list:
        """Fetch active game presets from API."""
        try:
            resp = requests.get(
                f"{API_BASE_URL}/api/v1/game-presets/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                # Handle both list and paginated response shapes
                if isinstance(data, list):
                    return data
                return data.get("presets", data.get("items", []))
        except Exception:
            pass
        return []

    presets = _fetch_game_presets(st.session_state.get("token", ""))

    preset_options = {"— None (use manual skills_to_test) —": None}
    for p in presets:
        if p.get("is_active", True):
            label = f"{p['name']} (id={p['id']})"
            preset_options[label] = p

    selected_preset_label = st.selectbox(
        "Game Preset",
        options=list(preset_options.keys()),
        key="game_preset_selector",
        help="Selecting a preset auto-populates skill mappings with the preset's weights."
    )
    selected_preset = preset_options[selected_preset_label]

    # Store for form submission
    st.session_state["selected_game_preset"] = selected_preset

    if selected_preset:
        game_cfg = selected_preset.get("game_config", {})
        skill_cfg = game_cfg.get("skill_config", {})
        skills_tested: list = skill_cfg.get("skills_tested", [])
        skill_weights: dict = skill_cfg.get("skill_weights", {})

        if skills_tested:
            st.success(
                f"✅ **{selected_preset['name']}** — {len(skills_tested)} skill"
                f"{'s' if len(skills_tested) != 1 else ''} will be developed automatically"
            )

            if skill_weights:
                avg_w = sum(skill_weights.values()) / len(skill_weights)
                preview_rows = []
                for sk in skills_tested:
                    frac = skill_weights.get(sk, avg_w)
                    reactivity = round(max(0.1, min(5.0, frac / avg_w)), 2)
                    bar_pct = int(min(100, reactivity * 50))   # reactivity=1.0 → 50% bar

                    if reactivity > 1.05:
                        icon = "🔴"
                        label_str = f"Dominant ({reactivity:.2f}×)"
                    elif reactivity < 0.95:
                        icon = "🔵"
                        label_str = f"Supporting ({reactivity:.2f}×)"
                    else:
                        icon = "⚪"
                        label_str = f"Balanced ({reactivity:.2f}×)"

                    preview_rows.append((icon, sk.replace("_", " ").title(), label_str, bar_pct, frac))

                # Sort: dominant first
                preview_rows.sort(key=lambda r: r[3], reverse=True)

                col_skill, col_role, col_bar = st.columns([2, 2, 3])
                col_skill.markdown("**Skill**")
                col_role.markdown("**Role**")
                col_bar.markdown("**Reactivity** (vs average)")

                for icon, sk_display, label_str, bar_pct, frac in preview_rows:
                    col_skill.write(f"{icon} {sk_display}")
                    col_role.write(label_str)
                    col_bar.progress(bar_pct, text=f"{frac:.0%} of game")

                st.caption(
                    "🔴 Dominant = larger skill delta after tournament  "
                    "🔵 Supporting = smaller delta  "
                    "⚪ Balanced = average impact"
                )
            else:
                # No weights — show simple list
                st.info(
                    "Skills will be mapped with equal weight (1.0×): "
                    + ", ".join(f"**{sk}**" for sk in skills_tested)
                )
        else:
            st.warning(
                f"⚠️ Preset **{selected_preset['name']}** has no `skill_config.skills_tested` "
                "defined yet. Skill auto-sync will not occur — use `skills_to_test` manually."
            )
    else:
        st.info(
            "No preset selected. Skill mappings will be created from the "
            "`skills_to_test` field (uniform weight = 1.0 each)."
        )

    st.divider()

    # NOW the form starts - with location_id, campus_id, and reward policy already selected above
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
            # Enrollment Cost with Free option
            is_free = st.checkbox(
                "🆓 Free Tournament",
                value=False,
                key="is_free_tournament",
                help="Check this to make the tournament free (0 credits)"
            )

            if is_free:
                enrollment_cost = 0
                st.info("💎 Price: **FREE** (0 credits)")
            else:
                enrollment_cost = st.number_input(
                    "Price (Credits) *",
                    min_value=1,
                    value=500,
                    step=50,
                    key="enrollment_cost_input",
                    help="Enrollment fee in credits"
                )


        # ⚠️ BUSINESS LOGIC: Sessions can be auto-generated OR configured manually
        # ============================================================================
        # HEAD_TO_HEAD: Tournament Type Configuration
        # ============================================================================
        selected_tournament_type = None

        if tournament_format == "HEAD_TO_HEAD":
            st.divider()
            st.subheader("🏆 Tournament Type Configuration")

            # Fetch tournament types
            success, error, tournament_types = get_tournament_types(st.session_state.token)

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

        # 🔒 VALIDATION GUARD: Check skill selection
        if not st.session_state.get('tournament_reward_config_valid', False):
            st.error("⚠️ **Skill Selection Required**: You must select at least 1 skill for this tournament. Scroll up to the Skill Selection section.")
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
            # 🎁 V2: reward_policy_name still used for legacy compatibility
            reward_policy_name="default",
            # 🎯 NEW: Domain gap resolution fields
            assignment_type=assignment_type,
            max_players=max_players,
            enrollment_cost=enrollment_cost,
            # 🎯 NEW: Tournament format and type
            format=tournament_format,
            tournament_type_id=selected_tournament_type['id'] if selected_tournament_type else None,
            # 🎯 NEW: INDIVIDUAL_RANKING scoring configuration
            scoring_type=scoring_type,
            measurement_unit=measurement_unit,
            ranking_direction=ranking_direction
        )


def _create_tournament(
    tournament_date: date,
    name: str,
    specialization_type: str,
    campus_id: int,
    location_id: int,
    age_group: Optional[str],
    # 🎁 V2: reward_policy_name kept for legacy compatibility
    reward_policy_name: str = "default",
    # 🎯 NEW: Domain gap resolution fields
    assignment_type: str = "APPLICATION_BASED",
    max_players: int = 20,
    enrollment_cost: int = 500,
    # 🎯 NEW: Tournament format and type
    format: str = "HEAD_TO_HEAD",
    tournament_type_id: Optional[int] = None,
    # 🎯 NEW: INDIVIDUAL_RANKING scoring configuration
    scoring_type: str = "PLACEMENT",
    measurement_unit: Optional[str] = None,
    ranking_direction: Optional[str] = None
):
    """
    Create tournament via API

    BUSINESS LOGIC:
    - Instructor assignment happens AFTER creation via Tournament Management
    - Sessions can be auto-generated (if tournament_type_id provided) OR manually configured
    """
    try:
        request_body = {
            "date": tournament_date.isoformat(),
            "name": name,
            "specialization_type": specialization_type,
            "campus_id": campus_id,
            "location_id": location_id,
            "age_group": age_group,
            # ⚠️ BUSINESS LOGIC: Sessions added later via Tournament Management
            "sessions": [],
            "auto_book_students": False,
            # 🎁 V2: reward_policy_name kept for legacy compatibility
            "reward_policy_name": reward_policy_name,
            # 🎯 NEW: Domain gap resolution fields
            "assignment_type": assignment_type,
            "max_players": max_players,
            "enrollment_cost": enrollment_cost,
            # 🎯 NEW: Tournament format and type
            "format": format,
            "tournament_type_id": tournament_type_id,
            # 🎯 NEW: INDIVIDUAL_RANKING scoring configuration
            "scoring_type": scoring_type,
            "measurement_unit": measurement_unit,
            "ranking_direction": ranking_direction,
            # ⚠️ BUSINESS LOGIC: instructor_id is None at creation
            # Instructor assignment happens AFTER via Tournament Management:
            # - OPEN_ASSIGNMENT: Admin invites specific instructor
            # - APPLICATION_BASED: Instructors apply, admin selects
            "instructor_id": None
        }

        # 🔍 DEBUG: Show request payload
        st.write("**🔍 DEBUG: Tournament Creation Request**")
        st.json(request_body)

        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            json=request_body
        )

        # 🔍 DEBUG: Show response status
        st.write(f"**🔍 DEBUG: Response Status Code:** {response.status_code}")

        if response.status_code == 201:
            data = response.json()
            tournament_id = data['tournament_id']
            tournament_code = data.get('tournament_code', 'N/A')

            # 🎁 V2: Save reward config if provided
            reward_config_saved = False
            if 'tournament_reward_config' in st.session_state:
                from api_helpers_tournaments import save_tournament_reward_config

                reward_config = st.session_state['tournament_reward_config']
                config_dict = reward_config.model_dump(mode="json")

                success_config, error_config, saved_config = save_tournament_reward_config(
                    st.session_state.token,
                    tournament_id,
                    config_dict
                )

                if success_config:
                    reward_config_saved = True
                    st.success("✅ Reward configuration saved successfully!")
                else:
                    st.warning(f"⚠️ Tournament created but reward config failed: {error_config}")

            # Store success message in session state to persist across rerun
            st.session_state['tournament_created'] = {
                'id': tournament_id,
                'code': tournament_code,
                'name': name,
                'date': tournament_date.strftime("%Y-%m-%d"),
                'assignment_type': assignment_type,
                'max_players': max_players,
                'enrollment_cost': enrollment_cost,
                'reward_config_saved': reward_config_saved
            }

            # Rerun to show success message
            st.rerun()
        elif response.status_code == 409:
            st.error(f"❌ Tournament already exists for {tournament_date.strftime('%Y-%m-%d')}. Please choose a different date or delete the existing tournament first.")
            # 🔍 DEBUG: Show full error response
            try:
                st.write("**🔍 DEBUG: Full Error Response**")
                st.json(response.json())
            except:
                st.write(f"**🔍 DEBUG: Raw Response:** {response.text}")
        else:
            try:
                error_detail = response.json().get("detail", "Unknown error")
                # 🔍 DEBUG: Show full error response
                st.write("**🔍 DEBUG: Full Error Response**")
                st.json(response.json())
            except:
                error_detail = f"HTTP {response.status_code}"
                st.write(f"**🔍 DEBUG: Raw Response:** {response.text}")
            st.error(f"❌ Error creating tournament: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.write(f"**🔍 DEBUG: Exception Type:** {type(e).__name__}")
        st.write(f"**🔍 DEBUG: Exception Details:** {repr(e)}")


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
    """Dialog for distributing tournament rewards with confirmation (V2 - Unified System)"""
    tournament_id = st.session_state.get('distribute_rewards_tournament_id')
    tournament_name = st.session_state.get('distribute_rewards_tournament_name', 'Untitled')

    st.warning(f"⚠️ Are you sure you want to distribute rewards for **{tournament_name}**?")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("**This action will:**")
    st.write("✅ Calculate final rankings based on tournament results")
    st.write("✅ Award Skill Points based on placement and tournament mappings")
    st.write("✅ Award XP (Base + Bonus from skill points) and Credits")
    st.write("✅ Award visual Achievement Badges (placement + participation + milestones)")
    st.write("✅ Create audit trail via transactions")

    st.divider()
    st.info("**🔒 Idempotent:** Safe to call multiple times - won't duplicate rewards if already distributed.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎁 Confirm Distribution", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            if not token:
                st.error("❌ Authentication token not found. Please log in again.")
                return

            # Import V2 API helper
            from api_helpers_tournaments import distribute_tournament_rewards_v2

            # Call V2 reward distribution API
            success, error, result = distribute_tournament_rewards_v2(
                token,
                tournament_id,
                force_redistribution=False  # Idempotent mode
            )

            if success:
                # Check if this was a new distribution or idempotent call
                rewards_count = result.get('rewards_distributed_count', 0)
                summary = result.get('summary', {})

                if rewards_count == 0:
                    # Already distributed - show info message (NO animation)
                    st.info(f"ℹ️ Rewards were already distributed for **{tournament_name}**.")
                    st.write("**Previously distributed rewards:**")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("👥 Total Participants", result.get('total_participants', 0))
                    with col2:
                        st.metric("⭐ Total XP", summary.get('total_xp_awarded', 0))
                    with col3:
                        st.metric("💰 Total Credits", summary.get('total_credits_awarded', 0))

                    if 'total_badges_awarded' in summary:
                        st.metric("🏆 Badges Awarded", summary['total_badges_awarded'])

                else:
                    # New distribution - show success message + animation
                    st.success(f"✅ Rewards distributed successfully to {rewards_count} participants!")
                    st.balloons()

                    # Show distribution statistics
                    st.divider()
                    st.write("**📊 Distribution Summary:**")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("👥 Participants Rewarded", rewards_count)
                    with col2:
                        st.metric("⭐ Total XP", summary.get('total_xp_awarded', 0))
                    with col3:
                        st.metric("💰 Total Credits", summary.get('total_credits_awarded', 0))
                    with col4:
                        st.metric("🏆 Badges Awarded", summary.get('total_badges_awarded', 0))

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
