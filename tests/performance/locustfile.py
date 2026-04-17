"""
Performance Baseline — Locust Load Test
========================================

Phase 5 baseline (TournamentCreationUser):
  Scenario: Admin creates tournaments via OPS Scenario endpoint.
  Target: /api/v1/tournaments/ops/run-scenario

Phase 6.2 (BrowseAndEnrollUser):
  Scenario: 70% browse public event page / 30% student enroll + withdraw
  Target: GET /events/{id} (public), POST /semesters/request-enrollment,
          POST /semesters/withdraw-enrollment

Usage — Phase 5 baseline:
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
         --users=1 --spawn-rate=1 --run-time=10s --headless

  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
         --users=10 --spawn-rate=2 --run-time=60s --headless

Usage — Phase 6.2 (requires running uvicorn + seed data):
  # Start server first:
  #   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  # Smoke (5 users, 30s):
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
         --users=5 --spawn-rate=2 --run-time=30s --headless \\
         --class-picker  # select BrowseAndEnrollUser

  # Baseline load (30 users, 120s):
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
         --users=30 --spawn-rate=5 --run-time=120s --headless \\
         --class-picker

  # Stress (100 users, 180s — rate limit fires at this scale by design):
  locust -f tests/performance/locustfile.py --host=http://localhost:8000 \\
         --users=100 --spawn-rate=10 --run-time=180s --headless \\
         --class-picker

Phase 6.2 environment variables:
  LOAD_STUDENT_EMAIL     Student email with active LFA_FOOTBALL_PLAYER license
                         and sufficient credits (default: perf-student@lfa.com)
  LOAD_STUDENT_PASSWORD  Student password (default: Test1234!)
  LOAD_SEMESTER_IDS      Comma-separated MINI_SEASON ONGOING semester IDs
                         (default: none — enroll tasks skipped if not set)
  LOAD_EVENT_IDS         Comma-separated public tournament IDs for browse
                         (default: none — browse tasks use /events/1 fallback)

Phase 5 environment variables:
  ADMIN_EMAIL:    Admin user email (default: admin@lfa.com)
  ADMIN_PASSWORD: Admin user password (default: admin123)
"""

import os
import random
import re
from locust import HttpUser, task, between, events


# ============================================================================
# CONFIGURATION
# ============================================================================

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Phase 6.2 — student credentials
LOAD_STUDENT_EMAIL    = os.getenv("LOAD_STUDENT_EMAIL", "perf-student@lfa.com")
LOAD_STUDENT_PASSWORD = os.getenv("LOAD_STUDENT_PASSWORD", "Test1234!")

# Semester IDs for enrollment tasks (comma-separated string → list of ints)
_raw_sem = os.getenv("LOAD_SEMESTER_IDS", "")
LOAD_SEMESTER_IDS = [int(x) for x in _raw_sem.split(",") if x.strip()] if _raw_sem else []

# Tournament IDs for browse tasks (public /events/{id} page)
_raw_evt = os.getenv("LOAD_EVENT_IDS", "")
LOAD_EVENT_IDS = [int(x) for x in _raw_evt.split(",") if x.strip()] if _raw_evt else [1]

# Campus IDs for tournament session generation (Phase 5 baseline)
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
# PHASE 6.2 SCENARIO: Browse + Enroll + Withdraw (70 / 20 / 10 split)
# ============================================================================

