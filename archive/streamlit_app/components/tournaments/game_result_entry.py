"""
Game Result Entry Component
Allows master instructor to enter individual game results for tournament sessions
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
import sys
sys.path.append('.')
from config import API_BASE_URL


def render_game_result_entry(game_id: int, game_data: Dict[str, Any], token: str) -> None:
    """
    Render game result entry form for master instructor

    Args:
        game_id: Game (session) ID
        game_data: Game session data
        token: API auth token
    """
    st.subheader(f"📊 Enter Results: {game_data.get('title', 'Game')}")

    # Show game type if available
    game_type = game_data.get('game_type')
    if game_type:
        st.info(f"🎯 Game Type: **{game_type}**")

    # Check if results already submitted
    existing_results = _get_game_results(game_id, token)
    if existing_results:
        st.warning(f"⚠️ Results already submitted for this game ({len(existing_results)} participants)")
        if st.button("🔄 Edit Results", key=f"edit_results_{game_id}"):
            st.session_state[f"edit_mode_{game_id}"] = True
        else:
            _display_existing_results(existing_results)
            return

    # Get participants (booked students)
    participants = _get_game_participants(game_id, token)

    if not participants:
        st.warning("⚠️ No participants found for this game. Students need to book this session first.")
        return

    st.write(f"**Participants**: {len(participants)} students")
    st.divider()

    # Result entry form
    with st.form(f"game_result_form_{game_id}"):
        st.write("**Enter Individual Results**")

        results = []

        for idx, participant in enumerate(participants):
            st.markdown(f"### {idx + 1}. {participant['name']}")

            col1, col2, col3 = st.columns(3)

            with col1:
                score = st.number_input(
                    "Score",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.5,
                    key=f"score_{game_id}_{participant['id']}",
                    help="Score from 0-100"
                )

            with col2:
                rank = st.number_input(
                    "Rank",
                    min_value=1,
                    max_value=len(participants),
                    value=idx + 1,
                    key=f"rank_{game_id}_{participant['id']}",
                    help="Final rank/position"
                )

            with col3:
                notes = st.text_input(
                    "Notes (optional)",
                    max_chars=500,
                    key=f"notes_{game_id}_{participant['id']}",
                    placeholder="e.g., Excellent performance"
                )

            results.append({
                "user_id": participant['id'],
                "score": score,
                "rank": rank,
                "notes": notes if notes else None
            })

            st.divider()

        # Submit button
        submit = st.form_submit_button("✅ Submit Results", use_container_width=True)

        if submit:
            _submit_game_results(game_id, results, token)


def _get_game_participants(game_id: int, token: str) -> List[Dict[str, Any]]:
    """Get participants for a game session"""
    try:
        # Get bookings for this session
        response = requests.get(
            f"{API_BASE_URL}/api/v1/bookings/?session_id={game_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            bookings = data.get('bookings', []) if isinstance(data, dict) else data

            # Extract participant info (only confirmed bookings)
            participants = []
            for booking in bookings:
                if booking.get('status') == 'confirmed':
                    user = booking.get('user', {})
                    participants.append({
                        'id': user.get('id'),
                        'name': user.get('name', 'Unknown')
                    })

            return participants

        return []

    except Exception as e:
        st.error(f"Error loading participants: {str(e)}")
        return []


def _get_game_results(game_id: int, token: str) -> Optional[List[Dict[str, Any]]]:
    """Get existing game results"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions/{game_id}/results",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])

        return None

    except Exception as e:
        st.error(f"Error loading results: {str(e)}")
        return None


def _submit_game_results(game_id: int, results: List[Dict], token: str) -> None:
    """Submit game results to API"""
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/sessions/{game_id}/results",
            headers={"Authorization": f"Bearer {token}"},
            json={"results": results}
        )

        if response.status_code == 200:
            st.success("✅ Game results submitted successfully!")
            st.balloons()
            st.rerun()
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            st.error(f"❌ Error: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error submitting results: {str(e)}")


def _display_existing_results(results: List[Dict[str, Any]]) -> None:
    """Display existing game results"""
    st.write("**Submitted Results:**")

    # Sort by rank
    sorted_results = sorted(results, key=lambda x: x.get('rank', 999))

    for result in sorted_results:
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])

        with col1:
            rank = result.get('rank', '-')
            if rank == 1:
                st.markdown("🥇 **1st**")
            elif rank == 2:
                st.markdown("🥈 **2nd**")
            elif rank == 3:
                st.markdown("🥉 **3rd**")
            else:
                st.markdown(f"**{rank}th**")

        with col2:
            user_id = result.get('user_id', 'N/A')
            st.write(f"User ID: {user_id}")

        with col3:
            score = result.get('score', 0)
            st.metric("Score", f"{score:.1f}")

        with col4:
            notes = result.get('notes')
            if notes:
                st.caption(f"💬 {notes}")

    st.divider()
