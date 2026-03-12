"""
Master Instructor Management Module

Provides API wrapper functions for master instructor operations:
- Direct hire offers (PATHWAY A)
- Application-based hiring (PATHWAY B)
- Master instructor CRUD operations
- Available instructor listing
"""

import requests
from typing import Optional, List, Dict, Any
from config import API_BASE_URL


def get_api_url() -> str:
    """Get base API URL from config"""
    return f"{API_BASE_URL}/api/v1"


def get_headers(token: str) -> dict:
    """Build authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# Hybrid Hiring System: New Functions (PATHWAY A & B)
# ============================================================================

def create_direct_hire_offer(
    token: str,
    location_id: int,
    instructor_id: int,
    contract_start: str,
    contract_end: str,
    offer_deadline_days: int = 14,
    override_availability: bool = False
) -> Dict[str, Any]:
    """
    Admin: Create direct hire offer (PATHWAY A)

    Creates an OFFERED contract that instructor must accept/decline.

    Returns: MasterOfferResponse with availability analysis
    """
    url = f"{get_api_url()}/instructor-management/masters/direct-hire"
    payload = {
        "location_id": location_id,
        "instructor_id": instructor_id,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "offer_deadline_days": offer_deadline_days,
        "override_availability": override_availability
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def respond_to_master_offer(
    token: str,
    offer_id: int,
    action: str  # "ACCEPT" or "DECLINE"
) -> Dict[str, Any]:
    """
    Instructor: Accept or decline master instructor offer

    Returns: Updated master contract
    """
    url = f"{get_api_url()}/instructor-management/masters/offers/{offer_id}/respond"
    payload = {"action": action}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_my_master_offers(
    token: str,
    status: Optional[str] = None,
    include_expired: bool = False
) -> List[Dict[str, Any]]:
    """
    Instructor: View all master offers sent to me

    Args:
        status: Filter by status ("OFFERED", "ACCEPTED", "DECLINED", "EXPIRED")
        include_expired: Include expired offers

    Returns: List of MasterOfferResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/my-offers"
    params = {}
    if status:
        params["status"] = status
    if include_expired:
        params["include_expired"] = include_expired

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_pending_master_offers(token: str) -> List[Dict[str, Any]]:
    """
    Admin: View all pending offers across all locations

    Returns: List of pending MasterOfferResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/pending-offers"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def cancel_master_offer(token: str, offer_id: int) -> None:
    """
    Admin: Cancel a pending offer before instructor responds

    Deletes the offer (soft delete or status update depending on backend)
    """
    url = f"{get_api_url()}/instructor-management/masters/offers/{offer_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()


def hire_from_application(
    token: str,
    application_id: int,
    contract_start: str,
    contract_end: str,
    offer_deadline_days: int = 14
) -> Dict[str, Any]:
    """
    Admin: Accept application and create master offer (PATHWAY B)

    CRITICAL: Application acceptance ≠ contract acceptance!
    This creates an OFFERED contract that instructor must still accept.

    Returns: MasterOfferResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/hire-from-application"
    payload = {
        "application_id": application_id,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "offer_deadline_days": offer_deadline_days
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


# ============================================================================
# Legacy Functions (Backward Compatibility)
# ============================================================================

def create_master_instructor(
    token: str,
    location_id: int,
    instructor_id: int,
    contract_start: str,  # ISO format: "2026-01-01T00:00:00"
    contract_end: str
) -> Dict[str, Any]:
    """
    Admin: Hire a master instructor for a location

    Returns: MasterInstructorResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/"
    payload = {
        "location_id": location_id,
        "instructor_id": instructor_id,
        "contract_start": contract_start,
        "contract_end": contract_end
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_master_for_location(
    token: str,
    location_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get current master instructor for a location

    Returns: MasterInstructorResponse or None if no active master
    """
    url = f"{get_api_url()}/instructor-management/masters/{location_id}"
    response = requests.get(url, headers=get_headers(token))

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def list_all_masters(
    token: str,
    include_inactive: bool = False
) -> Dict[str, Any]:
    """
    List all master instructors

    Returns: MasterInstructorListResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/"
    params = {"include_inactive": include_inactive}
    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def update_master_instructor(
    token: str,
    master_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Admin: Update master instructor details

    Returns: Updated MasterInstructorResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/{master_id}"
    payload = kwargs
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def terminate_master_instructor(
    token: str,
    master_id: int
) -> Dict[str, Any]:
    """
    Admin: Terminate master instructor contract

    Returns: Updated MasterInstructorResponse
    """
    url = f"{get_api_url()}/instructor-management/masters/{master_id}"
    payload = {"is_active": False}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_available_instructors(token: str) -> List[Dict[str, Any]]:
    """
    Get all users with INSTRUCTOR role who can be hired as master instructors

    Returns: List of instructor user objects
    """
    url = f"{get_api_url()}/users/"
    params = {
        "role": "instructor",  # Use lowercase enum value, not uppercase name
        "is_active": True,
        "size": 100  # Get up to 100 instructors
    }
    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    data = response.json()

    # Extract users list from paginated response
    return data.get("users", [])
