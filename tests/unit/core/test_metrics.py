"""
Unit tests — app/core/metrics.py
=================================

Tests
-----
  MTR-01  increment() raises counter from 0 → 1
  MTR-02  increment(by=5) adds 5 in one call
  MTR-03  get_snapshot() returns a copy (mutations don't affect store)
  MTR-04  multiple distinct counters tracked independently
  MTR-05  reset() clears all counters
  MTR-06  thread-safety: 50 concurrent increments → exactly 50
  MTR-07  canonical counter names accepted without error
  MTR-08  bookings/reward/enrollment counters from service calls
"""
from __future__ import annotations

import threading
import pytest

from app.core.metrics import DomainMetrics


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def m() -> DomainMetrics:
    """Fresh DomainMetrics instance for each test."""
    return DomainMetrics()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDomainMetricsBasic:

    def test_mtr01_increment_defaults_to_one(self, m: DomainMetrics):
        """MTR-01: single increment raises counter to 1."""
        m.increment("rewards_generated")
        assert m.get_snapshot()["rewards_generated"] == 1

    def test_mtr02_increment_by_n(self, m: DomainMetrics):
        """MTR-02: increment(by=5) adds 5."""
        m.increment("bookings_created", by=5)
        assert m.get_snapshot()["bookings_created"] == 5

    def test_mtr03_snapshot_is_copy(self, m: DomainMetrics):
        """MTR-03: mutating snapshot does not affect the store."""
        m.increment("rewards_generated")
        snap = m.get_snapshot()
        snap["rewards_generated"] = 999
        assert m.get_snapshot()["rewards_generated"] == 1

    def test_mtr04_multiple_independent_counters(self, m: DomainMetrics):
        """MTR-04: distinct counters do not interfere."""
        m.increment("rewards_generated")
        m.increment("rewards_generated")
        m.increment("rewards_failed")
        m.increment("bookings_created", by=3)

        snap = m.get_snapshot()
        assert snap["rewards_generated"] == 2
        assert snap["rewards_failed"] == 1
        assert snap["bookings_created"] == 3

    def test_mtr05_reset_clears_all(self, m: DomainMetrics):
        """MTR-05: reset() zeroes every counter."""
        m.increment("rewards_generated", by=10)
        m.increment("bookings_created", by=5)
        m.reset()
        assert m.get_snapshot() == {}

    def test_mtr07_canonical_counter_names_accepted(self, m: DomainMetrics):
        """MTR-07: all documented canonical names are valid (no KeyError)."""
        canonical = [
            "rewards_generated",
            "rewards_failed",
            "bookings_created",
            "bookings_waitlisted",
            "enrollment_attempts",
            "enrollment_gate_blocked",
        ]
        for name in canonical:
            m.increment(name)
        snap = m.get_snapshot()
        for name in canonical:
            assert snap[name] == 1


class TestDomainMetricsThreadSafety:

    def test_mtr06_50_concurrent_increments_produce_exact_count(self):
        """MTR-06: 50 concurrent threads each incrementing once → exactly 50."""
        m = DomainMetrics()
        barrier = threading.Barrier(50)

        def worker():
            barrier.wait()  # all threads start simultaneously
            m.increment("rewards_generated")

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert m.get_snapshot()["rewards_generated"] == 50


class TestDomainMetricsServiceIntegration:

    def test_mtr08_metrics_singleton_importable(self):
        """MTR-08: process-wide singleton is importable and functional."""
        from app.core.metrics import metrics
        # Reset to avoid cross-test contamination (test isolation)
        metrics.reset()
        metrics.increment("bookings_created")
        assert metrics.get_snapshot()["bookings_created"] == 1
        metrics.reset()
