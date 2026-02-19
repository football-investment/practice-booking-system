"""
Game Results Parser Utility

Centralises the str/dict duality of the game_results JSONB column.
SQLAlchemy may return it as a dict (native JSONB) or as a JSON string
depending on driver / ORM configuration.  All callers should use
``parse_game_results()`` instead of ad-hoc ``json.loads()`` guards.
"""
import json
from typing import Any, Dict, List


def parse_game_results(raw: Any) -> Dict:
    """
    Parse the game_results column into a plain dict.

    The column is JSONB but may arrive as:
    - A dict   (native JSONB via psycopg2 / asyncpg)
    - A string (JSON-serialised, some driver configurations)
    - None     (session not yet recorded)

    Args:
        raw: Raw value from the ORM field.

    Returns:
        Parsed dict.  Returns ``{}`` for None, invalid JSON, or unexpected types.
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def get_participants(game_results: Dict) -> List[Dict]:
    """
    Extract the participants list from parsed game_results.

    Handles two historical key names:
    - "participants"  — current format
    - "raw_results"   — legacy format (some older sessions)

    Args:
        game_results: Already-parsed dict (from ``parse_game_results``).

    Returns:
        List of participant dicts, or empty list.
    """
    return game_results.get("participants") or game_results.get("raw_results") or []
