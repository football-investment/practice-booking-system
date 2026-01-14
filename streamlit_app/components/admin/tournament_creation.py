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
    Render reward distribution section for COMPLETED tournaments.

    Shows:
    - Tournament completion status
    - Reward distribution button
    - Distribution results
    """
    tournament_id = tournament.get('id')
    tournament_name = tournament.get('name', 'Unknown')

    st.subheader("🎁 Reward Distribution")

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
            "🎁 Distribute Rewards",
            key=f"distribute_{tournament_id}",
            use_container_width=True,
            type="primary",
            help="Distribute XP and credits to tournament participants based on rankings"
        ):
            # Call distribute rewards endpoint
            try:
                with st.spinner("Distributing rewards..."):
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=API_TIMEOUT
                    )

                    if response.status_code == 200:
                        result = response.json()

                        st.success("✅ **Rewards distributed successfully!**")

                        # Display distribution summary
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.metric(
                                "👥 Participants",
                                result.get('total_participants', 0)
                            )

                        with col_b:
                            st.metric(
                                "⭐ Total XP",
                                result.get('xp_distributed', 0)
                            )

                        with col_c:
                            st.metric(
                                "💰 Total Credits",
                                result.get('credits_distributed', 0)
                            )

                        # Show individual rewards if available
                        if 'rewards' in result:
                            st.divider()
                            st.caption("**Individual Rewards:**")

                            for reward in result.get('rewards', []):
                                placement = reward.get('placement', 'N/A')
                                player_name = reward.get('player_name', 'Unknown')
                                xp = reward.get('xp', 0)
                                credits = reward.get('credits', 0)

                                st.caption(
                                    f"• **{placement}** - {player_name}: "
                                    f"+{xp} XP, +{credits} credits"
                                )

                        time.sleep(2)
                        st.rerun()

                    else:
                        error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                        error_msg = error_data.get('detail', response.text)
                        st.error(f"❌ Distribution failed: {error_msg}")

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


@st.dialog("🚀 Start Tournament")
def show_start_tournament_dialog():
    """Dialog for starting a tournament (READY_FOR_ENROLLMENT → IN_PROGRESS)"""
    tournament_id = st.session_state.get('start_tournament_id')
    tournament_name = st.session_state.get('start_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will start the tournament and transition to **IN_PROGRESS** status.")
    st.warning("⚠️ Requires minimum 2 enrolled participants.")

    # Reason for transition
    reason = st.text_area(
        "Transition Reason",
        value="Tournament started - enrollment closed",
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
