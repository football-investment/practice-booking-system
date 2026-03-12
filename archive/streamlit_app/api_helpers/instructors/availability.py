"""
Availability Management Module

Provides API wrapper functions for instructor availability:
- Availability window management
- Conflict checking
- Scheduling integration
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
# Availability Management
# ============================================================================

def set_instructor_availability(
    token: str,
    instructor_id: int,
    start_date: str,  # ISO format
    end_date: str,    # ISO format
    available: bool = True
) -> Dict[str, Any]:
    """
    Set instructor availability window

    Args:
        token: Auth token
        instructor_id: Instructor ID
        start_date: ISO format date
        end_date: ISO format date
        available: True for available window, False for unavailable

    Returns: AvailabilityResponse
    """
    url = f"{get_api_url()}/instructor-management/availability/"
    payload = {
        "instructor_id": instructor_id,
        "start_date": start_date,
        "end_date": end_date,
        "available": available
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_instructor_availability(
    token: str,
    instructor_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get instructor availability windows

    Args:
        token: Auth token
        instructor_id: Instructor ID
        start_date: Optional filter start (ISO format)
        end_date: Optional filter end (ISO format)

    Returns: List of AvailabilityResponse
    """
    url = f"{get_api_url()}/instructor-management/availability/{instructor_id}"
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def update_availability(
    token: str,
    availability_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Update an availability record

    Args:
        token: Auth token
        availability_id: Availability record ID
        **kwargs: Fields to update (start_date, end_date, available, etc.)

    Returns: Updated AvailabilityResponse
    """
    url = f"{get_api_url()}/instructor-management/availability/{availability_id}"
    payload = kwargs
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def delete_availability(token: str, availability_id: int) -> None:
    """
    Delete an availability record

    Args:
        token: Auth token
        availability_id: Availability record ID
    """
    url = f"{get_api_url()}/instructor-management/availability/{availability_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()
