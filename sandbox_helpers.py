"""
Sandbox Helper Functions

Reusable functions for the tournament sandbox application.
All API calls use the centralized api_client from streamlit_components.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.feedback import Error, Success, Loading


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
    """Fetch active game presets"""
    try:
        data = api_client.get("/api/v1/game-presets/")
        return data.get("presets", [])
    except APIError as e:
        Error.message(f"Failed to fetch game presets: {e.message}")
        return []


def fetch_preset_details(preset_id: int) -> Optional[Dict]:
    """Fetch full preset configuration"""
    try:
        return api_client.get(f"/api/v1/game-presets/{preset_id}")
    except APIError as e:
        Error.message(f"Failed to fetch preset details: {e.message}")
        return None


def update_preset(preset_id: int, update_data: Dict) -> bool:
    """Update game preset"""
    try:
        api_client.patch(f"/api/v1/game-presets/{preset_id}", data=update_data)
        Success.message("Preset updated successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to update preset: {e.message}")
        return False


def create_preset(preset_data: Dict) -> bool:
    """Create new game preset"""
    try:
        api_client.post("/api/v1/game-presets/", data=preset_data)
        Success.message("Preset created successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to create preset: {e.message}")
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

    card = Card(title=title, card_id=f"leaderboard_{tournament_id}")
    with card.container():
        # Display leaderboard table
        if 'leaderboard' in leaderboard_data and leaderboard_data['leaderboard']:
            rankings = leaderboard_data['leaderboard']

            # Build table data
            table_data = []
            for rank_data in rankings[:10]:  # Show top 10
                player_name = rank_data.get('name') or rank_data.get('username', 'Unknown')
                gd = rank_data.get('goal_difference', 0)
                table_data.append({
                    "Rank": f"#{rank_data.get('rank', '?')}",
                    "Player": player_name,
                    "Points": rank_data.get('points', 0),
                    "Goals": f"{rank_data.get('goals_for', 0)}-{rank_data.get('goals_against', 0)}",
                    "GD": f"{gd:+d}" if gd != 0 else "0",
                    "Record": f"{rank_data.get('wins', 0)}W-{rank_data.get('draws', 0)}D-{rank_data.get('losses', 0)}L"
                })

            st.table(table_data)

            # Show completion progress
            total_matches = leaderboard_data.get('total_matches', 0)
            completed_matches = leaderboard_data.get('completed_matches', 0)
            if total_matches > 0:
                progress = completed_matches / total_matches
                st.progress(progress)
                st.caption(f"Progress: {completed_matches}/{total_matches} matches completed ({progress*100:.0f}%)")
        else:
            st.info("No rankings yet. Submit match results to see standings.")

    card.close_container()


def calculate_tournament_stats(tournaments: List[Dict]) -> Dict[str, int]:
    """Calculate tournament statistics"""
    return {
        'total': len(tournaments),
        'completed': sum(1 for t in tournaments if t.get('tournament_status') == 'COMPLETED'),
        'in_progress': sum(1 for t in tournaments if t.get('tournament_status') == 'IN_PROGRESS'),
        'draft': sum(1 for t in tournaments if t.get('tournament_status') == 'DRAFT')
    }
