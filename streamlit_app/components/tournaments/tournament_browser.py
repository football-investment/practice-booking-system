"""
Tournament Browser Component
Allows LFA Football Players to browse and enroll in worldwide tournaments
"""
import streamlit as st
from datetime import date, timedelta
from typing import Dict, Any
import time


def render_tournament_browser(token: str, user: dict):
    """
    Tournament Browser - Browse and enroll in worldwide tournaments

    Features:
    1. Filters: Age category, date range
    2. Tournament cards with details (date, location, sessions, capacity)
    3. Enrollment button with conflict warnings
    4. Credit balance check
    5. Success/error notifications
    """

    st.markdown("### 🌍 Worldwide Tournaments")
    st.caption("Browse and enroll in competitive football tournaments")

    # Get user's age category
    from utils.age_category import get_age_category_for_season
    player_age_category = get_age_category_for_season(user.get('date_of_birth'))

    # For 18+ users, get category from database
    if not player_age_category:
        import subprocess
        try:
            result = subprocess.run([
                'psql', '-U', 'postgres', '-h', 'localhost',
                '-d', 'lfa_intern_system', '-t', '-A', '-c',
                f"SELECT age_category FROM semester_enrollments WHERE user_id = {user.get('id')} AND age_category IS NOT NULL ORDER BY created_at DESC LIMIT 1;"
            ], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                player_age_category = result.stdout.strip()
        except:
            pass

    if not player_age_category:
        st.warning("⚠️ Age category not determined. Please enroll in your first tournament to set your category.")
        return

    # Determine available age filters based on player's category
    # PRE: Only PRE
    # YOUTH: YOUTH or AMATEUR (special case!)
    # AMATEUR/PRO: Only their category
    if player_age_category == "PRE":
        available_filters = ["All", "PRE"]
    elif player_age_category == "YOUTH":
        available_filters = ["All", "YOUTH", "AMATEUR"]  # Can see both!
    elif player_age_category in ["AMATEUR", "PRO"]:
        available_filters = ["All", player_age_category]
    else:
        available_filters = ["All"]

    # === FILTERS SECTION ===
    with st.expander("🔍 Filters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            # Age category filter (only show allowed categories)
            age_filter = st.selectbox(
                "Age Category",
                options=available_filters,
                index=0,  # Default to "All"
                key="tournament_age_filter"
            )

            # Show info about YOUTH special case
            if player_age_category == "YOUTH":
                st.caption("💡 As a YOUTH player, you can enroll in YOUTH or AMATEUR tournaments")

        with col2:
            # Date range filter (default: today until end of year)
            today = date.today()
            end_of_year = date(today.year, 12, 31)

            date_from = st.date_input(
                "From Date",
                value=today,
                key="tournament_date_from"
            )
            date_to = st.date_input(
                "To Date",
                value=end_of_year,
                key="tournament_date_to"
            )

    # === FETCH TOURNAMENTS ===
    from api_helpers_tournaments import get_available_tournaments

    success, error, tournaments = get_available_tournaments(
        token,
        age_group=age_filter if age_filter != "All" else None,
        start_date=date_from.isoformat(),
        end_date=date_to.isoformat()
    )

    if not success:
        st.error(f"❌ Failed to load tournaments: {error}")
        return

    if not tournaments:
        st.info("📭 No tournaments available matching your filters.")
        return

    # === TOURNAMENT CARDS ===
    st.markdown(f"**{len(tournaments)} tournament(s) found**")
    st.markdown("---")

    for tournament in tournaments:
        _render_tournament_card(tournament, token, user)


def _render_tournament_card(tournament: dict, token: str, user: dict):
    """Render single tournament card with enrollment option"""

    tournament_data = tournament['tournament']
    is_enrolled = tournament['is_enrolled']
    enrollment_count = tournament['enrollment_count']
    sessions = tournament['sessions']
    location = tournament.get('location')
    campus = tournament.get('campus')

    # Card container
    with st.container():
        # Header
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### 🏆 {tournament_data['name']}")
            st.caption(f"**{tournament_data['code']}** | {tournament_data['age_group']} Category")

        with col2:
            # Enrollment status badge
            if is_enrolled:
                st.success("✅ Enrolled")
            else:
                st.info("Available")

        # Details
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📅 Date**")
            st.write(tournament_data['start_date'])

        with col2:
            st.markdown("**📍 Location**")
            if campus:
                st.write(f"{campus['name']} - {location['city']}" if location else campus['name'])
            elif location:
                st.write(location['city'])
            else:
                st.write("TBD")

        with col3:
            st.markdown("**👥 Enrollments**")
            st.write(f"{enrollment_count} students")

        # Sessions
        if sessions:
            with st.expander(f"🏆 {len(sessions)} Game(s)", expanded=False):
                for session in sessions:
                    game_type = session.get('game_type') or 'Tournament Game'
                    # ✅ Use enrollment_count instead of session bookings
                    # (enrollment is the source of truth for tournaments)
                    st.markdown(f"""
                    - **{game_type}**
                      {session['start_time']} - {session['end_time']} |
                      {enrollment_count}/{tournament_data.get('max_players', 'N/A')} enrolled
                    """)

        # Cost (show FREE for 0 cost tournaments)
        cost = tournament_data['enrollment_cost']
        if cost == 0:
            st.markdown("**💰 Cost:** 🆓 **FREE** (0 credits)")
        else:
            st.markdown(f"**💰 Cost:** {cost} credits")

        # Enrollment button
        if is_enrolled:
            st.info("✅ You are already enrolled in this tournament.")
        else:
            if st.button(
                "📝 Enroll Now",
                key=f"enroll_{tournament_data['id']}",
                type="primary",
                use_container_width=True
            ):
                _handle_enrollment(tournament_data['id'], tournament_data, token, user)

        st.markdown("---")


def _handle_enrollment(tournament_id: int, tournament_data: dict, token: str, user: dict):
    """Handle tournament enrollment with validations and conflict warnings"""

    # Check credit balance
    from api_helpers_general import get_current_user
    success, error, fresh_user = get_current_user(token)

    if not success:
        st.error("❌ Failed to verify credit balance")
        return

    # Verify user has LFA_FOOTBALL_PLAYER license
    user_licenses = fresh_user.get('licenses', [])
    lfa_license = next(
        (lic for lic in user_licenses if lic.get('specialization_type') == 'LFA_FOOTBALL_PLAYER'),
        None
    )

    if not lfa_license:
        st.error("❌ LFA Football Player license not found")
        return

    # ✅ FIX: Backend doesn't return credit_balance in license object!
    # Use user-level credit_balance instead (from root of fresh_user)
    credit_balance = fresh_user.get('credit_balance', 0)
    enrollment_cost = tournament_data['enrollment_cost']

    if credit_balance < enrollment_cost:
        st.error(f"❌ Insufficient credits: Need {enrollment_cost}, you have {credit_balance}")
        if st.button("💰 Buy Credits", key=f"buy_credits_{tournament_id}"):
            st.switch_page("pages/My_Credits.py")
        return

    # Confirm enrollment with dialog
    @st.dialog("Confirm Tournament Enrollment")
    def confirm_enrollment():
        st.markdown(f"### 🏆 {tournament_data['name']}")
        st.markdown(f"**Date:** {tournament_data['start_date']}")
        st.markdown(f"**Age Category:** {tournament_data['age_group']}")

        # Show cost (special handling for FREE tournaments)
        if enrollment_cost == 0:
            st.markdown("**Cost:** 🆓 **FREE** (0 credits)")
            st.markdown(f"**Your Balance:** {credit_balance} credits")
            st.markdown(f"**Remaining:** {credit_balance} credits (no charge)")
        else:
            st.markdown(f"**Cost:** {enrollment_cost} credits")
            st.markdown(f"**Your Balance:** {credit_balance} credits")
            st.markdown(f"**Remaining:** {credit_balance - enrollment_cost} credits")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel", use_container_width=True, key=f"cancel_enroll_{tournament_id}"):
                st.rerun()
        with col2:
            if st.button("✅ Confirm Enrollment", type="primary", use_container_width=True, key=f"confirm_enroll_{tournament_id}"):
                # Call enrollment API
                from api_helpers_tournaments import enroll_in_tournament
                enroll_success, enroll_error, enrollment_data = enroll_in_tournament(
                    token, tournament_id
                )

                if enroll_success:
                    st.success("🎉 Successfully enrolled in tournament!")

                    # Show conflict warnings if any
                    conflicts = enrollment_data.get('conflicts', [])
                    warnings = enrollment_data.get('warnings', [])

                    if conflicts:
                        st.warning("⚠️ Schedule Conflicts Detected:")
                        for conflict in conflicts:
                            st.markdown(f"- {conflict.get('message', 'Conflict detected')}")

                    if warnings:
                        st.info("ℹ️ Warnings:")
                        for warning in warnings:
                            st.markdown(f"- {warning}")

                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ Enrollment failed: {enroll_error}")

    confirm_enrollment()
