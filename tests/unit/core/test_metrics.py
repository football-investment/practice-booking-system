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
  MTR-09  format_prometheus() includes HELP + TYPE + _total lines
  MTR-10  format_prometheus() on empty store returns comment line
  MTR-11  format_prometheus() does not double _total suffix
  MTR-12  format_prometheus() emits sorted counter names
  MTR-13  evaluate_alerts() returns "ok" when no traffic
  MTR-14  evaluate_alerts() returns "warning" on high reward failure rate
  MTR-15  evaluate_alerts() returns "warning" on high waitlist rate
  MTR-16  evaluate_alerts() returns "warning" on high gate block rate
  MTR-17  evaluate_alerts() returns "warning" on slow_queries_total exceeding threshold
  MTR-18  evaluate_alerts() does not emit ratio alerts when denominator is zero
  MTR-19  evaluate_alerts() status "ok" when all ratios are below threshold
  MTR-20  increment_labeled() stores count under label string
  MTR-21  increment_labeled() multiple label values tracked independently
  MTR-22  get_labeled_snapshot() returns a copy (mutations don't affect store)
  MTR-23  reset() clears labeled counters as well as flat counters
  MTR-24  format_prometheus() includes labeled metrics with {key="val"} syntax
  MTR-25  format_prometheus() labels appear under same HELP/TYPE block as flat total
  MTR-26  increment_labeled() label keys are sorted (consistent label_str)
  MTR-27  increment_labeled() with allowed label value produces no warning
  MTR-28  increment_labeled() with unknown label value logs a cardinality warning
  MTR-29  increment_labeled() with unguarded label key is silently accepted
  MTR-30  cardinality warning does not block the increment
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from app.core.metrics import DomainMetrics


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def m() -> DomainMetrics:
    """Fresh DomainMetrics instance for each test."""
    return DomainMetrics()


def _fake_settings(**overrides) -> SimpleNamespace:
    """Return a SimpleNamespace that mimics the alert threshold settings."""
    defaults = dict(
        ALERT_REWARD_FAILURE_RATE=0.05,
        ALERT_BOOKING_WAITLIST_RATE=0.30,
        ALERT_ENROLLMENT_GATE_BLOCK_RATE=0.20,
        ALERT_SLOW_QUERY_TOTAL=10,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── Tests — basic behaviour ────────────────────────────────────────────────────

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
            "slow_queries_total",
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


# ── Tests — Prometheus format ──────────────────────────────────────────────────

class TestDomainMetricsPrometheus:

    def test_mtr09_format_prometheus_includes_help_type_total(self, m: DomainMetrics):
        """MTR-09: format_prometheus() emits HELP, TYPE and _total metric line."""
        m.increment("rewards_generated", by=42)
        text = m.format_prometheus()

        assert "# HELP rewards_generated_total" in text
        assert "# TYPE rewards_generated_total counter" in text
        assert "rewards_generated_total 42" in text

    def test_mtr10_format_prometheus_empty_store_returns_comment(self, m: DomainMetrics):
        """MTR-10: format_prometheus() on empty store returns a comment line, not an error."""
        text = m.format_prometheus()
        assert text.startswith("#")
        # No metric lines — only the comment
        non_comment = [l for l in text.splitlines() if l and not l.startswith("#")]
        assert non_comment == []

    def test_mtr11_format_prometheus_no_double_total_suffix(self, m: DomainMetrics):
        """MTR-11: counter already named with _total is not doubled."""
        m.increment("slow_queries_total", by=3)
        text = m.format_prometheus()

        assert "slow_queries_total 3" in text
        assert "slow_queries_total_total" not in text

    def test_mtr12_format_prometheus_sorted_output(self, m: DomainMetrics):
        """MTR-12: Prometheus output is sorted alphabetically by counter name."""
        m.increment("rewards_generated")
        m.increment("bookings_created")
        m.increment("enrollment_attempts")

        text = m.format_prometheus()
        # Extract metric lines (not HELP/TYPE lines)
        metric_lines = [
            l for l in text.splitlines()
            if l and not l.startswith("#")
        ]
        names = [l.split()[0] for l in metric_lines]
        assert names == sorted(names)

    def test_mtr09b_format_prometheus_ends_with_newline(self, m: DomainMetrics):
        """Prometheus exposition format must end with a newline."""
        m.increment("bookings_created")
        assert m.format_prometheus().endswith("\n")


# ── Tests — Alert evaluation ───────────────────────────────────────────────────

class TestDomainMetricsAlerts:

    def test_mtr13_evaluate_alerts_ok_when_no_traffic(self, m: DomainMetrics):
        """MTR-13: no traffic (all zeros) → status 'ok', ratio alerts absent."""
        result = m.evaluate_alerts(_fake_settings())

        assert result["status"] == "ok"
        thresholds = result["thresholds"]
        # Ratio-based alerts should NOT appear when denominator is zero
        assert "reward_failure_rate" not in thresholds
        assert "booking_waitlist_rate" not in thresholds
        assert "enrollment_gate_block_rate" not in thresholds
        # slow_queries_total is always present (absolute count)
        assert thresholds["slow_queries_total"]["firing"] is False

    def test_mtr14_evaluate_alerts_warning_on_high_reward_failure(self, m: DomainMetrics):
        """MTR-14: rewards_failed / total > threshold → status 'warning'."""
        m.increment("rewards_generated", by=10)
        m.increment("rewards_failed", by=2)  # 16.7 % > 5 % default

        result = m.evaluate_alerts(_fake_settings(ALERT_REWARD_FAILURE_RATE=0.05))

        assert result["status"] == "warning"
        assert result["thresholds"]["reward_failure_rate"]["firing"] is True

    def test_mtr15_evaluate_alerts_warning_on_high_waitlist_rate(self, m: DomainMetrics):
        """MTR-15: bookings_waitlisted / total > threshold → status 'warning'."""
        m.increment("bookings_created", by=5)
        m.increment("bookings_waitlisted", by=5)  # 50 % > 30 % default

        result = m.evaluate_alerts(_fake_settings(ALERT_BOOKING_WAITLIST_RATE=0.30))

        assert result["status"] == "warning"
        assert result["thresholds"]["booking_waitlist_rate"]["firing"] is True

    def test_mtr16_evaluate_alerts_warning_on_high_gate_block_rate(self, m: DomainMetrics):
        """MTR-16: enrollment_gate_blocked / attempts > threshold → status 'warning'."""
        m.increment("enrollment_attempts", by=10)
        m.increment("enrollment_gate_blocked", by=4)  # 40 % > 20 % default

        result = m.evaluate_alerts(_fake_settings(ALERT_ENROLLMENT_GATE_BLOCK_RATE=0.20))

        assert result["status"] == "warning"
        assert result["thresholds"]["enrollment_gate_block_rate"]["firing"] is True

    def test_mtr17_evaluate_alerts_warning_on_slow_query_count(self, m: DomainMetrics):
        """MTR-17: slow_queries_total > ALERT_SLOW_QUERY_TOTAL → status 'warning'."""
        m.increment("slow_queries_total", by=15)  # > 10 default

        result = m.evaluate_alerts(_fake_settings(ALERT_SLOW_QUERY_TOTAL=10))

        assert result["status"] == "warning"
        assert result["thresholds"]["slow_queries_total"]["firing"] is True
        assert result["thresholds"]["slow_queries_total"]["value"] == 15

    def test_mtr18_evaluate_alerts_no_ratio_when_denominator_zero(self, m: DomainMetrics):
        """MTR-18: ratio alerts absent when denominator is zero (avoids div-by-zero)."""
        # Only gate_blocked set, but enrollment_attempts = 0
        m.increment("enrollment_gate_blocked", by=5)

        result = m.evaluate_alerts(_fake_settings())

        # Ratio alert should NOT appear (denominator = 0)
        assert "enrollment_gate_block_rate" not in result["thresholds"]

    def test_mtr19_evaluate_alerts_ok_when_below_thresholds(self, m: DomainMetrics):
        """MTR-19: all counters present but ratios within threshold → status 'ok'."""
        m.increment("rewards_generated", by=100)
        m.increment("rewards_failed", by=2)          # 1.96 % < 5 %
        m.increment("bookings_created", by=100)
        m.increment("bookings_waitlisted", by=10)    # 9.1 % < 30 %
        m.increment("enrollment_attempts", by=100)
        m.increment("enrollment_gate_blocked", by=15)  # 15 % < 20 %
        m.increment("slow_queries_total", by=5)       # 5 ≤ 10

        result = m.evaluate_alerts(_fake_settings())

        assert result["status"] == "ok"
        for alert_key, alert_data in result["thresholds"].items():
            assert alert_data["firing"] is False, (
                f"Alert '{alert_key}' unexpectedly firing: {alert_data}"
            )


# ── Tests — Labeled counters ───────────────────────────────────────────────────

class TestDomainMetricsLabeled:

    def test_mtr20_increment_labeled_stores_count(self, m: DomainMetrics):
        """MTR-20: increment_labeled() stores count under the correct label string."""
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"})
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"})
        m.increment_labeled("bookings_created", {"event_category": "MATCH"})

        snap = m.get_labeled_snapshot()
        assert snap["bookings_created"]["event_category=TRAINING"] == 2
        assert snap["bookings_created"]["event_category=MATCH"] == 1

    def test_mtr21_increment_labeled_independent_counters(self, m: DomainMetrics):
        """MTR-21: different counter names with same labels are tracked independently."""
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"}, by=5)
        m.increment_labeled("bookings_waitlisted", {"event_category": "TRAINING"}, by=2)

        snap = m.get_labeled_snapshot()
        assert snap["bookings_created"]["event_category=TRAINING"] == 5
        assert snap["bookings_waitlisted"]["event_category=TRAINING"] == 2

    def test_mtr22_get_labeled_snapshot_returns_copy(self, m: DomainMetrics):
        """MTR-22: mutating the returned labeled snapshot does not affect the store."""
        m.increment_labeled("rewards_generated", {"event_category": "TRAINING"})
        snap = m.get_labeled_snapshot()
        snap["rewards_generated"]["event_category=TRAINING"] = 999

        fresh = m.get_labeled_snapshot()
        assert fresh["rewards_generated"]["event_category=TRAINING"] == 1

    def test_mtr23_reset_clears_labeled_counters(self, m: DomainMetrics):
        """MTR-23: reset() clears both flat and labeled counters."""
        m.increment("bookings_created", by=3)
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"}, by=3)
        m.reset()

        assert m.get_snapshot() == {}
        assert m.get_labeled_snapshot() == {}

    def test_mtr24_format_prometheus_labeled_with_braces(self, m: DomainMetrics):
        """MTR-24: labeled metrics appear with {key="val"} Prometheus syntax."""
        m.increment("bookings_created", by=10)
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"}, by=8)
        m.increment_labeled("bookings_created", {"event_category": "MATCH"}, by=2)

        text = m.format_prometheus()

        assert 'bookings_created_total{event_category="TRAINING"} 8' in text
        assert 'bookings_created_total{event_category="MATCH"} 2' in text

    def test_mtr25_format_prometheus_labeled_under_same_help_type_block(self, m: DomainMetrics):
        """MTR-25: flat total and labeled breakdowns appear under one HELP/TYPE block."""
        m.increment("bookings_created", by=10)
        m.increment_labeled("bookings_created", {"event_category": "TRAINING"}, by=8)

        text = m.format_prometheus()
        # Only one HELP line for the metric
        help_count = text.count("# HELP bookings_created_total")
        assert help_count == 1
        # Flat total present
        assert "bookings_created_total 10" in text
        # Labeled breakdown present
        assert 'bookings_created_total{event_category="TRAINING"} 8' in text

    def test_mtr26_increment_labeled_keys_sorted(self, m: DomainMetrics):
        """MTR-26: label keys are sorted — calling order doesn't change label_str."""
        m.increment_labeled("rewards_generated", {"b_key": "2", "a_key": "1"})
        m.increment_labeled("rewards_generated", {"a_key": "1", "b_key": "2"})

        snap = m.get_labeled_snapshot()
        # Both calls should map to the same sorted label string
        assert snap["rewards_generated"].get("a_key=1,b_key=2") == 2


# ── Tests — Cardinality guard ──────────────────────────────────────────────────

class TestDomainMetricsCardinalityGuard:

    def test_mtr27_known_label_value_no_warning(self, m: DomainMetrics, caplog):
        """MTR-27: increment_labeled() with an allowed label value produces no warning."""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.metrics.cardinality"):
            m.increment_labeled("bookings_created", {"event_category": "TRAINING"})
        assert not caplog.records

    def test_mtr28_unknown_label_value_logs_warning(self, m: DomainMetrics, caplog):
        """MTR-28: increment_labeled() with a high-cardinality value logs a WARNING."""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.metrics.cardinality"):
            m.increment_labeled("bookings_created", {"event_category": "UNKNOWN_TYPE_99"})
        assert len(caplog.records) == 1
        msg = caplog.records[0].getMessage()
        assert "cardinality" in msg.lower()
        assert "UNKNOWN_TYPE_99" in msg

    def test_mtr29_unguarded_label_key_no_warning(self, m: DomainMetrics, caplog):
        """MTR-29: increment_labeled() with a label key not in the guard dict is silently accepted."""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.metrics.cardinality"):
            m.increment_labeled("bookings_created", {"custom_dimension": "anything"})
        assert not caplog.records

    def test_mtr30_cardinality_warning_does_not_block_increment(self, m: DomainMetrics, caplog):
        """MTR-30: the counter is still incremented even when a cardinality warning fires."""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.metrics.cardinality"):
            m.increment_labeled("bookings_created", {"event_category": "UNKNOWN_TYPE_99"})
        snap = m.get_labeled_snapshot()
        assert snap["bookings_created"]["event_category=UNKNOWN_TYPE_99"] == 1