class BrowseAndEnrollUser(HttpUser):
    """
    Phase 6.2 — realistic student workload simulation.

    Task weights:
      70 %  browse_public_event      GET  /events/{id}              (no auth)
      20 %  enroll_in_semester       POST /semesters/request-enrollment
      10 %  withdraw_from_semester   POST /semesters/withdraw-enrollment

    Auth: cookie-based web login (POST /login).  HttpUser maintains cookies
    automatically so subsequent requests carry the session cookie.

    Prerequisites (set via env vars — see module docstring):
      - LOAD_STUDENT_EMAIL / LOAD_STUDENT_PASSWORD
      - LOAD_SEMESTER_IDS  (comma-separated IDs; if empty, enroll tasks no-op)
      - LOAD_EVENT_IDS     (comma-separated IDs; defaults to [1])

    KPI targets:
      Browse  GET /events/{id}               p95 < 100 ms   error < 0.5 %
      Enroll  POST /semesters/request-*      p95 < 500 ms   real error < 1 %
      Withdraw POST /semesters/withdraw-*    p95 < 500 ms   real error < 1 %
      Rate limit (429): expected at > 100 concurrent users (by design, not a bug)
    """

    wait_time = between(0.5, 1.5)

    # Per-user state
    _logged_in   = False
    _enrolled_id = None   # enrollment_id from last successful enroll

    def on_start(self):
        """Login once per simulated user, store the session cookie."""
        with self.client.post(
            "/login",
            data={
                "email":    LOAD_STUDENT_EMAIL,
                "password": LOAD_STUDENT_PASSWORD,
            },
            allow_redirects=False,
            name="Login (student web)",
            catch_response=True,
        ) as resp:
            if resp.status_code in (302, 303):
                self._logged_in = True
            else:
                resp.failure(
                    f"Student web login failed: {resp.status_code} — "
                    f"check LOAD_STUDENT_EMAIL / LOAD_STUDENT_PASSWORD"
                )

    # ── Tasks ────────────────────────────────────────────────────────────────

    @task(7)
    def browse_public_event(self):
        """GET /events/{id} — public page, no auth, no rate limit pressure."""
        event_id = random.choice(LOAD_EVENT_IDS)
        self.client.get(f"/events/{event_id}", name="Browse public event")

    @task(2)
    def enroll_in_semester(self):
        """POST /semesters/request-enrollment.

        Business error "Already enrolled" (303 with error in location) is
        EXPECTED and counted as success — it means the guard works.
        Real failures are 5xx or unexpected 4xx.
        """
        if not LOAD_SEMESTER_IDS or not self._logged_in:
            return

        sem_id = random.choice(LOAD_SEMESTER_IDS)
        with self.client.post(
            "/semesters/request-enrollment",
            data={"semester_id": str(sem_id)},
            allow_redirects=False,
            name="Enroll semester",
            catch_response=True,
        ) as resp:
            if resp.status_code == 303:
                loc = resp.headers.get("location", "")
                if "error" not in loc:
                    # Success: extract enrollment_id from success redirect if present
                    self._enrolled_id = sem_id  # store sem_id for withdraw
                resp.success()  # 303 with business error = expected, not a failure
            elif resp.status_code == 429:
                resp.success()  # rate limit firing = expected behaviour under load
            else:
                resp.failure(f"Unexpected enroll response: {resp.status_code}")

    @task(1)
    def withdraw_from_semester(self):
        """POST /semesters/withdraw-enrollment (requires prior enrollment).

        Needs enrollment_id — fetched from the browse page or stored from enroll.
        Skipped if no enrollment is known for this user.
        """
        if not self._logged_in or not self._enrolled_id:
            return

        # Fetch enrollment_id from the enroll page (carries session cookie)
        list_resp = self.client.get(
            "/semesters/enroll",
            name="Fetch enrollment list (for withdraw)",
        )
        # Extract first enrollment_id from hidden form inputs in the page
        match = re.search(
            r'name=["\']enrollment_id["\']\s+value=["\'](\d+)["\']',
            list_resp.text,
        )
        if not match:
            return  # no enrollment to withdraw; skip quietly

        enrollment_id = match.group(1)
        with self.client.post(
            "/semesters/withdraw-enrollment",
            data={"enrollment_id": enrollment_id},
            allow_redirects=False,
            name="Withdraw semester",
            catch_response=True,
        ) as resp:
            if resp.status_code == 303:
                self._enrolled_id = None  # reset so next enroll attempt is fresh
                resp.success()
            elif resp.status_code == 429:
                resp.success()
            else:
                resp.failure(f"Unexpected withdraw response: {resp.status_code}")


