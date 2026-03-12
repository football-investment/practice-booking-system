# Testing Strategy — LFA Practice Booking System

> **Last updated:** v1.0.1 (2026-03-12) | **Coverage:** stmt 88.7%, branch 83.5% | **Tests:** 8870 passed, 1 xfailed

---

## Test Pyramid

```
            ┌─────────────────┐
            │   Cypress E2E   │  cypress/    (7 specs, browser-level)
            │   (UI flows)    │
        ┌───┴─────────────────┴───┐
        │  Blocking E2E Gates (17)│  tests/e2e/integration_critical/
        │  (live server, real DB) │
    ┌───┴─────────────────────────┴───┐
    │  Integration / Smoke Tests      │  tests/integration/
    │  (TestClient, real DB via ORM)  │
┌───┴─────────────────────────────────┴───┐
│         Unit Tests (no DB)              │  tests/unit/
│  Services · Models · Endpoints · Core  │
│  ┌─────────────────────────────────┐   │
│  │  Contract Tests (schema only)   │   │  tests/unit/contract/
│  │  Field names · Types · Defaults │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

| Tier | Location | DB? | Server? | Runtime |
|------|----------|-----|---------|---------|
| Unit | `tests/unit/` | No | No | <2 min |
| Contract (schema) | `tests/unit/contract/` | No | No | <5 s |
| Integration (smoke) | `tests/integration/` | Yes (TestClient) | No | ~5 min |
| E2E Blocking Gates | `tests/e2e/integration_critical/` | Yes | Yes (uvicorn) | ~10 min each |
| Cypress | `cypress/` | Yes | Yes (uvicorn) | ~15 min |

**Contract tests** (`tests/unit/contract/`) validate Pydantic response schema field names, types, and
defaults — no DB or server needed. Any field rename or removal in `app/schemas/` causes an immediate
failure in the `unit-tests` CI step (< 2 min feedback). Smoke tests only assert status codes;
contract tests fill the schema-integrity gap.

---

## CI Gates (Blocking)

All gates live in `.github/workflows/test-baseline-check.yml`.
Every gate runs after `unit-tests` succeeds. All must be **green** before merge.

| Gate Job | Tests | What It Validates |
|----------|-------|-------------------|
| `unit-tests` | ~6440 unit + contract + openapi-snapshot + tournament | 0 failures, stmt ≥ 87%, branch ≥ 78%, `--durations=20` for slow-test profiling |
| `smoke-tests` | ~1654 API smoke | All API endpoints return expected status codes |
| `api-module-integrity` | Import check | All `app/` modules load cleanly, route count ≥ 71 |
| `hardcoded-id-guard` | Lint | No `user_id=1` in unit/service tests |
| `payment-workflow-gate` | 3 E2E tests | Credit purchase → balance → deduct flow |
| `core-access-gate` | 2 E2E tests | Health endpoint + admin login |
| `student-lifecycle-gate` | 2 E2E tests | Student registration → enrollment lifecycle |
| `instructor-lifecycle-gate` | 1 E2E test | Instructor assignment flow |
| `refund-workflow-gate` | 1 E2E test | Booking cancel → credit refund |
| `multi-campus-gate` | 1 E2E test | Session creation across campuses |
| `session-management-gate` | 4 E2E tests | Session CRUD + availability |
| `skill-assessment-lifecycle-gate` | 9 E2E tests | Football skill assessment end-to-end |
| `booking-lifecycle-gate` | 3 E2E tests | Confirm → waitlist → cancel → auto-promote (3× flake detection) |
| `auth-lifecycle-gate` | 6 E2E tests | Login → token → refresh → protected endpoint (3× flake detection) |
| `enrollment-workflow-gate` | 3 E2E tests | Enroll → auto-approve → duplicate rejected (3× flake detection) |
| `user-account-gate` | 3 E2E tests | Password change → old creds fail → new creds work (3× flake detection) |
| `instructor-assignment-lifecycle-gate` | 4 E2E tests | Admin assigns instructor → accept/decline, auth guards (3× flake detection) |

---

## CI Gate Categories (Sprint 42)

Gates organized by functional domain — use this when diagnosing CI failures.

| Category | Gate Jobs |
|----------|-----------|
| Platform Quality (4) | `unit-tests`, `smoke-tests`, `api-module-integrity`, `hardcoded-id-guard` |
| Auth & Access (2) | `core-access-gate`, `auth-lifecycle-gate` |
| Student Journey (2) | `student-lifecycle-gate`, `user-account-gate` |
| Booking & Sessions (3) | `booking-lifecycle-gate`, `session-management-gate`, `multi-campus-gate` |
| Financial (2) | `payment-workflow-gate`, `refund-workflow-gate` |
| Enrollment (1) | `enrollment-workflow-gate` |
| Instructor (2) | `instructor-lifecycle-gate`, `instructor-assignment-lifecycle-gate` |
| Skills & Assessment (1) | `skill-assessment-lifecycle-gate` |

---

## Business Flow Map (Sprint 42)

All critical user journeys mapped to CI gates. Gaps documented with rationale.

| Flow | Journey | CI Gate | Status |
|------|---------|---------|--------|
| Authentication | Login → token → refresh → protected endpoint | `auth-lifecycle-gate` | ✅ Gated |
| Core Access | Health check + admin login | `core-access-gate` | ✅ Gated |
| Student Onboarding | Register → profile → semester enrollment | `student-lifecycle-gate` | ✅ Gated |
| User Account | Password change → old creds fail → new creds work | `user-account-gate` | ✅ Gated |
| Booking | Book → waitlist → cancel → auto-promote | `booking-lifecycle-gate` | ✅ Gated |
| Session Management | Create session → availability → check-in | `session-management-gate` | ✅ Gated |
| Multi-Campus Ops | Session distribution across campuses | `multi-campus-gate` | ✅ Gated |
| Payment | Purchase credits → balance → deduct | `payment-workflow-gate` | ✅ Gated |
| Refund | Cancel booking → credit refund | `refund-workflow-gate` | ✅ Gated |
| Enrollment | Enroll → auto-approve → duplicate rejected | `enrollment-workflow-gate` | ✅ Gated |
| Skill Assessment | Assessment → submission → grading | `skill-assessment-lifecycle-gate` | ✅ Gated |
| Instructor (App-based) | Application → position accept | `instructor-lifecycle-gate` | ✅ Gated |
| Instructor (Admin-directed) | Admin assign → instructor accept/decline | `instructor-assignment-lifecycle-gate` | ✅ Gated |
| License Lifecycle | Level advancement → certification | — | ⚠️ Unit+smoke (≥95%) |
| Curriculum/Learning | Track enroll → module complete → progress | — | ⚠️ Unit+smoke (≥95%) |
| Quiz Assessment | Take quiz → score → update progress | — | ⚠️ Unit+smoke (≥90%) |
| Gamification | XP gain → level → badge | — | ⚠️ Unit only (≥95%) |

### Ungated Flow Gate Decisions (Sprint 42)

Explicit per-flow analysis confirming no E2E gate is needed:

| Flow | Evidence | Gate Decision | Rationale |
|------|----------|--------------|-----------|
| License Lifecycle | 10+ test files, `test_license_service.py` 49+ tests, ≥95% unit coverage | **No E2E gate** | Financial risk already gated via `payment-workflow-gate`. Level advancement is deterministic pure logic with no cross-service state machine. |
| Curriculum/Learning | 8 test files, `test_curriculum_exercises/modules/lessons` suites, ≥95% unit coverage | **No E2E gate** | Track enroll → module complete is a stateless, linear flow. All curriculum state transitions are exhaustively tested at unit level. |
| Quiz Assessment | 4 files, `test_quiz_service.py` ~1027 lines (most comprehensive unit test in the suite), ≥90% unit coverage | **No E2E gate** | Every quiz state transition is exercised at unit level. No concurrent state machine or auth-token dependency that would require live-server validation. |
| Gamification | 3 files, 48+ tests in `test_gamification_xp_service.py`, ≥95% unit coverage | **No E2E gate** | XP gain is a side effect of booking/attendance (both already gated). Not a user-facing journey; adding a gate would create artificial coupling to booking infrastructure. |

**Conclusion:** All four flows remain ungated. They lack the complex multi-service state machines
(auth tokens, DB transactions, concurrent state changes) that justify E2E gating. The unit+smoke
layer provides ≥90% coverage per flow with faster feedback than an E2E gate would offer.

---

## Running Locally

### Prerequisites
```bash
# Start local DB (if not running)
brew services start postgresql@14

