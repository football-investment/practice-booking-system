"""
Unit tests — GET /metrics and GET /metrics/alerts endpoints
============================================================

Tests
-----
  EP-01  GET /metrics returns JSON counters dict
  EP-02  GET /metrics?format=prometheus returns text/plain
  EP-03  GET /metrics?format=prometheus contains _total metric lines
  EP-04  GET /metrics?format=json is same as default JSON response
  EP-05  GET /metrics/alerts returns status and thresholds keys
  EP-06  GET /metrics/alerts status is "ok" when counters are zero
  EP-07  GET /metrics/alerts status is "warning" when slow_queries_total exceeded
  EP-08  GET /metrics JSON includes labeled_counters key
  EP-09  GET /metrics JSON labeled_counters populated after increment_labeled()
  EP-10  GET /health/ready returns 200 when DB healthy
  EP-11  GET /health/ready returns 503 when DB unhealthy
  EP-12  GET /health/worker returns 503 when Redis is down
  EP-13  GET /health/worker returns 200 when Redis is healthy (degraded worker)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset the process-wide metrics singleton before and after each test."""
    from app.core.metrics import metrics
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestMetricsJsonEndpoint:

    def test_ep01_json_response_has_counters_key(self, client: TestClient):
        """EP-01: GET /metrics returns {"counters": {...}}."""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert "counters" in body
        assert isinstance(body["counters"], dict)

    def test_ep02_prometheus_response_is_text_plain(self, client: TestClient):
        """EP-02: GET /metrics?format=prometheus returns text/plain content-type."""
        resp = client.get("/metrics?format=prometheus")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/plain" in content_type

    def test_ep03_prometheus_response_contains_total_lines(self, client: TestClient):
        """EP-03: Prometheus format contains _total metric lines after incrementing."""
        from app.core.metrics import metrics
        metrics.increment("bookings_created", by=7)

        resp = client.get("/metrics?format=prometheus")
        assert resp.status_code == 200
        text = resp.text
        assert "bookings_created_total 7" in text
        assert "# TYPE bookings_created_total counter" in text

    def test_ep04_format_json_param_same_as_default(self, client: TestClient):
        """EP-04: ?format=json gives same structure as the default response."""
        from app.core.metrics import metrics
        metrics.increment("rewards_generated", by=3)

        default_resp = client.get("/metrics")
        json_resp = client.get("/metrics?format=json")

        assert default_resp.status_code == 200
        assert json_resp.status_code == 200
        assert default_resp.json() == json_resp.json()


class TestMetricsAlertsEndpoint:

    def test_ep05_alerts_returns_status_and_thresholds(self, client: TestClient):
        """EP-05: GET /metrics/alerts returns status and thresholds keys."""
        resp = client.get("/metrics/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "thresholds" in body

    def test_ep06_alerts_ok_when_counters_zero(self, client: TestClient):
        """EP-06: status is 'ok' when no counters have been incremented."""
        resp = client.get("/metrics/alerts")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ep07_alerts_warning_when_slow_query_exceeded(self, client: TestClient):
        """EP-07: status becomes 'warning' when slow_queries_total > threshold (default 10)."""
        from app.core.metrics import metrics
        metrics.increment("slow_queries_total", by=11)

        resp = client.get("/metrics/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "warning"
        assert body["thresholds"]["slow_queries_total"]["firing"] is True


class TestMetricsLabeledEndpoint:

    def test_ep08_json_includes_labeled_counters_key(self, client: TestClient):
        """EP-08: GET /metrics JSON always includes 'labeled_counters' key."""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "labeled_counters" in resp.json()

    def test_ep09_labeled_counters_populated_after_increment(self, client: TestClient):
        """EP-09: labeled_counters reflects increment_labeled() calls."""
        from app.core.metrics import metrics
        metrics.increment_labeled("bookings_created", {"event_category": "TRAINING"}, by=4)

        resp = client.get("/metrics")
        assert resp.status_code == 200
        labeled = resp.json()["labeled_counters"]
        assert labeled["bookings_created"]["event_category=TRAINING"] == 4


class TestHealthEndpointStatusCodes:
    """Health endpoints return correct HTTP status codes for orchestrators."""

    def test_ep10_health_ready_200_when_db_healthy(self, client: TestClient):
        """EP-10: /health/ready returns 200 when database health check passes."""
        from unittest.mock import AsyncMock, patch
        with patch(
            "app.main.HealthChecker.get_database_health",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ):
            resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_ep11_health_ready_503_when_db_unhealthy(self, client: TestClient):
        """EP-11: /health/ready returns 503 when database is unreachable."""
        from unittest.mock import AsyncMock, patch
        with patch(
            "app.main.HealthChecker.get_database_health",
            new_callable=AsyncMock,
            return_value={"status": "unhealthy"},
        ):
            resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not_ready"
        assert resp.json()["database"] == "unhealthy"

    def test_ep12_health_worker_503_when_redis_down(self, client: TestClient):
        """EP-12: /health/worker returns 503 when Redis is unreachable."""
        from unittest.mock import AsyncMock, patch
        with patch(
            "app.main.HealthChecker.get_worker_health",
            new_callable=AsyncMock,
            return_value={"status": "unhealthy", "redis": "unhealthy", "workers": None},
        ):
            resp = client.get("/health/worker")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unhealthy"

    def test_ep13_health_worker_200_when_degraded(self, client: TestClient):
        """EP-13: /health/worker returns 200 when Redis ok but no workers registered."""
        from unittest.mock import AsyncMock, patch
        with patch(
            "app.main.HealthChecker.get_worker_health",
            new_callable=AsyncMock,
            return_value={"status": "degraded", "redis": "healthy", "workers": []},
        ):
            resp = client.get("/health/worker")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"
