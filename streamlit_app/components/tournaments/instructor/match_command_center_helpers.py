"""
Match Command Center Helper Functions

Reusable functions for match command center module.
All API calls use centralized api_client from streamlit_components.
"""

from typing import Dict, Any, Optional, List
from streamlit_components.core.api_client import api_client, APIError
from streamlit_components.feedback import Error, Success


def parse_time_format(time_str: str) -> float:
    """Parse MM:SS.CC time format to total seconds"""
    time_str = time_str.strip().replace(' ', '')

    if not time_str:
        raise ValueError("Empty input")

    if ':' not in time_str:
        try:
            seconds = float(time_str)
            if seconds < 0:
                raise ValueError("Time cannot be negative")
            return seconds
        except ValueError:
            raise ValueError("Invalid number format")

    parts = time_str.split(':')
    if len(parts) != 2:
        raise ValueError("Use MM:SS.CC format (e.g., 1:30.45)")

    try:
        minutes = int(parts[0])
        seconds = float(parts[1])
    except ValueError:
        raise ValueError("Invalid time format")

    if minutes < 0 or seconds < 0:
        raise ValueError("Time cannot be negative")
    if seconds >= 60:
        raise ValueError("Seconds must be < 60")

    return minutes * 60 + seconds


def format_time_display(total_seconds: float) -> str:
    """Convert total seconds to MM:SS.CC display format"""
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:05.2f}"


def get_active_match(tournament_id: int) -> Optional[Dict[str, Any]]:
    """Fetch the active match for the tournament"""
    try:
        return api_client.get(f"/api/v1/tournaments/{tournament_id}/active-match")
    except APIError as e:
        Error.message(f"Failed to fetch active match: {e.message}")
        return None


def mark_attendance(session_id: int, user_id: int, status: str) -> bool:
    """Mark attendance for a participant"""
    try:
        api_client.post(
            f"/api/v1/sessions/{session_id}/attendance",
            data={"user_id": user_id, "status": status}
        )
        Success.message(f"Marked {status}")
        return True
    except APIError as e:
        Error.message(f"Failed to mark attendance: {e.message}")
        return False


def get_rounds_status(session_id: int) -> Optional[Dict]:
    """Get rounds status for a session"""
    try:
        return api_client.get(f"/api/v1/sessions/{session_id}/rounds-status")
    except APIError as e:
        Error.message(f"Failed to fetch rounds status: {e.message}")
        return None


def submit_round_results(tournament_id: int, session_id: int, round_number: int, results: Dict[str, str]) -> bool:
    """
    Submit results for a round in an INDIVIDUAL_RANKING tournament.

    Args:
        tournament_id: Tournament ID
        session_id: Session ID
        round_number: Round number (1, 2, 3, ...)
        results: Dict mapping user_id (str) to measured value (str), e.g., {"123": "12.5s", "456": "95"}
    """
    try:
        api_client.post(
            f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results",
            data={
                "round_number": round_number,
                "results": results,
                "notes": None
            }
        )
        Success.message(f"Round {round_number} results submitted!")
        return True
    except APIError as e:
        Error.message(f"Failed to submit round results: {e.message}")
        return False


def finalize_individual_ranking_session(session_id: int) -> bool:
    """Finalize individual ranking session"""
    try:
        api_client.post(f"/api/v1/sessions/{session_id}/finalize-individual-ranking")
        Success.message("Session finalized successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to finalize session: {e.message}")
        return False


def submit_match_results(session_id: int, results: Dict) -> bool:
    """Submit match results"""
    try:
        api_client.post(
            f"/api/v1/sessions/{session_id}/results",
            data=results
        )
        Success.message("Results submitted successfully!")
        return True
    except APIError as e:
        Error.message(f"Failed to submit results: {e.message}")
        return False


def get_leaderboard(tournament_id: int) -> Optional[Dict[str, Any]]:
    """Fetch tournament leaderboard"""
    try:
        return api_client.get(f"/api/v1/tournaments/{tournament_id}/leaderboard")
    except APIError as e:
        Error.message(f"Failed to fetch leaderboard: {e.message}")
        return None
