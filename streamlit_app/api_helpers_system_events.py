"""
System Events API Helpers — Rendszerüzenetek panel
===================================================
Thin HTTP wrappers for the admin system-events panel.

All functions return:
    Tuple[bool, Optional[str], <data>]
    (success, error_message, payload)

Endpoints used:
    GET   /api/v1/system-events                  — list with filters
    PATCH /api/v1/system-events/{id}/resolve     — mark resolved
    PATCH /api/v1/system-events/{id}/unresolve   — reopen
"""

import requests
from typing import Any, Dict, List, Optional, Tuple

from config import API_BASE_URL, API_TIMEOUT


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def get_system_events(
    token: str,
    *,
    level: Optional[str] = None,
    event_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Fetch system events with optional filters.

    Returns (success, error_message, {"items": [...], "total": N, ...})
    """
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if level is not None:
        params["level"] = level
    if event_type is not None:
        params["event_type"] = event_type
    if resolved is not None:
        params["resolved"] = str(resolved).lower()

    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/v1/system-events",
            headers=_auth_headers(token),
            params=params,
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", {}
        try:
            detail = resp.json().get("detail") or resp.json().get("error", {}).get("message") or resp.text
        except Exception:
            detail = resp.text
        return False, f"API error {resp.status_code}: {detail}", {}
    except requests.exceptions.Timeout:
        return False, "Request timed out — system events unavailable.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to API server.", {}
    except Exception as exc:
        return False, f"Unexpected error: {exc}", {}


def resolve_system_event(
    token: str,
    event_id: int,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Mark a system event as resolved."""
    try:
        resp = requests.patch(
            f"{API_BASE_URL}/api/v1/system-events/{event_id}/resolve",
            headers=_auth_headers(token),
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", {}
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        return False, f"API error {resp.status_code}: {detail}", {}
    except Exception as exc:
        return False, f"Unexpected error: {exc}", {}


def unresolve_system_event(
    token: str,
    event_id: int,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Reopen a resolved system event."""
    try:
        resp = requests.patch(
            f"{API_BASE_URL}/api/v1/system-events/{event_id}/unresolve",
            headers=_auth_headers(token),
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", {}
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        return False, f"API error {resp.status_code}: {detail}", {}
    except Exception as exc:
        return False, f"Unexpected error: {exc}", {}


def purge_system_events(
    token: str,
    retention_days: int = 90,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Purge resolved system events older than `retention_days` days.
    Returns (success, error_message, {"deleted": N, "message": "..."}).
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/system-events/purge",
            headers=_auth_headers(token),
            params={"retention_days": retention_days},
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, None, resp.json()
        if resp.status_code == 401:
            return False, "SESSION_EXPIRED", {}
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        return False, f"API error {resp.status_code}: {detail}", {}
    except Exception as exc:
        return False, f"Unexpected error: {exc}", {}
