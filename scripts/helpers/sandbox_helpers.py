"""
Sandbox Helper Functions

Reusable functions for the tournament sandbox application.
All API calls use the centralized api_client from streamlit_components.
Game presets are loaded from JSON files for persistence across database resets.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.feedback import Error, Success, Loading

# Path to game presets directory
PRESETS_DIR = Path(__file__).parent / "config" / "game_presets"


def fetch_locations() -> List[Dict]:
    """Fetch available locations from backend"""
    try:
        return api_client.get("/api/v1/admin/locations")
    except APIError as e:
        Error.message(f"Failed to fetch locations: {e.message}")
        return []


def fetch_campuses_by_location(location_id: int) -> List[Dict]:
    """Fetch campuses filtered by location"""
    try:
        return api_client.get(f"/api/v1/admin/locations/{location_id}/campuses")
    except APIError as e:
        Error.message(f"Failed to fetch campuses: {e.message}")
        return []


def fetch_users(search: str = None, limit: int = 50) -> List[Dict]:
    """Fetch users for selection"""
    params = {"limit": limit}
    if search:
        params["search"] = search

    try:
        return api_client.get("/api/v1/sandbox/users", params=params)
    except APIError as e:
        Error.message(f"Failed to fetch users: {e.message}")
        return []


def fetch_instructors() -> List[Dict]:
    """Fetch available instructors"""
    try:
        return api_client.get("/api/v1/sandbox/instructors")
    except APIError as e:
        Error.message(f"Failed to fetch instructors: {e.message}")
        return []


def fetch_game_presets() -> List[Dict]:
    """Fetch active game presets from API (database)"""
    try:
        response = api_client.get("/api/v1/game-presets/")
        # API returns {"presets": [...]} format
        return response.get("presets", []) if isinstance(response, dict) else []
    except APIError as e:
        Error.message(f"Failed to fetch game presets: {e.message}")
        return []


def fetch_preset_details(preset_id: int) -> Optional[Dict]:
    """Fetch full preset configuration from API (database)"""
    try:
        return api_client.get(f"/api/v1/game-presets/{preset_id}")
    except APIError as e:
        Error.message(f"Failed to fetch preset details: {e.message}")
        return None


def create_game_preset(code: str, name: str, description: str, game_config: Dict) -> Optional[Dict]:
    """Create a new game preset via API"""
    try:
        payload = {
            "code": code,
            "name": name,
            "description": description,
            "game_config": game_config,
            "is_active": True,
            "is_recommended": False,
            "is_locked": False
        }

        # DEBUG: Check auth token
        auth_token = st.session_state.get("auth_token")
        user_role = st.session_state.get("user_role")
        current_user = st.session_state.get("current_user")

        st.write("**DEBUG: Authentication Status:**")
        st.write(f"- Auth token exists: {auth_token is not None}")
        st.write(f"- Token preview: {auth_token[:20] + '...' if auth_token else 'None'}")
        st.write(f"- User role: {user_role}")
        st.write(f"- Current user: {current_user.get('email') if current_user else 'None'}")

        st.write("**DEBUG: Create Preset Payload:**")
        st.json(payload)

        # Call API - pass payload as positional arg, it becomes the 'data' param
        response = api_client.post("/api/v1/game-presets/", payload)

        st.write("**DEBUG: API Response:**")
        st.json(response)

        return response
    except APIError as e:
        st.error(f"**DEBUG: APIError details:**")
        st.write(f"- Message: {e.message}")
        st.write(f"- Status code: {e.status_code}")
        st.write(f"- Detail: {e.detail}")
        Error.message(f"Failed to create preset: {e.message}")
        return None
    except Exception as e:
        st.error(f"**DEBUG: Unexpected error:**")
        st.write(f"- Type: {type(e).__name__}")
        st.write(f"- Message: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        Error.message(f"Failed to create preset: {str(e)}")
        return None


def update_preset(preset_id: int, update_data: Dict) -> bool:
    """Update game preset via API (database)"""
    try:
        # Fetch current preset from API
        current_preset = fetch_preset_details(preset_id)
        if not current_preset:
            Error.message(f"Preset with ID {preset_id} not found")
            return False

        # Prepare update payload
        game_config = current_preset.get('game_config', {})

        # Update game_config with new data
        if 'skill_config' in update_data:
            game_config['skill_config'] = update_data['skill_config']

        if 'metadata' in update_data:
            game_config['metadata'] = update_data['metadata']

        if 'format_config' in update_data:
            game_config['format_config'] = update_data['format_config']

        if 'simulation_config' in update_data:
            game_config['simulation_config'] = update_data['simulation_config']

        # Build full update payload
        payload = {
            "name": update_data.get('name', current_preset.get('name')),
            "description": update_data.get('description', current_preset.get('description')),
            "game_config": game_config,
            "is_active": update_data.get('is_active', current_preset.get('is_active', True)),
            "is_recommended": update_data.get('is_recommended', current_preset.get('is_recommended', False)),
            "is_locked": update_data.get('is_locked', current_preset.get('is_locked', False))
        }

        # Update via API
        response = api_client.patch(f"/api/v1/game-presets/{preset_id}", payload)

        if response:
            Success.message("✅ Preset updated successfully!")
            return True
        else:
            Error.message("Failed to update preset")
            return False

    except APIError as e:
        Error.message(f"Failed to update preset: {e.message}")
        return False
    except Exception as e:
        Error.message(f"Failed to update preset: {str(e)}")
        return False


def create_preset(preset_data: Dict) -> bool:
    """Create new game preset in JSON file"""
    try:
        # Generate ID from existing presets
        presets = fetch_game_presets()
        max_id = max([p.get('id', 0) for p in presets], default=0)
        new_id = max_id + 1

        preset_data['id'] = new_id

        # Get code for filename
        code = preset_data.get('code')
        if not code:
            Error.message("Preset code is required")
            return False

        preset_file = PRESETS_DIR / f"{code}.json"

        if preset_file.exists():
            Error.message(f"Preset with code '{code}' already exists")
            return False

        # Write to JSON file
        with open(preset_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)

        Success.message("✅ Preset created in JSON file successfully!")
        return True
    except Exception as e:
        Error.message(f"Failed to create preset: {e}")
        return False


def validate_and_fix_tournament_id(tournament_id: int) -> Optional[int]:
    """
    Validate tournament_id and fix if it's actually a session_id.

    This handles the common bug where session_id gets stored as tournament_id.

    Args:
        tournament_id: The ID to validate

    Returns:
        Valid tournament_id or None if not found
    """
    try:
        # First try to fetch as tournament directly
        tournament = api_client.get(f"/api/v1/tournaments/{tournament_id}/summary")
        if tournament:
            # Valid tournament ID
            return tournament_id
    except APIError:
        pass

    # Not a valid tournament ID - try sessions endpoint (will work if it's a valid tournament)
    try:
        sessions = api_client.get(f"/api/v1/tournaments/{tournament_id}/sessions")
        if sessions and len(sessions) > 0:
            # This means tournament_id is valid (sessions endpoint worked)
            return tournament_id
    except APIError:
        pass

    # Last attempt: maybe it's a session ID? Query all recent tournaments and find matching session
    try:
        all_tournaments = fetch_tournaments()
        for tournament in all_tournaments[:50]:  # Check last 50 tournaments
            t_id = tournament.get('id')
            if not t_id:
                continue
            try:
                sessions = api_client.get(f"/api/v1/tournaments/{t_id}/sessions")
                for session in sessions:
                    if session.get('id') == tournament_id:
                        # Found it! This tournament_id is actually a session_id
                        Success.toast(f"⚠️ Auto-corrected: {tournament_id} (session) → {t_id} (tournament)")
                        return t_id
            except APIError:
                continue
    except Exception:
        pass

    # If we get here, the ID is invalid
    Error.message(f"Invalid tournament_id: {tournament_id}. Please create a new tournament or select from history.")
    return None


def fetch_leaderboard(tournament_id: int) -> Optional[Dict]:
    """Fetch tournament leaderboard data"""
    # Validate tournament_id first
    valid_id = validate_and_fix_tournament_id(tournament_id)
    if not valid_id:
        return None

    try:
        return api_client.get(f"/api/v1/tournaments/{valid_id}/leaderboard")
    except APIError as e:
        Error.message(f"Failed to fetch leaderboard: {e.message}")
        return None


def fetch_tournament_sessions(tournament_id: int) -> List[Dict]:
    """Fetch sessions for a tournament"""
    # Validate tournament_id first
    valid_id = validate_and_fix_tournament_id(tournament_id)
    if not valid_id:
        return []

    try:
        return api_client.get(f"/api/v1/tournaments/{valid_id}/sessions")
    except APIError as e:
        Error.message(f"Failed to fetch sessions: {e.message}")
        return []


def fetch_tournaments() -> List[Dict]:
    """Fetch all tournaments (semesters)"""
    try:
        response_data = api_client.get("/api/v1/semesters/")

        # Handle both dict {'semesters': [...]} and list [...] formats
        if isinstance(response_data, dict):
            return response_data.get('semesters', [])
        return response_data if response_data else []
    except APIError as e:
        Error.message(f"Failed to fetch tournaments: {e.message}")
        return []


def get_sandbox_tournaments() -> List[Dict]:
    """Fetch only sandbox tournaments with enriched data"""
    all_tournaments = fetch_tournaments()
    sandbox_tournaments = [
        t for t in all_tournaments
        if 'SANDBOX' in t.get('code', '') or 'sandbox' in t.get('code', '').lower()
    ]

    # Enrich with participant_count and game_preset_name from tournament details
    for tournament in sandbox_tournaments:
        tournament_id = tournament.get('id')
        if tournament_id:
            try:
                # Fetch detailed tournament info to get participant_count and game_preset_name
                details = api_client.get(f"/api/v1/tournaments/{tournament_id}/summary")
                if details:
                    tournament['participant_count'] = details.get('total_participants', 0)
                    # Try to get game preset name from game_config or tournament details
                    if 'game_preset_name' in details:
                        tournament['game_preset_name'] = details['game_preset_name']
            except:
                # If enrichment fails, use defaults
                tournament.setdefault('participant_count', 0)
                tournament.setdefault('game_preset_name', None)

    return sandbox_tournaments


def fetch_tournament_status(tournament_id: int) -> str:
    """
    Fetch tournament status for E2E testing

    Returns the tournament_status enum value (e.g., "REWARDS_DISTRIBUTED")
    """
    try:
        details = api_client.get(f"/api/v1/tournaments/{tournament_id}/summary")
        if details:
            return details.get('tournament_status', 'UNKNOWN')
        return 'UNKNOWN'
    except APIError:
        return 'UNKNOWN'


def render_mini_leaderboard(tournament_id: int, title: str = "Current Standings") -> None:
    """
    Render a compact leaderboard view for use in workflow steps

    Args:
        tournament_id: Tournament ID
        title: Title for the leaderboard section
    """
    from streamlit_components.layouts import Card

    # Validate tournament_id first
    valid_id = validate_and_fix_tournament_id(tournament_id)
    if not valid_id:
        st.error(f"❌ Invalid tournament ID: {tournament_id}. Please restart the workflow or select a tournament from history.")
        return

    leaderboard_data = fetch_leaderboard(valid_id)

    # 🐛 DEBUG PANEL: Show raw API response
    with st.expander("🐛 DEBUG: Raw Leaderboard API Response", expanded=False):
        st.write(f"**Tournament ID (original):** {tournament_id}")
        st.write(f"**Tournament ID (validated):** {valid_id}")
        if leaderboard_data:
            st.json(leaderboard_data)
        else:
            st.error("❌ No leaderboard data returned from API")

    if not leaderboard_data:
        return

    # Detect tournament format
    tournament_format = leaderboard_data.get('tournament_format', 'HEAD_TO_HEAD')
    is_individual = tournament_format == 'INDIVIDUAL_RANKING'

    card = Card(title=title, card_id=f"leaderboard_{tournament_id}")
    with card.container():
        # ✅ NEW APPROACH: For INDIVIDUAL_RANKING, show separate tables for each round + final standings
        if is_individual and leaderboard_data.get('performance_rankings'):
            performance_rankings = leaderboard_data['performance_rankings']
            scoring_type = leaderboard_data.get('scoring_type', 'TIME_BASED')

            # ========================================
            # FETCH SESSION DATA TO GET ROUND RESULTS
            # ========================================
            try:
                sessions = fetch_tournament_sessions(valid_id)
                round_results_data = None

                if sessions and len(sessions) > 0:
                    # Get first session (assuming single session for INDIVIDUAL_RANKING)
                    session = sessions[0]
                    rounds_data = session.get('rounds_data', {})
                    round_results_data = rounds_data.get('round_results', {}) if rounds_data else None
            except Exception as e:
                st.warning(f"Could not load round-by-round data: {e}")
                round_results_data = None

            # ========================================
            # DISPLAY ROUND-BY-ROUND TABLES
            # ========================================
            if round_results_data and len(round_results_data) > 0:
                # Display each round as a separate ranked table
                for round_num_str in sorted(round_results_data.keys(), key=lambda x: int(x)):
                    round_num = int(round_num_str)
                    round_data = round_results_data[round_num_str]

                    st.markdown(f"### 🏁 Round {round_num} Results")

                    # Build table for this round
                    round_table = []
                    for user_id_str, value_str in round_data.items():
                        user_id = int(user_id_str)

                        # Parse time value
                        try:
                            time_value = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
                        except (ValueError, TypeError):
                            time_value = 999.99

                        # Get player name from performance_rankings
                        player_name = "Unknown"
                        for p in performance_rankings:
                            if p.get('user_id') == user_id:
                                player_name = p.get('name', 'Unknown')
                                break

                        # If not found, try leaderboard
                        if player_name == "Unknown":
                            leaderboard = leaderboard_data.get('leaderboard', [])
                            for player in leaderboard:
                                if player.get('user_id') == user_id:
                                    player_name = player.get('name', 'Unknown')
                                    break

                        round_table.append({
                            'user_id': user_id,
                            'name': player_name,
                            'time': time_value
                        })

                    # Sort by time (ASC for TIME_BASED)
                    if scoring_type == 'TIME_BASED':
                        round_table.sort(key=lambda x: x['time'])
                    else:
                        round_table.sort(key=lambda x: x['time'], reverse=True)

                    # Add ranks and format
                    display_table = []
                    for rank, entry in enumerate(round_table, start=1):
                        # Medal emoji for top 3
                        if rank == 1:
                            rank_display = "🥇 1st"
                        elif rank == 2:
                            rank_display = "🥈 2nd"
                        elif rank == 3:
                            rank_display = "🥉 3rd"
                        else:
                            rank_display = f"#{rank}"

                        # Format value based on scoring type
                        if scoring_type == 'TIME_BASED':
                            value_display = f"{entry['time']:.2f}s"
                            column_header = "Time"
                        elif scoring_type == 'DISTANCE_BASED':
                            value_display = f"{entry['time']:.2f}m"
                            column_header = "Distance"
                        elif scoring_type == 'SCORE_BASED' or scoring_type == 'ROUNDS_BASED':
                            value_display = f"{entry['time']:.0f} pts"
                            column_header = "Points"
                        else:
                            value_display = f"{entry['time']:.2f}"
                            column_header = "Score"

                        display_table.append({
                            "Rank": rank_display,
                            "Player": entry['name'],
                            column_header: value_display
                        })

                    # ✅ FIX: Use st.dataframe with hide_index=True to prevent 0-based ranking display
                    import pandas as pd
                    df = pd.DataFrame(display_table)
                    st.dataframe(df, hide_index=True, use_container_width=True)
                    st.markdown("---")

                # ========================================
                # FINAL STANDINGS (Best overall)
                # ========================================
                st.markdown("### 🏆 Final Standings (Best Performance)")

                # Build user_id to name mapping from leaderboard
                leaderboard = leaderboard_data.get('leaderboard', [])
                user_names = {u['user_id']: u.get('name', u.get('email', 'Unknown')) for u in leaderboard}

                # ✅ TIED RANKS: Detect tied ranks and give same medal to all tied players
                # Group performance_rankings by rank to detect ties
                rank_groups = {}
                for rank_data in performance_rankings[:10]:
                    rank = rank_data.get('rank', '?')
                    if rank not in rank_groups:
                        rank_groups[rank] = []
                    rank_groups[rank].append(rank_data)

                # UI Testing Contract: Rankings Table with data-testid attributes
                # Get winner_count from leaderboard_data (backend should provide this)
                winner_count = leaderboard_data.get('winner_count', 3)  # Default to 3 if not provided

                rankings_html = '<div data-testid="tournament-rankings"><table data-testid="rankings-table" style="width:100%; border-collapse: collapse;"><tbody>'

                for rank_data in performance_rankings[:10]:
                    perf_rank = rank_data.get('rank', '?')
                    user_id = rank_data.get('user_id')
                    player_name = user_names.get(user_id, rank_data.get('name', 'Unknown'))
                    best_score = rank_data.get('best_score') or rank_data.get('final_value', 0)

                    # Determine if winner based on rank and winner_count
                    is_winner = "true" if perf_rank <= winner_count else "false"

                    # Check if this rank is tied (multiple players with same rank)
                    is_tied = len(rank_groups.get(perf_rank, [])) > 1

                    # Medal emoji with tied rank indicator
                    if perf_rank == 1:
                        rank_display = "🥇 1st" + (" [TIE]" if is_tied else "")
                    elif perf_rank == 2:
                        rank_display = "🥈 2nd" + (" [TIE]" if is_tied else "")
                    elif perf_rank == 3:
                        rank_display = "🥉 3rd" + (" [TIE]" if is_tied else "")
                    else:
                        rank_display = f"#{perf_rank}" + (" [TIE]" if is_tied else "")

                    # Format score based on scoring type
                    if scoring_type == 'TIME_BASED':
                        score_display = f"{best_score:.2f}s"
                    elif scoring_type == 'DISTANCE_BASED':
                        score_display = f"{best_score:.2f}m"
                    elif scoring_type == 'SCORE_BASED' or scoring_type == 'ROUNDS_BASED':
                        score_display = f"{best_score:.0f} pts"
                    else:
                        score_display = f"{best_score:.2f}"

                    # Winner badge if applicable
                    winner_badge = '<span data-testid="winner-badge">🏆</span> ' if is_winner == "true" else ''

                    rankings_html += f'<tr data-testid="ranking-row" data-user-id="{user_id}" data-rank="{perf_rank}" data-is-winner="{is_winner}" style="border-bottom: 1px solid #ddd;"><td data-testid="rank" style="padding: 8px;">{winner_badge}{rank_display}</td><td data-testid="player-name" style="padding: 8px;">{player_name}</td><td data-testid="final-score" style="padding: 8px;">{score_display}</td></tr>'

                rankings_html += '</tbody></table></div>'
                st.markdown(rankings_html, unsafe_allow_html=True)

            else:
                # Fallback: No round data, show simple final standings
                st.markdown("### 🏆 Final Standings")

                # Build user_id to name mapping from leaderboard
                leaderboard = leaderboard_data.get('leaderboard', [])
                user_names = {u['user_id']: u.get('name', u.get('email', 'Unknown')) for u in leaderboard}

                # UI Testing Contract: Rankings Table with data-testid attributes
                winner_count = leaderboard_data.get('winner_count', 3)

                rankings_html = '<div data-testid="tournament-rankings"><table data-testid="rankings-table" style="width:100%; border-collapse: collapse;"><tbody>'

                for rank_data in performance_rankings[:10]:
                    perf_rank = rank_data.get('rank', '?')
                    user_id = rank_data.get('user_id')
                    player_name = user_names.get(user_id, rank_data.get('name', 'Unknown'))
                    best_score = rank_data.get('best_score') or rank_data.get('final_value', 0)

                    # Determine if winner
                    is_winner = "true" if perf_rank <= winner_count else "false"

                    # Medal emoji
                    if perf_rank == 1:
                        rank_display = "🥇 1st"
                    elif perf_rank == 2:
                        rank_display = "🥈 2nd"
                    elif perf_rank == 3:
                        rank_display = "🥉 3rd"
                    else:
                        rank_display = f"#{perf_rank}"

                    # Format score
                    if scoring_type == 'TIME_BASED':
                        score_display = f"{best_score:.2f}s"
                    elif scoring_type == 'DISTANCE_BASED':
                        score_display = f"{best_score:.2f}m"
                    elif scoring_type == 'SCORE_BASED' or scoring_type == 'ROUNDS_BASED':
                        score_display = f"{best_score:.0f} pts"
                    else:
                        score_display = f"{best_score:.2f}"

                    # Winner badge
                    winner_badge = '<span data-testid="winner-badge">🏆</span> ' if is_winner == "true" else ''

                    rankings_html += f'<tr data-testid="ranking-row" data-user-id="{user_id}" data-rank="{perf_rank}" data-is-winner="{is_winner}" style="border-bottom: 1px solid #ddd;"><td data-testid="rank" style="padding: 8px;">{winner_badge}{rank_display}</td><td data-testid="player-name" style="padding: 8px;">{player_name}</td><td data-testid="final-score" style="padding: 8px;">{score_display}</td></tr>'

                rankings_html += '</tbody></table></div>'
                st.markdown(rankings_html, unsafe_allow_html=True)

        # Display leaderboard table (for HEAD_TO_HEAD tournaments)
        elif 'leaderboard' in leaderboard_data and leaderboard_data['leaderboard']:
            rankings = leaderboard_data['leaderboard']

            # Get scoring type for format-specific columns
            scoring_type = leaderboard_data.get('scoring_type', 'PLACEMENT')

            # Build table data based on tournament format and scoring type
            table_data = []
            for rank_data in rankings[:10]:  # Show top 10
                player_name = rank_data.get('name') or rank_data.get('username', 'Unknown')

                if is_individual:
                    # INDIVIDUAL_RANKING: Format based on scoring_type
                    if scoring_type in ['TIME_BASED', 'DISTANCE_BASED', 'SCORE_BASED']:
                        # Show only rank, player, and result (no goals/GD/record)
                        result_value = rank_data.get('points', 0)  # Points field stores the actual result

                        # Format based on scoring type
                        if scoring_type == 'TIME_BASED':
                            result_display = f"{result_value:.2f}s"
                        elif scoring_type == 'DISTANCE_BASED':
                            result_display = f"{result_value:.2f}m"
                        elif scoring_type == 'SCORE_BASED':
                            result_display = f"{result_value:.0f} pts"
                        else:
                            result_display = f"{result_value:.2f}"

                        row = {
                            "Rank": f"#{rank_data.get('rank', '?')}",
                            "Player": player_name,
                            "Result": result_display
                        }
                    else:
                        # PLACEMENT or other: Show only rank and player
                        row = {
                            "Rank": f"#{rank_data.get('rank', '?')}",
                            "Player": player_name,
                            "Best Score": rank_data.get('best_score', 'N/A')
                        }
                else:
                    # HEAD_TO_HEAD: Show full match statistics (goals, GD, record)
                    gd = rank_data.get('goal_difference', 0)
                    row = {
                        "Rank": f"#{rank_data.get('rank', '?')}",
                        "Player": player_name,
                        "Points": rank_data.get('points', 0),
                        "Goals": f"{rank_data.get('goals_for', 0)}-{rank_data.get('goals_against', 0)}",
                        "GD": f"{gd:+d}" if gd != 0 else "0",
                        "Record": f"{rank_data.get('wins', 0)}W-{rank_data.get('draws', 0)}D-{rank_data.get('losses', 0)}L"
                    }

                table_data.append(row)

            # UI Testing Contract: HEAD_TO_HEAD rankings with data-testid
            rankings_html = '<div data-testid="tournament-rankings"><table data-testid="rankings-table" style="width:100%; border-collapse: collapse;"><tbody>'

            for row_data in table_data:
                rank = row_data.get('Rank', '?')
                player = row_data.get('Player', 'Unknown')

                rankings_html += f'<tr data-testid="ranking-row" style="border-bottom: 1px solid #ddd;">'
                rankings_html += f'<td data-testid="rank" style="padding: 8px;">{rank}</td>'
                rankings_html += f'<td data-testid="player-name" style="padding: 8px;">{player}</td>'

                # Add additional columns based on row data
                for key, value in row_data.items():
                    if key not in ['Rank', 'Player']:
                        rankings_html += f'<td style="padding: 8px;">{value}</td>'

                rankings_html += '</tr>'

            rankings_html += '</tbody></table></div>'
            st.markdown(rankings_html, unsafe_allow_html=True)

            # Show completion progress
            total_matches = leaderboard_data.get('total_matches', 0)
            completed_matches = leaderboard_data.get('completed_matches', 0)
            if total_matches > 0:
                progress = completed_matches / total_matches
                st.progress(progress)
                if is_individual:
                    st.caption(f"Progress: {completed_matches}/{total_matches} rounds completed ({progress*100:.0f}%)")
                else:
                    st.caption(f"Progress: {completed_matches}/{total_matches} matches completed ({progress*100:.0f}%)")
        else:
            st.info("No rankings yet. Submit results to see standings.")

    card.close_container()


def fetch_distributed_rewards(tournament_id: int) -> Optional[Dict]:
    """Fetch distributed rewards for a tournament"""
    # Validate tournament_id first
    valid_id = validate_and_fix_tournament_id(tournament_id)
    if not valid_id:
        return None

    try:
        return api_client.get(f"/api/v1/tournaments/{valid_id}/distributed-rewards")
    except APIError as e:
        Error.message(f"Failed to fetch distributed rewards: {e.message}")
        return None


def render_rewards_table(tournament_id: int) -> None:
    """
    Render tables showing distributed rewards per user

    Shows two tables:
    1. Final standings with total rewards (aggregated across all rounds)
    2. Round-by-round performance breakdown

    Args:
        tournament_id: Tournament ID
    """
    from streamlit_components.layouts import Card

    # Validate tournament_id first
    valid_id = validate_and_fix_tournament_id(tournament_id)
    if not valid_id:
        st.error(f"❌ Invalid tournament ID: {tournament_id}. Please select a valid tournament from history.")
        return

    rewards_data = fetch_distributed_rewards(valid_id)

    if not rewards_data:
        return

    # Check if rewards distributed
    if not rewards_data.get('rewards_distributed', False):
        st.info(f"ℹ️ {rewards_data.get('message', 'Rewards have not been distributed yet')}")
        return

    # === TABLE 1: Final Standings with Total Rewards ===
    card = Card(title="Final Standings & Total Rewards", card_id=f"rewards_final_{tournament_id}")
    with card.container():
        # UI Testing Contract: Rewards Summary with data-testid attributes
        total_credits = rewards_data.get('total_credits_awarded', 0)
        total_xp = rewards_data.get('total_xp_awarded', 0)
        players_rewarded = rewards_data.get('rewards_count', 0)
        skill_rewards_count = sum(1 for r in rewards_data.get('rewards', []) if r.get('skill_points_awarded'))

        summary_html = f'''
        <div data-testid="rewards-summary">
            <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                <div data-testid="players-rewarded" data-value="{players_rewarded}" style="flex: 1;">
                    <strong>Total Players:</strong> {players_rewarded}
                </div>
                <div data-testid="total-xp" data-value="{total_xp}" style="flex: 1;">
                    <strong>Total XP Awarded:</strong> {total_xp}
                </div>
                <div data-testid="total-credits" data-value="{total_credits}" style="flex: 1;">
                    <strong>Total Credits Awarded:</strong> {total_credits}
                </div>
                <div data-testid="skill-rewards-count" data-value="{skill_rewards_count}" style="flex: 1;">
                    <strong>Skill Rewards:</strong> {skill_rewards_count}
                </div>
            </div>
        </div>
        '''
        st.markdown(summary_html, unsafe_allow_html=True)

        st.markdown("---")

        # Rewards table
        rewards = rewards_data.get('rewards', [])
        if rewards:
            table_data = []
            for reward in rewards:
                rank = reward.get('rank')
                rank_display = f"#{rank}" if rank else "N/A"

                # Add medal emoji for top 3
                if rank == 1:
                    rank_display = "🥇 1st"
                elif rank == 2:
                    rank_display = "🥈 2nd"
                elif rank == 3:
                    rank_display = "🥉 3rd"

                # Get skill points awarded (from skill_points_awarded dict)
                skill_points = reward.get('skill_points_awarded', {})

                # Format skill changes as a compact string
                if skill_points:
                    # Show top 3 skill changes with +/- prefix
                    skill_changes = []
                    for skill_name, points in sorted(skill_points.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
                        if points > 0:
                            skill_changes.append(f"↗️ {skill_name} +{points}")
                        elif points < 0:
                            skill_changes.append(f"↘️ {skill_name} {points}")
                    skill_display = ", ".join(skill_changes) if skill_changes else "—"
                else:
                    skill_display = "—"

                row = {
                    "Rank": rank_display,
                    "Player": reward.get('player_name', 'Unknown'),
                    "Skill Changes": skill_display,
                    "XP": reward.get('xp', 0),
                    "Credits": reward.get('credits', 0)
                }
                table_data.append(row)

            # Convert to DataFrame and hide the index column
            import pandas as pd
            df = pd.DataFrame(table_data)
            st.table(df.set_index(df.columns[0]))  # Use first column (Rank) as index
        else:
            st.info("No rewards data available")

    card.close_container()

    # === TABLE 2: Round-by-Round Performance ===
    # Fetch all rankings for this tournament (all rounds)
    try:
        from app.database import SessionLocal
        from app.models.tournament_ranking import TournamentRanking
        from app.models.user import User

        db = SessionLocal()
        try:
            all_rankings = db.query(
                TournamentRanking.user_id,
                TournamentRanking.rank,
                TournamentRanking.points,
                User.name,
                User.email
            ).join(
                User, TournamentRanking.user_id == User.id
            ).filter(
                TournamentRanking.tournament_id == valid_id
            ).order_by(
                TournamentRanking.rank
            ).all()

            if all_rankings:
                card2 = Card(title="Round-by-Round Performance", card_id=f"rewards_rounds_{tournament_id}")
                with card2.container():
                    st.caption("Individual round placements throughout the tournament")

                    # Group rankings by unique point values (each unique point value = one round)
                    # This assumes each round has unique point distributions
                    from collections import defaultdict
                    rounds_by_points = defaultdict(list)

                    for ranking in all_rankings:
                        user_id, rank, points, name, email = ranking
                        player_name = name or email
                        # Group by rank to identify rounds (each round has ranks 1, 2, 3, etc.)
                        rounds_by_points[rank].append({
                            "rank": rank,
                            "player": player_name,
                            "points": float(points) if points else 0
                        })

                    # Sort by rank to get rounds in order
                    sorted_ranks = sorted(rounds_by_points.keys())

                    # Calculate how many unique players there are
                    unique_users = set(r[0] for r in all_rankings)
                    players_per_round = len(unique_users)

                    # Group into rounds by detecting when rank resets to 1
                    import pandas as pd
                    round_num = 1
                    current_round = []
                    prev_rank = None

                    for idx, ranking in enumerate(all_rankings):
                        user_id, rank, points, name, email = ranking
                        player_name = name or email

                        # Detect new round: when rank jumps back to 1 (or a lower value)
                        if prev_rank is not None and rank == 1 and len(current_round) > 0:
                            # Finish previous round
                            st.markdown(f"**Round {round_num}**")
                            df_round = pd.DataFrame(current_round)
                            st.dataframe(df_round, use_container_width=True, hide_index=True)
                            st.markdown("---")

                            current_round = []
                            round_num += 1

                        current_round.append({
                            "Rank": f"#{rank}" if rank else "N/A",
                            "Player": player_name,
                            "Points": float(points) if points else 0
                        })
                        prev_rank = rank

                    # Display last round
                    if current_round:
                        st.markdown(f"**Round {round_num}**")
                        df_round = pd.DataFrame(current_round)
                        st.dataframe(df_round, use_container_width=True, hide_index=True)

                card2.close_container()
        finally:
            db.close()
    except Exception as e:
        st.warning(f"Could not load round-by-round data: {e}")


def auto_fill_tournament_results(tournament_id: int, session: Dict) -> bool:
    """
    Auto-fill ALL remaining rounds for a tournament session.

    This function generates random results for all uncompleted rounds
    to match the configured number_of_rounds.

    Args:
        tournament_id: The tournament ID
        session: Session dict with structure_config and rounds_data

    Returns:
        True if auto-fill succeeded, False otherwise
    """
    import random

    try:
        session_id = session.get('id')
        num_rounds = session.get('structure_config', {}).get('number_of_rounds', 3)
        scoring_method = session.get('structure_config', {}).get('scoring_method', 'SCORE_BASED')
        participants = session.get('participants', [])

        if not participants:
            Error.message("No participants found for auto-fill")
            return False

        # Get rounds_data to determine current round
        rounds_data = session.get('rounds_data', {})
        completed_rounds = rounds_data.get('completed_rounds', 0)

        # Calculate how many rounds need to be filled
        rounds_to_fill = num_rounds - completed_rounds

        if rounds_to_fill <= 0:
            Success.message(f"All {num_rounds} rounds already completed!")
            return True

        st.info(f"Auto-filling {rounds_to_fill} remaining round(s)...")

        # Auto-fill each remaining round
        for round_num in range(completed_rounds + 1, num_rounds + 1):
            round_results = {}

            # Generate random results for all participants
            for participant in participants:
                user_id_str = str(participant['id'])

                if scoring_method == 'TIME_BASED':
                    # Random time between 10.0 and 60.0 seconds
                    time_value = round(random.uniform(10.0, 60.0), 2)
                    round_results[user_id_str] = f"{time_value:.2f}s"
                else:
                    # Random score between 50 and 100
                    score_value = random.randint(50, 100)
                    round_results[user_id_str] = str(score_value)

            # Submit round results via API
            try:
                api_client.post(
                    f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_num}/submit-results",
                    data={
                        "round_number": round_num,
                        "results": round_results,
                        "notes": "Auto-generated (sandbox)"
                    }
                )
                st.success(f"✅ Round {round_num} auto-filled")
            except APIError as e:
                Error.message(f"Failed to auto-fill round {round_num}: {e.message}")
                return False

        Success.message(f"🎉 Auto-filled {rounds_to_fill} round(s) successfully!")
        return True

    except Exception as e:
        Error.message(f"Auto-fill error: {str(e)}")
        return False


# Note: auto_fill_head_to_head_results() removed - manual UI pending (sandbox_workflow.py:638)


def calculate_tournament_stats(tournaments: List[Dict]) -> Dict[str, int]:
    """Calculate tournament statistics"""
    return {
        'total': len(tournaments),
        'completed': sum(1 for t in tournaments if t.get('tournament_status') == 'COMPLETED'),
        'in_progress': sum(1 for t in tournaments if t.get('tournament_status') == 'IN_PROGRESS'),
        'draft': sum(1 for t in tournaments if t.get('tournament_status') == 'DRAFT')
    }
