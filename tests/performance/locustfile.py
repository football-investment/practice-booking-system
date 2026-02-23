"""
Performance Baseline — Locust Load Test

Purpose: Establish baseline latency + throughput metrics for critical revenue path
Scenario: Tournament creation + enrollment workflow
Target: Revenue-critical API endpoint (/api/v1/tournaments/ops/run-scenario)

Philosophy:
- 1 baseline scenario (NO complexity)
- Measure: p50, p95, p99 latency + RPS (requests per second)
- Identify: Performance degradation threshold
- Guard: Prevent regression via CI performance gate

Usage:
  # Local smoke test (1 user, 10s)
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
         --users=1 --spawn-rate=1 --run-time=10s --headless

  # Baseline load (10 concurrent users, 60s)
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
         --users=10 --spawn-rate=2 --run-time=60s --headless

  # Web UI mode (interactive)
  locust -f tests/performance/locustfile.py --host=http://localhost:8000

Environment Variables:
  ADMIN_EMAIL: Admin user email (default: admin@lfa.com)
  ADMIN_PASSWORD: Admin user password (default: admin123)
"""

import os
import random
from locust import HttpUser, task, between, events


# ============================================================================
# CONFIGURATION
# ============================================================================

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Campus IDs for tournament session generation
# Note: Uses existing PERF_TEST_Campus (id=9) created for location 10
# If not available, create via: POST /api/v1/admin/locations/{id}/campuses
CAMPUS_IDS = [9]


# ============================================================================
# BASELINE SCENARIO: Tournament Creation + Enrollment
# ============================================================================

class TournamentCreationUser(HttpUser):
    """
    Simulates admin creating tournaments via OPS Scenario endpoint.

    Workflow:
    1. Login as admin (once per user session)
    2. Create tournament via OPS Scenario (smoke_test, 4 players)
    3. Verify response: tournament_id + enrolled_count = 4

    Metrics tracked:
    - /api/v1/auth/login: p50, p95, p99 latency
    - /api/v1/tournaments/ops/run-scenario: p50, p95, p99 latency, RPS
    """

    # Wait time between tasks (simulates user think time)
    wait_time = between(1, 3)

    # Admin token (set on_start, reused across tasks)
    admin_token = None


    def on_start(self):
        """
        Called once when a simulated user starts.
        Login as admin and store token for subsequent requests.
        """
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            name="Login (Admin)"
        )

        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
        else:
            # Login failed - mark as failure and stop
            response.failure(f"Admin login failed: {response.text}")
            self.environment.runner.quit()


    @task
    def create_tournament_smoke_test(self):
        """
        Baseline scenario: Create tournament via OPS Scenario.

        Measures:
        - Tournament creation latency (revenue-critical path)
        - Auto-enrollment success rate
        - API error rate (4xx, 5xx)

        Expected:
        - HTTP 200 (success)
        - tournament_id present
        - enrolled_count = 4 (auto mode with @lfa-seed.hu users)
        """
        if not self.admin_token:
            # Skip if login failed
            return

        # Randomize tournament type to simulate realistic load distribution
        tournament_types = ["knockout", "league"]
        selected_type = random.choice(tournament_types)

        response = self.client.post(
            "/api/v1/tournaments/ops/run-scenario",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "scenario": "smoke_test",
                "player_count": 4,  # Auto mode (uses @lfa-seed.hu users)
                "tournament_format": "HEAD_TO_HEAD",
                "tournament_type_code": selected_type,
                "simulation_mode": "manual",
                "dry_run": False,
                "confirmed": False,
                "campus_ids": CAMPUS_IDS,
            },
            name="Create Tournament (OPS Scenario)"
        )

        # Validate response structure
        if response.status_code == 200:
            data = response.json()
            tournament_id = data.get("tournament_id")
            enrolled_count = data.get("enrolled_count", 0)

            if not tournament_id:
                response.failure("Missing tournament_id in response")
            elif enrolled_count != 4:
                response.failure(f"Expected 4 enrollments, got {enrolled_count}")
        else:
            # HTTP error (4xx, 5xx) - automatically marked as failure by Locust
            pass


# ============================================================================
# PERFORMANCE BASELINE METRICS (Expected Values)
# ============================================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Print baseline performance expectations.
    Run after load test to compare actual vs expected metrics.
    """
    print("=" * 70)
    print("PERFORMANCE BASELINE EXPECTATIONS (v1.0)")
    print("=" * 70)
    print("Endpoint: POST /api/v1/tournaments/ops/run-scenario")
    print()
    print("Latency Targets:")
    print("  - p50 (median):  < 500ms")
    print("  - p95:           < 1500ms")
    print("  - p99:           < 3000ms")
    print()
    print("Throughput Target:")
    print("  - RPS (10 users): > 5 req/s")
    print()
    print("Error Rate:")
    print("  - Failure rate:  < 1%")
    print()
    print("Load Profile:")
    print("  - Concurrent users: 1-10")
    print("  - Duration: 60s")
    print("=" * 70)
    print()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print performance summary after test completion.
    """
    print()
    print("=" * 70)
    print("PERFORMANCE TEST COMPLETE")
    print("=" * 70)
    print("Next steps:")
    print("1. Review Locust report (latency percentiles, RPS, error rate)")
    print("2. Compare actual metrics vs baseline expectations")
    print("3. If degradation > 20%: Investigate performance regression")
    print("4. Update PERFORMANCE_BASELINE_SPECIFICATION.md with findings")
    print("=" * 70)
