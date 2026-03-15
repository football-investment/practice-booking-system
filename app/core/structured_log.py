"""
Structured logging helpers — consistent event identifiers across all flows.

All operational events (reward, booking, enrollment) emit log lines in a
uniform ``event=<name> field=value …`` format so that production log
aggregators (ELK, Loki, CloudWatch Insights) can filter and correlate
across services without parsing free-form strings.

Usage
-----
    from app.core.structured_log import log_event, log_warn

    log_event(_logger, "reward_awarded",
              user_id=123, session_id=456, xp=50, multiplier=1.5)
    # → INFO  event=reward_awarded user_id=123 session_id=456 xp=50 multiplier=1.5

Canonical event names
---------------------
Reward flow:
    reward_awarded          — EventRewardLog upserted successfully
    reward_failed           — DB error during award (exception re-raised)

Enrollment flow:
    enrollment_gate_blocked — Parent-semester gate rejected enrolment
    enrollment_gate_passed  — Parent-semester gate accepted enrolment
    enrollment_created      — SemesterEnrollment row committed

Booking flow:
    booking_created         — Booking committed (status: CONFIRMED / WAITLISTED)
    booking_duplicate       — Concurrent duplicate caught (IntegrityError → 409)
    booking_cancelled       — Booking cancelled by student or admin

Session flow:
    session_scheduled       — Session created in a semester
    session_capacity_full   — Session confirmed slots exhausted (next → WAITLIST)

Consistent field names
-----------------------
    user_id, session_id, semester_id, enrollment_id, booking_id
    xp, multiplier, status, event_category, capacity, confirmed_count
    error (exception repr for failed events)
"""
from __future__ import annotations

import logging
from typing import Any


def log_event(
    logger: logging.Logger,
    event_name: str,
    *,
    level: str = "info",
    **fields: Any,
) -> None:
    """
    Emit a structured log line: ``event=<event_name> key=value …``.

    Fields are sorted alphabetically after ``event`` so that log output is
    deterministic and easy to grep.  Non-string values are formatted with
    ``%r`` only when they would otherwise be ambiguous (e.g. None, lists).
    """
    parts = [f"event={event_name}"]
    for key in sorted(fields):
        value = fields[key]
        if value is None or isinstance(value, (list, dict, bool)):
            parts.append(f"{key}={value!r}")
        else:
            parts.append(f"{key}={value}")
    getattr(logger, level)(" ".join(parts))


def log_info(logger: logging.Logger, event_name: str, **fields: Any) -> None:
    log_event(logger, event_name, level="info", **fields)


def log_warn(logger: logging.Logger, event_name: str, **fields: Any) -> None:
    log_event(logger, event_name, level="warning", **fields)


def log_debug(logger: logging.Logger, event_name: str, **fields: Any) -> None:
    log_event(logger, event_name, level="debug", **fields)


def log_error(logger: logging.Logger, event_name: str, **fields: Any) -> None:
    log_event(logger, event_name, level="error", **fields)
