"""
Slow Query Monitoring Middleware

This middleware logs slow database queries for performance monitoring.
Helps identify N+1 query problems and optimization opportunities.
"""

import time
import logging
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine
from datetime import datetime
import json

# Configure logging
logger = logging.getLogger("slow_query_monitor")
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler("logs/slow_queries.log")
console_handler = logging.StreamHandler()

# Create formatters
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class QueryMonitor:
    """
    Monitors database queries and logs slow queries.

    Features:
    - Logs queries exceeding threshold
    - Tracks query count per request
    - Detects N+1 query patterns
    - Performance metrics collection
    """

    def __init__(self, slow_query_threshold_ms: int = 100):
        """
        Initialize query monitor.

        Args:
            slow_query_threshold_ms: Threshold in milliseconds for slow queries
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_count = 0
        self.total_query_time_ms = 0
        self.queries = []
        self.start_time = None

    def reset(self):
        """Reset query statistics for new request"""
        self.query_count = 0
        self.total_query_time_ms = 0
        self.queries = []
        self.start_time = time.time()

    def log_query(
        self,
        statement: str,
        parameters: dict,
        duration_ms: float,
        caller_info: Optional[str] = None
    ):
        """
        Log a database query.

        Args:
            statement: SQL statement
            parameters: Query parameters
            duration_ms: Query execution time in milliseconds
            caller_info: Optional caller context
        """
        self.query_count += 1
        self.total_query_time_ms += duration_ms

        query_info = {
            "query_number": self.query_count,
            "duration_ms": round(duration_ms, 2),
            "statement": statement[:200],  # Truncate for readability
            "parameters": str(parameters)[:100],
            "caller": caller_info,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.queries.append(query_info)

        # Log slow queries
        if duration_ms > self.slow_query_threshold_ms:
            logger.warning(
                f"SLOW QUERY ({duration_ms:.2f}ms): {statement[:100]}"
            )

    def get_summary(self) -> dict:
        """
        Get query statistics summary.

        Returns:
            Dictionary with query statistics
        """
        request_duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0

        return {
            "query_count": self.query_count,
            "total_query_time_ms": round(self.total_query_time_ms, 2),
            "average_query_time_ms": round(
                self.total_query_time_ms / self.query_count if self.query_count > 0 else 0,
                2
            ),
            "slowest_query_ms": round(
                max([q["duration_ms"] for q in self.queries]) if self.queries else 0,
                2
            ),
            "request_duration_ms": round(request_duration_ms, 2),
            "queries": self.queries[-10:]  # Last 10 queries
        }

    def detect_n_plus_one(self) -> bool:
        """
        Detect potential N+1 query patterns.

        Returns:
            True if N+1 pattern detected
        """
        if self.query_count < 10:
            return False

        # Check for similar queries executed multiple times
        statement_counts = {}
        for query in self.queries:
            stmt = query["statement"][:50]  # Compare first 50 chars
            statement_counts[stmt] = statement_counts.get(stmt, 0) + 1

        # If same query executed 10+ times, likely N+1
        for count in statement_counts.values():
            if count >= 10:
                logger.error(
                    f"N+1 QUERY PATTERN DETECTED: {count} similar queries in single request"
                )
                return True

        return False


# Global query monitor instance
query_monitor = QueryMonitor()


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQLAlchemy event: before query execution"""
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQLAlchemy event: after query execution"""
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    duration_ms = total_time * 1000

    # Log query
    query_monitor.log_query(
        statement=statement,
        parameters=parameters,
        duration_ms=duration_ms
    )


@contextmanager
def monitor_queries(endpoint_name: str):
    """
    Context manager to monitor queries for a specific endpoint.

    Usage:
        with monitor_queries("GET /sessions/"):
            # Your database operations here
            sessions = db.query(Session).all()

    Args:
        endpoint_name: Name of the endpoint being monitored
    """
    query_monitor.reset()

    try:
        yield query_monitor
    finally:
        summary = query_monitor.get_summary()

        # Log summary
        logger.info(
            f"ENDPOINT: {endpoint_name} | "
            f"Queries: {summary['query_count']} | "
            f"Total Time: {summary['total_query_time_ms']}ms | "
            f"Request Duration: {summary['request_duration_ms']}ms"
        )

        # Check for N+1 patterns
        if query_monitor.detect_n_plus_one():
            logger.error(
                f"N+1 PATTERN in {endpoint_name}: "
                f"{summary['query_count']} queries executed"
            )

        # Log detailed info if too many queries
        if summary['query_count'] > 20:
            logger.warning(
                f"HIGH QUERY COUNT in {endpoint_name}: "
                f"{summary['query_count']} queries | "
                f"Queries: {json.dumps(summary['queries'], indent=2)}"
            )


def get_performance_metrics() -> dict:
    """
    Get current performance metrics.

    Returns:
        Dictionary with performance metrics
    """
    return query_monitor.get_summary()
