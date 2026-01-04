"""
E2E Test Fixtures - Self-Contained Test Data Creation

This module provides fixtures for creating test data via API calls,
ensuring E2E tests are completely self-contained and don't rely on manual data setup.

Pattern: Each fixture creates data, yields it for the test, then cleans up.
"""

import requests
import pytest
from typing import Dict, Any, Generator
from datetime import datetime, timedelta
import os


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


# ============================================================================
# Helper Functions for API Calls
# ============================================================================

def create_admin_token() -> str:
    """Get admin authentication token."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_instructor_user(token: str) -> Dict[str, Any]:
    """Create a test instructor user via API."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    instructor_data = {
        "email": f"test_instructor_{timestamp}@test.com",
        "name": f"Test Instructor {timestamp}",
        "password": "TestPass123!",
        "role": "instructor",  # ✅ FIXED: lowercase role value
        "date_of_birth": "1990-01-01T00:00:00"  # ✅ FIXED: ISO datetime format
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json=instructor_data
    )
    response.raise_for_status()

    user = response.json()
    # Add password for login
    user["password"] = instructor_data["password"]
    return user


def create_student_users(token: str, count: int = 5) -> list[Dict[str, Any]]:
    """Create multiple test student users via API."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    students = []

    for i in range(count):
        student_data = {
            "email": f"test_student_{timestamp}_{i}@test.com",
            "name": f"Test Student {i+1}",
            "password": "TestPass123!",
            "role": "student",  # ✅ FIXED: lowercase role value
            "date_of_birth": "2005-01-01T00:00:00",  # ✅ FIXED: ISO datetime format
            "specialization": "LFA_PLAYER_YOUTH"
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json=student_data
        )
        response.raise_for_status()

        user = response.json()
        user["password"] = student_data["password"]
        students.append(user)

    return students


def create_tournament_semester(token: str) -> Dict[str, Any]:
    """Create a test tournament semester via API."""
    today = datetime.now().date()
    semester_data = {
        "name": f"Test Tournament {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "code": f"TOURN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "specialization_type": "LFA_PLAYER_YOUTH",
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=30)).isoformat(),
        "status": "ONGOING",
        "is_tournament": True
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/semesters",
        headers={"Authorization": f"Bearer {token}"},
        json=semester_data
    )
    response.raise_for_status()
    return response.json()


def create_tournament_session(
    token: str,
    semester_id: int,
    instructor_id: int,
    date: str = None
) -> Dict[str, Any]:
    """Create a test tournament session via API."""
    if date is None:
        date = datetime.now().date().isoformat()

    session_data = {
        "semester_id": semester_id,
        "instructor_id": instructor_id,
        "date_start": f"{date}T10:00:00",
        "date_end": f"{date}T12:00:00",
        "location": "Test Stadium",
        "max_participants": 20,
        "status": "SCHEDULED",
        "is_tournament_game": True,
        "session_type": "ON_SITE"  # Tournament sessions are always ON_SITE
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json=session_data
    )
    response.raise_for_status()
    return response.json()


def create_booking(
    token: str,
    session_id: int,
    user_id: int
) -> Dict[str, Any]:
    """Create a test booking via API."""
    booking_data = {
        "session_id": session_id,
        "user_id": user_id,
        "status": "CONFIRMED"
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json=booking_data
    )
    response.raise_for_status()
    return response.json()


def cleanup_user(token: str, user_id: int):
    """Delete a test user via API."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup user {user_id}: {e}")


def cleanup_semester(token: str, semester_id: int):
    """Delete a test semester via API (cascades to sessions and bookings)."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/semesters/{semester_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup semester {semester_id}: {e}")


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def admin_token() -> Generator[str, None, None]:
    """Provide admin authentication token."""
    token = create_admin_token()
    yield token
    # No cleanup needed for admin token


@pytest.fixture(scope="function")
def test_instructor(admin_token: str) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test instructor user.

    Returns:
        Dict with user data including 'email' and 'password' for login

    Cleanup:
        Automatically deletes user after test
    """
    instructor = create_instructor_user(admin_token)
    yield instructor
    cleanup_user(admin_token, instructor["id"])


@pytest.fixture(scope="function")
def test_students(admin_token: str) -> Generator[list[Dict[str, Any]], None, None]:
    """
    Create 5 test student users.

    Returns:
        List of dicts with user data including 'email' and 'password'

    Cleanup:
        Automatically deletes all students after test
    """
    students = create_student_users(admin_token, count=5)
    yield students
    for student in students:
        cleanup_user(admin_token, student["id"])


@pytest.fixture(scope="function")
def tournament_with_session(
    admin_token: str,
    test_instructor: Dict[str, Any],
    test_students: list[Dict[str, Any]]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a complete tournament setup with:
    - Tournament semester
    - Tournament session (today)
    - Instructor assigned
    - 5 student bookings (confirmed)

    Returns:
        Dict containing:
        - semester: Tournament semester data
        - session: Tournament session data
        - instructor: Instructor user data
        - students: List of student user data
        - bookings: List of booking data

    Cleanup:
        Automatically deletes semester (cascades to sessions and bookings)
    """
    # Create tournament semester
    semester = create_tournament_semester(admin_token)

    # Create tournament session
    session = create_tournament_session(
        admin_token,
        semester["id"],
        test_instructor["id"]
    )

    # Create bookings for all students
    bookings = []
    for student in test_students:
        booking = create_booking(admin_token, session["id"], student["id"])
        bookings.append(booking)

    # Return complete test data
    test_data = {
        "semester": semester,
        "session": session,
        "instructor": test_instructor,
        "students": test_students,
        "bookings": bookings
    }

    yield test_data

    # Cleanup (cascade delete)
    cleanup_semester(admin_token, semester["id"])


@pytest.fixture(scope="function")
def tournament_multiple_sessions(
    admin_token: str,
    test_instructor: Dict[str, Any],
    test_students: list[Dict[str, Any]]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create tournament with 3 sessions (past, today, future).

    Useful for testing session list display and date filtering.
    """
    semester = create_tournament_semester(admin_token)

    today = datetime.now().date()
    sessions = []

    # Past session
    past_session = create_tournament_session(
        admin_token,
        semester["id"],
        test_instructor["id"],
        (today - timedelta(days=1)).isoformat()
    )
    sessions.append(past_session)

    # Today's session
    today_session = create_tournament_session(
        admin_token,
        semester["id"],
        test_instructor["id"],
        today.isoformat()
    )
    sessions.append(today_session)

    # Future session
    future_session = create_tournament_session(
        admin_token,
        semester["id"],
        test_instructor["id"],
        (today + timedelta(days=1)).isoformat()
    )
    sessions.append(future_session)

    # Create bookings for today's session only
    bookings = []
    for student in test_students:
        booking = create_booking(admin_token, today_session["id"], student["id"])
        bookings.append(booking)

    test_data = {
        "semester": semester,
        "sessions": sessions,
        "today_session": today_session,
        "instructor": test_instructor,
        "students": test_students,
        "bookings": bookings
    }

    yield test_data

    cleanup_semester(admin_token, semester["id"])
