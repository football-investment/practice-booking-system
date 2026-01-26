"""
Tournament Creation Module - Enrollment and rewards
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Dict
import requests
import time

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from config import API_BASE_URL, API_TIMEOUT


def render_reward_distribution_section(token: str, tournament: Dict):
    """
    Render reward distribution section for COMPLETED tournaments (V2 - Unified System).

    Shows:
    - Tournament completion status
    - Reward distribution button
    - Distribution results with skill points, XP breakdown, and badges
    """
    from api_helpers_tournaments import distribute_tournament_rewards_v2

    tournament_id = tournament.get('id')
    tournament_name = tournament.get('name', 'Unknown')

    st.subheader("🎁 Reward Distribution (V2)")

    # Check if rewards already distributed
    reward_policy = tournament.get('reward_policy_snapshot')
    if reward_policy:
        st.success("✅ **Reward policy configured**")
        st.caption(f"Policy: {reward_policy.get('name', 'Unknown')}")
    else:
        st.warning("⚠️ **No reward policy configured for this tournament**")
        st.caption("Rewards cannot be distributed without a configured policy.")
        return

    st.divider()

    # Distribute Rewards button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "🎁 Distribute Rewards (V2)",
            key=f"distribute_{tournament_id}",
            use_container_width=True,
            type="primary",
            help="Distribute skill points, XP, credits, and achievement badges"
        ):
            # Call V2 distribute rewards endpoint
            try:
                with st.spinner("Distributing rewards..."):
                    success, error, result = distribute_tournament_rewards_v2(
                        token,
                        tournament_id,
                        force_redistribution=False  # Idempotent mode
                    )

                    if success and result.get('success'):
                        rewards_count = result.get('rewards_distributed_count', 0)
                        summary = result.get('summary', {})

                        if rewards_count == 0:
                            # Already distributed - show info (NO animation)
                            st.info(f"ℹ️ **Rewards were already distributed for {tournament_name}**")
                            st.caption("Previously distributed rewards:")

                            col_a, col_b, col_c, col_d = st.columns(4)
                            with col_a:
                                st.metric("👥 Participants", result.get('total_participants', 0))
                            with col_b:
                                st.metric("⭐ Total XP", summary.get('total_xp_awarded', 0))
                            with col_c:
                                st.metric("💰 Total Credits", summary.get('total_credits_awarded', 0))
                            with col_d:
                                st.metric("🏆 Badges", summary.get('total_badges_awarded', 0))

                        else:
                            # New distribution - show success (WITH animation)
                            st.success(f"✅ **Rewards distributed successfully to {rewards_count} participants!**")
                            st.balloons()

                            # Display distribution summary
                            col_a, col_b, col_c, col_d = st.columns(4)

                            with col_a:
                                st.metric("👥 Participants", rewards_count)

                            with col_b:
                                total_xp = summary.get('total_xp_awarded', 0)
                                st.metric("⭐ Total XP", total_xp)

                            with col_c:
                                total_credits = summary.get('total_credits_awarded', 0)
                                st.metric("💰 Total Credits", total_credits)

                            with col_d:
                                total_badges = summary.get('total_badges_awarded', 0)
                                st.metric("🏆 Badges", total_badges)

                            st.info("ℹ️ Rewards distributed. Participants can view their badges and XP breakdown in their profiles.")

                    else:
                        st.error(f"❌ Distribution failed: {error}")

            except Exception as e:
                st.error(f"❌ Error distributing rewards: {str(e)}")


@st.dialog("📝 Open Enrollment")
def show_open_enrollment_dialog():
    """Dialog for opening enrollment (INSTRUCTOR_CONFIRMED → READY_FOR_ENROLLMENT)"""
    tournament_id = st.session_state.get('open_enrollment_tournament_id')
    tournament_name = st.session_state.get('open_enrollment_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will open enrollment for this tournament.")
    st.warning("⚠️ Players will be able to enroll after this action.")

    # Reason for transition
    reason = st.text_area(
        "Reason",
        value="Opening enrollment for tournament",
        key="open_enrollment_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📝 Open Enrollment", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "READY_FOR_ENROLLMENT",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Enrollment opened successfully!")
                    st.balloons()
                    time.sleep(2)
                    # Clear session state
                    if 'open_enrollment_tournament_id' in st.session_state:
                        del st.session_state['open_enrollment_tournament_id']
                    if 'open_enrollment_tournament_name' in st.session_state:
                        del st.session_state['open_enrollment_tournament_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'open_enrollment_tournament_id' in st.session_state:
                del st.session_state['open_enrollment_tournament_id']
            if 'open_enrollment_tournament_name' in st.session_state:
                del st.session_state['open_enrollment_tournament_name']
            st.rerun()


@st.dialog("🌍 Publish Tournament")
def show_publish_tournament_dialog():
    """Dialog for publishing tournament (READY_FOR_ENROLLMENT → ENROLLMENT_OPEN)"""
    tournament_id = st.session_state.get('publish_tournament_id')
    tournament_name = st.session_state.get('publish_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will make the tournament visible to players for enrollment.")
    st.success("✅ Players will be able to browse and enroll in this tournament.")

    # Reason for transition
    reason = st.text_area(
        "Reason",
        value="Tournament published - players can now enroll",
        key="publish_tournament_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🌍 Publish Tournament", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "ENROLLMENT_OPEN",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Tournament published successfully!")
                    st.balloons()
                    time.sleep(2)
                    # Clear session state
                    if 'publish_tournament_id' in st.session_state:
                        del st.session_state['publish_tournament_id']
                    if 'publish_tournament_name' in st.session_state:
                        del st.session_state['publish_tournament_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'publish_tournament_id' in st.session_state:
                del st.session_state['publish_tournament_id']
            if 'publish_tournament_name' in st.session_state:
                del st.session_state['publish_tournament_name']
            st.rerun()


@st.dialog("🔒 Close Enrollment")
def show_close_enrollment_dialog():
    """Dialog for closing enrollment (ENROLLMENT_OPEN → ENROLLMENT_CLOSED)"""
    tournament_id = st.session_state.get('close_enrollment_tournament_id')
    tournament_name = st.session_state.get('close_enrollment_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will close enrollment and prevent new players from joining.")
    st.warning("⚠️ Requires minimum 2 enrolled participants.")

    # Reason for transition
    reason = st.text_area(
        "Reason",
        value="Enrollment deadline reached",
        key="close_enrollment_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔒 Close Enrollment", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "ENROLLMENT_CLOSED",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Enrollment closed successfully!")
                    time.sleep(2)
                    # Clear session state
                    if 'close_enrollment_tournament_id' in st.session_state:
                        del st.session_state['close_enrollment_tournament_id']
                    if 'close_enrollment_tournament_name' in st.session_state:
                        del st.session_state['close_enrollment_tournament_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'close_enrollment_tournament_id' in st.session_state:
                del st.session_state['close_enrollment_tournament_id']
            if 'close_enrollment_tournament_name' in st.session_state:
                del st.session_state['close_enrollment_tournament_name']
            st.rerun()


@st.dialog("🚀 Start Tournament")
def show_start_tournament_dialog():
    """Dialog for starting a tournament (ENROLLMENT_CLOSED → IN_PROGRESS)"""
    tournament_id = st.session_state.get('start_tournament_id')
    tournament_name = st.session_state.get('start_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will start the tournament and transition to **IN_PROGRESS** status.")
    st.warning("⚠️ Enrollment is now closed. Tournament will begin.")

    # Reason for transition
    reason = st.text_area(
        "Transition Reason",
        value="Tournament started",
        key="start_tournament_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Tournament", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "IN_PROGRESS",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Tournament started successfully!")
                    st.balloons()
                    time.sleep(2)
                    # Clear session state
                    if 'start_tournament_id' in st.session_state:
                        del st.session_state['start_tournament_id']
                    if 'start_tournament_name' in st.session_state:
                        del st.session_state['start_tournament_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'start_tournament_id' in st.session_state:
                del st.session_state['start_tournament_id']
            if 'start_tournament_name' in st.session_state:
                del st.session_state['start_tournament_name']
            st.rerun()