# Apply migrations
alembic upgrade head

# Seed test data
python scripts/seed_tournament_types.py
python scripts/seed_lfa_test_users.py
```

### Unit tests (no DB, no server)
```bash
pytest tests/unit/ -q --tb=short
```

### Integration / smoke tests (DB, no server)
```bash
pytest tests/integration/ -q --tb=short
```

### Coverage check
```bash
# Full coverage run (matches CI scope)
pytest tests/unit/ tests/integration/tournament/ \
  --cov=app --cov-branch --cov-report=term-missing -q --tb=no 2>/dev/null | tail -5
python .github/scripts/check_coverage.py

# With smoke tests appended (full CI scope)
pytest tests/unit/ tests/integration/ \
  --cov=app --cov-branch -q --tb=no --maxfail=9999 2>/dev/null | tail -3
```

### E2E blocking gates (requires live server)
```bash
# Start server
uvicorn app.main:app --port 8000 &

# Run individual gate
PYTHONPATH=. pytest tests/e2e/integration_critical/test_auth_lifecycle.py -v
PYTHONPATH=. pytest tests/e2e/integration_critical/test_enrollment_workflow.py -v
PYTHONPATH=. pytest tests/e2e/integration_critical/test_booking_lifecycle.py -v
PYTHONPATH=. pytest tests/e2e/integration_critical/test_user_account.py -v

# Flake detection dry-run (3× repetition, same as CI)
PYTHONPATH=. pytest tests/e2e/integration_critical/test_user_account.py --count=3 -v
```

### Flake detection (non-blocking)

The `.github/workflows/flake-detection.yml` workflow runs all integration-critical E2E tests
**5 times sequentially** (`--count=5`) to surface intermittent failures before they become outages.

- **Trigger:** manual (`workflow_dispatch`) or weekly (Saturday 03:00 UTC)
- **Not blocking:** failures here do not prevent PRs from merging
- **When to run manually:** after adding new E2E tests, after infrastructure changes, or when a CI flake is suspected

```bash
# Local flake detection simulation (all suites, 3×)
PYTHONPATH=. pytest tests/e2e/integration_critical/ --count=3 -v --durations=10
```

### Cypress (browser E2E)
```bash
cd cypress && npx cypress run
```

---

## Adding New Tests

### Step 1 — Pick the right tier

| You want to test... | Use |
|--------------------|-----|
| A service method, model property, or utility function | Unit test in `tests/unit/` |
| A Pydantic response schema field name, type, or default | Contract test in `tests/unit/contract/` |
| An API endpoint's response code and payload shape | Smoke test in `tests/integration/api_smoke/` |
| A multi-step business flow (login → enroll → pay) | E2E blocking gate in `tests/e2e/integration_critical/` |
| A UI interaction or browser behavior | Cypress in `cypress/` |

### Step 2 — Use the factory layer

All domain payload generation is centralised in `tests/factories/`:

```python
from tests.factories import create_student_payload, login_payload
from tests.factories.session_factory import create_session_payload
from tests.factories.booking_factory import create_booking_payload
from tests.factories.enrollment_factory import enroll_in_tournament_payload
from tests.integration.api_smoke.tournament_payloads import create_tournament_payload
```

For unit tests, use `MagicMock` directly — no factory needed.

### Step 3 — Assert narrow, not broad

```python
# ✅ Good — asserts the business contract
assert resp.status_code in [200, 201]
assert data["request_status"] == "APPROVED"

# ❌ Avoid — too broad, masks regressions
assert resp.status_code < 500
```

---

## Coverage Targets

| Metric | CI Threshold | Sprint 54 Actual |
|--------|-------------|-----------------|
| Statement | ≥ 88% | 88.7% ✅ |
| Branch (pure) | ≥ 80% | 83.5% ✅ |
| Combined | ≥ 85% | 88%+ ✅ |

**web_routes layer:** ~85% combined (was 71% pre-Sprint 54). All 4 previously zero-coverage web_route files now have unit tests:
- `auth.py`, `profile.py`, `specialization.py`, `onboarding.py` — all covered ≥ Sprint 54
- Missing imports in these files are patched via `patch(..., create=True)` — see Sprint 54 Patterns section.

Unreachable branches: `dashboard.py` lines 185-186 (only 3 UserRoles; student early-returns), `admin.py` lines 92-233 (`admin_enrollments_page` excluded — db.refresh on lazy-loaded relationships).

## Test Performance Baseline (Sprint 40 `--durations=20`)

Unit suite profiled locally after Sprint 39 changes:
- **Total:** 6307 tests in ~23s — all sub-300ms per test
- **Slowest:** 0.26s (`test_skill_progression_service.py`)
- **Conclusion:** No optimization needed. The `--durations=20` CI flag (added Sprint 39) will surface any future regressions.

Coverage is measured by `python .github/scripts/check_coverage.py` in the `unit-tests` CI job.

**Scope:** `tests/unit/` + `tests/integration/tournament/` + `tests/integration/api_smoke/`
**App scope:** all files under `app/` (via `--cov=app`)

---

## OpenAPI Schema Snapshot (Sprint 42)

The full API contract is versioned as a committed JSON file (`tests/snapshots/openapi_snapshot.json`).
Any endpoint or schema change is visible in the PR diff and triggers an immediate test failure.

**How it works:** `FastAPI.openapi()` generates the schema from registered routes without connecting
to a database or starting a server. The test runs in the `unit-tests` CI step (< 2 min feedback).

**496 routes, 382 components** versioned as of Sprint 42.

```bash
# Update snapshot after intentional API changes
python scripts/update_openapi_snapshot.py

