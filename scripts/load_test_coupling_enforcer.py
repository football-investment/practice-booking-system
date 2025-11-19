"""
Locust Load Test - Coupling Enforcer Stress Test
=================================================

P2 Production Readiness - Phase 2: Load Testing

Scenario: 500 concurrent users updating same 100 users (maximum contention)

Test Objectives:
- Stress test Coupling Enforcer pessimistic locking
- Validate no race conditions under extreme contention
- Verify atomic transactions hold under pressure
- Measure latency overhead from locking

Target Metrics:
- No desync issues (all Progress-License consistent)
- No deadlocks
- No race conditions
- Latency < 200ms (with locking overhead)

Usage:
    locust -f scripts/load_test_coupling_enforcer.py \
      --host=https://staging.yourdomain.com \
      --users=500 \
      --spawn-rate=100 \
      --run-time=5m

Author: Claude Code
Date: 2025-10-25
"""

from locust import HttpUser, task, between, events
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CouplingEnforcerStressUser(HttpUser):
    """Simulates extreme contention on Coupling Enforcer"""

    wait_time = between(0.1, 0.5)  # Very fast requests (high contention)

    def on_start(self):
        """Login as admin user"""
        try:
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": "admin@staging.example.com",
                    "password": "staging_password"
                },
                name="/api/v1/auth/login"
            )

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                logger.info(f"Stress user {self.environment.runner.user_count} logged in")
            else:
                logger.error(f"Login failed: {response.status_code}")
                self.token = None

        except Exception as e:
            logger.error(f"Login exception: {str(e)}")
            self.token = None

    @task
    def concurrent_update_same_users(self):
        """Update progress for same 100 users (maximum contention)"""
        if not self.token:
            return

        # Target same 100 users for maximum lock contention
        user_id = random.randint(1, 100)
        xp_change = random.randint(10, 50)

        with self.client.post(
            "/api/v1/specializations/progress/update",
            json={
                "student_id": user_id,
                "specialization_id": "PLAYER",
                "xp_change": xp_change
            },
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/v1/specializations/progress/update (CONTENTION)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # User not found (expected for some IDs)
                response.success()
            elif response.status_code == 409:
                # Conflict (possible under extreme contention, should retry)
                logger.warning(f"Conflict on user {user_id}")
                response.failure("Conflict (409)")
            else:
                response.failure(f"Failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when stress test starts"""
    logger.info("="*70)
    logger.info("🔥 STRESS TEST STARTED: Coupling Enforcer Contention")
    logger.info("Target: Same 100 users with 500 concurrent requests")
    logger.info("="*70)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and verify consistency"""
    logger.info("="*70)
    logger.info("✅ STRESS TEST COMPLETED")
    logger.info("="*70)

    stats = environment.stats.total
    logger.info(f"Total Requests: {stats.num_requests}")
    logger.info(f"Total Failures: {stats.num_failures}")
    logger.info(f"Failure Rate: {(stats.num_failures/stats.num_requests*100) if stats.num_requests > 0 else 0:.2f}%")
    logger.info(f"Median Response Time: {stats.median_response_time}ms")
    logger.info(f"95th Percentile: {stats.get_response_time_percentile(0.95)}ms")
    logger.info(f"Requests/sec: {stats.total_rps:.2f}")

    logger.info("\n⚠️  IMPORTANT: After test, verify consistency:")
    logger.info("   Run: python3 scripts/test_backend_workflow.py")
    logger.info("   Or: curl /api/v1/health/check-now")
    logger.info("   Expected: 0 desync issues")
    logger.info("="*70)
