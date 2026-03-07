"""
Sprint 30 — app/middleware/query_logger.py
==========================================
Target: ≥85% statement, ≥70% branch

Covers:
  QueryMonitor.reset()             — initializes state
  QueryMonitor.log_query()         — fast query (no warning) + slow query (warning logged)
  QueryMonitor.get_summary()       — with start_time/queries, without start_time
  QueryMonitor.detect_n_plus_one() — count < 10, count ≥ 10 no pattern,
                                     count ≥ 10 with repeated query (N+1 detected)
  monitor_queries()                — no N+1 no overflow, N+1 detected, query count > 20
  get_performance_metrics()        — returns summary dict
"""

import pytest
from unittest.mock import patch, MagicMock
import time


# ── helpers ──────────────────────────────────────────────────────────────────

def _fresh_monitor():
    """Return a fresh QueryMonitor with reset state."""
    from app.middleware.query_logger import QueryMonitor
    m = QueryMonitor(slow_query_threshold_ms=100)
    m.reset()
    return m


# ============================================================================
# QueryMonitor.reset()
# ============================================================================

class TestQueryMonitorReset:

    def test_reset_clears_state(self):
        """QMR-01: reset → query_count=0, total=0, queries=[], start_time set."""
        m = _fresh_monitor()
        m.query_count = 5
        m.total_query_time_ms = 500
        m.queries = [{"a": 1}]
        m.reset()
        assert m.query_count == 0
        assert m.total_query_time_ms == 0
        assert m.queries == []
        assert m.start_time is not None


# ============================================================================
# QueryMonitor.log_query()
# ============================================================================

class TestQueryMonitorLogQuery:

    def test_fast_query_no_warning(self, caplog):
        """QML-01: duration < threshold → no warning logged."""
        import logging
        m = _fresh_monitor()
        with caplog.at_level(logging.DEBUG, logger="slow_query_monitor"):
            m.log_query("SELECT 1", {}, duration_ms=50)
        assert m.query_count == 1
        assert m.total_query_time_ms == 50
        assert len(m.queries) == 1
        assert not any("SLOW" in msg for msg in caplog.messages)

    def test_slow_query_logs_warning(self, caplog):
        """QML-02: duration > threshold → 'SLOW QUERY' warning logged."""
        import logging
        m = _fresh_monitor()
        with caplog.at_level(logging.WARNING, logger="slow_query_monitor"):
            m.log_query("SELECT * FROM big_table", {}, duration_ms=500)
        assert any("SLOW" in msg for msg in caplog.messages)

    def test_multiple_queries_accumulate(self):
        """QML-03: multiple calls → count and total accumulate."""
        m = _fresh_monitor()
        m.log_query("SELECT 1", {}, duration_ms=10)
        m.log_query("SELECT 2", {}, duration_ms=20)
        assert m.query_count == 2
        assert m.total_query_time_ms == 30

    def test_statement_truncated_to_200(self):
        """QML-04: long statement → truncated to 200 chars in query_info."""
        m = _fresh_monitor()
        long_stmt = "X" * 300
        m.log_query(long_stmt, {}, duration_ms=5)
        assert len(m.queries[0]["statement"]) == 200

    def test_caller_info_stored(self):
        """QML-05: caller_info provided → stored in query_info."""
        m = _fresh_monitor()
        m.log_query("SELECT 1", {}, duration_ms=5, caller_info="test_caller")
        assert m.queries[0]["caller"] == "test_caller"


# ============================================================================
# QueryMonitor.get_summary()
# ============================================================================