# Run snapshot test
pytest tests/unit/contract/test_openapi_snapshot.py -v
```

What the test catches:
- Renamed or removed endpoints
- Changed request/response schemas or field names
- Added/removed path parameters or query params
- Modified operation metadata (tags, summary, operationId)

---

## Mutation Testing (Sprint 46)

Mutation testing measures **test effectiveness beyond coverage**: if a test kills a mutant, it
proves the test can detect that specific bug. Kill rate = (killed mutants) / (total mutants).

**Project baseline: ≥70% kill rate per module, 70.7% combined** (regression threshold: −2pp).
**Long-term milestone: ≥80% combined kill rate** (current gap: ~9.3pp).
Machine-readable baseline: `tests/snapshots/mutation_baseline.json`.

### Target Modules (7 modules)

| Module | Domain | Rationale | Coverage | Test File(s) |
|--------|--------|-----------|----------|-------------|
| `sandbox_verdict_calculator.py` | Scoring | Pure scoring logic | 97% | `test_sandbox_verdict_calculator.py` |
| `specialization_validation.py` | Enrollment | Pure validation | 98% | `test_specialization_validation.py` |
| `credit_service.py` | Payment | Financial operations, high business risk | 96% | `test_credit_service.py`, `test_credit_service_unit.py` |
| `license_authorization_service.py` | Access control | License level threshold guards | 100% | `test_license_authorization_service.py` |
| `gamification/xp_service.py` | Gamification | XP arithmetic | 100% | `test_gamification_xp_service.py` |
| `enrollment_conflict_service.py` | **Booking/Enrollment** | Time-overlap/travel conflict detection | 93% | `test_enrollment_conflict_service.py` |
| `license_renewal_service.py` | **Payment** | License renewal credits, expiry logic | 97% | `test_license_renewal_service.py` |

**Selection rationale:** Pure-logic modules with high existing coverage (mutations are reachable
and catchable). Financial/access-control/booking modules prioritized for business risk.
Sprint 46 expands into the booking and payment domains as requested.

### Sprint Trend

| Sprint | Modules | Total Mutants | Killed | Combined | Delta |
|--------|---------|---------------|--------|----------|-------|
| 42     | 3       | 385           | 242    | 62.9%    | —     |
| 43     | 3       | 385           | 279    | 72.5%    | +9.6pp |
| 45     | 5       | 718           | 542    | 75.5%    | +3.0pp |
| 46     | **7**   | **1116**      | **789**| **70.7% ✅** | −4.8pp (scope expansion) |

> **Note:** The combined drop Sprint 45→46 reflects adding 2 new modules (398 mutants) that start
> below 70%. This is normal when expanding scope; the existing 5 modules are unchanged.
> Long-term goal: ≥80% combined (milestone).

Per-module Sprint 46 breakdown:

| Module | Mutants | Killed | Survived | Kill Rate | Sprint 45 | Delta |
|--------|---------|--------|----------|-----------|-----------|-------|
| `sandbox_verdict_calculator.py` | 224 | 157 | 67 | **70.1% ✅** | 70.1% | stable |
| `specialization_validation.py` | 128 | 104 | 24 | **81.3% ✅** | 81.3% | stable |
| `credit_service.py` | 33 | 22 | 11 | 66.7% raw / **100% eff. ✅** | 100% eff. | stable |
| `license_authorization_service.py` | 191 | 152 | 39 | **79.6% ✅** | 79.6% | stable |
| `gamification/xp_service.py` | 142 | 108 | 34 | **76.1% ✅** | 75.4% | +0.7pp |
| `enrollment_conflict_service.py` | 247 | 140 | 107 | 56.7% ❌ | — (new) | — |
| `license_renewal_service.py` | 151 | 106 | 45 | **70.2% ✅** | — (new) | — |

### Kill Rate Dashboard

```
  Combined kill rate — target ≥70%  |  milestone ≥80%

  Sprint 42  █████████████░░░░░░░  62.9%
  Sprint 43  ██████████████░░░░░░  72.5%
  Sprint 45  ███████████████░░░░░  75.5%
  Sprint 46  ██████████████░░░░░░  70.7%  ← 2 new modules

  Target    ██████████████░░░░░░  70%   (per-module minimum)
  Milestone ████████████████░░░░  80%   (long-term goal, ~9.3pp gap)
```

Generated automatically in CI Step Summary by `python scripts/mutation_report.py`.

### enrollment_conflict_service — Initial Baseline (56.7%)

This module's 107 surviving mutants break down into two groups:

1. **Pure static method mutants (~12 survivors, Sprint 46 targeted tests killed ~11)**:
   String-list items (`LFA_PLAYER_YOUTH` etc.), comparison operators (`<` → `<=`), `@staticmethod`
   removals, `or` → `and` in location guard, `0 <= min_gap < BUFFER` bounds.
   Sprint 46 added 9 targeted tests to kill these.

2. **DB-heavy method mutants (~95 survivors)** in `check_enrollment_conflicts()`:
   Complex dict-building code (conflict_type/severity string literals, `.isoformat()` null-guards)
   in the conflict result dictionary. Not architecturally untestable — require full mock setup
   asserting on the complete conflict dict structure. **Sprint 47 goal**: add 5–10 integration-style
   unit tests asserting on conflict dict fields to push past 70%.

### Credit Service Survivor Breakdown

| Category | Count | Lines | Testable? |
|----------|-------|-------|-----------|
| Validation message strings (XX-wrap) | 4 | 63, 66, 128, 135 | **Yes — fixed Sprint 44** |
| Logger string mutations | 10 | 75, 76, 99–101, 118, 119, 124, 125, 132 | No (see below) |
| ORM filter comparison (`==` → `!=`) | 1 | 113 | No (see below) |

**Logger strings (10 survivors):** `logger.info/warning/error(f"...")` content mutations.
Not functionally observable — log content changes don't affect return values or control flow.

**ORM filter mock-bypass (1 survivor, line 113):** Mock chain ignores filter expression.
Would require real-DB integration test to kill. Accepted as architectural limitation.

**Effective kill rate** = 22 killed / (33 total − 11 acceptable) = **100% ✅**

### Regression Gate

The "Check for regressions" CI step (non-blocking) compares each run against the last sprint
baseline in `mutation_baseline.json`:

- **Combined regression**: current combined rate drops **≥2pp** below baseline → step turns red
- **Per-module regression**: effective kill rate drops **≥3pp** below module baseline → step turns red
- **Action required**: investigate surviving mutants with `mutmut show <id>` and add targeted tests

A red regression step does **not** block PRs — it is a signal to prioritize before the next sprint.

```bash
# Run regression check locally
python scripts/mutation_report.py --check-regression
```

### Running Locally

```bash
# Incremental run (only untested mutants — fast when expanding scope)
python -m mutmut run

# Full re-run (all mutants; use after major test changes)
python -m mutmut run --rerun-all

# Structured report (reads SQLite cache — does NOT use broken `mutmut results` CLI)
python scripts/mutation_report.py

# Regression check
python scripts/mutation_report.py --check-regression
```

### CI Workflow

`.github/workflows/mutation-testing.yml` — **non-blocking**, manual + weekly (Saturday 04:00 UTC).
Failures here do not prevent PRs from merging.

| Step | What it does |
|------|-------------|
| Verify test suite passes | Runs all 8 mutation-target test files as a sanity check |
| Run mutation tests | `python -m mutmut run` (incremental — skips already-tested mutants) |
| Generate mutation report | Reads `.mutmut-cache` SQLite → Markdown table + ASCII dashboard in Step Summary |
| Check for regressions | `--check-regression` flag → red step if ≥2pp combined drop or ≥3pp per-module |

**When to update `mutation_baseline.json`:** After each sprint that changes kill rates, update
`tests/snapshots/mutation_baseline.json` to record the new baseline and append to `history[]`.
The report script reads this file to show sprint-over-sprint deltas and the milestone gap in CI.

---

## Web Routes Unit Testing

### Why `asyncio.run()` instead of TestClient

Web route tests call async endpoint functions **directly** via `asyncio.run(endpoint(...))`.
This bypasses FastAPI's dependency injection and the ASGI stack entirely, giving precise
control over every DB query and making tests fast (no HTTP overhead).

Trade-off: you must supply all injected parameters (`request`, `db`, `user`) manually.
Use `MagicMock()` for `request`; build `db` chains yourself; use a user factory helper.

### DB Mock Chain Reference

| Query pattern in source | How to mock |
|------------------------|-------------|
| `db.query(M).filter().first()` | `db.query.return_value.filter.return_value.first.return_value = obj` |
| `db.query(M).filter().all()` | `db.query.return_value.filter.return_value.all.return_value = [...]` |
| `db.query(M).filter().order_by().all()` | `db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [...]` |
| `db.query(M).options(...).order_by().all()` | `db.query.return_value.options.return_value.order_by.return_value.all.return_value = [...]` |
| `db.query(M).options(...).filter().order_by().all()` | `db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [...]` |
| `db.query(M).count()` | `db.query.return_value.count.return_value = N` |
| `db.query(M).filter().count()` | `db.query.return_value.filter.return_value.count.return_value = N` |
| Sequential `.first()` calls | `db.query.return_value.filter.return_value.first.side_effect = [obj1, obj2, ...]` |

### Known Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TypeError: '>=' not supported between MagicMock and date` | `semester.end_date` left as MagicMock | Set `semester.end_date = date(2027, 12, 31)` |
| `TypeError: multiple values for keyword argument 'user'` | `fb.user = MagicMock()` puts `user` in `__dict__` | Access via `fb.user.name = "X"` (not assignment) |
| `AuditAction.UPDATE` AttributeError | `AuditAction` is a plain class, no `UPDATE` constant | Use `AuditAction.FOOTBALL_SKILLS_UPDATED` (fixed in admin.py) |
| `StopIteration` in async tests | `side_effect` list exhausted (too few entries) | Add entries for ALL subsequent filter().first() calls |

