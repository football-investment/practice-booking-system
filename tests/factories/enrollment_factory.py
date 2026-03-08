"""
Enrollment payload factory for smoke and E2E tests.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.factories.enrollment_factory import (
        enroll_in_tournament_payload,
        reject_enrollment_payload,
    )

Notes:
    - Tournament enrollment (POST /tournaments/{id}/enroll) is auto-approved —
      no admin approve step needed for that flow.
    - The approve/reject workflow applies to semester project enrollments
      (POST /semester-enrollments/{id}/approve).
    - batch_enroll_payload is for POST /tournaments/{id}/admin/batch-enroll.
"""

from __future__ import annotations

from typing import List


def enroll_in_tournament_payload() -> dict:
    """
    Body for POST /api/v1/tournaments/{tournament_id}/enroll.

    The endpoint takes no body — enrollment is identified by the
    authenticated user and the tournament_id path parameter.
    Returns empty dict (sent as empty JSON body or omitted).
    """
    return {}


def approve_enrollment_payload() -> dict:
    """
    Body for POST /api/v1/semester-enrollments/{enrollment_id}/approve.

    No body required — approval is signalled by the endpoint call itself.
    """
    return {}


def reject_enrollment_payload(reason: str = "Test rejection") -> dict:
    """
    Body for POST /api/v1/semester-enrollments/{enrollment_id}/reject.

    Args:
        reason: Human-readable rejection reason.
    """
    return {"reason": reason}


def batch_enroll_payload(player_ids: List[int]) -> dict:
    """
    Body for POST /api/v1/tournaments/{tournament_id}/admin/batch-enroll.

    Args:
        player_ids: List of student user IDs to enroll.
    """
    return {"player_ids": player_ids}
