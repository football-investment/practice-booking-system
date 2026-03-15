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
slow_queries_total      SQL queries that exceeded the slow-query threshold (200 ms)

Labeled counters
----------------
The same counters above can also be broken down by label using
``increment_labeled()``.  Labels are low-cardinality key/value pairs such as
``event_category`` (TRAINING | MATCH | …).  Use ``get_labeled_snapshot()`` or
the Prometheus export to see per-label breakdowns.

Usage::

    from app.core.metrics import metrics

    metrics.increment("rewards_generated")
    metrics.increment_labeled("rewards_generated", {"event_category": "TRAINING"})

    snapshot = metrics.get_snapshot()
    # → {"rewards_generated": 42, ...}

    labeled = metrics.get_labeled_snapshot()
    # → {"rewards_generated": {"event_category=TRAINING": 42}, ...}

Prometheus export::

    text = metrics.format_prometheus()
    # → "# HELP rewards_generated_total ...\\n...\\nrewards_generated_total 42\\n"
    # → "rewards_generated_total{event_category=\\"TRAINING\\"} 42\\n"

Alert evaluation::

    result = metrics.evaluate_alerts(settings)
    # → {"status": "ok"|"warning", "thresholds": {...}}
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Dict


# Human-readable descriptions for Prometheus HELP lines.
_COUNTER_HELP: Dict[str, str] = {
    "rewards_generated": (
        "Total successful award_session_completion() calls."
    ),
    "rewards_failed": (
        "Total award_session_completion() calls that raised an exception."
    ),
    "bookings_created": (
        "Total bookings committed with status CONFIRMED."
    ),
    "bookings_waitlisted": (
        "Total bookings committed with status WAITLISTED (capacity full)."
    ),
    "enrollment_attempts": (
        "Total create_enrollment() endpoint calls."
    ),
    "enrollment_gate_blocked": (
        "Total enrollment attempts blocked by the parent-semester hierarchy gate."
    ),
    "slow_queries_total": (
        "Total SQL queries that exceeded the slow-query threshold (200 ms)."
    ),
}


