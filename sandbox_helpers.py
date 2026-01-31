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
    """Fetch active game presets from JSON files"""
    try:
        presets = []

        # Read all JSON files in presets directory
        if PRESETS_DIR.exists():
            for json_file in sorted(PRESETS_DIR.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        preset = json.load(f)
                        if preset.get('is_active', True):
                            presets.append(preset)
                except json.JSONDecodeError as e:
                    Error.message(f"Invalid JSON in {json_file.name}: {e}")
                except Exception as e:
                    Error.message(f"Error reading {json_file.name}: {e}")
        else:
            Error.message(f"Presets directory not found: {PRESETS_DIR}")

        return presets
    except Exception as e:
        Error.message(f"Failed to fetch game presets: {e}")
        return []


def fetch_preset_details(preset_id: int) -> Optional[Dict]:
    """Fetch full preset configuration from JSON files"""
    try:
        # Load all presets and find by ID
        presets = fetch_game_presets()
        for preset in presets:
            if preset.get('id') == preset_id:
                return preset

        Error.message(f"Preset with ID {preset_id} not found")
        return None
    except Exception as e:
        Error.message(f"Failed to fetch preset details: {e}")
        return None


def update_preset(preset_id: int, update_data: Dict) -> bool:
    """Update game preset in JSON file"""
    try:
        # Find the preset file
        presets = fetch_game_presets()
        preset = None
        preset_file = None

        for p in presets:
            if p.get('id') == preset_id:
                preset = p
                # Find corresponding JSON file
                code = p.get('code')
                preset_file = PRESETS_DIR / f"{code}.json"
                break

        if not preset or not preset_file or not preset_file.exists():
            Error.message(f"Preset with ID {preset_id} not found")
            return False

        # Update the preset data
        if 'skill_config' in update_data:
            # Merge skill_config into game_config
            if 'game_config' not in preset:
                preset['game_config'] = {}
            preset['game_config']['skill_config'] = update_data['skill_config']

        # Write back to JSON file
        with open(preset_file, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2, ensure_ascii=False)

        Success.message("✅ Preset saved to JSON file successfully!")
        return True
    except Exception as e:
        Error.message(f"Failed to update preset: {e}")
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


def fetch_leaderboard(tournament_id: int) -> Optional[Dict]:
    """Fetch tournament leaderboard data"""
    try:
        return api_client.get(f"/api/v1/tournaments/{tournament_id}/leaderboard")
    except APIError as e:
        Error.message(f"Failed to fetch leaderboard: {e.message}")
        return None


def fetch_tournament_sessions(tournament_id: int) -> List[Dict]:
    """Fetch sessions for a tournament"""
    try:
        return api_client.get(f"/api/v1/tournaments/{tournament_id}/sessions")
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
    """Fetch only sandbox tournaments"""
    all_tournaments = fetch_tournaments()
    return [
        t for t in all_tournaments
        if 'SANDBOX' in t.get('code', '') or 'sandbox' in t.get('code', '').lower()
    ]


def render_mini_leaderboard(tournament_id: int, title: str = "Current Standings") -> None:
    """
    Render a compact leaderboard view for use in workflow steps

    Args:
        tournament_id: Tournament ID
        title: Title for the leaderboard section
    """
    from streamlit_components.layouts import Card

    leaderboard_data = fetch_leaderboard(tournament_id)

    if not leaderboard_data:
        return

    # Detect tournament format
    tournament_format = leaderboard_data.get('tournament_format', 'HEAD_TO_HEAD')
    is_individual = tournament_format == 'INDIVIDUAL_RANKING'

    card = Card(title=title, card_id=f"leaderboard_{tournament_id}")
    with card.container():
        # Display leaderboard table
        if 'leaderboard' in leaderboard_data and leaderboard_data['leaderboard']:
            rankings = leaderboard_data['leaderboard']

            # Build table data based on tournament format
            table_data = []
            for rank_data in rankings[:10]:  # Show top 10
                player_name = rank_data.get('name') or rank_data.get('username', 'Unknown')

                if is_individual:
                    # INDIVIDUAL_RANKING: Show only rank, player, and best score
                    row = {
                        "Rank": f"#{rank_data.get('rank', '?')}",
                        "Player": player_name,
                        "Best Score": rank_data.get('best_score', 'N/A')
                    }
                else:
                    # HEAD_TO_HEAD: Show full match statistics
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

            st.table(table_data)

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


def calculate_tournament_stats(tournaments: List[Dict]) -> Dict[str, int]:
    """Calculate tournament statistics"""
    return {
        'total': len(tournaments),
        'completed': sum(1 for t in tournaments if t.get('tournament_status') == 'COMPLETED'),
        'in_progress': sum(1 for t in tournaments if t.get('tournament_status') == 'IN_PROGRESS'),
        'draft': sum(1 for t in tournaments if t.get('tournament_status') == 'DRAFT')
    }
