"""
Match Command Center Screen Components

Screen rendering functions for match command center.
"""

import streamlit as st
from typing import Dict, Any
from streamlit_components.layouts import Card
from components.tournaments.instructor.match_command_center_helpers import mark_attendance


def render_attendance_step(match: Dict[str, Any]):
    """Render attendance step for match.

    match is the inner active_match dict from get_active_match() (envelope already unwrapped).
    Field mapping: session_id → session_id, match_participants → participant list,
    participant.user_id → user id for attendance calls.
    """
    st.markdown("### 📋 Mark Attendance")

    card = Card(title="Participant Attendance", card_id="attendance")
    with card.container():
        # active_match uses "match_participants" and "session_id" (not "participants" / "id")
        participants = match.get('match_participants') or []
        session_id = match.get('session_id')

        if not participants:
            st.info("No participants assigned to this match yet.")
        else:
            for participant in participants:
                user_id = participant.get('user_id')
                if user_id is None:
                    continue

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(participant.get('name', 'Unknown'))

                with col2:
                    if st.button("✅ Present", key=f"btn_present_{user_id}"):
                        mark_attendance(session_id, user_id, 'PRESENT')

                with col3:
                    if st.button("❌ Absent", key=f"btn_absent_{user_id}"):
                        mark_attendance(session_id, user_id, 'ABSENT')
    card.close_container()