class TestQueryMonitorGetSummary:

    def test_empty_monitor_summary(self):
        """QMS-01: no queries → count=0, slowest=0."""
        m = _fresh_monitor()
        summary = m.get_summary()
        assert summary["query_count"] == 0
        assert summary["total_query_time_ms"] == 0
        assert summary["average_query_time_ms"] == 0
        assert summary["slowest_query_ms"] == 0

    def test_summary_with_queries(self):
        """QMS-02: with queries → averages and max computed correctly."""
        m = _fresh_monitor()
        m.log_query("SELECT 1", {}, duration_ms=10)
        m.log_query("SELECT 2", {}, duration_ms=30)
        summary = m.get_summary()
        assert summary["query_count"] == 2
        assert summary["total_query_time_ms"] == 40
        assert summary["average_query_time_ms"] == 20
        assert summary["slowest_query_ms"] == 30

    def test_no_start_time_request_duration_zero(self):
        """QMS-03: start_time=None → request_duration_ms=0."""
        from app.middleware.query_logger import QueryMonitor
        m = QueryMonitor()
        m.start_time = None
        summary = m.get_summary()
        assert summary["request_duration_ms"] == 0

    def test_last_10_queries_only(self):
        """QMS-04: more than 10 queries → only last 10 in 'queries' key."""
        m = _fresh_monitor()
        for i in range(15):
            m.log_query(f"SELECT {i}", {}, duration_ms=1)
        summary = m.get_summary()
        assert len(summary["queries"]) == 10


# ============================================================================
# QueryMonitor.detect_n_plus_one()
# ============================================================================

class TestDetectNPlusOne:

    def test_less_than_10_queries_returns_false(self):
        """N1-01: query_count < 10 → False immediately."""
        m = _fresh_monitor()
        m.query_count = 5
        assert m.detect_n_plus_one() is False

    def test_10_queries_no_pattern_returns_false(self):
        """N1-02: 10 different queries → no N+1 → False."""
        m = _fresh_monitor()
        for i in range(10):
            m.log_query(f"SELECT {i} FROM table_{i}", {}, duration_ms=1)
        assert m.detect_n_plus_one() is False

    def test_n_plus_one_detected(self, caplog):
        """N1-03: same query repeated 10+ times → True + error logged."""
        import logging
        m = _fresh_monitor()
        same_stmt = "SELECT * FROM users WHERE id = %s"
        for i in range(11):
            m.log_query(same_stmt, {}, duration_ms=1)
        with caplog.at_level(logging.ERROR, logger="slow_query_monitor"):
            result = m.detect_n_plus_one()
        assert result is True
        assert any("N+1" in msg for msg in caplog.messages)


# ============================================================================
# monitor_queries() context manager
# ============================================================================

class TestMonitorQueries:

    def test_basic_context_manager(self, caplog):
        """MQ-01: basic usage → logs endpoint summary."""
        import logging
        from app.middleware.query_logger import monitor_queries
        with caplog.at_level(logging.INFO, logger="slow_query_monitor"):
            with monitor_queries("GET /test") as mon:
                pass  # no queries
        assert any("GET /test" in msg for msg in caplog.messages)

    def test_n_plus_one_detection_in_context(self, caplog):
        """MQ-02: 11 identical queries → N+1 error logged."""
        import logging
        from app.middleware.query_logger import monitor_queries
        with caplog.at_level(logging.ERROR, logger="slow_query_monitor"):
            with monitor_queries("GET /heavy") as mon:
                for _ in range(11):
                    mon.log_query("SELECT * FROM same_table WHERE id=%s", {}, duration_ms=1)
        assert any("N+1" in msg for msg in caplog.messages)

    def test_high_query_count_logs_warning(self, caplog):
        """MQ-03: query_count > 20 → warning logged."""
        import logging
        from app.middleware.query_logger import monitor_queries
        with caplog.at_level(logging.WARNING, logger="slow_query_monitor"):
            with monitor_queries("GET /bloated") as mon:
                for i in range(21):
                    mon.log_query(f"SELECT {i}", {}, duration_ms=1)
        assert any("HIGH QUERY COUNT" in msg for msg in caplog.messages)


# ============================================================================
# get_performance_metrics()
# ============================================================================

class TestGetPerformanceMetrics:

    def test_returns_summary_dict(self):
        """GPM-01: returns dict with standard keys."""
        from app.middleware.query_logger import get_performance_metrics
        result = get_performance_metrics()
        assert "query_count" in result
        assert "total_query_time_ms" in result
        assert "average_query_time_ms" in result
        assert "slowest_query_ms" in result
