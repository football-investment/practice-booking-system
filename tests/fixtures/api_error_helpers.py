"""
API Error Response Contract
===========================

The custom exception handler in ``app/core/exceptions.py`` wraps every
HTTPException in the envelope::

    {
        "error": {
            "code":       "http_4XX",
            "message":    "<human-readable detail>",
            "timestamp":  "<ISO-8601>",
            "request_id": "<uuid>"
        }
    }

FastAPI's built-in ``{"detail": "..."}`` format is **not** emitted by this
application for handled exceptions.  All test assertions against error messages
must use :func:`get_error_message` (or :func:`assert_error_contains`) rather
than ``resp.json()["detail"]``.

Usage example::

    from tests.fixtures.api_error_helpers import assert_error_contains

    resp = client.post("/api/v1/semester-enrollments/enroll", json=payload)
    assert resp.status_code == 403
    assert_error_contains(resp, "parent program")
"""
from __future__ import annotations


def get_error_message(response) -> str:
    """
    Extract the human-readable error message from any API error response.

    Handles both the application's custom envelope
    ``{"error": {"message": "..."}}`` and FastAPI's default
    ``{"detail": "..."}`` (kept as fallback for safety, should not appear in
    production responses that go through the custom exception handler).

    :param response: A starlette / httpx / requests Response object.
    :returns: The error message string, or ``""`` if not found.
    """
    try:
        body = response.json()
    except Exception:
        return response.text

    if not isinstance(body, dict):
        return ""

    # Primary: application custom envelope (app/core/exceptions.py)
    if "error" in body:
        return body["error"].get("message", "")

    # Fallback: FastAPI default (should not occur but safe to handle)
    return str(body.get("detail", ""))


def assert_error_contains(response, substring: str) -> None:
    """
    Assert that the API error message contains ``substring`` (case-insensitive).

    Raises ``AssertionError`` with full context when the check fails.

    Example::

        assert_error_contains(resp, "parent program")
        # passes when resp.json()["error"]["message"] contains "parent program"

    :param response: An httpx / starlette Response object.
    :param substring: Text that must appear in the error message.
    """
    msg = get_error_message(response)
    assert substring.lower() in msg.lower(), (
        f"Expected {substring!r} in error message.\n"
        f"  Got:  {msg!r}\n"
        f"  Body: {response.json()}"
    )


def get_error_code(response) -> str:
    """
    Extract the ``code`` field from the error envelope.

    Example: ``"http_403"``, ``"http_404"``.

    :param response: An httpx / starlette Response object.
    :returns: The code string, or ``""`` if not found.
    """
    try:
        body = response.json()
    except Exception:
        return ""
    if isinstance(body, dict) and "error" in body:
        return body["error"].get("code", "")
    return ""