### Per-file Coverage Targets (web_routes layer)

| File | stmt% | branch% | Notes |
|------|-------|---------|-------|
| admin.py | ≥75% | ≥60% | Lines 92-233 (`admin_enrollments_page`) excluded — db.refresh on lazy-loaded relationships |
| dashboard.py | ≥95% | ≥70% | Lines 185-186 unreachable (only 3 roles; student early-returns) |
| instructor.py | ≥98% | ≥90% | Lines 526/532/539->556 are nested loop exits, hard to trigger without real DB |
| attendance.py | ≥95% | ≥85% | Lines 54->56 etc. are multi-condition branch exits |
| sessions.py | ≥95% | ≥85% | |
| quiz.py | ≥85% | ≥75% | |

---

## Web Flows Integration Testing (`tests/integration/web_flows/`)

End-to-end validation of the web_routes → service → DB chain using real PostgreSQL
with per-test SAVEPOINT isolation. Each test POSTs to an actual FastAPI route and
validates both the HTTP response AND the resulting DB state.

### Infrastructure

| Component | Solution |
|-----------|----------|
| DB isolation | SAVEPOINT per test (same pattern as `tests/integration/conftest.py`) |
| Auth injection | `app.dependency_overrides[get_current_user_web] = lambda: user` |
| CSRF bypass | `TestClient(app, headers={"Authorization": "Bearer test-csrf-bypass"})` — `CSRFProtectionMiddleware` skips validation for Bearer auth requests |
| Redirect assertions | `follow_redirects=False` → check `resp.status_code == 303` + `resp.headers["location"]` |
| DB state validation | `test_db.expire_all()` then re-query after the request |

### Fixture Layer (`conftest.py`)

```
test_db         ← SAVEPOINT-isolated session (local override)
  ↓ used by:
  semester        ← minimal Semester (code unique, status=ONGOING)
  future_session  ← on-site, date_start=NOW+24h (bookable, cancellable)
  active_session  ← on-site, date_start=NOW-5min, date_end=NOW+1h (attendance window)
  hybrid_session  ← hybrid, actual_start_time set (quiz unlockable)
  future_booking  ← student CONFIRMED booking on future_session
  active_booking  ← student CONFIRMED booking on active_session

student_client    ← TestClient + get_current_user_web → student_user + Bearer bypass
instructor_client ← TestClient + get_current_user_web → instructor_user + Bearer bypass
```

### Test Files and Flows

| File | Tests | Routes / service exercised | Key DB assertions |
|------|-------|--------------------------|-------------------|
| `test_booking_cancellation.py` | 6 | POST `/sessions/book/{id}`, `/sessions/cancel/{id}` | `Booking` row created / deleted |
| `test_attendance_lifecycle.py` | 7 | POST `/sessions/{id}/attendance/mark`, `/attendance/confirm` | `Attendance.status`, `ConfirmationStatus` transitions |
| `test_hybrid_session_flow.py` | 4 | POST `/sessions/{id}/unlock-quiz` | `session.quiz_unlocked` True/False |
| `test_virtual_quiz_flow.py` | 4 | POST `/quizzes/{id}/submit` | `QuizAttempt.completed_at` set, `passed`, `score` |
| `test_concurrency.py` | 5 | Same as above (double-call sequences) | Row count invariants, `completed_at` unchanged |
| `test_xp_grant.py` | 6 | `award_attendance_xp()`, `award_xp()` (service-direct) | `Attendance.xp_earned`, `UserStats.total_xp`, `User.xp_balance` |

### Timing Constraints

```python
# Booking/cancellation window (12h deadline):
date_start = _now_bp() + timedelta(hours=24)   # future_session — bookable & cancellable
date_start = _now_bp() + timedelta(hours=6)    # near_future_session — within 12h deadline (blocked)

# Attendance marking window (15min before → session end):
date_start = _now_bp() - timedelta(minutes=5)  # active_session
date_end   = _now_bp() + timedelta(hours=1)

# Quiz unlock: requires session_type=HYBRID + actual_start_time is not None
# unstarted_hybrid_session: actual_start_time=None → unlock blocked
```

### Running

```bash
pytest tests/integration/web_flows/ -v           # 26 tests, ~4s
pytest tests/integration/web_flows/ -v --tb=short  # with failure detail
```

---

## Failure Modes — Tested Edge Cases

Each entry documents the guard that fires, whether it is enforced at DB level or application level, and the expected outcome for both the HTTP response and DB state.

### Booking / Cancellation

| Scenario | Guard layer | HTTP response | DB state after |
|----------|------------|---------------|----------------|
| Book when already booked | Application: `already_booked` check before INSERT | 303 `?info=already_booked` | exactly 1 `Booking` row |
| Cancel when no booking exists | Application: booking lookup → None | 303 `?error=booking_not_found` | no row (unchanged) |
| Book within 12h of start | Application: `date_start - NOW < 12h` | 303 `?error=booking_deadline_passed` | no row created |
| Cancel within 12h of start | Application: deadline check before DELETE | 303 `?error=cancellation_deadline_passed` | `Booking` row preserved |
| Double cancel (row already gone) | Application: second lookup → None | 303 `?error=booking_not_found` | stays deleted |

**DB constraint behind booking idempotency**:
```sql
CREATE UNIQUE INDEX uq_active_booking ON bookings (user_id, session_id)
  WHERE status <> 'CANCELLED';
```
This partial unique index catches true concurrent double-bookings at DB level (would raise `IntegrityError`), providing defence-in-depth beyond the application guard.

### Attendance

| Scenario | Guard layer | HTTP response | DB state after |
|----------|------------|---------------|----------------|
| Mark attendance for unbooked student | Application: booking lookup → None | 303 `?error=student_not_enrolled` | no `Attendance` row |
| Student tries to confirm (not STUDENT role) | Application: role check | 303 `?error=unauthorized` | unchanged |
| Confirm when no attendance record exists | Application: attendance lookup → None | 303 `?error=no_attendance` | no row |
| Double mark same student (upsert) | Application: UPDATE existing row | 303 `?success=attendance_marked` | still 1 row |
| Mark present then absent | Application: UPDATE existing row | 303 `?success=attendance_marked` | 1 row, `status=absent` |

**DB constraint behind attendance uniqueness**:
```sql
ALTER TABLE attendance ADD CONSTRAINT uq_booking_attendance UNIQUE (booking_id);
```
Prevents two `Attendance` records referencing the same `Booking`. **Gap**: when `booking_id=NULL` (tournament sessions), no DB-level constraint prevents duplicate `(user_id, session_id)` rows — the application upsert is the only guard.

### Quiz Submission

| Scenario | Guard layer | HTTP response | DB state after |
|----------|------------|---------------|----------------|
| Submit nonexistent attempt_id | Application: attempt lookup → None → 404 | 404 | unchanged |
| Submit already-completed attempt | Application: `completed_at is not None` | 400 | `completed_at` from 1st submit preserved |
| Submit with session_id but no booking | Application: booking check after session_id provided | 403 | `completed_at` remains None |
| Double submit (2nd after 1st committed) | Application: `completed_at is not None` guard | 400 | `completed_at` unchanged |

**DB constraint behind quiz idempotency**: none — `QuizAttempt` allows multiple attempts per `(user_id, quiz_id)` by design. The `completed_at IS NOT NULL` guard is **application-level only**. A concurrent double-submit race (both see `completed_at=None` before either commits) could theoretically mark the attempt completed twice; mitigated in production by client-side disable-on-submit and connection pooling serialization.

### Hybrid Session Quiz Unlock

