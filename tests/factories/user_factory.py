"""
User payload factory for smoke and E2E tests.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.factories.user_factory import create_student_payload, login_payload
"""

from __future__ import annotations

from typing import Optional


def create_student_payload(
    *,
    suffix: Optional[str] = None,
    dob: str = "2000-01-01",
) -> dict:
    """
    Minimal-valid payload for POST /api/v1/users/ with role=student.

    Args:
        suffix: Optional string for uniqueness (e.g. timestamp).
        dob: Date of birth ISO string — 2000-01-01 is PRO age group (25+ years).
    """
    name_suffix = f"_{suffix}" if suffix else ""
    email_suffix = f".{suffix}" if suffix else ""
    return {
        "name": f"Test Student{name_suffix}",
        "email": f"test.student{email_suffix}@test.lfa",
        "password": f"TestPass{name_suffix or '_default'}",
        "role": "student",
        "is_active": True,
        "onboarding_completed": True,
        "payment_verified": True,
        "date_of_birth": dob,
    }


def create_instructor_payload(
    *,
    suffix: Optional[str] = None,
) -> dict:
    """
    Minimal-valid payload for POST /api/v1/users/ with role=instructor.
    """
    name_suffix = f"_{suffix}" if suffix else ""
    email_suffix = f".{suffix}" if suffix else ""
    return {
        "name": f"Test Instructor{name_suffix}",
        "email": f"test.instructor{email_suffix}@test.lfa",
        "password": f"TestPass{name_suffix or '_default'}",
        "role": "instructor",
        "is_active": True,
        "onboarding_completed": True,
        "payment_verified": True,
    }


def create_admin_payload(
    *,
    suffix: Optional[str] = None,
) -> dict:
    """
    Minimal-valid payload for POST /api/v1/users/ with role=admin.
    """
    name_suffix = f"_{suffix}" if suffix else ""
    email_suffix = f".{suffix}" if suffix else ""
    return {
        "name": f"Test Admin{name_suffix}",
        "email": f"test.admin{email_suffix}@test.lfa",
        "password": f"TestPass{name_suffix or '_default'}",
        "role": "admin",
        "is_active": True,
        "onboarding_completed": True,
        "payment_verified": True,
    }


def login_payload(email: str, password: str) -> dict:
    """
    Payload for POST /api/v1/auth/login.
    """
    return {"email": email, "password": password}


def change_password_payload(old: str, new_: str) -> dict:
    """
    Payload for POST /api/v1/auth/change-password.
    """
    return {"old_password": old, "new_password": new_}
