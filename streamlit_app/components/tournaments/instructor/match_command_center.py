"""
Match Command Center - Tournament UI (Concept A)

Sequential, match-centric workflow for tournament management:
1. Show active match needing attention
2. 2-button attendance (Present/Absent only)
3. Result entry form (rank-based)
4. Auto-advance to next match
5. Live leaderboard sidebar

This is the POST-START tournament interface focusing on:
- Match management
- Result recording
- Live standings
"""

import streamlit as st
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import API_TIMEOUT
import re


# ============================================================================
# TIME FORMAT PARSER
# ============================================================================

def parse_time_format(time_str: str) -> float:
    """
    Parse MM:SS.CC time format to total seconds.

    Supported formats:
    - MM:SS.CC (e.g., "1:30.45" = 90.45 seconds)
    - MM:SS (e.g., "1:30" = 90.0 seconds)
    - SS.CC (e.g., "10.5" = 10.5 seconds)
    - SS (e.g., "10" = 10.0 seconds)
    - M:SS.CC (e.g., "1:05.5" = 65.5 seconds)

    Args:
        time_str: Time string in MM:SS.CC format

    Returns:
        Total seconds as float

    Raises:
        ValueError: If format is invalid
    """
    # Clean input: strip whitespace and remove any extra spaces
    time_str = time_str.strip().replace(' ', '')

    if not time_str:
        raise ValueError("Empty input")

    # Try parsing as pure decimal number first (e.g., "10.5", "45")
    if ':' not in time_str:
        try:
            seconds = float(time_str)
            if seconds < 0:
                raise ValueError("Time cannot be negative")
            return seconds
        except ValueError:
            raise ValueError("Invalid number format")

    # Parse MM:SS or MM:SS.CC format
    parts = time_str.split(':')

    if len(parts) != 2:
        raise ValueError("Use MM:SS.CC format (e.g., 1:30.45)")

    try:
        minutes = int(parts[0])
        seconds = float(parts[1])
    except ValueError:
        raise ValueError("Invalid time format")

    # Validate
    if minutes < 0 or seconds < 0:
        raise ValueError("Time cannot be negative")

    if seconds >= 60:
        raise ValueError("Seconds must be < 60")

    total_seconds = minutes * 60 + seconds

    return total_seconds


def format_time_display(total_seconds: float) -> str:
    """
    Convert total seconds to MM:SS.CC display format.

    Args:
        total_seconds: Total time in seconds

    Returns:
        Formatted time string (e.g., "1:30.45")
    """
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:05.2f}"


# ============================================================================
# API HELPERS
# ============================================================================

def get_active_match(token: str, tournament_id: int) -> Optional[Dict[str, Any]]:
    """Fetch the current active match from backend"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/active-match"
        st.write(f"🌐 Calling: {url}")  # DEBUG in UI
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        st.write(f"📡 Response: {response.status_code}")  # DEBUG in UI
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ API Error {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        st.error(f"❌ Exception: {str(e)}")
        return None


def mark_attendance(token: str, session_id: int, user_id: int, status: str) -> tuple[bool, str]:
    """
    Mark attendance for a tournament participant.

    For tournament sessions, booking_id is nullable since participants are tracked via
    participant_user_ids array, not bookings.
    """
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"http://localhost:8000/api/v1/attendance/",
        headers=headers,
        json={
            "user_id": user_id,
            "session_id": session_id,
            "booking_id": None,  # Tournament sessions don't use bookings
            "status": status
        }
    )
    if response.status_code == 200:
        return True, "Attendance marked successfully"
    else:
        return False, response.json().get("detail", "Failed to mark attendance")


def get_rounds_status(
    token: str,
    tournament_id: int,
    session_id: int
) -> Optional[Dict[str, Any]]:
    """
    🔄 Get rounds status for INDIVIDUAL_RANKING session.

    Returns:
    - total_rounds: Total number of rounds
    - completed_rounds: Number of rounds with results
    - pending_rounds: List of round numbers without results
    - round_results: All recorded results by round
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Failed to get rounds status: {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ Exception getting rounds status: {str(e)}")
        return None


def submit_round_results(
    token: str,
    tournament_id: int,
    session_id: int,
    round_number: int,
    results: Dict[str, str],
    notes: Optional[str] = None
) -> tuple[bool, str]:
    """
    🔄 Submit results for a specific round in INDIVIDUAL_RANKING tournament.

    Args:
        results: Dict of user_id -> measured_value (e.g., {"123": "12.5s", "456": "95"})
    """
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "round_number": round_number,
        "results": results,
        "notes": notes
    }

    url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results"

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return True, "Round results recorded successfully"
    else:
        error_detail = response.json().get("detail", "Failed to submit round results")
        return False, error_detail


def finalize_individual_ranking_session(
    token: str,
    tournament_id: int,
    session_id: int
) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    🏆 Finalize INDIVIDUAL_RANKING session and calculate final rankings.

    This endpoint:
    - Validates all rounds are completed
    - Aggregates results across all rounds
    - Calculates final rankings based on ranking_direction
    - Saves to game_results and TournamentRanking table

    Returns:
        (success, message, response_data)
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions/{session_id}/finalize"

    response = requests.post(url, headers=headers)

    if response.status_code in [200, 201]:
        data = response.json()
        return True, data.get("message", "Session finalized successfully"), data
    else:
        error_detail = response.json().get("detail", "Failed to finalize session")
        return False, error_detail, None


def submit_match_results(
    token: str,
    tournament_id: int,
    session_id: int,
    results: List[Dict[str, Any]],
    notes: Optional[str] = None
) -> tuple[bool, str]:
    """
    ✅ NEW: Submit structured match results to /submit-results endpoint

    This replaces the legacy /results endpoint with structured format support.
    """
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "results": results,
        "notes": notes
    }

    url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results"
    st.write(f"🌐 Calling: {url}")
    st.write(f"📤 Payload: {payload}")

    response = requests.post(url, headers=headers, json=payload)

    st.write(f"📡 Response: {response.status_code}")
    if response.status_code in [200, 201]:
        st.write(f"✅ Success Response:")
        st.json(response.json())
        return True, "Results recorded successfully"
    else:
        st.write(f"❌ Error Response:")
        st.json(response.json())
        return False, response.json().get("detail", "Failed to record results")


