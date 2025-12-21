"""
Performance Monitoring Middleware for FastAPI

Integrates query monitoring with FastAPI requests.
Automatically tracks database queries for each API endpoint.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.query_logger import monitor_queries, get_performance_metrics
import logging

logger = logging.getLogger("performance_middleware")


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for performance monitoring.

    Features:
    - Tracks request duration
    - Monitors database queries per request
    - Logs slow endpoints
    - Detects N+1 query patterns
    - Adds performance headers to response
    """

    def __init__(
        self,
        app,
        slow_request_threshold_ms: int = 1000,
        enable_headers: bool = True
    ):
        """
        Initialize performance monitoring middleware.

        Args:
            app: FastAPI application
            slow_request_threshold_ms: Threshold for slow request logging
            enable_headers: Add performance headers to response
        """
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.enable_headers = enable_headers

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with performance monitoring.

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with performance headers
        """
        # Get endpoint name
        endpoint_name = f"{request.method} {request.url.path}"

        # Start timing
        start_time = time.time()

        # Monitor queries
        with monitor_queries(endpoint_name) as monitor:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Get query metrics
            metrics = get_performance_metrics()

            # Log slow requests
            if duration_ms > self.slow_request_threshold_ms:
                logger.warning(
                    f"SLOW REQUEST ({duration_ms:.2f}ms): {endpoint_name} | "
                    f"Queries: {metrics['query_count']} | "
                    f"DB Time: {metrics['total_query_time_ms']:.2f}ms"
                )

            # Add performance headers
            if self.enable_headers:
                response.headers["X-Request-Duration-Ms"] = str(round(duration_ms, 2))
                response.headers["X-Query-Count"] = str(metrics['query_count'])
                response.headers["X-Query-Time-Ms"] = str(
                    round(metrics['total_query_time_ms'], 2)
                )

            # Log general info
            logger.info(
                f"{endpoint_name} | "
                f"Duration: {duration_ms:.2f}ms | "
                f"Queries: {metrics['query_count']} | "
                f"DB Time: {metrics['total_query_time_ms']:.2f}ms"
            )

            return response
