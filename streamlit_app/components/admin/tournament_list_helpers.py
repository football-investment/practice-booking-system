"""
Tournament List Helper Functions

Reusable functions for tournament list module.
All API calls use centralized api_client from streamlit_components.
"""

import streamlit as st
import os
import psycopg2
from typing import List, Dict, Optional
from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.feedback import Error, Success


def get_user_names_from_db(user_ids: List[int]) -> Dict[int, str]:
    """Fetch user names from database by IDs"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        if not user_ids:
            return {}

        query = """
            SELECT id, name, email
            FROM users
            WHERE id = ANY(%s)
        """
        cursor.execute(query, (user_ids,))
        rows = cursor.fetchall()

        user_names = {}
        for row in rows:
            user_id, name, email = row
            display_name = f"{name} ({email})" if name else email
            user_names[user_id] = display_name

        cursor.close()
        conn.close()
        return user_names

    except Exception as e:
        Error.message(f"Error fetching user names: {str(e)}")
        return {}


def get_tournament_sessions_from_db(tournament_id: int) -> List[Dict]:
    """Fetch tournament sessions from database"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        query = """
            SELECT
                id, title, tournament_phase, tournament_round,
                group_identifier, match_format, scoring_type,
                participant_user_ids, scheduled_start_time, duration_minutes
            FROM sessions
            WHERE semester_id = %s
            ORDER BY scheduled_start_time, id
        """
        cursor.execute(query, (tournament_id,))
        rows = cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append({
                'id': row[0],
                'title': row[1],
                'tournament_phase': row[2],
                'tournament_round': row[3],
                'group_identifier': row[4],
                'match_format': row[5],
                'scoring_type': row[6],
                'participant_user_ids': row[7],
                'scheduled_start_time': row[8],
                'duration_minutes': row[9]
            })

        cursor.close()
        conn.close()
        return sessions

    except Exception as e:
        Error.message(f"Error fetching sessions: {str(e)}")
        return []


def get_location_info(location_id: int) -> Dict[str, str]:
    """Get location information"""
    try:
        location = api_client.get(f"/api/v1/admin/locations/{location_id}")
        return {
            'id': location.get('id'),
            'name': location.get('name', 'Unknown')
        }
    except APIError:
        return {'id': location_id, 'name': 'Unknown'}


def get_campus_info(campus_id: int) -> Dict[str, str]:
    """Get campus information"""
    try:
        campus = api_client.get(f"/api/v1/admin/campuses/{campus_id}")
        return {
            'id': campus.get('id'),
            'name': campus.get('name', 'Unknown')
        }
    except APIError:
        return {'id': campus_id, 'name': 'Unknown'}


def get_all_tournaments() -> List[Dict]:
    """Fetch all tournaments"""
    try:
        response = api_client.get("/api/v1/semesters/")
        if isinstance(response, dict):
            return response.get('semesters', [])
        return response if response else []
    except APIError as e:
        Error.message(f"Failed to fetch tournaments: {e.message}")
        return []


def get_tournament_sessions(tournament_id: int) -> List[Dict]:
    """Fetch tournament sessions via API"""
    try:
        return api_client.get(f"/api/v1/tournaments/{tournament_id}/sessions")
    except APIError as e:
        Error.message(f"Failed to fetch sessions: {e.message}")
        return []


def update_tournament(tournament_id: int, data: Dict) -> bool:
    """Update tournament"""
    try:
        api_client.patch(f"/api/v1/semesters/{tournament_id}", data=data)
        Success.message("Tournament updated successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to update tournament: {e.message}")
        return False


def get_tournament_enrollment_count(tournament_id: int) -> int:
    """Get enrollment count"""
    try:
        result = api_client.get(f"/api/v1/tournaments/{tournament_id}/enrollment-count")
        return result.get('count', 0)
    except APIError:
        return 0


def generate_tournament_sessions(tournament_id: int, data: Dict) -> Optional[Dict]:
    """Generate tournament sessions"""
    try:
        result = api_client.post(f"/api/v1/tournaments/{tournament_id}/generate-sessions", data=data)
        Success.message("Sessions generated successfully!")
        return result
    except APIError as e:
        Error.api_error(e, show_details=True)
        return None


def preview_tournament_sessions(tournament_id: int, data: Dict) -> Optional[Dict]:
    """Preview tournament sessions"""
    try:
        return api_client.post(f"/api/v1/tournaments/{tournament_id}/preview-sessions", data=data)
    except APIError as e:
        Error.message(f"Failed to preview sessions: {e.message}")
        return None


def delete_generated_sessions(tournament_id: int) -> bool:
    """Delete generated sessions"""
    try:
        api_client.delete(f"/api/v1/tournaments/{tournament_id}/sessions")
        Success.message("Sessions deleted successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to delete sessions: {e.message}")
        return False


def save_tournament_reward_config(tournament_id: int, config: Dict) -> bool:
    """Save reward configuration"""
    try:
        api_client.post(f"/api/v1/tournaments/{tournament_id}/reward-config", data=config)
        Success.message("Reward config saved successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to save reward config: {e.message}")
        return False