def get_leaderboard(token: str, tournament_id: int) -> Optional[Dict[str, Any]]:
    """Fetch tournament leaderboard"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"http://localhost:8000/api/v1/tournaments/{tournament_id}/leaderboard",
        headers=headers
    )
    if response.status_code == 200:
        return response.json()
    return None


# ============================================================================
# MAIN UI COMPONENT
# ============================================================================

def render_match_command_center(token: str, tournament_id: int):
    """
    Main Match Command Center UI

    Layout:
    - Header with tournament info
    - Active match card (prominent)
    - 2-button attendance (Present/Absent)
    - Result entry form
    - Live leaderboard (sidebar or bottom)
    - Match queue preview
    """
    st.markdown("# ⚽ Match Command Center")

    # 🔍 DEBUG: Confirm function is called
    print(f"🚀 render_match_command_center CALLED with tournament_id={tournament_id}")

    # ============================================================================
    # FETCH ACTIVE MATCH
    # ============================================================================
    print(f"🌐 About to call get_active_match(tournament_id={tournament_id})")
    match_data = get_active_match(token, tournament_id)
    print(f"📦 get_active_match returned: {type(match_data)} - {bool(match_data)}")

    # 🔍 DEBUG
    with st.expander("🔍 DEBUG: API Response", expanded=False):
        if match_data:
            st.json(match_data)
        else:
            st.error("❌ API returned None")

    if not match_data:
        st.error("Failed to load tournament data")
        return

    active_match = match_data.get("active_match")
    tournament_name = match_data.get("tournament_name", "Tournament")

    # ⚠️ PREREQUISITE CHECK: Handle blocked matches
    prerequisite_status = match_data.get("prerequisite_status")
    if prerequisite_status and not prerequisite_status.get('ready', True):
        st.markdown(f"### 🏆 {tournament_name}")
        st.error("⚠️ **Cannot Start Next Match**")
        st.warning(prerequisite_status.get('reason', 'Prerequisites not met'))
        st.info(f"**Action Required:** {prerequisite_status.get('action_required', 'Complete previous matches')}")
        st.markdown("---")
        st.caption("Some matches require previous results before they can be started.")

        # ✅ Show leaderboard even when matches are blocked (to allow finalization)
        st.markdown("---")
        render_leaderboard_sidebar(token, tournament_id)
        return

    # ✅ NEW: Calculate tournament progress
    total_matches = match_data.get("total_matches", 0)
    completed_matches = match_data.get("completed_matches", 0)
    current_match_number = completed_matches + 1 if active_match else completed_matches

    st.markdown(f"### 🏆 {tournament_name}")

    # ✅ NEW: Progress indicator
    if total_matches > 0:
        progress_percentage = (completed_matches / total_matches) * 100
        st.progress(progress_percentage / 100, text=f"🎯 Tournament Progress: {completed_matches}/{total_matches} matches completed ({progress_percentage:.0f}%)")

    if not active_match:
        # All matches completed
        st.success("✅ All matches have been completed!")
        st.markdown("---")
        render_final_leaderboard(token, tournament_id)
        return

    # ============================================================================
    # ACTIVE MATCH CARD
    # ============================================================================
    st.markdown("---")
    st.markdown(f"## 🎮 Match {current_match_number}/{total_matches}: {active_match['match_name']}")

    # ✅ NEW: Display ranking metadata
    ranking_mode = active_match.get('ranking_mode')
    group_identifier = active_match.get('group_identifier')
    tournament_phase = active_match.get('tournament_phase')
    pod_tier = active_match.get('pod_tier')

    # Build metadata badges
    metadata_badges = []

    if tournament_phase:
        metadata_badges.append(f"📌 {tournament_phase}")

    if group_identifier:
        metadata_badges.append(f"🔤 Group {group_identifier}")

    if ranking_mode == 'TIERED' and pod_tier:
        tier_names = {1: "Quarter-Finals", 2: "Semi-Finals", 3: "Finals", 4: "Special Round"}
        tier_name = tier_names.get(pod_tier, f"Tier {pod_tier}")
        metadata_badges.append(f"🏆 {tier_name}")

    if ranking_mode == 'PERFORMANCE_POD' and pod_tier:
        pod_names = {1: "Top Pod 🔥", 2: "Middle Pod ⚡", 3: "Bottom Pod 💪"}
        pod_name = pod_names.get(pod_tier, f"Pod {pod_tier}")
        metadata_badges.append(f"🎯 {pod_name}")

    if metadata_badges:
        st.caption(" • ".join(metadata_badges))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Present", active_match['present_count'])
    with col2:
        st.metric("⏳ Pending", active_match['pending_count'])
    with col3:
        # ✅ Use match_participants_count (scope-correct)
        st.metric("👥 Total", active_match.get('match_participants_count', 0))

    if active_match.get('start_time'):
        start_time = datetime.fromisoformat(active_match['start_time'])
        st.caption(f"🕐 Scheduled: {start_time.strftime('%Y-%m-%d %H:%M')}")

    if active_match.get('location'):
        st.caption(f"📍 Location: {active_match['location']}")

    # ✅ NEW: Show expected vs actual participants (for validation)
    expected = active_match.get('expected_participants')
    actual = active_match.get('match_participants_count', 0)
    if expected and expected != actual:
        st.warning(f"⚠️ Expected {expected} participants, but found {actual}. Check enrollment.")

    st.markdown("---")

    # ✅ NEW: Ranking mode explanation (collapsible)
    with st.expander("ℹ️ Match Type & Scoring", expanded=False):
        if ranking_mode == 'ALL_PARTICIPANTS':
            st.info("**League Format**: All enrolled players compete together and are ranked. Points: 1st=3pts, 2nd=2pts, 3rd=1pt")
        elif ranking_mode == 'GROUP_ISOLATED':
            st.info(f"**Group Stage Format**: Only Group {group_identifier} members compete in this match. Points are awarded within the group.")
        elif ranking_mode == 'TIERED':
            st.info(f"**Knockout Format (Tier {pod_tier})**: All players compete, but tier level affects point multipliers. Higher tiers = more points!")
        elif ranking_mode == 'QUALIFIED_ONLY':
            st.info("**Knockout Stage**: Only top qualifiers from previous rounds compete in this match.")
        elif ranking_mode == 'PERFORMANCE_POD':
            st.info(f"**Swiss System (Pod {pod_tier})**: Players grouped by performance. Top performers compete in Pod 1, etc.")

    # ============================================================================
    # WORKFLOW TABS
    # ============================================================================
    tab1, tab2, tab3 = st.tabs(["✅ Attendance", "🏅 Results", "📊 Leaderboard"])

    with tab1:
        render_attendance_step(token, active_match)

    with tab2:
        render_results_step(token, tournament_id, active_match)

    with tab3:
        render_leaderboard_sidebar(token, tournament_id)

    # ============================================================================
    # MATCH QUEUE (upcoming matches)
    # ============================================================================
    upcoming = match_data.get("upcoming_matches", [])
    if upcoming:
        st.markdown("---")
        st.markdown("### 📋 Upcoming Matches")
        for match in upcoming[:3]:  # Show max 3
            st.caption(f"• {match['match_name']} - {match.get('start_time', 'TBD')}")


# ============================================================================
# STEP 1: ATTENDANCE ROLL CALL
# ============================================================================

def render_attendance_step(token: str, match: Dict[str, Any]):
    """2-button attendance interface (Present/Absent only)"""
    st.markdown("### ✅ Step 1: Attendance Roll Call")
    st.caption("Mark which players are present for this match")

    session_id = match['session_id']
    # ✅ Use match_participants (explicit scope)
    participants = match.get('match_participants', [])

    if not participants:
        st.info("No participants enrolled in this match")
        return

    # Display participants with 2-button interface
    for participant in participants:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            status = participant['attendance_status']
            if status == "present":
                st.markdown(f"✅ **{participant['name']}**")
            elif status == "absent":
                st.markdown(f"❌ ~~{participant['name']}~~")
            else:
                st.markdown(f"⏳ {participant['name']}")

        with col2:
            if st.button(
                "✅ Present",
                key=f"present_{participant['user_id']}",
                disabled=(status == "present"),
                type="primary" if status != "present" else "secondary"
            ):
                success, msg = mark_attendance(
                    token,
                    session_id,
                    participant['user_id'],
                    "present"
                )
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with col3:
            if st.button(
                "❌ Absent",
                key=f"absent_{participant['user_id']}",
                disabled=(status == "absent")
            ):
                success, msg = mark_attendance(
                    token,
                    session_id,
                    participant['user_id'],
                    "absent"
                )
                if success:
                    st.warning(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ============================================================================
# STEP 2: RECORD RESULTS
# ============================================================================

def render_results_step(token: str, tournament_id: int, match: Dict[str, Any]):
    """
    ✅ NEW: Dynamic result entry form based on match_format

    Supports multiple formats:
    - INDIVIDUAL_RANKING: Placement-based (1st, 2nd, 3rd)
    - HEAD_TO_HEAD: Winner selection (future)
    - TEAM_MATCH: Team scores (future)
    - TIME_BASED: Time recording (future)
    - SKILL_RATING: Disabled (extension point)
    """
    st.markdown("### 🏅 Step 2: Record Match Results")

    session_id = match['session_id']

    # ⚠️ PREREQUISITE CHECK: Handle cases where match cannot start yet
    if 'prerequisite_status' in match and not match['prerequisite_status'].get('ready', True):
        prereq = match['prerequisite_status']
        st.error(f"⚠️ **Cannot Start This Match**")
        st.warning(prereq.get('reason', 'Prerequisites not met'))
        st.info(f"**Action Required:** {prereq.get('action_required', 'Complete previous matches')}")
        st.markdown("---")
        st.caption("This knockout match requires completed group stage results to determine qualified participants.")
        return

    # ✅ EXPLICIT SCOPE: Use MATCH participants ONLY (not tournament participants!)
    match_participants = match.get('match_participants', [])
    tournament_participants = match.get('tournament_participants', [])

    # ⚠️ FAIL-FAST: If no match_participants defined, this is a developer error
    if 'match_participants' not in match:
        st.error("🚨 DEVELOPER ERROR: API response missing 'match_participants' field!")
        st.error("The /active-match endpoint must provide explicit match-scoped participants.")
        st.stop()

    # Debug panel: Show scope difference
    if len(match_participants) != len(tournament_participants):
        st.warning(f"⚠️ SCOPE MISMATCH: Match has {len(match_participants)} participants, but tournament has {len(tournament_participants)} total enrollments.")
        with st.expander("🔍 Debug: Scope Comparison"):
            st.caption(f"**Match Participants** (use for results): {len(match_participants)}")
            st.json([p['name'] for p in match_participants])
            st.caption(f"**Tournament Participants** (context only): {len(tournament_participants)}")
            st.json([p['name'] for p in tournament_participants])

    # ✅ NEW: Get match format metadata from API
    match_format = match.get('match_format', 'INDIVIDUAL_RANKING')
    scoring_type = match.get('scoring_type', 'PLACEMENT')
    structure_config = match.get('structure_config', {})

    # Display format info
    st.caption(f"Format: **{match_format}** • Scoring: **{scoring_type}**")
    st.caption(f"Match Scope: **{len(match_participants)}** participants (filtered for THIS MATCH)")

    # Only show PRESENT participants FROM MATCH SCOPE
    present_participants = [p for p in match_participants if p['is_present']]

    if not present_participants:
        st.warning("⚠️ No participants marked as present yet. Complete attendance first.")
        return

    if len(present_participants) < 2:
        st.warning("⚠️ At least 2 players must be present to record results.")
        return

    st.markdown("---")

    # ✅ NEW: Dispatch to format-specific UI
    if match_format == 'INDIVIDUAL_RANKING':
        render_individual_ranking_form(token, tournament_id, match, present_participants)
    elif match_format == 'HEAD_TO_HEAD':
        render_head_to_head_form(token, tournament_id, match, present_participants)
    elif match_format == 'TEAM_MATCH':
        render_team_match_form(token, tournament_id, match, present_participants)
    elif match_format == 'TIME_BASED':
        render_time_based_form(token, tournament_id, match, present_participants)
    elif match_format == 'SKILL_RATING':
        st.error("❌ SKILL_RATING format is not yet implemented. Business logic pending.")
        st.info("🔌 This is an extension point. The rating criteria and scoring algorithm will be defined in a future release.")
    else:
        st.error(f"❌ Match format '{match_format}' is not yet supported in the UI.")
        st.info(f"Supported formats: INDIVIDUAL_RANKING, HEAD_TO_HEAD, TEAM_MATCH, TIME_BASED")


def render_individual_ranking_form(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]]
):
    """
    ✅ INDIVIDUAL_RANKING: Measured value entry for INDIVIDUAL_RANKING tournaments

    For INDIVIDUAL_RANKING tournaments (format="INDIVIDUAL_RANKING"), the system records
    measured performance values (e.g., seconds, meters, points) directly.

    The ranking is then calculated automatically based on:
    - measurement_unit (e.g., "seconds", "meters", "points")
    - ranking_direction (ASC = lower is better, DESC = higher is better)

    Backend Flow:
    1. User submits measured values → [{"user_id": X, "measured_value": 10.5}, ...]
    2. Backend stores measured_value in TournamentRanking.points
    3. Backend calculates ranks based on ranking_direction
    """
    session_id = match['session_id']

    # Get tournament metadata
    tournament_format = match.get('tournament_format', 'HEAD_TO_HEAD')
    measurement_unit = match.get('measurement_unit')
    ranking_direction = match.get('ranking_direction', 'DESC')

    # Check if this is an INDIVIDUAL_RANKING tournament
    if tournament_format == 'INDIVIDUAL_RANKING':
        # ✅ NEW: Measured value entry for INDIVIDUAL_RANKING tournaments
        render_measured_value_entry(
            token=token,
            tournament_id=tournament_id,
            match=match,
            present_participants=present_participants,
            measurement_unit=measurement_unit,
            ranking_direction=ranking_direction
        )
    else:
        # Legacy placement-based entry for HEAD_TO_HEAD tournaments with INDIVIDUAL_RANKING match_format
        render_placement_based_entry(
            token=token,
            tournament_id=tournament_id,
            match=match,
            present_participants=present_participants
        )


def render_rounds_based_entry(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]],
    measurement_unit: str,
    ranking_direction: str
):
    """
    🔄 NEW ARCHITECTURE: Rounds-based entry for INDIVIDUAL_RANKING tournaments.

    Instead of treating each round as a separate session, all rounds are stored
    in a single session's rounds_data field.

    UI Features:
    - Shows completed rounds (read-only)
    - Shows current round for data entry
    - Shows pending rounds (grayed out)
    - Instructor can reload page and continue where they left off
    - Idempotent: Can re-submit a round to correct mistakes
    """
    session_id = match['session_id']

    # Get rounds status from backend
    rounds_status = get_rounds_status(token, tournament_id, session_id)

    if not rounds_status:
        st.error("❌ Failed to load rounds status from backend")
        return

    total_rounds = rounds_status['total_rounds']
    completed_rounds = rounds_status['completed_rounds']
    pending_rounds = rounds_status['pending_rounds']
    round_results = rounds_status['round_results']
    is_complete = rounds_status['is_complete']

    # Determine current round (first pending, or last completed if all done)
    if pending_rounds:
        current_round = pending_rounds[0]
    elif completed_rounds > 0:
        current_round = completed_rounds  # Show last completed round
    else:
        current_round = 1

    # Display round progress
    st.markdown(f"### 🔄 Round {current_round} of {total_rounds}")

    progress_percentage = (completed_rounds / total_rounds) * 100
    st.progress(progress_percentage / 100)
    st.caption(f"✅ Completed: {completed_rounds} | ⏳ Remaining: {len(pending_rounds)}")

    # Show tabs for all rounds
    round_tabs = st.tabs([f"Round {i}" for i in range(1, total_rounds + 1)])

    for round_num in range(1, total_rounds + 1):
        with round_tabs[round_num - 1]:
            is_completed = str(round_num) in round_results
            is_current = round_num == current_round
            is_pending = round_num in pending_rounds and round_num != current_round

            if is_completed and not is_current:
                # COMPLETED ROUND: Read-only display
                st.success(f"✅ Round {round_num} completed")
                results = round_results[str(round_num)]

                st.markdown("#### Results:")
                for user_id_str, value_str in results.items():
                    # Find participant name
                    participant = next((p for p in present_participants if str(p['user_id']) == user_id_str), None)
                    name = participant['name'] if participant else f"User {user_id_str}"
                    st.caption(f"**{name}**: {value_str}")

            elif is_current:
                # CURRENT ROUND: Allow data entry
                if is_completed:
                    st.info(f"ℹ️ Round {round_num} is completed. You can re-submit to update results (idempotent).")
                else:
                    st.info(f"📝 Recording results for Round {round_num}")

                # Render input form for current round
                _render_round_input_form(
                    token, tournament_id, session_id, round_num,
                    present_participants, measurement_unit, ranking_direction,
                    existing_results=round_results.get(str(round_num))
                )

            else:
                # PENDING ROUND: Grayed out
                st.caption(f"⏳ Round {round_num} - Not started yet")

    # ============================================================================
    # 🏆 FINALIZE SESSION: Show button when all rounds completed
    # ============================================================================
    if completed_rounds == total_rounds and not pending_rounds:
        st.markdown("---")
        st.markdown("### 🏆 Tournament Complete")

        # Check if session is already finalized
        session_finalized = match.get('game_results') is not None

        if session_finalized:
            st.success("✅ This session has been finalized!")
            st.info("Final rankings have been calculated and saved to the leaderboard.")

            # Allow re-finalization to update rankings (e.g., after system updates)
            st.caption("💡 Click below to recalculate rankings (e.g., after data corrections)")
            button_label = "🔄 Re-calculate Rankings"
            button_type = "secondary"
        else:
            st.info(f"📊 All {total_rounds} rounds completed! Click the button below to calculate final rankings.")
            button_label = "🏁 Finalize Session & Calculate Rankings"
            button_type = "primary"

        # Explain aggregation logic
        if ranking_direction == "ASC":
            aggregation_text = "🔽 **Lowest (best) time** from all rounds will determine the winner."
        else:
            aggregation_text = "🔼 **Highest score** from all rounds will determine the winner."

        st.caption(aggregation_text)

        # Finalize/Re-finalize button (always shown)
        if st.button(button_label, type=button_type, use_container_width=True):
            with st.spinner("Calculating final rankings..."):
                success, message, response_data = finalize_individual_ranking_session(
                    token, tournament_id, session_id
                )

            if success:
                st.success(message)

                # Display dual rankings
                if response_data:
                    col1, col2 = st.columns(2)

                    # Performance Rankings (Best Individual Time)
                    if 'performance_rankings' in response_data:
                        with col1:
                            st.markdown("#### 🏃 Best Individual Performance")
                            st.caption("Fastest time across all rounds")
                            rankings = response_data['performance_rankings']

                            for rank_entry in rankings:
                                rank = rank_entry['rank']
                                user_id = rank_entry['user_id']
                                final_value = rank_entry['final_value']
                                unit = rank_entry.get('measurement_unit', '')

                                # Find participant name
                                participant = next((p for p in present_participants if p['user_id'] == user_id), None)
                                name = participant['name'] if participant else f"User {user_id}"

                                # Medal emoji for top 3
                                if rank == 1:
                                    medal = "🥇"
                                elif rank == 2:
                                    medal = "🥈"
                                elif rank == 3:
                                    medal = "🥉"
                                else:
                                    medal = f"#{rank}"

                                st.markdown(f"**{medal} {name}**: {final_value} {unit}")

                    # Wins Rankings (Most Round Victories)
                    if 'wins_rankings' in response_data:
                        with col2:
                            st.markdown("#### 🏆 Most Round Victories")
                            st.caption("Most 1st place finishes")
                            rankings = response_data['wins_rankings']

                            for rank_entry in rankings:
                                rank = rank_entry['rank']
                                user_id = rank_entry['user_id']
                                wins = rank_entry['wins']
                                total = rank_entry.get('total_rounds', 0)

                                # Find participant name
                                participant = next((p for p in present_participants if p['user_id'] == user_id), None)
                                name = participant['name'] if participant else f"User {user_id}"

                                # Medal emoji for top 3
                                if rank == 1:
                                    medal = "🥇"
                                elif rank == 2:
                                    medal = "🥈"
                                elif rank == 3:
                                    medal = "🥉"
                                else:
                                    medal = f"#{rank}"

                                st.markdown(f"**{medal} {name}**: {wins}/{total} wins")

                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {message}")


def _render_round_input_form(
    token: str,
    tournament_id: int,
    session_id: int,
    round_number: int,
    present_participants: List[Dict[str, Any]],
    measurement_unit: str,
    ranking_direction: str,
    existing_results: Optional[Dict[str, str]] = None
):
    """
    Render input form for a specific round.

    Args:
        existing_results: Previous results for this round (for idempotent re-submission)
    """
    # Initialize session state for measured values
    state_key = f"round_{session_id}_{round_number}_values"
    if state_key not in st.session_state:
        # Pre-populate with existing results if available
        if existing_results:
            st.session_state[state_key] = {
                int(user_id): float(value.rstrip('s').rstrip(' points').rstrip(' meters'))
                for user_id, value in existing_results.items()
            }
        else:
            st.session_state[state_key] = {}

    # Display info
    direction_text = "🔽 Lower is better" if ranking_direction == "ASC" else "🔼 Higher is better"
    unit_display = measurement_unit or "value"

    # Create example based on measurement unit
    is_time_measurement = unit_display.lower() in ["seconds", "sec", "s", "minutes", "min", "m"]

    if is_time_measurement:
        example_text = '''**How to enter time:**
Use the three input boxes for each participant:
• **Perc** (minutes): 0-59
• **Másodperc** (seconds): 0-59
• **Századmásodperc** (hundredths): 0-99

Example: 1 min 30.45 sec = Perc: 1, Másodperc: 30, Századmásodperc: 45'''
    elif unit_display.lower() in ["meters", "m", "metres"]:
        example_text = 'Enter distance in meters. Example: `15.2` for 15.2 meters'
    elif unit_display.lower() in ["points", "pts", "score"]:
        example_text = 'Enter score/points. Example: `95` for 95 points'
    else:
        example_text = f'Enter numeric values in {unit_display}'

    st.info(f"""
    ℹ️ **Recording Performance Metrics**

    📏 **Measurement Unit**: **{unit_display.upper()}**

    📊 **Ranking Method**: {direction_text}

    💡 **How to enter values**:
    {example_text}
    """)

    st.markdown("#### Enter Performance Values")
    st.caption(f"Record measured values for all {len(present_participants)} participants")

    measured_values_dict = st.session_state[state_key]

    # Input fields for each participant
    for participant in present_participants:
        user_id = participant['user_id']

        st.markdown(f"**{participant['name']}**")

        if is_time_measurement:
            # Time input with separate boxes
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            # Get existing value if available
            existing_value = measured_values_dict.get(user_id, 0.0)
            existing_minutes = int(existing_value // 60)
            remaining_seconds = existing_value % 60
            existing_seconds = int(remaining_seconds)
            existing_hundredths = int((remaining_seconds - existing_seconds) * 100)

            with col1:
                minutes = st.number_input(
                    "Perc",
                    min_value=0,
                    max_value=59,
                    step=1,
                    value=existing_minutes,
                    key=f"min_{session_id}_{round_number}_{user_id}",
                    help="Perc (0-59)"
                )

            with col2:
                seconds = st.number_input(
                    "Másodperc",
                    min_value=0,
                    max_value=59,
                    step=1,
                    value=existing_seconds,
                    key=f"sec_{session_id}_{round_number}_{user_id}",
                    help="Másodperc (0-59)"
                )

            with col3:
                hundredths = st.number_input(
                    "Századmásodperc",
                    min_value=0,
                    max_value=99,
                    step=1,
                    value=existing_hundredths,
                    key=f"hun_{session_id}_{round_number}_{user_id}",
                    help="Századmásodperc (0-99)"
                )

            with col4:
                # Calculate total time
                total_seconds = minutes * 60 + seconds + (hundredths / 100.0)

                if total_seconds > 0:
                    st.metric("Össz", f"{total_seconds:.2f}s")
                    measured_values_dict[user_id] = total_seconds
                else:
                    st.caption("⏱️ 0.00s")
                    if user_id in measured_values_dict:
                        del measured_values_dict[user_id]

        else:
            # Regular numeric input
            col1, col2 = st.columns([2, 1])

            existing_value = measured_values_dict.get(user_id, 0.0)

            with col1:
                value = st.number_input(
                    f"Value ({unit_display})",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=existing_value,
                    key=f"measured_{session_id}_{round_number}_{user_id}",
                    help=f"Enter the measured value in {unit_display}",
                    placeholder=f"0.00"
                )

            with col2:
                if value > 0:
                    st.metric("Érték", f"{value:.2f}")

            if value > 0:
                measured_values_dict[user_id] = value
            elif user_id in measured_values_dict:
                del measured_values_dict[user_id]

        st.markdown("---")

    st.markdown("")  # Extra spacing

    # Check if all participants have values
    all_entered = len(measured_values_dict) == len(present_participants)

    if not all_entered:
        st.warning(f"⚠️ Please enter values for all {len(present_participants)} participants ({len(measured_values_dict)}/{len(present_participants)} completed)")

    # Show preview
    if measured_values_dict:
        st.markdown("#### 📊 Performance Preview")

        # Convert to list for sorting
        preview_list = [
            {"user_id": uid, "value": val, "name": next((p['name'] for p in present_participants if p['user_id'] == uid), f"User {uid}")}
            for uid, val in measured_values_dict.items()
        ]

        # Sort based on ranking direction
        if ranking_direction == "ASC":
            sorted_preview = sorted(preview_list, key=lambda x: x['value'])
        else:
            sorted_preview = sorted(preview_list, key=lambda x: x['value'], reverse=True)

        for idx, entry in enumerate(sorted_preview, 1):
            medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))

            if is_time_measurement:
                value_display = f"**{format_time_display(entry['value'])}**"
            else:
                value_display = f"**{entry['value']:.2f}** {unit_display}"

            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.caption(medal)
            with col2:
                st.caption(entry['name'])
            with col3:
                st.caption(value_display)

    # Optional notes
    notes = st.text_area(
        "Round Notes (Optional)",
        key=f"notes_{session_id}_{round_number}",
        placeholder="Any observations for this round..."
    )

    # Submit button
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        button_clicked = st.button(
            f"🏅 Submit Round {round_number} Results",
            type="primary",
            disabled=(not all_entered),
            use_container_width=True,
            key=f"submit_{session_id}_{round_number}"
        )

        if button_clicked:
            # Convert to backend format: user_id -> "value + unit"
            results_dict = {}
            for user_id, value in measured_values_dict.items():
                if is_time_measurement:
                    results_dict[str(user_id)] = f"{value:.2f}s"
                elif unit_display.lower() in ["meters", "m", "metres"]:
                    results_dict[str(user_id)] = f"{value:.2f} meters"
                elif unit_display.lower() in ["points", "pts", "score"]:
                    results_dict[str(user_id)] = f"{value:.0f} points"
                else:
                    results_dict[str(user_id)] = f"{value:.2f}"

            # Submit to backend
            success, msg = submit_round_results(
                token, tournament_id, session_id, round_number,
                results_dict, notes if notes else None
            )

            if success:
                st.success(f"✅ Round {round_number} results recorded!")
                # Clear state
                if state_key in st.session_state:
                    del st.session_state[state_key]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button(
            "🔄 Reset Form",
            use_container_width=True,
            key=f"reset_{session_id}_{round_number}"
        ):
            st.session_state[state_key] = {}
            st.rerun()


def render_measured_value_entry(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]],
    measurement_unit: str,
    ranking_direction: str
):
    """
    ✅ NEW: Measured value entry for INDIVIDUAL_RANKING tournaments

    Examples:
    - 100m Sprint: measurement_unit="seconds", ranking_direction="ASC" (lower is better)
    - Long Jump: measurement_unit="meters", ranking_direction="DESC" (higher is better)
    - Skill Challenge: measurement_unit="points", ranking_direction="DESC" (higher is better)
    """
    session_id = match['session_id']

    # 🔄 Check if this session has rounds_data (new architecture)
    rounds_data = match.get('rounds_data', {})
    total_rounds = rounds_data.get('total_rounds', 0)

    if total_rounds > 0:
        # NEW ARCHITECTURE: Rounds-based entry
        render_rounds_based_entry(
            token, tournament_id, match, present_participants,
            measurement_unit, ranking_direction
        )
        return

    # LEGACY: Single session entry (fallback for old tournaments)

    # Initialize session state for measured values
    if f"measured_values_{session_id}" not in st.session_state:
        st.session_state[f"measured_values_{session_id}"] = {}

    # Display info
    direction_text = "🔽 Lower is better" if ranking_direction == "ASC" else "🔼 Higher is better"
    unit_display = measurement_unit or "value"

    # Create example based on measurement unit
    is_time_measurement = unit_display.lower() in ["seconds", "sec", "s", "minutes", "min", "m"]

    if is_time_measurement:
        example_text = '''**How to enter time:**
Use the three input boxes for each participant:
• **Perc** (minutes): 0-59
• **Másodperc** (seconds): 0-59
• **Századmásodperc** (hundredths): 0-99

Example: 1 min 30.45 sec = Perc: 1, Másodperc: 30, Századmásodperc: 45'''
    elif unit_display.lower() in ["meters", "m", "metres"]:
        example_text = 'Enter distance in meters. Example: `15.2` for 15.2 meters'
    elif unit_display.lower() in ["points", "pts", "score"]:
        example_text = 'Enter score/points. Example: `95` for 95 points'
    else:
        example_text = f'Enter numeric values in {unit_display}'

    st.info(f"""
    ℹ️ **Recording Performance Metrics**

    📏 **Measurement Unit**: **{unit_display.upper()}**

    📊 **Ranking Method**: {direction_text}

    💡 **How to enter values**:
    {example_text}
    """)

    st.markdown("#### Enter Performance Values")
    st.caption(f"Record measured values for all {len(present_participants)} participants")

    measured_values = st.session_state[f"measured_values_{session_id}"]

    # Input fields for each participant
    for participant in present_participants:
        user_id = participant['user_id']

        st.markdown(f"**{participant['name']}**")

        if is_time_measurement:
            # Time input with separate boxes for minutes, seconds, hundredths
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

            with col1:
                minutes = st.number_input(
                    "Perc",
                    min_value=0,
                    max_value=59,
                    step=1,
                    key=f"min_{session_id}_{user_id}",
                    help="Perc (0-59)"
                )

            with col2:
                seconds = st.number_input(
                    "Másodperc",
                    min_value=0,
                    max_value=59,
                    step=1,
                    key=f"sec_{session_id}_{user_id}",
                    help="Másodperc (0-59)"
                )

            with col3:
                hundredths = st.number_input(
                    "Századmásodperc",
                    min_value=0,
                    max_value=99,
                    step=1,
                    key=f"hun_{session_id}_{user_id}",
                    help="Századmásodperc (0-99)"
                )

            with col4:
                # Calculate total time
                total_seconds = minutes * 60 + seconds + (hundredths / 100.0)

                if total_seconds > 0:
                    st.metric("Össz", f"{total_seconds:.2f}s")

                    # Store value
                    measured_values[user_id] = {
                        "user_id": user_id,
                        "name": participant['name'],
                        "measured_value": total_seconds
                    }
                else:
                    st.caption("⏱️ 0.00s")
                    # Remove if exists
                    if user_id in measured_values:
                        del measured_values[user_id]

        else:
            # Regular numeric input for non-time measurements
            col1, col2 = st.columns([2, 1])

            with col1:
                value = st.number_input(
                    f"Value ({unit_display})",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"measured_{session_id}_{user_id}",
                    help=f"Enter the measured value in {unit_display}",
                    placeholder=f"0.00"
                )

            with col2:
                if value > 0:
                    st.metric("Érték", f"{value:.2f}")

            if value > 0:
                measured_values[user_id] = {
                    "user_id": user_id,
                    "name": participant['name'],
                    "measured_value": value
                }
            elif user_id in measured_values:
                del measured_values[user_id]

        st.markdown("---")

    st.markdown("")  # Extra spacing

    # Check if all participants have values
    all_entered = len(measured_values) == len(present_participants)

    if not all_entered:
        st.warning(f"⚠️ Please enter values for all {len(present_participants)} participants ({len(measured_values)}/{len(present_participants)} completed)")

    # Show preview (sorted by performance)
    if measured_values:
        st.markdown("#### 📊 Performance Preview")

        # Sort by measured value based on ranking_direction
        if ranking_direction == "ASC":
            # Lower is better (e.g., time)
            sorted_values = sorted(measured_values.values(), key=lambda x: x['measured_value'])
        else:
            # Higher is better (e.g., score, distance)
            sorted_values = sorted(measured_values.values(), key=lambda x: x['measured_value'], reverse=True)

        for idx, entry in enumerate(sorted_values, 1):
            value = entry['measured_value']
            name = entry['name']

            # Medal for top 3
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx}."

            # Format value display
            if is_time_measurement:
                value_display = f"**{format_time_display(value)}**"
            else:
                value_display = f"**{value:.2f}** {unit_display}"

            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.caption(medal)
            with col2:
                st.caption(name)
            with col3:
                st.caption(value_display)

    # Optional match notes
    match_notes = st.text_area(
        "Match Notes (Optional)",
        key=f"notes_{session_id}",
        placeholder="Any additional observations or comments..."
    )

    # Validation and submit
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🏅 Submit Results",
            type="primary",
            disabled=(not all_entered),
            use_container_width=True
        ):
            # Convert measured values to backend format
            results_list = [
                {
                    "user_id": p['user_id'],
                    "measured_value": p['measured_value']
                }
                for p in measured_values.values()
            ]

            # Submit to backend
            success, msg = submit_match_results(
                token,
                tournament_id,
                session_id,
                results_list,
                match_notes if match_notes else None
            )

            if success:
                st.success("✅ Results recorded! Advancing to next match...")
                # Clear measured values from session state
                del st.session_state[f"measured_values_{session_id}"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.session_state[f"measured_values_{session_id}"] = {}
            st.rerun()


def render_placement_based_entry(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]]
):
    """
    Legacy placement-based entry for HEAD_TO_HEAD tournaments with INDIVIDUAL_RANKING match_format

    This is used when tournament.format = "HEAD_TO_HEAD" but match_format = "INDIVIDUAL_RANKING".
    In this case, we use the old placement system (1st, 2nd, 3rd) and award points.
    """
    session_id = match['session_id']

    # Initialize session state for placements
    if f"placements_{session_id}" not in st.session_state:
        st.session_state[f"placements_{session_id}"] = {}

    st.info("""
    ℹ️ **Recording Placements (Multi-Player Ranking)**
    All participants compete together in this match.
    Assign placement (1st, 2nd, 3rd, 4th, etc.) to each participant.
    - **1st place**: 3 points
    - **2nd place**: 2 points
    - **3rd place**: 1 point
    - **4th+ place**: 0 points
    """)

    st.markdown("#### Assign Placements")
    st.caption(f"Rank all {len(present_participants)} participants by their performance")

    placements = st.session_state[f"placements_{session_id}"]

    # Display placement selection for each participant
    placement_options = list(range(1, len(present_participants) + 1))

    for participant in present_participants:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{participant['name']}**")

        with col2:
            placement = st.selectbox(
                f"Placement for {participant['name']}",
                options=[0] + placement_options,  # 0 = not assigned
                format_func=lambda x: "Select..." if x == 0 else f"{x}{'st' if x == 1 else 'nd' if x == 2 else 'rd' if x == 3 else 'th'}",
                key=f"placement_{session_id}_{participant['user_id']}",
                label_visibility="collapsed"
            )

            if placement > 0:
                placements[participant['user_id']] = {
                    "user_id": participant['user_id'],
                    "name": participant['name'],
                    "placement": placement
                }
            elif participant['user_id'] in placements:
                del placements[participant['user_id']]

    st.markdown("---")

    # Validation: Check for duplicate placements
    assigned_placements = [p['placement'] for p in placements.values()]
    has_duplicates = len(assigned_placements) != len(set(assigned_placements))

    if has_duplicates:
        st.error("❌ Each placement can only be assigned to one participant!")
        duplicate_positions = [p for p in assigned_placements if assigned_placements.count(p) > 1]
        st.warning(f"Duplicate placements found: {list(set(duplicate_positions))}")

    # Check if all participants are ranked
    all_ranked = len(placements) == len(present_participants)

    if not all_ranked:
        st.warning(f"⚠️ Please assign placements to all {len(present_participants)} participants ({len(placements)}/{len(present_participants)} completed)")

    # Show preview
    if placements:
        st.markdown("#### 📊 Placement Preview")
        sorted_placements = sorted(placements.values(), key=lambda x: x['placement'])

        for entry in sorted_placements:
            placement = entry['placement']
            name = entry['name']

            # Calculate points
            if placement == 1:
                points = 3
                medal = "🥇"
            elif placement == 2:
                points = 2
                medal = "🥈"
            elif placement == 3:
                points = 1
                medal = "🥉"
            else:
                points = 0
                medal = f"{placement}{'th' if placement > 3 else ''}"

            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.caption(medal)
            with col2:
                st.caption(name)
            with col3:
                st.caption(f"**{points}** pts")

    # Optional match notes
    match_notes = st.text_area(
        "Match Notes (Optional)",
        key=f"notes_{session_id}",
        placeholder="Any additional observations or comments..."
    )

    # Validation and submit
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🏅 Submit Placements",
            type="primary",
            disabled=(not all_ranked or has_duplicates),
            use_container_width=True
        ):
            # Convert placements to backend format
            results_list = [
                {
                    "user_id": p['user_id'],
                    "placement": p['placement']
                }
                for p in placements.values()
            ]

            # Submit to backend
            success, msg = submit_match_results(
                token,
                tournament_id,
                session_id,
                results_list,
                match_notes if match_notes else None
            )

            if success:
                st.success("✅ Placements recorded! Advancing to next match...")
                # Clear placements from session state
                del st.session_state[f"placements_{session_id}"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.session_state[f"placements_{session_id}"] = {}
            st.rerun()


def render_head_to_head_form(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]]
):
    """
    ✅ HEAD_TO_HEAD: 1v1 winner selection or score-based

    UI: Winner selection (radio button) or score input
    Output:
      - WIN_LOSS: [{"user_id": X, "result": "WIN"}, {"user_id": Y, "result": "LOSS"}]
      - SCORE_BASED: [{"user_id": X, "score": A}, {"user_id": Y, "score": B}]
    """
    session_id = match['session_id']
    scoring_type = match.get('scoring_type', 'WIN_LOSS')

    # Validation: HEAD_TO_HEAD requires exactly 2 participants
    if len(present_participants) != 2:
        st.error(f"❌ HEAD_TO_HEAD format requires exactly 2 participants. Found {len(present_participants)}.")
        return

    player_a = present_participants[0]
    player_b = present_participants[1]

    st.markdown("#### Match Result")
    st.caption(f"**{player_a['name']}** vs **{player_b['name']}**")

    # Initialize session state
    if f"results_{session_id}" not in st.session_state:
        st.session_state[f"results_{session_id}"] = {}

    if scoring_type == 'SCORE_BASED':
        # Score-based input
        st.markdown("##### Enter Scores")

        col1, col2 = st.columns(2)
        with col1:
            score_a = st.number_input(
                f"{player_a['name']} Score",
                min_value=0,
                step=1,
                key=f"score_a_{session_id}"
            )
        with col2:
            score_b = st.number_input(
                f"{player_b['name']} Score",
                min_value=0,
                step=1,
                key=f"score_b_{session_id}"
            )

        results_list = [
            {"user_id": player_a['user_id'], "score": score_a},
            {"user_id": player_b['user_id'], "score": score_b}
        ]

    else:  # WIN_LOSS → Changed to SCORE_BASED
        # Score input for both players
        st.markdown("##### Match Result")
        st.caption("Enter the final score for each player")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"**{player_a['name']}**")
            score_a = st.number_input(
                "Score",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key=f"score_a_{session_id}",
                label_visibility="collapsed"
            )

        with col_b:
            st.markdown(f"**{player_b['name']}**")
            score_b = st.number_input(
                "Score",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key=f"score_b_{session_id}",
                label_visibility="collapsed"
            )

        # Build SCORE_BASED results
        results_list = [
            {
                "user_id": player_a['user_id'],
                "score": score_a,
                "opponent_score": score_b
            },
            {
                "user_id": player_b['user_id'],
                "score": score_b,
                "opponent_score": score_a
            }
        ]

        # Show predicted winner
        if score_a > score_b:
            st.success(f"✅ Winner: **{player_a['name']}** ({score_a} - {score_b})")
        elif score_b > score_a:
            st.success(f"✅ Winner: **{player_b['name']}** ({score_b} - {score_a})")
        elif score_a == score_b and score_a > 0:
            st.info(f"🤝 Draw/Tie ({score_a} - {score_b})")
        else:
            st.warning("⚠️ Enter scores to determine winner")

    # Optional match notes
    match_notes = st.text_area(
        "Match Notes (Optional)",
        key=f"notes_{session_id}",
        placeholder="Any additional observations or comments..."
    )

    st.markdown("---")

    # Submit button
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🏅 Submit Results & Continue",
            type="primary",
            use_container_width=True
        ):
            success, msg = submit_match_results(
                token,
                tournament_id,
                session_id,
                results_list,
                match_notes if match_notes else None
            )

            if success:
                st.success("✅ Results recorded! Advancing to next match...")
                if f"results_{session_id}" in st.session_state:
                    del st.session_state[f"results_{session_id}"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.rerun()


def render_team_match_form(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]]
):
    """
    ✅ TEAM_MATCH: Team-based competition

    UI: Assign players to teams, enter team scores
    Output: [{"user_id": X, "team": "A", "team_score": 5, "opponent_score": 3}, ...]
    """
    session_id = match['session_id']
    structure_config = match.get('structure_config', {})

    # Initialize session state
    if f"team_assignments_{session_id}" not in st.session_state:
        st.session_state[f"team_assignments_{session_id}"] = {}
    if f"team_scores_{session_id}" not in st.session_state:
        st.session_state[f"team_scores_{session_id}"] = {"A": 0, "B": 0}

    st.markdown("#### Assign Players to Teams")

    team_assignments = st.session_state[f"team_assignments_{session_id}"]

    # Team assignment UI
    for participant in present_participants:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**{participant['name']}**")

        with col2:
            team = st.selectbox(
                "Team",
                options=["Not Assigned", "Team A", "Team B"],
                key=f"team_{session_id}_{participant['user_id']}",
                label_visibility="collapsed"
            )

            if team != "Not Assigned":
                team_id = "A" if team == "Team A" else "B"
                team_assignments[participant['user_id']] = {
                    "user_id": participant['user_id'],
                    "team": team_id
                }
            elif participant['user_id'] in team_assignments:
                del team_assignments[participant['user_id']]

    st.markdown("---")

    # Validation: All players must be assigned
    if len(team_assignments) < len(present_participants):
        st.warning(f"⚠️ Please assign all {len(present_participants)} players to teams")
        return

    # Count teams
    team_a_count = sum(1 for p in team_assignments.values() if p['team'] == 'A')
    team_b_count = sum(1 for p in team_assignments.values() if p['team'] == 'B')

    # Validation: Both teams must have players
    if team_a_count == 0 or team_b_count == 0:
        st.error("❌ Both teams must have at least one player")
        return

    st.markdown(f"**Team A**: {team_a_count} players • **Team B**: {team_b_count} players")
    st.markdown("---")

    # Team scores
    st.markdown("#### Enter Team Scores")

    team_scores = st.session_state[f"team_scores_{session_id}"]

    col1, col2 = st.columns(2)
    with col1:
        team_scores['A'] = st.number_input(
            f"Team A Score ({team_a_count} players)",
            min_value=0,
            step=1,
            key=f"score_team_a_{session_id}"
        )

    with col2:
        team_scores['B'] = st.number_input(
            f"Team B Score ({team_b_count} players)",
            min_value=0,
            step=1,
            key=f"score_team_b_{session_id}"
        )

    # Build results list
    results_list = []
    for user_id, assignment in team_assignments.items():
        team_id = assignment['team']
        opponent_team = 'B' if team_id == 'A' else 'A'

        results_list.append({
            "user_id": user_id,
            "team": team_id,
            "team_score": team_scores[team_id],
            "opponent_score": team_scores[opponent_team]
        })

    # Optional match notes
    match_notes = st.text_area(
        "Match Notes (Optional)",
        key=f"notes_{session_id}",
        placeholder="Any additional observations or comments..."
    )

    st.markdown("---")

    # Submit button
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🏅 Submit Results & Continue",
            type="primary",
            use_container_width=True
        ):
            success, msg = submit_match_results(
                token,
                tournament_id,
                session_id,
                results_list,
                match_notes if match_notes else None
            )

            if success:
                st.success("✅ Results recorded! Advancing to next match...")
                if f"team_assignments_{session_id}" in st.session_state:
                    del st.session_state[f"team_assignments_{session_id}"]
                if f"team_scores_{session_id}" in st.session_state:
                    del st.session_state[f"team_scores_{session_id}"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.session_state[f"team_assignments_{session_id}"] = {}
            st.session_state[f"team_scores_{session_id}"] = {"A": 0, "B": 0}
            st.rerun()


def render_time_based_form(
    token: str,
    tournament_id: int,
    match: Dict[str, Any],
    present_participants: List[Dict[str, Any]]
):
    """
    ✅ TIME_BASED: Performance time recording

    UI: Time input (seconds) for each participant
    Output: [{"user_id": X, "time_seconds": 12.45}, ...]
    """
    session_id = match['session_id']

    # Initialize session state
    if f"times_{session_id}" not in st.session_state:
        st.session_state[f"times_{session_id}"] = {}

    st.markdown("#### Record Performance Times")
    st.caption("Enter time in seconds (e.g., 11.23 for 11.23 seconds)")

    times_dict = st.session_state[f"times_{session_id}"]

    # Time input for each participant
    for participant in present_participants:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**{participant['name']}**")

        with col2:
            time_seconds = st.number_input(
                "Time (seconds)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key=f"time_{session_id}_{participant['user_id']}",
                label_visibility="collapsed"
            )

            if time_seconds > 0:
                times_dict[participant['user_id']] = {
                    "user_id": participant['user_id'],
                    "time_seconds": time_seconds
                }
            elif participant['user_id'] in times_dict:
                del times_dict[participant['user_id']]

    # Optional match notes
    match_notes = st.text_area(
        "Match Notes (Optional)",
        key=f"notes_{session_id}",
        placeholder="Any additional observations or comments..."
    )

    st.markdown("---")

    # Validation: All participants must have times
    if len(times_dict) < len(present_participants):
        st.warning(f"⚠️ Please enter times for all {len(present_participants)} participants")
        return

    # Show preview (sorted by time)
    st.markdown("#### ⏱️ Performance Preview")
    sorted_times = sorted(times_dict.values(), key=lambda x: x['time_seconds'])

    for idx, result in enumerate(sorted_times, 1):
        participant_name = next(
            (p['name'] for p in present_participants if p['user_id'] == result['user_id']),
            "Unknown"
        )
        st.caption(f"#{idx} • {participant_name} • {result['time_seconds']:.2f}s")

    st.markdown("---")

    # Submit button
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🏅 Submit Results & Continue",
            type="primary",
            disabled=(len(times_dict) < len(present_participants)),
            use_container_width=True
        ):
            results_list = list(times_dict.values())

            success, msg = submit_match_results(
                token,
                tournament_id,
                session_id,
                results_list,
                match_notes if match_notes else None
            )

            if success:
                st.success("✅ Results recorded! Advancing to next match...")
                if f"times_{session_id}" in st.session_state:
                    del st.session_state[f"times_{session_id}"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.session_state[f"times_{session_id}"] = {}
            st.rerun()


# ============================================================================
# KNOCKOUT RESULTS HELPERS
# ============================================================================

def render_knockout_results_bracket(token: str, tournament_id: int, leaderboard_data: dict):
    """Display knockout bracket results in pyramid style (bottom-up to final)"""
    # KNOCKOUT STAGE VIEWING NOT YET IMPLEMENTED
    # Endpoint GET /api/v1/tournaments/{id}/sessions is in backlog
    st.info("🚧 **Knockout Stage Results Display Coming Soon**")
    st.markdown("""
    The knockout bracket visualization is currently under development.

    **Available Now:**
    - ✅ Group Stage Results (see above)
    - ✅ Match recording and scoring
    - ✅ Leaderboard rankings

    **Coming Soon:**
    - 🚧 Knockout bracket progression
    - 🚧 Semifinal & Final results display
    """)
    return

    # Filter knockout sessions (placeholder for future implementation)
    knockout_sessions = []

    if not knockout_sessions:
        st.warning(f"⚠️ No knockout matches found. Total sessions loaded: {len(sessions)}")
        with st.expander("🔍 DEBUG: Show all sessions"):
            st.json(sessions)
        return

    # Get user names
    user_names = {}
    if leaderboard_data.get('group_standings'):
        for group_id, standings in leaderboard_data['group_standings'].items():
            for player in standings:
                user_names[player['user_id']] = player['name']

    # Organize by round
    from collections import defaultdict
    rounds = defaultdict(list)
    for session in knockout_sessions:
        if session.get('tournament_round'):
            rounds[session['tournament_round']].append(session)

    # Display rounds from bottom (semifinals) to top (final)
    sorted_rounds = sorted(rounds.items())

    for round_num, matches in sorted_rounds:
        # Determine round name
        if any('bronze' in m.get('title', '').lower() for m in matches):
            continue  # Skip bronze for now, show separately

        if round_num == 1:
            st.markdown("#### ⚔️ Semifinals")
        elif round_num == 2:
            st.markdown("#### 🥇 Final")
        else:
            st.markdown(f"#### Round {round_num}")

        # Display matches side by side
        cols = st.columns(len(matches))

        for idx, (col, match) in enumerate(zip(cols, matches)):
            with col:
                participant_ids = match.get('participant_user_ids', [])
                game_results = match.get('game_results')

                if len(participant_ids) >= 2:
                    player1_name = user_names.get(participant_ids[0], f"Player {participant_ids[0]}")
                    player2_name = user_names.get(participant_ids[1], f"Player {participant_ids[1]}")

                    if game_results:
                        # Parse results to get scores
                        import json
                        if isinstance(game_results, str):
                            game_results = json.loads(game_results)

                        raw_results = game_results.get('raw_results', [])
                        score1 = next((r['score'] for r in raw_results if r['user_id'] == participant_ids[0]), 0)
                        score2 = next((r['score'] for r in raw_results if r['user_id'] == participant_ids[1]), 0)

                        winner_id = participant_ids[0] if score1 > score2 else participant_ids[1]

                        st.markdown(f"**{player1_name}** {score1} - {score2} **{player2_name}**")
                        st.caption(f"✅ Winner: {user_names.get(winner_id)}")
                    else:
                        st.markdown(f"{player1_name} vs {player2_name}")
                        st.caption("⏳ Pending")

        st.markdown("---")

    # Show bronze match separately
    bronze_matches = [m for m in knockout_sessions if 'bronze' in m.get('title', '').lower()]
    if bronze_matches:
        st.markdown("#### 🥉 Bronze Match (3rd Place)")
        bronze_match = bronze_matches[0]

        participant_ids = bronze_match.get('participant_user_ids', [])
        game_results = bronze_match.get('game_results')

        if len(participant_ids) >= 2:
            player1_name = user_names.get(participant_ids[0], f"Player {participant_ids[0]}")
            player2_name = user_names.get(participant_ids[1], f"Player {participant_ids[1]}")

            if game_results:
                import json
                if isinstance(game_results, str):
                    game_results = json.loads(game_results)

                raw_results = game_results.get('raw_results', [])
                score1 = next((r['score'] for r in raw_results if r['user_id'] == participant_ids[0]), 0)
                score2 = next((r['score'] for r in raw_results if r['user_id'] == participant_ids[1]), 0)

                winner_id = participant_ids[0] if score1 > score2 else participant_ids[1]

                st.markdown(f"**{player1_name}** {score1} - {score2} **{player2_name}**")
                st.caption(f"✅ Winner: {user_names.get(winner_id)}")


def render_group_results_table(group_standings: dict):
    """Display group stage results in table format"""
    import pandas as pd

    for group_id, standings in sorted(group_standings.items()):
        st.markdown(f"### 📍 Group {group_id}")

        df_data = []
        for player in standings:
            rank = player['rank']
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
            qualify = "✅" if rank <= 2 else ""

            df_data.append({
                "Pos": medal,
                "Player": player['name'],
                "MP": player.get('matches_played', 0),
                "Pts": player['points'],
                "W": player['wins'],
                "D": player['draws'],
                "L": player['losses'],
                "GF": player['goals_for'],
                "GA": player['goals_against'],
                "GD": f"{player['goal_difference']:+d}",
                "": qualify
            })

        df = pd.DataFrame(df_data)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pos": st.column_config.TextColumn("Pos", width="small"),
                "Player": st.column_config.TextColumn("Player", width="medium"),
                "MP": st.column_config.NumberColumn("MP", width="small"),
                "Pts": st.column_config.NumberColumn("Pts", width="small"),
                "W": st.column_config.NumberColumn("W", width="small"),
                "D": st.column_config.NumberColumn("D", width="small"),
                "L": st.column_config.NumberColumn("L", width="small"),
                "GF": st.column_config.NumberColumn("GF", width="small"),
                "GA": st.column_config.NumberColumn("GA", width="small"),
                "GD": st.column_config.TextColumn("GD", width="small"),
                "": st.column_config.TextColumn("", width="small")
            }
        )

        st.caption("✅ = Qualified for Knockout Stage")
        st.markdown("---")


# ============================================================================
# KNOCKOUT BRACKET VIEW
# ============================================================================

def render_knockout_bracket(leaderboard_data: dict):
    """Display knockout bracket (supports both pure knockout and group+knockout)"""
    st.markdown("### 🏆 Knockout Stage Bracket")

    # Check if this is pure knockout or group+knockout
    group_standings = leaderboard_data.get('group_standings')
    knockout_bracket = leaderboard_data.get('knockout_bracket')

    if group_standings:
        st.info("✅ Group stage finalized! Top 2 from each group advance to knockout rounds.")
    else:
        st.info("✅ Single elimination tournament - seeded bracket")

    st.markdown("---")

    # ✅ NEW: Use bracket data from API
    if knockout_bracket:
        # Display each round
        for round_data in knockout_bracket:
            round_num = round_data['round']
            round_name = round_data['round_name']
            matches = round_data['matches']

            # Special icon for each round type
            if 'final' in round_name.lower() and '3rd' not in round_name.lower():
                icon = "🏆"
            elif '3rd' in round_name.lower() or 'bronze' in round_name.lower():
                icon = "🥉"
            elif 'semi' in round_name.lower():
                icon = "⚔️"
            else:
                icon = "🎯"

            st.markdown(f"#### {icon} {round_name}")

            # Display matches in columns (max 4 per row)
            num_matches = len(matches)
            cols_per_row = min(4, num_matches)

            if cols_per_row > 0:
                cols = st.columns(cols_per_row)

                for idx, match in enumerate(matches):
                    with cols[idx % cols_per_row]:
                        match_number = match.get('match_number', idx + 1)
                        participants = match.get('participants', [])
                        winner = match.get('winner')
                        completed = match.get('completed', False)

                        st.markdown(f"**Match {match_number}**")

                        if participants and len(participants) >= 2:
                            # Show actual participants
                            p1 = participants[0]
                            p2 = participants[1]

                            # Highlight winner if match is completed
                            if completed and winner:
                                if winner == p1['user_id']:
                                    st.markdown(f"✅ **{p1['name']}** (Winner)")
                                    st.markdown(f"❌ {p2['name']}")
                                elif winner == p2['user_id']:
                                    st.markdown(f"❌ {p1['name']}")
                                    st.markdown(f"✅ **{p2['name']}** (Winner)")
                                else:
                                    # No winner yet
                                    st.markdown(f"🔵 **{p1['name']}**")
                                    st.markdown("*vs*")
                                    st.markdown(f"🔵 **{p2['name']}**")
                            else:
                                # Match not completed yet
                                st.markdown(f"🔵 **{p1['name']}**")
                                st.markdown("*vs*")
                                st.markdown(f"🔵 **{p2['name']}**")
                        else:
                            # Participants TBD (determined by previous round)
                            st.markdown("🔄 *TBD*")
                            st.caption("Winner from previous round")

                        st.markdown("---")

            st.markdown("")  # Add spacing between rounds

    else:
        # ✅ FALLBACK: Old hardcoded logic for group+knockout (legacy support)
        # Get user names from group standings
        user_names = {}
        if group_standings:
            for group_id, standings in group_standings.items():
                for player in standings:
                    user_names[player['user_id']] = player['name']

        st.markdown("#### ⚔️ Semifinals")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Match 1**")
            # Get top 2 from each group
            groups = sorted(group_standings.items())
            if len(groups) >= 2:
                a1_id = groups[0][1][0]['user_id']  # Group A winner
                b2_id = groups[1][1][1]['user_id'] if len(groups[1][1]) >= 2 else None  # Group B runner-up

                if a1_id and b2_id:
                    st.markdown(f"🥇 **{user_names.get(a1_id)}** (Group A #1)")
                    st.markdown("*vs*")
                    st.markdown(f"🥈 **{user_names.get(b2_id)}** (Group B #2)")
                else:
                    st.markdown("*TBD*")

        with col2:
            st.markdown("**Match 2**")
            if len(groups) >= 2:
                b1_id = groups[1][1][0]['user_id']  # Group B winner
                a2_id = groups[0][1][1]['user_id'] if len(groups[0][1]) >= 2 else None  # Group A runner-up

                if b1_id and a2_id:
                    st.markdown(f"🥇 **{user_names.get(b1_id)}** (Group B #1)")
                    st.markdown("*vs*")
                    st.markdown(f"🥈 **{user_names.get(a2_id)}** (Group A #2)")
                else:
                    st.markdown("*TBD*")

        st.markdown("---")

        st.markdown("#### 🥇 Final")
        st.markdown("*Winners from Semifinals will compete for the championship*")
        st.markdown("🏆 **TBD** vs **TBD**")


# ============================================================================
# LEADERBOARD SIDEBAR
# ============================================================================

def render_leaderboard_sidebar(token: str, tournament_id: int):
    """Display live tournament leaderboard"""
    st.markdown("### 📊 Live Leaderboard")

    leaderboard_data = get_leaderboard(token, tournament_id)

    if not leaderboard_data:
        st.error("Failed to load leaderboard")
        return

    leaderboard = leaderboard_data.get("leaderboard", [])
    group_standings = leaderboard_data.get("group_standings")  # ✅ NEW
    knockout_bracket = leaderboard_data.get("knockout_bracket")  # ✅ NEW: Pure knockout tournaments

    # Progress bar
    total = leaderboard_data.get("total_matches", 0)
    completed = leaderboard_data.get("completed_matches", 0)

    if total > 0:
        progress = completed / total
        st.progress(progress, text=f"Progress: {completed}/{total} matches completed")

    st.markdown("---")

    # ✅ Check if group stage is finalized (from leaderboard response)
    group_stage_finalized = leaderboard_data.get("group_stage_finalized", False)

    # ✅ NEW: Show knockout bracket (for pure knockout or group+knockout tournaments)
    if knockout_bracket and group_stage_finalized:
        # Pure knockout tournament or group stage finalized → show bracket
        render_knockout_bracket(leaderboard_data)
        return
    elif group_standings and group_stage_finalized:
        # Group stage finalized but no bracket yet (should not happen)
        render_knockout_bracket(leaderboard_data)
        return
    elif group_standings:
        st.markdown("#### 🔤 Group Stage Standings")

        import pandas as pd

        # Display each group in a clean table
        for group_id, standings in sorted(group_standings.items()):
            st.markdown(f"### 📍 Group {group_id}")

            # Create DataFrame for clean table display
            df_data = []
            for player in standings:
                rank = player['rank']
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
                qualify = "✅" if rank <= 2 else ""

                df_data.append({
                    "Pos": medal,
                    "Player": player['name'],
                    "MP": player.get('matches_played', 0),
                    "Pts": player['points'],
                    "W": player['wins'],
                    "D": player['draws'],
                    "L": player['losses'],
                    "GF": player['goals_for'],
                    "GA": player['goals_against'],
                    "GD": f"{player['goal_difference']:+d}",
                    "": qualify
                })

            df = pd.DataFrame(df_data)

            # Apply CSS for centered table content
            st.markdown("""
                <style>
                    .stDataFrame table {
                        text-align: center !important;
                    }
                    .stDataFrame td, .stDataFrame th {
                        text-align: center !important;
                    }
                </style>
            """, unsafe_allow_html=True)

            # Display with custom styling - all columns centered
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Pos": st.column_config.TextColumn("Pos", width="small", help="Position"),
                    "Player": st.column_config.TextColumn("Player", width="medium"),
                    "MP": st.column_config.NumberColumn("MP", width="small", help="Matches Played"),
                    "Pts": st.column_config.NumberColumn("Pts", width="small", help="Points"),
                    "W": st.column_config.NumberColumn("W", width="small", help="Wins"),
                    "D": st.column_config.NumberColumn("D", width="small", help="Draws"),
                    "L": st.column_config.NumberColumn("L", width="small", help="Losses"),
                    "GF": st.column_config.NumberColumn("GF", width="small", help="Goals For"),
                    "GA": st.column_config.NumberColumn("GA", width="small", help="Goals Against"),
                    "GD": st.column_config.TextColumn("GD", width="small", help="Goal Difference"),
                    "": st.column_config.TextColumn("", width="small", help="Qualifies")
                }
            )

            st.caption("✅ = Qualifies for Knockout Stage")
            st.markdown("---")

        st.info("📊 **Top 2 from each group** advance to the knockout stage")

        # ✅ Check if all group matches are completed
        if completed == total and total > 0:
            st.markdown("---")
            st.markdown("### 🏁 Group Stage Complete!")
            st.success("All group stage matches have been completed. Finalize the group stage to proceed to knockout rounds.")

            from api_helpers_tournaments import finalize_group_stage

            if st.button("🎯 Finalize Group Stage & Save Snapshot", type="primary", use_container_width=True):
                with st.spinner("Finalizing group stage and saving snapshot..."):
                    success, error, data = finalize_group_stage(token, tournament_id)

                    if success:
                        st.success("✅ " + data.get('message', 'Group stage finalized successfully!'))

                        if data.get('snapshot_saved'):
                            st.info("📸 Snapshot saved to database")

                        if data.get('qualified_participants'):
                            st.success(f"🎉 {len(data['qualified_participants'])} players qualified for knockout stage")

                        st.balloons()
                        st.rerun()
                    else:
                        if "not completed yet" in error:
                            st.warning(f"⚠️ {error}")
                        else:
                            st.error(f"❌ Failed to finalize: {error}")

        return

    # ============================================================================
    # 🏃 INDIVIDUAL_RANKING: Show dual rankings side-by-side
    # ============================================================================
    tournament_format = leaderboard_data.get('tournament_format', 'HEAD_TO_HEAD')
    performance_rankings = leaderboard_data.get('performance_rankings')
    wins_rankings = leaderboard_data.get('wins_rankings')

    if tournament_format == "INDIVIDUAL_RANKING" and performance_rankings and wins_rankings:
        # Show dual rankings in two columns
        col1, col2 = st.columns(2)

        # 🏃 Performance Rankings (Best Individual Time)
        with col1:
            st.markdown("#### 🏃 Best Performance")
            st.caption("Fastest time across all rounds")

            for rank_entry in performance_rankings[:10]:  # Top 10
                rank = rank_entry['rank']
                user_id = rank_entry['user_id']
                final_value = rank_entry['final_value']
                unit = rank_entry.get('measurement_unit', '')

                # Find user name from leaderboard
                user_name = next((p['name'] for p in leaderboard if p['user_id'] == user_id), f"User {user_id}")

                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                st.markdown(f"**{medal} {user_name}**: {final_value} {unit}")

        # 🏆 Wins Rankings (Most Round Victories)
        with col2:
            st.markdown("#### 🏆 Most Wins")
            st.caption("Most 1st place finishes")

            for rank_entry in wins_rankings[:10]:  # Top 10
                rank = rank_entry['rank']
                user_id = rank_entry['user_id']
                wins = rank_entry['wins']
                total = rank_entry.get('total_rounds', 0)

                # Find user name from leaderboard
                user_name = next((p['name'] for p in leaderboard if p['user_id'] == user_id), f"User {user_id}")

                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                st.markdown(f"**{medal} {user_name}**: {wins}/{total} wins")

    # ============================================================================
    # Display global rankings (fallback for HEAD_TO_HEAD tournaments)
    # ============================================================================
    elif leaderboard:
        for entry in leaderboard[:10]:  # Top 10
            rank = entry['rank']
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."

            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.markdown(f"**{medal}**")
            with col2:
                st.markdown(f"**{entry['name']}**")
            with col3:
                st.markdown(f"**{entry['points']}** pts")

            # Calculate total matches from wins/losses/draws
            total_matches = entry.get('wins', 0) + entry.get('losses', 0) + entry.get('draws', 0)
            st.caption(f"Matches: {total_matches} (W: {entry.get('wins', 0)} L: {entry.get('losses', 0)} D: {entry.get('draws', 0)})")
            st.markdown("---")
    else:
        st.info("No rankings yet. Complete the first match to see standings.")


def render_final_leaderboard(token: str, tournament_id: int):
    """Full leaderboard view when tournament is complete"""
    st.markdown("## 🏆 Final Standings")

    leaderboard_data = get_leaderboard(token, tournament_id)

    if not leaderboard_data:
        st.error("Failed to load leaderboard")
        return

    # ✅ NEW: Check if we have final_standings from knockout tournament
    final_standings = leaderboard_data.get("final_standings")

    if final_standings:
        # Display knockout tournament final standings (1st, 2nd, 3rd, 4th)
        st.markdown("### 🎖️ Podium")

        # Create 3 columns for podium display (2nd, 1st, 3rd)
        col1, col2, col3 = st.columns([1, 1.5, 1])

        # Find each position
        champion = next((p for p in final_standings if p['rank'] == 1), None)
        runner_up = next((p for p in final_standings if p['rank'] == 2), None)
        third_place = next((p for p in final_standings if p['rank'] == 3), None)
        fourth_place = next((p for p in final_standings if p['rank'] == 4), None)

        with col1:
            if runner_up:
                st.markdown(f"### 🥈")
                st.markdown(f"**{runner_up['name']}**")
                st.caption(runner_up['title'])

        with col2:
            if champion:
                st.markdown(f"### 🥇")
                st.markdown(f"# **{champion['name']}**")
                st.caption("🏆 " + champion['title'])

        with col3:
            if third_place:
                st.markdown(f"### 🥉")
                st.markdown(f"**{third_place['name']}**")
                st.caption(third_place['title'])

        st.markdown("---")

        # Display full rankings
        st.markdown("### 📋 Complete Rankings")

        for player in final_standings:
            cols = st.columns([1, 4, 2])
            with cols[0]:
                st.markdown(f"**{player['medal']} {player['rank']}**")
            with cols[1]:
                st.markdown(f"**{player['name']}**")
            with cols[2]:
                st.markdown(f"*{player['title']}*")

        st.markdown("---")

        # ✅ Display knockout bracket with results
        st.markdown("### 🏆 Knockout Stage Results")
        render_knockout_results_bracket(token, tournament_id, leaderboard_data)

        st.markdown("---")

        # ✅ Display group stage results
        st.markdown("### 🔤 Group Stage Results")
        group_standings = leaderboard_data.get("group_standings")
        if group_standings:
            render_group_results_table(group_standings)

        return

    # Fallback: Use old leaderboard display for non-knockout tournaments
    leaderboard = leaderboard_data.get("leaderboard", [])

    if not leaderboard:
        st.info("No rankings available")
        return

    # Podium display for top 3
    if len(leaderboard) >= 3:
        st.markdown("### 🎖️ Podium")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"### 🥈 2nd Place")
            st.markdown(f"**{leaderboard[1]['name']}**")
            st.metric("Points", leaderboard[1]['points'])

        with col2:
            st.markdown(f"### 🥇 1st Place")
            st.markdown(f"**{leaderboard[0]['name']}**")
            st.metric("Points", leaderboard[0]['points'])

        with col3:
            st.markdown(f"### 🥉 3rd Place")
            st.markdown(f"**{leaderboard[2]['name']}**")
            st.metric("Points", leaderboard[2]['points'])

        st.markdown("---")

    # Full standings table
    st.markdown("### 📊 Complete Standings")

    import pandas as pd

    # Check tournament format from leaderboard_data
    tournament_format = leaderboard_data.get('tournament_format', 'HEAD_TO_HEAD')

    if tournament_format == 'INDIVIDUAL_RANKING':
        # INDIVIDUAL_RANKING: Show only Rank, Player, Points
        df = pd.DataFrame([
            {
                "Rank": entry['rank'],
                "Player": entry['name'],
                "Performance": entry['points']
            }
            for entry in leaderboard
        ])
    else:
        # HEAD_TO_HEAD: Show full stats with Wins/Losses/Draws
        df = pd.DataFrame([
            {
                "Rank": entry['rank'],
                "Player": entry['name'],
                "Points": entry['points'],
                "Wins": entry.get('wins', 0),
                "Losses": entry.get('losses', 0),
                "Draws": entry.get('draws', 0)
            }
            for entry in leaderboard
        ])

    st.dataframe(df, use_container_width=True, hide_index=True)
