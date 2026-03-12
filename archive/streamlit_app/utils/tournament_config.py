"""
Shared tournament configuration utilities.

Provides helpers for:
- Unwrapping ROUNDS_BASED scoring type to underlying measurement type
- Getting unit/label pairs for scoring types

Used by: leaderboard.py, result_entry.py, tournament_monitor.py, session_grid.py
"""


def unwrap_scoring_type(session: dict) -> str:
    """
    Unwrap ROUNDS_BASED to underlying scoring_method from structure_config.

    ROUNDS_BASED sessions store the actual measurement type
    (TIME_BASED, DISTANCE_BASED, SCORE_BASED) in structure_config.scoring_method.
    This function resolves it transparently.

    Args:
        session: Session dict from API response

    Returns:
        Resolved scoring type string (e.g. "TIME_BASED", "SCORE_BASED")
    """
    raw = session.get("scoring_type", "")
    if raw != "ROUNDS_BASED":
        return raw
    cfg = session.get("structure_config") or {}
    return cfg.get("scoring_method") or cfg.get("scoring_type") or "TIME_BASED"


def scoring_unit(scoring_type: str) -> tuple[str, str]:
    """
    Returns (unit_label, agg_label) for a scoring type.

    Args:
        scoring_type: e.g. "TIME_BASED", "DISTANCE_BASED", "SCORE_BASED", "ROUNDS_BASED"

    Returns:
        Tuple of (unit_label, agg_label):
        - TIME_BASED / ROUNDS_BASED: ("s", "best")
        - DISTANCE_BASED:            ("m", "best")
        - SCORE_BASED / others:      ("pts", "best")
    """
    if "TIME" in scoring_type or scoring_type == "ROUNDS_BASED":
        return "s", "best"
    if "DISTANCE" in scoring_type:
        return "m", "best"
    return "pts", "best"
