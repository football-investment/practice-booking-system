"""
Tournament Fixtures View - VALIDATION ONLY

This component displays ONLY the tournament schedule/fixtures.

NO ranking, NO result entry, NO placement logic - ONLY the draw.

Purpose: Verify that backend schedule generation is correct.
"""

import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


def get_tournament_sessions(token: str, tournament_id: int) -> Optional[List[Dict[str, Any]]]:
    """Fetch all tournament sessions (matches) from backend"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions"
        st.write(f"🔍 DEBUG: Attempting to fetch from: {url}")  # DEBUG
        response = requests.get(url, headers=headers, timeout=10)
        st.write(f"🔍 DEBUG: Response status: {response.status_code}")  # DEBUG
        if response.status_code == 200:
            data = response.json()
            st.write(f"🔍 DEBUG: Received {len(data) if isinstance(data, list) else 'N/A'} sessions")  # DEBUG
            st.write(f"🔍 DEBUG: First session data: {data[0] if data else 'No data'}")  # DEBUG
            return data
        else:
            st.error(f"Failed to fetch sessions: {response.status_code}")
            st.write(f"🔍 DEBUG: Response content: {response.text[:200]}")  # DEBUG
            return None
    except Exception as e:
        st.error(f"Error fetching sessions: {str(e)}")
        import traceback
        st.write(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")  # DEBUG
        return None


def render_tournament_fixtures(token: str, tournament_id: int):
    """
    Display tournament fixtures in simple format:

    Group A - Round 1
    A vs B
    C vs D

    Group A - Round 2
    A vs C
    B vs D
    """
    st.markdown("## 📋 Tournament Fixtures")
    st.caption("Backend schedule verification - NO result entry, NO ranking")

    # Fetch sessions
    sessions = get_tournament_sessions(token, tournament_id)

    if not sessions:
        st.warning("No sessions found for this tournament")
        return

    # Group sessions by group_identifier and round_number
    fixtures_by_group = {}

    for session in sessions:
        # ✅ FIX: Use tournament_phase for knockout matches (no group_identifier)
        group_id = session.get('group_identifier')
        if group_id is None:
            # Knockout matches don't have group_identifier
            group_id = session.get('tournament_phase', 'Knockout Stage')

        round_num = session.get('round_number', 0)

        if group_id not in fixtures_by_group:
            fixtures_by_group[group_id] = {}

        if round_num not in fixtures_by_group[group_id]:
            fixtures_by_group[group_id][round_num] = []

        fixtures_by_group[group_id][round_num].append(session)

    # Display fixtures grouped by group and round
    # Handle None values in group_identifier by treating them as empty string for sorting
    for group_id in sorted(fixtures_by_group.keys(), key=lambda x: x if x is not None else ""):
        st.markdown(f"### {group_id}")

        rounds = fixtures_by_group[group_id]
        # Handle None values in round_number by treating them as -1 for sorting
        for round_num in sorted(rounds.keys(), key=lambda x: x if x is not None else -1):
            st.markdown(f"**Round {round_num}**")

            matches = rounds[round_num]
            for match in matches:
                # Get participant names from backend response
                participant_names = match.get('participant_names', [])

                # Handle None value (not just empty list)
                if participant_names is None:
                    participant_names = []

                # Fallback to user IDs if no names
                if not participant_names:
                    participant_ids = match.get('participant_user_ids', [])
                    # Handle None value in participant_ids too
                    if participant_ids is None:
                        participant_ids = []
                    participant_names = [f"User {uid}" for uid in participant_ids]

                # Format match display
                if len(participant_names) >= 2:
                    match_str = " vs ".join(participant_names)
                elif match.get('matchup_display'):
                    # ✅ KNOCKOUT MATCHES: Show seeding placeholders (A1 vs B2, etc.)
                    match_str = match.get('matchup_display')
                else:
                    match_str = f"Match with {len(participant_names)} participants"

                # Show date/time if available
                date_str = ""
                if match.get('date'):
                    try:
                        dt = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
                        date_str = f" - {dt.strftime('%Y-%m-%d %H:%M')}"
                    except:
                        pass

                st.write(f"  • {match_str}{date_str}")

            st.markdown("")  # Spacing between rounds

        st.markdown("---")  # Separator between groups

    # Summary
    st.info(f"Total matches: {len(sessions)}")
