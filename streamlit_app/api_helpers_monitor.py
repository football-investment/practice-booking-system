"""
Tournament Monitor API Helpers
===============================
Thin HTTP wrappers for the real-time admin monitoring screen.

All functions return:
    Tuple[bool, Optional[str], <data>]
    (success, error_message, payload)

Endpoints used:
    GET  /api/v1/tournaments/admin/list               — list active tournaments
    GET  /api/v1/tournaments/{id}/sessions            — all sessions for a tournament
    GET  /api/v1/tournaments/{id}/campus-schedules    — per-campus config
    GET  /api/v1/tournaments/{id}/calculate-rankings  — current leaderboard (non-destructive GET)
    POST /api/v1/tournaments/ops/run-scenario         — trigger an ops scenario
"""

import requests
from typing import Any, Dict, List, Optional, Tuple

from config import API_BASE_URL, API_TIMEOUT


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get(path: str, token: str, params: Optional[Dict] = None) -> Tuple[bool, Optional[str], Any]:
    """Perform an authenticated GET and return (success, error, data)."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", None
        ct = resp.headers.get("content-type", "")
        err = resp.json().get("detail", resp.text) if "json" in ct else resp.text
        return False, f"HTTP {resp.status_code}: {err}", None
    except requests.exceptions.Timeout:
        return False, "Request timed out.", None
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server.", None
    except Exception as exc:
        return False, f"Unexpected error: {exc}", None


def _post(path: str, token: str, payload: Dict) -> Tuple[bool, Optional[str], Any]:
    """Perform an authenticated POST and return (success, error, data)."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=API_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", None
        ct = resp.headers.get("content-type", "")
        err = resp.json().get("detail", resp.text) if "json" in ct else resp.text
        return False, f"HTTP {resp.status_code}: {err}", None
    except requests.exceptions.Timeout:
        return False, "Request timed out.", None
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server.", None
    except Exception as exc:
        return False, f"Unexpected error: {exc}", None


