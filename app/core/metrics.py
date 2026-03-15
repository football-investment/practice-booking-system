"""
Domain event counters — lightweight in-process metrics.
========================================================

Thread-safe counters for key operational events.  Counters accumulate from
process start so the ``GET /metrics`` endpoint always shows lifetime totals —
useful for dashboards and alerting (e.g. spike in ``rewards_failed``).

No external dependencies (no Prometheus, no StatsD): just a dict behind a
``threading.Lock``.  For multi-process deployments each process has its own
counters; aggregate at the load-balancer or log aggregator level.

Canonical counter names
-----------------------
rewards_generated       successful ``award_session_completion()`` calls
rewards_failed          ``award_session_completion()`` calls that raised an exception
bookings_created        bookings committed with status CONFIRMED
bookings_waitlisted     bookings committed with status WAITLISTED (capacity full)
enrollment_attempts     ``create_enrollment()`` endpoint calls
enrollment_gate_blocked enrollment attempts blocked by parent-semester hierarchy gate

Usage::

    from app.core.metrics import metrics

    metrics.increment("rewards_generated")
    metrics.increment("rewards_failed")

    snapshot = metrics.get_snapshot()
    # → {"rewards_generated": 42, "rewards_failed": 0, ...}
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict


class DomainMetrics:
    """Thread-safe in-process counter store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)

    def increment(self, name: str, by: int = 1) -> None:
        """Atomically increment counter ``name`` by ``by`` (default 1)."""
        with self._lock:
            self._counters[name] += by

    def get_snapshot(self) -> Dict[str, int]:
        """Return a point-in-time copy of all counters."""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """Reset all counters to zero.  Intended for test isolation only."""
        with self._lock:
            self._counters.clear()


#: Process-wide singleton — import this in service and endpoint modules.
metrics = DomainMetrics()