| Scenario | Guard layer | HTTP response | DB state after |
|----------|------------|---------------|----------------|
| Non-instructor tries to unlock | Application: `user.id != session.instructor_id` | 303 `?error=unauthorized` | `quiz_unlocked` unchanged |
| Unlock on non-HYBRID session | Application: `session_type != HYBRID` | 303 `?error=unlock_only_hybrid` | unchanged |
| Unlock on unstarted session | Application: `actual_start_time is None` | 303 `?error=session_not_started_unlock` | unchanged |

---

## SELECT FOR UPDATE — Path Coverage Analysis (quiz submit)

`submit_quiz` in [app/api/web_routes/quiz.py](app/api/web_routes/quiz.py) acquires a row-level lock on the `QuizAttempt` row **before** checking `completed_at`. This ensures concurrent submits are serialised at DB level.

### Call-site (line 279)

```python
attempt = db.query(QuizAttempt).filter(
    QuizAttempt.id == attempt_id,
    QuizAttempt.user_id == user.id,
    QuizAttempt.quiz_id == quiz_id
).with_for_update().first()          # ← row-level lock acquired here
```

### Path trace

```
POST /quizzes/{quiz_id}/submit
│
├─ fetch quiz → 404 if not found (lock NOT acquired — no attempt involved)
│
├─ if session_id provided:
│   ├─ fetch SessionQuiz → 404 (lock NOT acquired)
│   ├─ fetch Session → 404 (lock NOT acquired)
│   ├─ check session.date_start < now → 403 (lock NOT acquired)
│   └─ fetch Booking → 403 if missing (lock NOT acquired)
│
├─ attempt = .filter(...).with_for_update().first()   ← LOCK ACQUIRED
│   ├─ attempt is None  → 404  (lock released on exception rollback) ✅
│   ├─ completed_at set → 400  (lock released on exception rollback) ✅
│   └─ else: calculate score, db.commit(), lock released               ✅
│
└─ render quiz_result.html
```

**Conclusion**: The lock is acquired on the **single path** that accesses the attempt row. Every branch that touches `completed_at` (404-not-found, 400-already-done, 200-success) does so under the lock. No path reads the attempt row without `WITH FOR UPDATE`. ✅

### Race condition neutralised

| Without `SELECT FOR UPDATE` | With `SELECT FOR UPDATE` |
|-----------------------------|--------------------------|
| T1 reads `completed_at=None` | T1 acquires lock, reads `completed_at=None` |
| T2 reads `completed_at=None` | T2 **blocks** waiting for T1 |
| Both set `completed_at`, both return 200 | T1 sets `completed_at`, commits, releases lock |
| Last write wins — XP double-awarded | T2 acquires lock, reads `completed_at≠None` → 400 |

### Unit test pattern (`_make_db`)

Because `with_for_update()` breaks the default MagicMock chain, all `TestSubmitQuiz` tests that reach the attempt query use the `_make_db` static helper:

```python
@staticmethod
def _make_db(*side_effects):
    db = MagicMock()
    fm = db.query.return_value.filter.return_value
    fm.with_for_update.return_value = fm   # loop: with_for_update() → same mock
    fm.first.side_effect = list(side_effects)
    return db
```

### Migration rollback test

`tests/integration/test_migration_rollback.py` (7 tests) verifies the attendance partial unique index (`uq_attendance_user_session_no_booking`) can be:
- Applied: index present, correct `UNIQUE … WHERE booking_id IS NULL` definition
- Rolled back: `downgrade -1` drops only the new index, PK and FK constraints intact
- Re-applied: `upgrade head` restores the index and revision
- Idempotent: double `upgrade head` is a no-op

Run explicitly (modifies real DB schema, auto-restored by fixture):
```bash
pytest tests/integration/test_migration_rollback.py -v
```

---

## CI Pipeline Benchmark (2026-03-09, local, M-series Mac)

Full pipeline: **unit → integration → E2E**, measured separately. E2E requires a running backend — run offline means Cypress is skipped in the table below.

| Layer | Scope | Tests | Time | Notes |
|-------|-------|-------|------|-------|
| Unit | `tests/unit/` | ~8 100 + 1 xfail | **~25s** | asyncio.run + MagicMock, no network |
| Integration: tournament | `tests/integration/tournament/` | 25 | **~3s** | real PostgreSQL SAVEPOINT |
| Integration: web_flows | `tests/integration/web_flows/` | 32 | **~5s** | real PostgreSQL SAVEPOINT + TestClient (+6 xp_grant) |
| Integration: api_smoke | `tests/integration/api_smoke/` | ~1 737 | **~70s** | live endpoint contract |
| **Combined (CI full)** | unit + integration | **8 932 + 1 xfail** | **~60s** | CI gate: stmt ≥88%, branch ≥80% |
| E2E Cypress (web) | `cypress/e2e/web/` (15 spec files) | **140** | **~6min** | FastAPI Jinja2 HTML frontend; requires live backend |
| E2E Playwright | `tests/e2e/` | — | — | golden_path smoke tests |

### Permanent xfailed test (do not remove)

```
tests/unit/booking/test_booking_concurrency_p0.py::
  TestRaceB02CapacityOverbooking::test_b02_race_window_produces_overbooking_documents_the_unsafe_state
```

**Why it is xfail, not skipped:**
This test documents the architectural limitation that `SELECT FOR UPDATE` on MagicMock is a no-op — the mock cannot simulate DB-level row locking. Both concurrent mock calls still see `confirmed_count=0` from separate mock DBs. The companion test `test_b02_session_locked_with_for_update_before_confirmed_count` proves the lock is present in production code. Real-DB concurrency proof belongs in a future `tests/database/` suite.

**Regression signal:** If this test starts **passing** (xpass), it means either:
1. The lock guard was accidentally removed from the production route, OR
2. MagicMock behaviour changed in a new pytest-mock version
Both cases require investigation. The xfail reason string captures the full explanation.

**Slowest individual tests** (unit layer):

| Test | Time |
|------|------|
| `test_api_contract_unchanged` (OpenAPI snapshot) | 0.95s |
| `test_spec_none_returns_false` (lfa_coach_service) | 0.27s |
| `test_200_1st_place_default_policy` (rewards_endpoint) | 0.27s |
| `test_concurrent_thread_dispatch_unique_task_ids` (ops_scenario) | 0.26s |

All web_flows integration tests run in ≤ 0.18s each; slowest is TestClient startup overhead (~0.6s/fixture group).

**Run the combined benchmark locally**:
```bash
# Step 1 — unit + integration (matches CI scope)
pytest tests/unit/ tests/integration/tournament/ tests/integration/web_flows/ -q --tb=no

# Step 2 — coverage check (matches CI gate)
python -m pytest tests/unit/ tests/integration/tournament/ -q --cov=app --cov-branch --cov-report=term --tb=no 2>/dev/null | tail -5
python .github/scripts/check_coverage.py

# Step 3 — E2E (requires live backend)
# ./start_backend.sh &
# npx cypress run --spec "cypress/e2e/**/*.cy.js"
```

---

## Mock Patterns (Quick Reference)

Key patterns confirmed working — full details in `.claude/projects/*/memory/MEMORY.md`:

| Pattern | When to use |
|---------|-------------|
| `asyncio.run(endpoint_fn(...))` | Async FastAPI endpoints in unit tests |
| `MagicMock(spec=Booking)` + set attributes | Model hybrid property tests |
| `patch("app.module.ClassName")` | Service/endpoint injection |
| `db.query.side_effect = lambda model: q_map[model]` | Multi-model DB routing |
| `patch("app.core.init_admin.SessionLocal")` | DB at source (not relative import) |
| `SimpleNamespace(field=val)` | DB row substitutes (hasattr works correctly) |

---

## Sprint 54 — New Test Patterns

### 1. `patch(..., create=True)` — injecting missing names into modules

