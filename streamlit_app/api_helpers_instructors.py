"""
API Helpers for Instructor Management System

Provides wrapper functions for all instructor management endpoints:
- Master instructor management (Admin)
- Position posting and job board (Master + All instructors)
- Application management (Instructors + Master)
- Instructor assignments (Master + Matrix integration)
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
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
# Master Instructor Management (Admin Only)
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


def get_master_instructor_by_location(
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


def list_master_instructors(
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


# ============================================================================
# Position Posting (Master Instructors)
# ============================================================================

def create_position(
    token: str,
    location_id: int,
    specialization_type: str,
    age_group: str,
    year: int,
    time_period_start: str,  # e.g., "M01", "Q1"
    time_period_end: str,    # e.g., "M06", "Q2"
    description: str,
    application_deadline: str,  # ISO format
    priority: int = 5
) -> Dict[str, Any]:
    """
    Master Instructor: Post a new position opening

    Returns: PositionResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/"
    payload = {
        "location_id": location_id,
        "specialization_type": specialization_type,
        "age_group": age_group,
        "year": year,
        "time_period_start": time_period_start,
        "time_period_end": time_period_end,
        "description": description,
        "priority": priority,
        "application_deadline": application_deadline
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_my_positions(token: str, location_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Master Instructor: Get positions I posted

    Returns: PositionListResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/my-positions"
    params = {}
    if location_id:
        params["location_id"] = location_id

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_job_board(
    token: str,
    location_id: Optional[int] = None,
    specialization: Optional[str] = None,
    age_group: Optional[str] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    All Instructors: View public job board

    Returns: JobBoardResponse with user_has_applied flags
    """
    url = f"{get_api_url()}/instructor-management/positions/job-board"
    params = {}
    if location_id:
        params["location_id"] = location_id
    if specialization:
        params["specialization"] = specialization
    if age_group:
        params["age_group"] = age_group
    if year:
        params["year"] = year

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def update_position_status(
    token: str,
    position_id: int,
    status: str  # "OPEN", "FILLED", "CLOSED", "CANCELLED"
) -> Dict[str, Any]:
    """
    Master Instructor: Update position status

    Returns: Updated PositionResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/{position_id}"
    payload = {"status": status}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def close_position(token: str, position_id: int) -> Dict[str, Any]:
    """
    Master Instructor: Close position (shorthand for update_position_status)

    Returns: Updated PositionResponse
    """
    return update_position_status(token, position_id, "CLOSED")


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


# ============================================================================
# Instructor Assignments
# ============================================================================

def create_assignment(
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


def list_assignments(
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


def get_matrix_cell_instructors(
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


def deactivate_assignment(token: str, assignment_id: int) -> Dict[str, Any]:
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
    assignments_response = list_assignments(
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
    # Accept the application
    accept_application(token, application_id)

    # Extract position details
    position = application_data.get("position", {})
    applicant_id = application_data["applicant_id"]

    # Create assignment
    return create_assignment(
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
