"""
Locust Load Test - Health Dashboard Load
=========================================

P2 Production Readiness - Phase 2: Load Testing

Scenario: 100 admins refreshing dashboard simultaneously (mimics auto-refresh)

Test Objectives:
- Measure health API endpoint performance
- Validate manual check under concurrent requests
- Test JSON log parsing performance
- Verify no bottlenecks in health monitoring

Target Metrics:
- Requests/sec: >200
- Median Response Time: <50ms (cached data)
- Manual Check Time: <15s (for 10K users)
- Failure Rate: <0.1%

Usage:
    locust -f scripts/load_test_health_dashboard.py \
      --host=https://staging.yourdomain.com \
      --users=100 \
      --spawn-rate=20 \
      --run-time=10m

Author: Claude Code
Date: 2025-10-25
"""

from locust import HttpUser, task, between, events
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthDashboardUser(HttpUser):
    """Simulates admin users accessing health dashboard"""

    wait_time = between(30, 60)  # Mimic 30s auto-refresh with variance

    def on_start(self):
        """Login as admin user"""
        try:
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": "admin@example.com",
                    "password": "admin_password"
                },
                name="/api/v1/auth/login"
            )

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                logger.info(f"Admin user {self.environment.runner.user_count} logged in")
            else:
                logger.error(f"Login failed: {response.status_code}")
                self.token = None

        except Exception as e:
            logger.error(f"Login exception: {str(e)}")
            self.token = None

    @task(5)  # Weight: 5 (most common - auto-refresh)
    def get_health_status(self):
        """Get health status (dashboard auto-refresh)"""
        if not self.token:
            return

        with self.client.get(
            "/api/v1/health/status",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/status"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate response structure
                if "status" in data and "consistency_rate" in data:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(3)  # Weight: 3
    def get_health_metrics(self):
        """Get health metrics (dashboard metrics card)"""
        if not self.token:
            return

        with self.client.get(
            "/api/v1/health/metrics",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/metrics"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate metrics structure
                if "total_users_monitored" in data and "violations_count" in data:
                    response.success()
                else:
                    response.failure("Invalid metrics structure")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)  # Weight: 2
    def get_violations(self):
        """Get violations list (dashboard violations table)"""
        if not self.token:
            return

        with self.client.get(
            "/api/v1/health/violations",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/violations"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Should be array (even if empty)
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Expected array response")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)  # Weight: 1 (least common, expensive operation)
    def trigger_manual_check(self):
        """Trigger manual health check (expensive, 10K users)"""
        if not self.token:
            return

        with self.client.post(
            "/api/v1/health/check-now",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/check-now"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate check result structure
                if "total_checked" in data and "consistency_rate" in data:
                    logger.info(f"Manual check: {data['total_checked']} users, {data['consistency_rate']}% consistent")
                    response.success()
                else:
                    response.failure("Invalid check result structure")
            else:
                response.failure(f"Failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when dashboard load test starts"""
    logger.info("="*70)
    logger.info("🏥 LOAD TEST STARTED: Health Dashboard")
    logger.info("Target: 100 concurrent admins with 30s auto-refresh")
    logger.info("="*70)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion with detailed stats"""
    logger.info("="*70)
    logger.info("✅ DASHBOARD LOAD TEST COMPLETED")
    logger.info("="*70)

    # Overall stats
    stats = environment.stats.total
    logger.info(f"Total Requests: {stats.num_requests}")
    logger.info(f"Total Failures: {stats.num_failures}")
    logger.info(f"Failure Rate: {(stats.num_failures/stats.num_requests*100) if stats.num_requests > 0 else 0:.2f}%")
    logger.info(f"Median Response Time: {stats.median_response_time}ms")
    logger.info(f"95th Percentile: {stats.get_response_time_percentile(0.95)}ms")
    logger.info(f"Requests/sec: {stats.total_rps:.2f}")

    # Per-endpoint stats
    logger.info("\n📊 Per-Endpoint Breakdown:")
    for name, entry in environment.stats.entries.items():
        if entry.num_requests > 0:
            logger.info(f"  {name}:")
            logger.info(f"    Requests: {entry.num_requests}")
            logger.info(f"    Failures: {entry.num_failures}")
            logger.info(f"    Median: {entry.median_response_time}ms")
            logger.info(f"    95th: {entry.get_response_time_percentile(0.95)}ms")

    logger.info("="*70)