Some production modules have imports that may be absent at test collection time (e.g. lazy imports, conditional imports). Use `create=True` to inject the name into the module namespace without modifying production code:

```python
# auth.py imports UserRole, date, traceback at runtime but not at module level
with patch("app.api.web_routes.auth.UserRole", UserRole, create=True), \
     patch("app.api.web_routes.auth.date", date, create=True), \
     patch("app.api.web_routes.auth.traceback", traceback, create=True):
    result = asyncio.run(age_verification_submit(...))
```

**Affected modules:**

| Module | Missing names (require `create=True`) |
|--------|---------------------------------------|
| `app/api/web_routes/auth.py` | `UserRole`, `date`, `traceback` |
| `app/api/web_routes/profile.py` | `UserLicense`, `SemesterEnrollment`, `Semester`, `validate_specialization_for_age`, `traceback` |
| `app/api/web_routes/onboarding.py` | `SpecializationType`, `CreditTransaction`, `TransactionType`, `get_available_specializations` |

### 2. FastAPI `Query()` default gotcha

```python
# WRONG — page=Query(1, ge=1) is a FieldInfo object, NOT 1
list_sessions(db=db, current_user=user)  # → TypeError

# CORRECT — always pass explicit values when calling endpoints directly
list_sessions(db=db, current_user=user, page=1, size=50)
```

**Rule:** Any endpoint parameter declared as `page: int = Query(1, ge=1)` will receive the `FieldInfo` object as its default when called directly (not via HTTP). Always supply explicit values in unit tests.

### 3. MagicMock `__dict__` corruption

```python
# WRONG — replaces MagicMock's internal __dict__, causing AttributeError: _mock_methods
b = MagicMock()
b.__dict__ = {"id": 1, "status": BookingStatus.CONFIRMED, ...}

# CORRECT — set attributes individually or use keyword assignment
b = MagicMock()
b.id = 1
b.status = BookingStatus.CONFIRMED
```

### 4. Read-only enum `.value`

```python
# WRONG — UserRole.INSTRUCTOR.value is a read-only enum attribute
user.role = UserRole.INSTRUCTOR
user.role.value = "instructor"  # AttributeError: can't set attribute

# CORRECT — use a plain MagicMock when you need to set .value
role_mock = MagicMock()
role_mock.value = "instructor"
user.role = role_mock
```

### 5. 4-service pipeline mock (`sessions/queries.py`)

The `list_sessions` endpoint delegates to four services. Patch all at module level:

```python
_BASE = "app.api.api_v1.endpoints.sessions.queries"

def _service_patches(q):
    rfs_cls = MagicMock()
    rfs_cls.return_value.apply_role_semester_filter.return_value = q

    sfs_cls = MagicMock()
    sfs_cls.return_value.apply_specialization_filter.return_value = q
    sfs_cls.return_value.get_relevant_sessions_for_user.return_value = []
    sfs_cls.return_value.get_session_recommendations_summary.return_value = {}

    sa_cls = MagicMock()
    sa_cls.return_value.fetch_stats.return_value = {}

    rb_cls = MagicMock()
    rb_cls.return_value.build_response.return_value = MagicMock()

    return (
        patch(f"{_BASE}.RoleSemesterFilterService", rfs_cls),
        patch(f"{_BASE}.SessionFilterService", sfs_cls),
        patch(f"{_BASE}.SessionStatsAggregator", sa_cls),
        patch(f"{_BASE}.SessionResponseBuilder", rb_cls),
        rfs_cls, sfs_cls, sa_cls, rb_cls,
    )

# Usage:
p_rfs, p_sfs, p_sa, p_rb, rfs_cls, sfs_cls, sa_cls, rb_cls = _service_patches(q)
with p_rfs, p_sfs, p_sa, p_rb:
    result = list_sessions(db=db, current_user=user, page=1, size=50)
```

### 6. `with_for_update()` mock (admin booking cancel / attendance)

Routes that use `.with_for_update().first()` require a looped mock:

```python
def _wfu_mock_db(booking):
    """Mock DB for routes that call .filter(...).with_for_update().first()."""
    q = MagicMock()
    for m in ("filter", "join", "options", "order_by", "offset", "limit",
              "filter_by", "distinct"):
        getattr(q, m).return_value = q
    q.count.return_value = 0
    q.all.return_value = []
    q.scalar.return_value = 0

    fm = MagicMock()
    fm.with_for_update.return_value = fm   # loop: with_for_update() returns same mock
    fm.first.return_value = booking
    q.filter.return_value = fm             # override filter to return the wfu-aware mock

    db = MagicMock()
    db.query.return_value = q
    return db
```

### 7. XP service integration pattern

`award_attendance_xp` is **idempotent** (guard: `attendance.xp_earned > 0`). Call it twice on the same attendance record — second call returns the same amount without incrementing `UserStats.total_xp`:

```python
xp1 = award_attendance_xp(test_db, att.id)   # → 50 (base XP), sets att.xp_earned=50
xp2 = award_attendance_xp(test_db, att.id)   # → 50 (early return, no DB update)
assert xp1 == xp2  # same value
# UserStats.total_xp incremented only once
```

`award_xp` is **accumulative** (no idempotency guard) — each call adds the specified amount.

### 8. SAVEPOINT-isolated service test

For integration tests that test service functions directly (not via HTTP):

```python
def test_awards_base_xp(test_db, student_user, instructor_user):
    # 1. Create real DB objects
    sem = _make_semester(test_db)
    session = _make_session(test_db, sem.id, instructor_user.id)
    att = _make_attendance(test_db, student_user.id, session.id)

    # 2. Call service function (uses real DB)
    xp = award_attendance_xp(test_db, att.id)

    # 3. Expire session cache before re-querying
    test_db.expire_all()
    updated = test_db.query(Attendance).filter(Attendance.id == att.id).first()
    assert updated.xp_earned == 50
    # All changes rolled back by SAVEPOINT teardown
```

---

## Key Files

| Purpose | Location |
|---------|----------|
| Payload factories (all domains) | `tests/factories/` |
| Tournament payloads | `tests/integration/api_smoke/tournament_payloads.py` |
| E2E fixture helpers (create/delete user) | `tests/e2e/integration_critical/conftest.py` |
| Contract (schema) tests | `tests/unit/contract/` |
| OpenAPI snapshot | `tests/snapshots/openapi_snapshot.json` |
| OpenAPI snapshot test | `tests/unit/contract/test_openapi_snapshot.py` |
| OpenAPI snapshot updater | `scripts/update_openapi_snapshot.py` |
| Coverage script | `.github/scripts/check_coverage.py` |
| CI gates workflow | `.github/workflows/test-baseline-check.yml` |
| Mutation testing config | `setup.cfg` (`[mutmut]` section) |
| Mutation testing runner | `scripts/run_mutation_tests.sh` |
| Mutation testing report | `scripts/mutation_report.py` (reads SQLite cache, writes CI summary) |
| Mutation testing baseline | `tests/snapshots/mutation_baseline.json` (sprint history + targets) |
| Mutation testing CI (non-blocking) | `.github/workflows/mutation-testing.yml` |

---

## Test Architecture & Coverage Policy

### Architecture Overview

```
tests/
├── unit/                    # Fast, no DB — asyncio.run() or sync direct calls
│   ├── api/web_routes/      # FastAPI endpoint tests (asyncio.run pattern)
│   ├── services/            # Business logic (MagicMock DB)
│   ├── models/              # SQLAlchemy model unit tests
│   ├── booking/             # Booking/concurrency regression tests
│   ├── contract/            # Pydantic schema + OpenAPI snapshot tests
│   └── ...
├── integration/
│   ├── tournament/          # Tournament workflow integration (in-memory SQLite or real DB)
│   └── api_smoke/           # 579-endpoint smoke suite (requires running server + DB)
└── e2e/                     # Playwright Python E2E (requires full stack)
```

### Layer-by-layer Quality Gates