class DomainMetrics:
    """Thread-safe in-process counter store with optional label support."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        # Labeled counters: name → {label_string → count}
        # label_string is "key1=val1,key2=val2" (sorted by key)
        self._labeled_counters: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    # ── Flat counters ──────────────────────────────────────────────────────────

    def increment(self, name: str, by: int = 1) -> None:
        """Atomically increment flat counter ``name`` by ``by`` (default 1)."""
        with self._lock:
            self._counters[name] += by

    def get_snapshot(self) -> Dict[str, int]:
        """Return a point-in-time copy of all flat counters."""
        with self._lock:
            return dict(self._counters)

    # ── Labeled counters ───────────────────────────────────────────────────────

    def increment_labeled(
        self, name: str, labels: Dict[str, str], by: int = 1
    ) -> None:
        """
        Atomically increment a labeled counter.

        Labels are low-cardinality key/value pairs, e.g.
        ``{"event_category": "TRAINING"}``.  The label dict is serialised as
        sorted ``key=value`` pairs so callers do not need to pre-sort.

        Typically called *in addition* to ``increment()`` so both the flat
        total and the per-label breakdown are kept up-to-date.
        """
        label_str = ",".join(
            f"{k}={v}" for k, v in sorted(labels.items())
        )
        with self._lock:
            self._labeled_counters[name][label_str] += by

    def get_labeled_snapshot(self) -> Dict[str, Dict[str, int]]:
        """Return a point-in-time copy of all labeled counters."""
        with self._lock:
            return {
                name: dict(label_counts)
                for name, label_counts in self._labeled_counters.items()
            }

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all counters (flat and labeled).  Intended for test isolation."""
        with self._lock:
            self._counters.clear()
            self._labeled_counters.clear()

    # ── Prometheus exposition format ──────────────────────────────────────────

    def format_prometheus(self) -> str:
        """
        Return metrics in Prometheus text exposition format.

        Output is ``text/plain; version=0.0.4`` compatible.  Each counter is
        emitted with a ``# HELP`` line, a ``# TYPE counter`` line, and metric
        lines with a ``_total`` suffix (Prometheus naming convention).

        Flat totals appear first (no labels), followed by labeled breakdowns
        for any counter that has been incremented via ``increment_labeled()``.
        Counter names already ending with ``_total`` are not doubled.

        Returns an empty-comment line when no counters have been recorded yet.
        """
        flat = self.get_snapshot()
        labeled = self.get_labeled_snapshot()
        all_names = sorted(set(flat) | set(labeled))

        if not all_names:
            return "# No counters registered yet\n"

        lines: list[str] = []
        for name in all_names:
            prom_name = name if name.endswith("_total") else f"{name}_total"
            help_text = _COUNTER_HELP.get(name, f"Counter: {name}.")
            lines.append(f"# HELP {prom_name} {help_text}")
            lines.append(f"# TYPE {prom_name} counter")
            # Flat total (if present)
            if name in flat:
                lines.append(f"{prom_name} {flat[name]}")
            # Labeled breakdowns (if present)
            for label_str, count in sorted(labeled.get(name, {}).items()):
                # Convert "key=val,key2=val2" → {key="val",key2="val2"} syntax
                pairs = []
                for part in label_str.split(","):
                    k, v = part.split("=", 1)
                    pairs.append(f'{k}="{v}"')
                labels_rendered = "{" + ",".join(pairs) + "}"
                lines.append(f"{prom_name}{labels_rendered} {count}")

        return "\n".join(lines) + "\n"

    # ── Alert threshold evaluation ─────────────────────────────────────────────

    def evaluate_alerts(self, settings: Any) -> Dict[str, Any]:
        """
        Compare counter ratios against configured thresholds.

        Returns a dict with:
        - ``status``: ``"ok"`` or ``"warning"`` (warning if any threshold fires)
        - ``thresholds``: per-alert dict with ``value``, ``threshold``, ``firing``

        Only evaluates a ratio alert when the denominator > 0 (avoids
        false positives on a freshly started process with zero traffic).

        Parameters
        ----------
        settings:
            The application ``Settings`` instance — provides
            ``ALERT_REWARD_FAILURE_RATE``, ``ALERT_BOOKING_WAITLIST_RATE``,
            ``ALERT_ENROLLMENT_GATE_BLOCK_RATE``, ``ALERT_SLOW_QUERY_TOTAL``.
        """
        snapshot = self.get_snapshot()
        overall_status = "ok"
        thresholds: Dict[str, Any] = {}

        # ── Reward failure rate ────────────────────────────────────────────────
        total_rewards = (
            snapshot.get("rewards_generated", 0)
            + snapshot.get("rewards_failed", 0)
        )
        if total_rewards > 0:
            rate = snapshot.get("rewards_failed", 0) / total_rewards
            firing = rate > settings.ALERT_REWARD_FAILURE_RATE
            thresholds["reward_failure_rate"] = {
                "value": round(rate, 4),
                "threshold": settings.ALERT_REWARD_FAILURE_RATE,
                "firing": firing,
                "description": "rewards_failed / total_rewards",
            }
            if firing:
                overall_status = "warning"

        # ── Booking waitlist rate ──────────────────────────────────────────────
        total_bookings = (
            snapshot.get("bookings_created", 0)
            + snapshot.get("bookings_waitlisted", 0)
        )
        if total_bookings > 0:
            rate = snapshot.get("bookings_waitlisted", 0) / total_bookings
            firing = rate > settings.ALERT_BOOKING_WAITLIST_RATE
            thresholds["booking_waitlist_rate"] = {
                "value": round(rate, 4),
                "threshold": settings.ALERT_BOOKING_WAITLIST_RATE,
                "firing": firing,
                "description": "bookings_waitlisted / total_bookings",
            }
            if firing:
                overall_status = "warning"

        # ── Enrollment gate block rate ─────────────────────────────────────────
        total_enrollments = snapshot.get("enrollment_attempts", 0)
        if total_enrollments > 0:
            rate = snapshot.get("enrollment_gate_blocked", 0) / total_enrollments
            firing = rate > settings.ALERT_ENROLLMENT_GATE_BLOCK_RATE
            thresholds["enrollment_gate_block_rate"] = {
                "value": round(rate, 4),
                "threshold": settings.ALERT_ENROLLMENT_GATE_BLOCK_RATE,
                "firing": firing,
                "description": "enrollment_gate_blocked / enrollment_attempts",
            }
            if firing:
                overall_status = "warning"

        # ── Slow queries (absolute count, not ratio) ───────────────────────────
        slow_q = snapshot.get("slow_queries_total", 0)
        firing = slow_q > settings.ALERT_SLOW_QUERY_TOTAL
        thresholds["slow_queries_total"] = {
            "value": slow_q,
            "threshold": settings.ALERT_SLOW_QUERY_TOTAL,
            "firing": firing,
            "description": "absolute count of slow SQL queries since process start",
        }
        if firing:
            overall_status = "warning"

        return {"status": overall_status, "thresholds": thresholds}


#: Process-wide singleton — import this in service and endpoint modules.
metrics = DomainMetrics()