def _patch(path: str, token: str, payload: Dict) -> Tuple[bool, Optional[str], Any]:
    """Perform an authenticated PATCH and return (success, error, data)."""
    try:
        resp = requests.patch(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=API_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", None
        ct = resp.headers.get("content-type", "")
        err = resp.json().get("detail", resp.text) if "json" in ct else resp.text
        return False, f"HTTP {resp.status_code}: {err}", None
    except requests.exceptions.Timeout:
        return False, "Request timed out.", None
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server.", None
    except Exception as exc:
        return False, f"Unexpected error: {exc}", None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_active_tournaments(token: str) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Return all tournaments in IN_PROGRESS status.

    Uses the admin list endpoint with status filter.
    Falls back to /tournaments/available (without auth requirement) is not needed
    because this is admin-only monitoring.
    """
    ok, err, data = _get("/api/v1/tournaments/admin/list", token, params={"status": "IN_PROGRESS"})
    if ok:
        tournaments = data if isinstance(data, list) else data.get("tournaments", [])
        return True, None, tournaments
    return False, err, []


def get_all_tournaments_admin(token: str) -> Tuple[bool, Optional[str], List[Dict]]:
    """Return all tournaments (any status) for the selector dropdown."""
    ok, err, data = _get("/api/v1/tournaments/admin/list", token)
    if ok:
        tournaments = data if isinstance(data, list) else data.get("tournaments", [])
        # Normalise: prefer tournament_status for lifecycle decisions on each item
        for t in tournaments:
            if t.get("tournament_status"):
                t["status"] = t["tournament_status"]
        return True, None, tournaments
    return False, err, []


def get_tournament_sessions(token: str, tournament_id: int) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Return all sessions for a tournament.

    Each session dict contains (from the backend):
        id, title, tournament_phase, tournament_round, group_identifier,
        match_format, scoring_type, participant_user_ids, participant_names,
        date_start, date_end, result_submitted, campus_id, campus_name, ...
    """
    return _get(f"/api/v1/tournaments/{tournament_id}/sessions", token)


def get_campus_schedules(token: str, tournament_id: int) -> Tuple[bool, Optional[str], List[Dict]]:
    """Return per-campus schedule configs for a tournament."""
    ok, err, data = _get(f"/api/v1/tournaments/{tournament_id}/campus-schedules", token)
    if ok:
        return True, None, data if isinstance(data, list) else []
    return False, err, []


def get_tournament_rankings(token: str, tournament_id: int) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Return current tournament leaderboard.

    Note: calculate-rankings is a POST that MODIFIES state.
    We use GET /rankings (read-only) if it exists, otherwise we call
    GET /calculate-rankings — some backends expose it as GET for polling.
    Returns empty list gracefully if endpoint not available yet.
    """
    ok, err, data = _get(f"/api/v1/tournaments/{tournament_id}/rankings", token)
    if ok:
        rankings = data if isinstance(data, list) else data.get("rankings", [])
        return True, None, rankings
    # Graceful degradation — leaderboard not yet available is normal for ongoing tournaments
    return True, None, []


def get_tournament_detail(token: str, tournament_id: int) -> Tuple[bool, Optional[str], Dict]:
    """
    Return a single tournament's detail via the dedicated summary endpoint.

    Uses GET /api/v1/tournaments/{id}/summary — returns exactly one tournament,
    never the full list. Avoids the O(N) full-list fetch that the admin/list
    endpoint requires when used for single-record lookup.

    The summary response contains: id, tournament_id, name, status,
    tournament_status, total_bookings (enrolled count), sessions_count, etc.
    We normalise the field names to match what the monitor card expects.
    """
    ok, err, data = _get(f"/api/v1/tournaments/{tournament_id}/summary", token)
    if ok and data:
        # Normalise: summary uses total_bookings for enrolled count
        data.setdefault("enrolled_count", data.get("total_bookings", 0))
        data.setdefault("participant_count", data.get("total_bookings", 0))
        # ALWAYS prefer tournament_status for lifecycle decisions:
        # tournament_status = IN_PROGRESS / COMPLETED / REWARDS_DISTRIBUTED
        # status           = ONGOING / DRAFT (Semester lifecycle enum — unrelated)
        if data.get("tournament_status"):
            data["status"] = data["tournament_status"]
        return True, None, data
    return False, err or "Tournament not found", {}


def trigger_ops_scenario(
    token: str,
    scenario: str,
    player_count: int,
    tournament_type_code: Optional[str] = None,
    tournament_format: str = "HEAD_TO_HEAD",
    scoring_type: Optional[str] = None,
    ranking_direction: Optional[str] = None,
    tournament_name: Optional[str] = None,
    dry_run: bool = False,
    confirmed: bool = False,
    simulation_mode: str = "accelerated",
    game_preset_id: Optional[int] = None,
    reward_config: Optional[Dict] = None,
    number_of_rounds: Optional[int] = None,
    player_ids: Optional[List[int]] = None,
    campus_ids: Optional[List[int]] = None,
) -> Tuple[bool, Optional[str], Dict]:
    """
    POST /api/v1/tournaments/ops/run-scenario

    Trigger an admin ops scenario (seed players, create tournament, enroll,
    generate sessions) in one call.

    Returns (success, error_message, response_dict).
    """
    try:
        payload = {
            "scenario": scenario,
            "player_count": player_count,
            "tournament_format": tournament_format,
            "dry_run": dry_run,
            "confirmed": confirmed,
            "simulation_mode": simulation_mode,
        }
        if tournament_type_code:
            payload["tournament_type_code"] = tournament_type_code
        if scoring_type:
            payload["scoring_type"] = scoring_type
        if ranking_direction:
            payload["ranking_direction"] = ranking_direction
        if tournament_name:
            payload["tournament_name"] = tournament_name
        if game_preset_id is not None:
            payload["game_preset_id"] = game_preset_id
        if reward_config:
            payload["reward_config"] = reward_config
        if number_of_rounds is not None and number_of_rounds > 1:
            payload["number_of_rounds"] = number_of_rounds
        if player_ids:
            payload["player_ids"] = player_ids
        if campus_ids:
            payload["campus_ids"] = campus_ids

        resp = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/ops/run-scenario",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=max(API_TIMEOUT, 120),  # ops can take longer than default timeout
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        ct = resp.headers.get("content-type", "")
        try:
            err_body = resp.json()
            err = err_body.get("detail", str(err_body))
        except Exception:
            err = resp.text
        return False, f"HTTP {resp.status_code}: {err}", {}
    except requests.exceptions.Timeout:
        return False, "Request timed out (ops scenarios can take 30–120s for large player counts).", {}
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server.", {}
    except Exception as exc:
        return False, f"Unexpected error: {exc}", {}


def submit_h2h_result(
    token: str,
    session_id: int,
    user_id_1: int,
    score_1: int,
    user_id_2: int,
    score_2: int,
) -> Tuple[bool, Optional[str], Dict]:
    """Submit a head-to-head result for a 2-player session.

    PATCH /api/v1/sessions/{session_id}/head-to-head-results
    Expects exactly 2 participants with integer scores (0–99).
    """
    payload = {
        "results": [
            {"user_id": user_id_1, "score": score_1},
            {"user_id": user_id_2, "score": score_2},
        ]
    }
    ok, err, data = _patch(
        f"/api/v1/sessions/{session_id}/head-to-head-results", token, payload
    )
    return ok, err, data or {}


def submit_ir_round(
    token: str,
    tournament_id: int,
    session_id: int,
    round_number: int,
    results: Dict[str, str],
) -> Tuple[bool, Optional[str], Dict]:
    """Submit one round of results for a ROUNDS_BASED INDIVIDUAL_RANKING session.

    POST /api/v1/tournaments/{tid}/sessions/{session_id}/rounds/{round_number}/submit-results

    The `results` dict maps str(user_id) → measured_value string, e.g.:
      {"123": "12.5s", "456": "13.2s"}  for TIME_BASED
      {"123": "95",    "456": "82"}     for SCORE_BASED
    """
    payload = {"round_number": round_number, "results": results}
    ok, err, data = _post(
        f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results",
        token,
        payload,
    )
    return ok, err, data or {}


def submit_individual_ranking_results(
    token: str,
    tournament_id: int,
    session_id: int,
    results: list,
) -> Tuple[bool, Optional[str], Dict]:
    """Submit results for an INDIVIDUAL_RANKING session.

    POST /api/v1/tournaments/{tid}/sessions/{session_id}/submit-results

    The `results` list always uses the unified format (all scoring types):
      [{"user_id": 1, "measured_value": 10.5}, ...]
    The backend derives placement from measured_value based on ranking_direction
    (ASC for TIME_BASED → lower is better; DESC for DISTANCE/SCORE → higher is better).
    """
    payload = {"results": results, "notes": "OPS auto-simulated"}
    ok, err, data = _post(
        f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results",
        token,
        payload,
    )
    return ok, err, data or {}
