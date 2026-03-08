# Testing Strategy — LFA Practice Booking System

> **Last updated:** Sprint 44 | **Coverage:** stmt 89.0%, branch 81.0%

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

| Metric | CI Threshold | Sprint 41 Actual |
|--------|-------------|-----------------|
| Statement | ≥ 75% | 89.0% |
| Branch (pure) | ≥ 78% | 81.0% |
| Combined | ≥ 75% | ~88% |

**Target range:** 80–82% pure-branch. Contract tests add ~102 tests with minimal branch impact
(Pydantic `model_fields` introspection has no conditional logic). Coverage stays ~81%.

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

## Mutation Testing (Sprint 44)

Mutation testing measures **test effectiveness beyond coverage**: if a test kills a mutant, it
proves the test can detect that specific bug. Kill rate = (killed mutants) / (total mutants).

**Project baseline: ≥70% kill rate per module** (project-wide target, set Sprint 44).
Machine-readable baseline: `tests/snapshots/mutation_baseline.json`.

### Target Modules

| Module | Rationale | Unit Test Files |
|--------|-----------|----------------|
| `app/services/sandbox_verdict_calculator.py` | Pure scoring logic, 97% unit coverage | `test_sandbox_verdict_calculator.py` |
| `app/services/specialization_validation.py` | Pure validation, 98% unit coverage | `test_specialization_validation.py` |
| `app/services/credit_service.py` | Financial operations, high business risk | `test_credit_service.py`, `test_credit_service_unit.py` |

**Selection rationale:** Pure-logic modules (no complex mocking) with high existing coverage
(mutations are reachable and thus catchable). Financial logic prioritized for high business risk.

### Sprint Trend

| Sprint | sandbox | specialization | credit (raw) | credit (eff.) | Combined | Delta |
|--------|---------|----------------|-------------|---------------|----------|-------|
| 42     | 55%     | 81%            | 42%         | —             | 62.9%    | —     |
| 43     | 70.1% ✅ | 81.3% ✅       | 54.5%       | —             | 72.5%    | +9.6pp |
| 44 (projected) | 70.1% ✅ | 81.3% ✅ | ~66.7%   | ~100% ✅     | ~73.5%   | +1.0pp |

> **credit (eff.)** = killed / (total − acceptable survivors). Excludes logger-string mutants
> and ORM-filter mock-bypass mutants that are architecturally untestable. See breakdown below.

### Kill Rates (Sprint 43 Baseline)

Last full run: `.mutmut-cache` from Sprint 43 `--rerun-all`:

| Module | Mutants | Killed | Survived | Kill Rate |
|--------|---------|--------|----------|-----------|
| `sandbox_verdict_calculator.py` | 224 | 157 | 67 | **70.1% ✅** |
| `specialization_validation.py` | 128 | 104 | 24 | **81.3% ✅** |
| `credit_service.py` | 33 | 18 | 15 | **54.5%** (eff. 81.8% ✅) |
| **Combined** | **385** | **279** | **106** | **72.5% ✅** |

Sprint 43 improvements: sandbox +15.1pp (17 targeted insight-dict tests), credit +12.5pp
(new `test_credit_service_unit.py` for IntegrityError dead-code path).

Sprint 44 improvements (4 targeted tests, projected):
- `credit_service.py` lines 63/66/128: mutmut 2.x wraps strings as `"XX...XX"`.
  `pytest.raises(match=...)` uses `re.search()` — the substring still matched.
  Fixed with `str(exc_info.value) == "..."` exact-equality assertions.
- `credit_service.py` line 135 (`@staticmethod`): calling on the *class* works in
  Python 3 even without the decorator (no implicit `self` injection). Fixed by adding
  an instance-level call — Python 3 injects `self`, causing `TypeError` if @staticmethod
  is removed (5 args for 4-param signature).

### Credit Service Survivor Breakdown

15 survivors categorized (Sprint 43 cache):

| Category | Count | Lines | Testable? |
|----------|-------|-------|-----------|
| Validation message strings (XX-wrap) | 4 | 63, 66, 128, 135 | **Yes — fixed Sprint 44** |
| Logger string mutations | 10 | 75, 76, 99–101, 118, 119, 124, 125, 132 | No — see below |
| ORM filter comparison (`==` → `!=`) | 1 | 113 | No — see below |

**Logger strings (10 survivors):** `logger.info/warning/error(f"...")` content changes
(emoji prefixes, f-string text). Not functionally observable:
- Log output changes do not affect return values, raised exceptions, or control flow
- Asserting `mock_logger.info.call_args` creates brittle tests tied to log formatting

**ORM filter mock-bypass (1 survivor, line 113):** `CreditTransaction.idempotency_key == idempotency_key`
mutated to `!=`. The entire `db.query().filter().first()` chain is mocked — the filter
expression is never evaluated. Changing `==` to `!=` has no effect on mock return values.
Would require a real-DB integration test to kill. Accepted as architectural limitation.

**Effective kill rate** = 18 killed / (33 total − 11 acceptable) = **81.8% ✅**

### Running Locally

```bash
# Full run (10–30 min, cached after first run)
bash scripts/run_mutation_tests.sh

# HTML report
bash scripts/run_mutation_tests.sh --html

# View structured report (reads SQLite cache — does NOT use broken `mutmut results` CLI)
python scripts/mutation_report.py
```

### CI Workflow

`.github/workflows/mutation-testing.yml` — **non-blocking**, manual + weekly (Saturday 04:00 UTC).
Failures here do not prevent PRs from merging. After each run, the "Generate mutation report"
step writes a Markdown kill-rate table to the GitHub Actions Step Summary (visible in the
Actions UI without downloading any artifact).

**When to update `mutation_baseline.json`:** After each sprint that changes kill rates, update
`tests/snapshots/mutation_baseline.json` to record the new baseline and append to `history[]`.
The report script reads this file to show sprint-over-sprint deltas in the CI summary.

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
