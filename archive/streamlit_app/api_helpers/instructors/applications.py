"""
Application Management Module

Provides API wrapper functions for application operations:
- Job position applications (Instructors)
- Application review and approval (Master Instructors)
- Application status tracking
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
# Applications (Instructors + Master)
# ============================================================================

def apply_to_position(
    token: str,
    position_id: int,
    application_message: str
) -> Dict[str, Any]:
    """
    Instructor: Apply to a position

    Returns: ApplicationResponse
    """
    url = f"{get_api_url()}/instructor-management/applications/"
    payload = {
        "position_id": position_id,
        "application_message": application_message
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_my_applications(token: str, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Instructor: Get my applications

    Args:
        status: Optional filter ("PENDING", "ACCEPTED", "DECLINED")

    Returns: ApplicationListResponse
    """
    url = f"{get_api_url()}/instructor-management/applications/my-applications"
    params = {}
    if status:
        params["status"] = status

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_applications_for_position(
    token: str,
    position_id: int,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Master Instructor: Get all applications for a position

    Returns: ApplicationListResponse
    """
    url = f"{get_api_url()}/instructor-management/applications/for-position/{position_id}"
    params = {}
    if status:
        params["status"] = status

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def review_application(
    token: str,
    application_id: int,
    status: str  # "ACCEPTED" or "DECLINED"
) -> Dict[str, Any]:
    """
    Master Instructor: Accept or decline an application

    Returns: Updated ApplicationResponse
    """
    url = f"{get_api_url()}/instructor-management/applications/{application_id}"
    payload = {"status": status}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def accept_application(token: str, application_id: int) -> Dict[str, Any]:
    """Master Instructor: Accept an application (shorthand)"""
    return review_application(token, application_id, "ACCEPTED")


def decline_application(token: str, application_id: int) -> Dict[str, Any]:
    """Master Instructor: Decline an application (shorthand)"""
    return review_application(token, application_id, "DECLINED")


def withdraw_application(token: str, application_id: int) -> None:
    """
    Instructor: Withdraw a submitted application

    Only allowed for PENDING applications.
    """
    url = f"{get_api_url()}/instructor-management/applications/{application_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()
