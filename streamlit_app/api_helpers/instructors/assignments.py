"""
Instructor Assignments Module

Provides API wrapper functions for instructor assignment operations:
- Assignment creation and management
- Smart Matrix integration
- Session instructor management
- Co-instructor support
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
# Instructor Assignments
# ============================================================================

def assign_instructor_to_session(
    token: str,
    location_id: int,
    instructor_id: int,
    specialization_type: str,
    age_group: str,
    year: int,
    time_period_start: str,
    time_period_end: str,
    is_master: bool = False
) -> Dict[str, Any]:
    """
    Master Instructor: Create instructor assignment

    Usually created after accepting an application.
    Supports co-instructors (multiple assignments for same period).

    Returns: AssignmentResponse
    """
    url = f"{get_api_url()}/instructor-management/assignments/"
    payload = {
        "location_id": location_id,
        "instructor_id": instructor_id,
        "specialization_type": specialization_type,
        "age_group": age_group,
        "year": year,
        "time_period_start": time_period_start,
        "time_period_end": time_period_end,
        "is_master": is_master
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_instructor_assignments(
    token: str,
    location_id: Optional[int] = None,
    year: Optional[int] = None,
    specialization: Optional[str] = None,
    age_group: Optional[str] = None,
    include_inactive: bool = False
) -> Dict[str, Any]:
    """
    List instructor assignments with optional filters

    Returns: AssignmentListResponse
    """
    url = f"{get_api_url()}/instructor-management/assignments/"
    params = {"include_inactive": include_inactive}
    if location_id:
        params["location_id"] = location_id
    if year:
        params["year"] = year
    if specialization:
        params["specialization"] = specialization
    if age_group:
        params["age_group"] = age_group

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_session_instructors(
    token: str,
    location_id: int,
    specialization: str,
    age_group: str,
    year: int
) -> Dict[str, Any]:
    """
    Smart Matrix Integration: Get all instructors for a specific cell

    Returns: MatrixCellInstructors with:
    - All active instructors
    - Coverage information
    - Co-instructor flags
    """
    url = f"{get_api_url()}/instructor-management/assignments/matrix-cell"
    params = {
        "location_id": location_id,
        "specialization": specialization,
        "age_group": age_group,
        "year": year
    }
    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def update_instructor_assignment(
    token: str,
    assignment_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Master Instructor: Update an assignment

    Returns: Updated AssignmentResponse
    """
    url = f"{get_api_url()}/instructor-management/assignments/{assignment_id}"
    payload = kwargs
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def remove_instructor_from_session(token: str, assignment_id: int) -> Dict[str, Any]:
    """
    Master Instructor: Deactivate an assignment

    Returns: Updated AssignmentResponse
    """
    url = f"{get_api_url()}/instructor-management/assignments/{assignment_id}"
    payload = {"is_active": False}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def delete_assignment(token: str, assignment_id: int) -> None:
    """
    Master Instructor or Admin: Delete assignment

    Typically should deactivate instead of delete (for audit trail).
    Delete only if no sessions have been created yet.
    """
    url = f"{get_api_url()}/instructor-management/assignments/{assignment_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()


# ============================================================================
# Convenience Functions for Smart Matrix Integration
# ============================================================================

def get_location_instructors_summary(
    token: str,
    location_id: int,
    year: int
) -> Dict[str, Any]:
    """
    Get summary of all instructors assigned to a location for a given year

    Groups assignments by spec/age and includes coverage info.
    """
    assignments_response = get_instructor_assignments(
        token=token,
        location_id=location_id,
        year=year,
        include_inactive=False
    )

    # Group by spec/age
    summary = {}
    for assignment in assignments_response["assignments"]:
        key = f"{assignment['specialization_type']}/{assignment['age_group']}"

        if key not in summary:
            summary[key] = {
                "specialization_type": assignment["specialization_type"],
                "age_group": assignment["age_group"],
                "instructors": [],
                "total_assignments": 0
            }

        summary[key]["instructors"].append({
            "id": assignment["instructor_id"],
            "name": assignment.get("instructor_name", "Unknown"),
            "period": f"{assignment['time_period_start']}-{assignment['time_period_end']}",
            "is_master": assignment["is_master"]
        })
        summary[key]["total_assignments"] += 1

    return {
        "location_id": location_id,
        "year": year,
        "cells": list(summary.values())
    }


def create_assignment_from_application(
    token: str,
    application_id: int,
    application_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convenience function: Accept application and create assignment in one call

    Args:
        application_id: ID of the application to accept
        application_data: Full application object (must include position details)

    Returns: Created assignment
    """
    # Import here to avoid circular dependency
    from . import applications as app_module

    # Accept the application
    app_module.accept_application(token, application_id)

    # Extract position details
    position = application_data.get("position", {})
    applicant_id = application_data["applicant_id"]

    # Create assignment
    return assign_instructor_to_session(
        token=token,
        location_id=position["location_id"],
        instructor_id=applicant_id,
        specialization_type=position["specialization_type"],
        age_group=position["age_group"],
        year=position["year"],
        time_period_start=position["time_period_start"],
        time_period_end=position["time_period_end"],
        is_master=False
    )
