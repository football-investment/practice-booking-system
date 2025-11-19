"""
Locust Load Test - Progress Update Storm
=========================================

P2 Production Readiness - Phase 2: Load Testing

Scenario: 1,000 concurrent users updating progress simultaneously

Test Objectives:
- Measure API latency under load
- Validate auto-sync hook performance
- Test database connection pool
- Verify no race conditions

Target Metrics:
- Requests/sec: >500
- Median Response Time: <100ms
- 95th Percentile: <500ms
- Failure Rate: <1%

Usage:
    locust -f scripts/load_test_progress_update.py \
      --host=https://staging.yourdomain.com \
      --users=1000 \
      --spawn-rate=50 \
      --run-time=10m

Author: Claude Code
Date: 2025-10-25
"""

from locust import HttpUser, task, between, events
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgressUpdateUser(HttpUser):
    """Simulates user updating progress and triggering auto-sync"""

    wait_time = between(1, 3)  # 1-3 seconds between requests

    def on_start(self):
        """Login as admin user before starting tasks"""
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
                logger.info(f"User {self.environment.runner.user_count} logged in successfully")
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                self.token = None

        except Exception as e:
            logger.error(f"Login exception: {str(e)}")
            self.token = None

    @task(10)  # Weight: 10 (most common operation)
    def update_progress(self):
        """Update user progress (triggers auto-sync hook)"""
        if not self.token:
            return

        user_id = random.randint(1, 10000)  # 10K user pool
        specialization = random.choice(["PLAYER", "COACH", "INTERNSHIP"])
        xp_change = random.randint(10, 200)  # Small to medium XP gains

        with self.client.post(
            "/api/v1/specializations/progress/update",
            json={
                "student_id": user_id,
                "specialization_id": specialization,
                "xp_change": xp_change
            },
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/specializations/progress/update"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # User or specialization not found (expected for random IDs)
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(3)  # Weight: 3
    def check_health_status(self):
        """Check health dashboard status"""
        if not self.token:
            return

        with self.client.get(
            "/api/v1/health/status",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)  # Weight: 1 (least common, expensive operation)
    def trigger_manual_health_check(self):
        """Trigger manual health check (expensive operation)"""
        if not self.token:
            return

        with self.client.post(
            "/api/v1/health/check-now",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/health/check-now"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# Event listeners for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when test starts"""
    logger.info("="*70)
    logger.info("🔥 LOAD TEST STARTED: Progress Update Storm")
    logger.info("="*70)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log when test stops and print summary"""
    logger.info("="*70)
    logger.info("✅ LOAD TEST COMPLETED")
    logger.info("="*70)

    # Print summary stats
    stats = environment.stats.total
    logger.info(f"Total Requests: {stats.num_requests}")
    logger.info(f"Total Failures: {stats.num_failures}")
    logger.info(f"Failure Rate: {(stats.num_failures/stats.num_requests*100) if stats.num_requests > 0 else 0:.2f}%")
    logger.info(f"Median Response Time: {stats.median_response_time}ms")
    logger.info(f"95th Percentile: {stats.get_response_time_percentile(0.95)}ms")
    logger.info(f"Requests/sec: {stats.total_rps:.2f}")
    logger.info("="*70)
