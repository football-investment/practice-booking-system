"""
Context-Aware Terminology Helper
Renders "Session" vs "Game" based on tournament context
"""
from typing import Optional, Dict, Any


def get_session_term(semester_code: Optional[str], singular: bool = True) -> str:
    """
    Get appropriate term for session/game based on context

    Args:
        semester_code: Semester code (e.g., "TOURN-20251227")
        singular: If True, return singular form; else plural

    Returns:
        "Game"/"Games" for tournaments, "Session"/"Sessions" for regular seasons
    """
    is_tournament = semester_code and semester_code.startswith("TOURN-")

    if is_tournament:
        return "Game" if singular else "Games"
    else:
        return "Session" if singular else "Sessions"


def get_session_icon(semester_code: Optional[str]) -> str:
    """
    Get icon for session/game

    Args:
        semester_code: Semester code

    Returns:
        Icon emoji string
    """
    is_tournament = semester_code and semester_code.startswith("TOURN-")
    return "🏆" if is_tournament else "📅"


def format_session_label(session_data: Dict[str, Any], semester_code: Optional[str]) -> str:
    """
    Format session/game label with appropriate terminology

    Args:
        session_data: Session data dictionary
        semester_code: Semester code for context

    Returns:
        Formatted label string
    """
    term = get_session_term(semester_code, singular=True)
    title = session_data.get("title", "Untitled")

    # Add game type for tournaments if available
    if semester_code and semester_code.startswith("TOURN-"):
        game_type = session_data.get("game_type")
        if game_type:
            return f"{title} - {game_type}"

    return title


def is_tournament_semester(semester_code: Optional[str]) -> bool:
    """
    Check if semester is a tournament

    Args:
        semester_code: Semester code

    Returns:
        True if tournament, False otherwise
    """
    return bool(semester_code and semester_code.startswith("TOURN-"))