| Layer | Gate type | Threshold | Enforcement |
|-------|-----------|-----------|-------------|
| Unit + integration/tournament | stmt | ≥ 88% | `check_coverage.py` |
| Unit + integration/tournament | branch (pure) | ≥ 80% | `check_coverage.py` |
| Unit + integration/tournament | combined | ≥ 85% | `--fail-under=85` in workflow |
| Unit step alone | combined | ≥ 60% | `--cov-fail-under=60` in workflow |
| Mutation (service layer) | kill rate | ≥ 78% (regression) | `mutation-testing.yml` (non-blocking) |
| Contract | OpenAPI snapshot | exact match | `test_openapi_snapshot.py` |

### Coverage Exclusion Policy

Use `# pragma: no cover` / `# pragma: no branch` sparingly and only for:
1. **Structurally unreachable code** — e.g., enum-exhaustive if/elif/else where the else can never fire
2. **Platform/environment guards** — e.g., `if sys.platform == "win32":` in a Linux-only CI
3. **Debug/logging-only paths** — `if __name__ == "__main__":` blocks

Current exclusions in production code:
- `dashboard.py` line 183 `else:` — unreachable: only 3 UserRoles, STUDENT returns early
- `dashboard.py` line 116 `if ... or ...:` — `# pragma: no branch` — False branch unreachable for same reason
- `admin.py` lines 92–233 (`admin_enrollments_page`) — excluded from coverage target (not pragma), too complex for unit mocking (db.refresh on lazy-loaded relationships); tested at integration level

### Adding New Web Route Tests — Checklist

1. `asyncio.run(endpoint(request=MagicMock(), db=<configured_mock>, user=<role_mock>))`
2. Configure the **exact mock chain** your route uses (see "DB Mock Chain Reference" above)
3. Patch `app.api.web_routes.<module>.templates` to capture TemplateResponse calls
4. For sequential DB calls, use `side_effect=[result1, result2, ...]`
5. Verify: `template_name = mock_tmpl.TemplateResponse.call_args.args[0]`
6. For error paths: `pytest.raises(HTTPException)` + `assert exc.value.status_code == N`
7. If the module has missing imports, add `patch("...name", real_value, create=True)` — see Sprint 54 Patterns
8. Never set `mock.__dict__ = {...}` — set attributes individually (`mock.field = value`)
9. For `Query(N, ge=M)` parameters, always pass them explicitly — never rely on defaults
10. For `.value` on enum instances, use `role_mock = MagicMock(); role_mock.value = "role_str"`
11. If the route calls `.with_for_update().first()`, use the `_wfu_mock_db` helper pattern

---

## Sprint 56 — New Test Patterns

### 1. Cypress DOM queries for stable user-ID extraction

Admin CRUD tests need to find a non-admin user's ID from the `/admin/users` page.
The template emits `data-testid`, `data-role`, and `data-user-id` on every `<tr>`:

```html
<tr data-testid="user-row" data-role="{{ u.role.value }}" data-user-id="{{ u.id }}">
```

**Anti-pattern (fragile):**
```javascript
// Breaks when HTML serialisation order changes or CSS classes are renamed
const match = resp.body.match(/data-testid="user-row"[^>]*data-role="student"[^>]*data-user-id="(\d+)"/);
```

**Correct pattern (DOM-driven):**
```javascript
cy.visit('/admin/users');
cy.get('[data-testid="user-row"][data-role="student"]')
  .should('exist')                         // fails loudly if no student rows rendered
  .first()
  .should('have.attr', 'data-user-id')     // asserts attribute present AND yields its value
  .then((userId) => {
    cy.request({ method: 'POST', url: `/admin/users/${userId}/edit`, ... });
  });
```

**Key insight:** chai-jquery's `.should('have.attr', name)` with a single argument:
1. Asserts the attribute exists (fails with 15 s timeout if missing)
2. **Changes the Cypress subject to the attribute's string value**

Do NOT chain `.invoke('attr', name)` after `.should('have.attr', name)` — `invoke` would
try to call `.attr()` on a string, which has no such method, and fail with:
`cy.invoke() errored because the property: attr does not exist on your subject`.

### 2. beforeEach DB reset for mutation specs

Any Cypress spec that **mutates** the DB (edit user, toggle status, create semester) must
reset in `beforeEach`, not `before`:

```javascript
beforeEach(() => {
  cy.resetDb('baseline');
  cy.clearAllCookies();
});
```

**Why:** Cypress re-runs `beforeEach` before each retry attempt. If a test changes the
admin user's email and fails, the next retry starts with a fresh DB — so login still works.
Using `before()` runs only once per spec file; retries inherit the corrupted state.

### 3. Time-stable age assertions

Tests that compute a person's age must not hardcode year-specific bounds:

```python
# WRONG — breaks silently every year
assert age >= 24 and age <= 25

# CORRECT — dynamically computed from today
def _expected_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

assert service.calculate_age(dob) == _expected_age(dob)
```

### 4. OpenAPI snapshot must be regenerated after every new route

```bash
python scripts/update_openapi_snapshot.py
git add tests/snapshots/openapi_snapshot.json
```

`test_openapi_snapshot.py::test_api_contract_unchanged` enforces this in CI — any new
route that is not in the snapshot causes a hard failure.

---

## Sprint 56 — API & Frontend Consistency Audit (2026-03-10)

### Summary

| Metric | Value |
|--------|-------|
| Web routes audited | 58 (across 11 route files) |
| Templates on disk | 45 |
| Routes → existing template | 38/38 ✅ (no broken refs) |
| Unused templates | 7 (legacy/v2 duplicates) |
| Duplicate route groups | 1 (quiz routes in quiz.py + instructor.py) |
| Cypress specs | 15 |
| Cypress tests | 140 (all passing) |
| Pytest (unit + integration) | 8 932 passed, 1 xfailed |

### Unused templates (safe to remove in a future cleanup sprint)

| Template | Reason |
|----------|--------|
| `credits_old.html` | Superseded by `credits.html` |
| `instructor/student_belt_status.html` | No route references it |
| `instructor/student_skills_v2.html` | Superseded by `student_skills.html` |
| `admin/dashboard.html` | Admin dashboard uses role-specific templates |
| `admin/payment_management.html` | Duplicate of `admin/payments.html` |
| `admin/coupon_management.html` | Duplicate of `admin/coupons.html` (route uses one of them) |
| `dashboard_student_new.html` / `dashboard_student_switcher.html` | Legacy student dashboard variants |

### Duplicate quiz routes

`GET /quizzes/{quiz_id}/take`, `POST /quizzes/{quiz_id}/submit`, and
`POST /sessions/{session_id}/unlock-quiz` are defined in **both** `quiz.py` and
`instructor.py`. FastAPI registers both; the last one registered wins. Cleanup is a
Sprint 57 housekeeping task.

### Cypress coverage gaps (by priority)

The 15 specs cover **all critical user paths**. Known gaps (lower-priority, future sprints):

| Gap | Sprint target |
|-----|---------------|
| `GET /calendar` page render | Sprint 57 |
| `POST /admin/semesters/{id}/delete` hard-delete path | Sprint 57 |
| `GET /admin/students/{id}/motivation/{spec}` admin assessment | Sprint 58 |
| `POST /sessions/{id}/evaluate-student` + `evaluate-instructor` | Sprint 58 |
| Notifications inbox (Sprint 57 feature) | Sprint 57 |
| Tournament viewer (Sprint 57 feature) | Sprint 57 |

---

## Sprint 57 — New Test Patterns (2026-03-10)

### 1. Timer simulation with `cy.clock()` + `cy.tick()`

For quiz timer auto-submit tests, use Sinon's fake timer API:

```javascript
cy.clock();                          // MUST be called BEFORE cy.visit()
cy.visit(`/quizzes/${quizId}/take`);
cy.window().then((win) => {
  cy.stub(win, 'alert').as('timerAlert');   // prevent window.alert from blocking
});
// Derive tick duration dynamically from the rendered timer display
cy.get('#timer').invoke('text').then((text) => {
  const m = text.match(/Time: (\d+):(\d{2})/);
  const displayedSeconds = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
  cy.tick((displayedSeconds + 1) * 1000);  // fires all setInterval callbacks synchronously
});
cy.get('@timerAlert').should('have.been.calledWith', '⏰ Time is up! Submitting quiz...');
```

**Key rules:**
- `cy.clock()` before `cy.visit()` — otherwise `setInterval` is already running on the real timer
- `quizForm.submit()` (programmatic, used by timer callback) bypasses HTML5 `required` validation
- Button `.click()` does NOT bypass required validation — for zero-answer tests use `cy.request()`
- Parse timer text `"⏱️ Time: M:SS"` → `M*60+SS` remaining seconds = server-provided value

### 2. Label-based stat targeting for quiz results

Quiz result pages render stats as `.stat-label` / `.stat-value` sibling pairs. Target by label text to survive reordering:

```javascript
// Fragile — breaks if stat order changes:
cy.get('.stat-value').eq(0).should('have.text', '50.0%');

// Correct — label-anchored:
cy.contains('.stat-label', 'Score').parent().find('.stat-value').should('have.text', '50.0%');
cy.contains('.stat-label', 'Correct Answers').parent().find('.stat-value').should('have.text', '1 / 2');
```

### 3. DB persistence verification via `cy.task()`

After form submission, verify the backend actually persisted the result using a Cypress task that runs a Python subprocess:

```javascript
// cypress.config.js tasks:
getQuizAttemptData(attemptId) {
  const { execSync } = require('child_process');
  const script = [
    'import sys, json; sys.path.insert(0, ".")',
    'from app.database import SessionLocal',
    'from app.models.quiz import QuizAttempt',
    'db = SessionLocal()',
    `a = db.query(QuizAttempt).filter(QuizAttempt.id == ${parseInt(attemptId, 10)}).first()`,
    'db.close()',
    'print(json.dumps({"score": a.score, "correct_answers": a.correct_answers, "passed": a.passed}) if a else "null")',
  ].join('; ');
  const out = execSync(`python -c '${script}'`, { cwd, encoding: 'utf8' }).trim();
  return out === 'null' ? null : JSON.parse(out);
},
```

Usage in spec:
```javascript
cy.get('[name="attempt_id"]').invoke('val').then((rawAttemptId) => {
  const attemptId = parseInt(rawAttemptId, 10);
  // ... submit form ...
  cy.task('getQuizAttemptData', attemptId).then((row) => {
    expect(row.score).to.equal(50);
    expect(row.passed).to.be.true;
  });
});
```

### 4. Radio option ordering in quiz E2E fixture

The "E2E UI Quiz" fixture has deterministic ordering: options sorted by `order_index` ASC.
`.eq(0)` = correct answer (order_index=1), `.eq(1)` = wrong answer (order_index=2):

```javascript
// Select correct answer for question N (first radio = correct):
cy.get('.question').eq(0).find('input[type="radio"]').eq(0).check();  // correct
// Select wrong answer:
cy.get('.question').eq(0).find('input[type="radio"]').eq(1).check();  // wrong
```

### 5. FK truncation order: QuizUserAnswer before QuizAttempt

In `reset_e2e_web_db.py`, `quiz_user_answers` has a FK to `quiz_attempts`. Always delete user answers first:

```python
def _truncate_transactional_data(db):
    db.query(QuizUserAnswer).delete(synchronize_session=False)   # FK child first
    db.query(QuizAttempt).delete(synchronize_session=False)      # then parent
```

Forgetting this causes `ForeignKeyViolation` after the first quiz submission creates `QuizUserAnswer` rows.

---

## Sprint 58 — Audit Fixes & Coverage Gaps Closed (2026-03-10)

### Summary

| Metric | Value |
|--------|-------|
| Web routes audited | 57 HTML routes |
| Routes with Cypress E2E coverage before Sprint 58 | 47/57 (82.5%) |
| New spec file | `student/student_features.cy.js` (FEAT-01–06) |
| Coverage after Sprint 58 | 57/57 (100%) |
| Cypress specs | 17 |
| Cypress tests | 162 (all passing) |
| Pytest (unit + integration) | 6 980 passed, 1 xfailed |
| Production bug fixed | `student_features.py` missing `date` import (NameError on `/about-specializations`) |

### Production bug: missing `date` import in `student_features.py`

`GET /about-specializations` computes `user_age` using `date.today()`, but `date` was not
imported — only `datetime, timezone`. Any user with a `date_of_birth` set would see a 500.

**Fix:**
```python
# Before (broken):
from datetime import datetime, timezone

# After (fixed):
from datetime import date, datetime, timezone
```

This was caught by the Sprint 58 audit — the Cypress test FEAT-01 would have failed with a 500.

### New spec: `student/student_features.cy.js`

Covers 6 previously untested routes:

| Test | Route | Scenario |
|------|-------|----------|
| FEAT-01 | `GET /about-specializations` | Smoke: 200, no 500 |
| FEAT-02 | `GET /credits` | Smoke: 200, no 500, contains "credit" |
| FEAT-03 | `GET /dashboard-fresh` | Smoke: 200, cache-bypass route works |
| FEAT-04 | `GET /dashboard/{spec_type}` (no license) | Not 500 (403 or redirect) |
| FEAT-05 | `POST /sessions/{id}/attendance/change-request` (no request) | Error redirect, not 500 |
| FEAT-06 | `POST /sessions/{id}/evaluate-instructor` (no session) | Error redirect, not 500 |

### New tests in existing specs

| Test | Spec | Route covered |
|------|------|---------------|
| ADM-09 | `admin/user_management.cy.js` | `GET /admin/coupons` |
| ADM-10 | `admin/user_management.cy.js` | `GET /admin/invitation-codes` |
| XR-15 | `cross_role/full_student_lifecycle.cy.js` | `POST /sessions/{id}/evaluate-instructor` (happy path: session stopped, PRESENT) |

---

## v1.0.1 — P1 Technical Debt (2026-03-12)

### Sprint baseline

| Metric | Value |
|--------|-------|
| Tests passing | 8870 passed, 1 xfailed |
| Routes | 538 |
| Tag | `v1.0.1-core-stable` |

### Patterns introduced

**`asyncio.to_thread()` mock pattern** — `HealthChecker.get_worker_health()` runs blocking
Celery `inspect().ping()` via `asyncio.to_thread()`. Tests patch the entire method as `AsyncMock`:

```python
from unittest.mock import AsyncMock, patch

_WORKER_PATCH = "app.core.health.HealthChecker.get_worker_health"
_WORKER_RESULT = {"status": "healthy", "redis": "healthy", "workers": [], "error": None}

with patch(_WORKER_PATCH, new=AsyncMock(return_value=_WORKER_RESULT)):
    result = await HealthChecker.get_comprehensive_health()
```

**Alembic PostgreSQL enum recreation** — PG cannot drop enum values; recreate pattern:

```sql
CREATE TYPE myenum_new AS ENUM ('A', 'B');
ALTER TABLE t ALTER COLUMN c TYPE myenum_new USING c::text::myenum_new;
DROP TYPE myenum;
ALTER TYPE myenum_new RENAME TO myenum;
```

**Migration revision guard in tests** — `_current_revision() == REV_X` assertions in
`test_migration_rollback.py` are fragile: they break when newer migrations are added.
Only assert `_current_revision() == REV_X` when explicitly downgrading to that target;
never assert it equals a specific value after `upgrade head` (head moves forward).

**Semester.is_active cleanup pattern** — when removing a boolean alias column:
1. Grep for `ModelName(` within ±15 lines of each `is_active=` site to distinguish models
2. Fix app/ code first (generators, endpoints, web routes), then test fixtures
3. The migration rollback test checks for the presence of DB-level constraints, not revision IDs
