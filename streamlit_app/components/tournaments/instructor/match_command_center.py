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


# ============================================================================
# API HELPERS
# ============================================================================

def get_active_match(token: str, tournament_id: int) -> Optional[Dict[str, Any]]:
    """Fetch the current active match from backend"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/active-match"
        st.write(f"🌐 Calling: {url}")  # DEBUG in UI
        response = requests.get(url, headers=headers, timeout=10)
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
    ✅ INDIVIDUAL_RANKING: Placement-based result entry

    All participants compete together in a single match/session.
    User assigns placement (1st, 2nd, 3rd, 4th, etc.) to each participant.

    Backend Flow:
    1. User submits placements → [{"user_id": X, "placement": 1}, {"user_id": Y, "placement": 2}, ...]
    2. Backend validates placements (no duplicates, all participants ranked)
    3. Backend stores results in game_results JSON field
    4. Points are calculated based on placement (1st=3pts, 2nd=2pts, 3rd=1pt, etc.)
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

    else:  # WIN_LOSS
        # Winner selection
        st.markdown("##### Select Winner")

        winner_choice = st.radio(
            "Who won?",
            options=[player_a['name'], player_b['name'], "Draw/Tie"],
            key=f"winner_{session_id}",
            horizontal=True
        )

        if winner_choice == player_a['name']:
            results_list = [
                {"user_id": player_a['user_id'], "result": "WIN"},
                {"user_id": player_b['user_id'], "result": "LOSS"}
            ]
        elif winner_choice == player_b['name']:
            results_list = [
                {"user_id": player_b['user_id'], "result": "WIN"},
                {"user_id": player_a['user_id'], "result": "LOSS"}
            ]
        else:  # Draw
            results_list = [
                {"user_id": player_a['user_id'], "result": "DRAW"},
                {"user_id": player_b['user_id'], "result": "DRAW"}
            ]

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
    import requests
    from config import API_BASE_URL

    # Fetch tournament sessions
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            sessions = response.json()
        else:
            st.error(f"❌ Failed to load sessions: HTTP {response.status_code}")
            st.code(response.text)
            return
    except Exception as e:
        st.error(f"❌ Error loading sessions: {str(e)}")
        return

    # Filter knockout sessions
    knockout_sessions = [s for s in sessions if s.get('tournament_phase') == 'Knockout Stage']

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
    """Display knockout bracket (like World Cup/Euro style)"""
    st.markdown("### 🏆 Knockout Stage Bracket")
    st.info("✅ Group stage finalized! Top 2 from each group advance to knockout rounds.")
    st.markdown("---")

    # Get user names from group standings
    user_names = {}
    if leaderboard_data.get('group_standings'):
        for group_id, standings in leaderboard_data['group_standings'].items():
            for player in standings:
                user_names[player['user_id']] = player['name']

    # Hardcoded bracket structure for 4-player knockout (2 semifinals + 1 final)
    # In real implementation, this would be fetched from API

    st.markdown("#### ⚔️ Semifinals")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Match 1**")
        # Get top 2 from each group
        groups = sorted(leaderboard_data['group_standings'].items())
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

    # Progress bar
    total = leaderboard_data.get("total_matches", 0)
    completed = leaderboard_data.get("completed_matches", 0)

    if total > 0:
        progress = completed / total
        st.progress(progress, text=f"Progress: {completed}/{total} matches completed")

    st.markdown("---")

    # ✅ Check if group stage is finalized (from leaderboard response)
    group_stage_finalized = leaderboard_data.get("group_stage_finalized", False)

    # ✅ NEW: Show group standings OR knockout bracket
    if group_standings and group_stage_finalized:
        # Show knockout bracket instead of group standings
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

    # Display global rankings (fallback if no group standings)
    if leaderboard:
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