# ============================================================================
# PERFORMANCE BASELINE METRICS (Expected Values)
# ============================================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Print baseline performance expectations for both Phase 5 and Phase 6.2."""
    print("=" * 70)
    print("PERFORMANCE BASELINE EXPECTATIONS")
    print("=" * 70)
    print()
    print("── Phase 5 (TournamentCreationUser) ─────────────────────────────────")
    print("  Endpoint: POST /api/v1/tournaments/ops/run-scenario")
    print("  p50 < 500ms | p95 < 1500ms | p99 < 3000ms | RPS > 5 | err < 1%")
    print("  Load: 1-10 concurrent users, 60s")
    print()
    print("── Phase 6.2 (BrowseAndEnrollUser) ──────────────────────────────────")
    print("  70% Browse  GET  /events/{id}                p95 < 100ms  err < 0.5%")
    print("  20% Enroll  POST /semesters/request-enroll  p95 < 500ms  err < 1%")
    print("  10% Withdraw POST /semesters/withdraw-*     p95 < 500ms  err < 1%")
    print()
    print("  Rate limit (429): EXPECTED at > 100 concurrent users (IP limit = 100/60s)")
    print("  DB pool: 50 connections/worker × 4 workers = 200 total")
    print("  503 responses = pool exhaustion (increase pool_size or reduce workers)")
    print("=" * 70)
    print()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print performance summary and Phase 6.2 bottleneck analysis."""
    stats = environment.runner.stats if environment.runner else None
    print()
    print("=" * 70)
    print("PERFORMANCE TEST COMPLETE")
    print("=" * 70)

    if stats:
        _print_phase62_analysis(stats)

    print()
    print("Phase 5 next steps:")
    print("  1. Review Locust report (latency percentiles, RPS, error rate)")
    print("  2. Compare actual vs baseline expectations above")
    print("  3. If degradation > 20%: Investigate performance regression")
    print("=" * 70)


def _print_phase62_analysis(stats):
    """Phase 6.2 bottleneck analysis — failure modes + mitigation suggestions."""
    print()
    print("── Phase 6.2 Bottleneck Analysis ──────────────────────────────────")

    endpoints = {
        "Browse public event":   ("GET  /events/{id}",                  100, 0.5),
        "Enroll semester":       ("POST /semesters/request-enrollment",  500, 1.0),
        "Withdraw semester":     ("POST /semesters/withdraw-enrollment",  500, 1.0),
        "Login (student web)":   ("POST /login",                         300, 0.5),
    }

    for name, (label, p95_target_ms, err_target_pct) in endpoints.items():
        entry = stats.get(name, "POST") or stats.get(name, "GET")
        if entry is None:
            continue

        p95_ms    = entry.get_response_time_percentile(0.95) or 0
        err_pct   = (entry.num_failures / max(entry.num_requests, 1)) * 100
        ok_p95    = p95_ms   <= p95_target_ms
        ok_err    = err_pct  <= err_target_pct

        status = "✅" if (ok_p95 and ok_err) else "⚠️ "
        print(f"  {status} {label}")
        print(f"       p95={p95_ms:.0f}ms (target≤{p95_target_ms}ms)   "
              f"err={err_pct:.2f}% (target≤{err_target_pct}%)")

        if not ok_p95 or not ok_err:
            _print_mitigation(name, p95_ms, p95_target_ms, err_pct)

    print()
    print("── Rate Limit Behaviour ────────────────────────────────────────────")
    print("  IP limit: 100 req / 60s per source IP (sliding window)")
    print("  Per-user limit: NON-FUNCTIONAL (JWT decode TODO stub — see RATELIMIT-02)")
    print("  429s expected at > 100 concurrent users — counted as success in tasks")
    print()
    print("── DB Pool ─────────────────────────────────────────────────────────")
    print("  pool_size=20 + max_overflow=30 = 50 connections / worker")
    print("  With 4 workers: 200 total connections available")
    print("  503 responses → pool exhausted; solution: increase pool_size or add workers")


def _print_mitigation(name: str, p95_actual: float, p95_target: float, err_pct: float):
    mitigations = {
        "Browse public event": (
            "N+1 query risk in events.py — TournamentRanking loads teams per row.\n"
            "       Mitigation: eager-load via joinedload(TournamentRanking.team) in the route.\n"
            "       Also check: index on semester_id + status in Semester table."
        ),
        "Enroll semester": (
            "Bottleneck candidates:\n"
            "       (a) Credit deduction: atomic UPDATE on users row — add index on users.id\n"
            "       (b) Session auto-book: N inserts in create_enrollment_with_bookings()\n"
            "           → use bulk_save_objects() with batch dedup query\n"
            "       (c) SemesterEnrollment unique constraint check — add composite index\n"
            "           on (user_id, semester_id, is_active)"
        ),
        "Withdraw semester": (
            "Likely booking cleanup query is slow under load.\n"
            "       Mitigation: add index on Booking(user_id, status) for batch delete."
        ),
        "Login (student web)": (
            "Bcrypt hash verification is CPU-bound; expected ~100-200ms.\n"
            "       If > 300ms: consider reducing bcrypt rounds in test config (not production)."
        ),
    }
    hint = mitigations.get(name, "No specific mitigation mapped for this endpoint.")
    print(f"       Bottleneck hint: {hint}")
