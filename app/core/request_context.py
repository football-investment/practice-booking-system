"""
Request context — per-request and per-operation identifiers for log correlation.

``request_id_var``  is set by ``LoggingMiddleware`` at the start of every HTTP
request so that every ``structured_log`` call in the same async task carries
the same identifier, making it easy to group all log lines for one request in
any log aggregator (ELK, Loki, CloudWatch Insights, etc.).

``operation_id_var`` is set by callers for multi-step domain flows (booking,
enrollment, reward) to correlate several log events that belong to the same
logical operation — even when no HTTP request context is available (e.g. in
background tasks or load-simulation threads).

Usage (middleware)::

    from app.core.request_context import request_id_var
    request_id_var.set(str(uuid4()))

Usage (domain service)::

    from app.core.request_context import set_operation_id
    op_id = set_operation_id()          # auto-generate
    # all structured_log calls in this context include operation_id=<op_id>

Usage (read)::

    from app.core.request_context import get_request_id, get_operation_id
    rid = get_request_id()    # "" if not inside an HTTP request
    oid = get_operation_id()  # "" if not set by caller
"""
from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

# Set by LoggingMiddleware at HTTP request boundary
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Set by callers for multi-step domain flows
operation_id_var: ContextVar[str] = ContextVar("operation_id", default="")


def get_request_id() -> str:
    """Return the current request ID, or empty string if none is set."""
    return request_id_var.get()


def get_operation_id() -> str:
    """Return the current operation ID, or empty string if none is set."""
    return operation_id_var.get()


def set_operation_id(op_id: str | None = None) -> str:
    """
    Assign an operation_id for the current async/thread context.

    If ``op_id`` is None, a short random hex string is generated.
    Returns the assigned ID so the caller can log it explicitly at flow start.
    """
    oid = op_id or uuid4().hex[:12]
    operation_id_var.set(oid)
    return oid
