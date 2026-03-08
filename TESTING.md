# Testing Strategy — LFA Practice Booking System

> **Last updated:** Sprint 38 | **Coverage:** stmt 87.7%, branch 78.6%

---

## Test Pyramid

```
            ┌─────────────────┐
            │   Cypress E2E   │  cypress/    (7 specs, browser-level)
            │   (UI flows)    │
        ┌───┴─────────────────┴───┐
        │  Blocking E2E Gates (15)│  tests/e2e/integration_critical/
        │  (live server, real DB) │
    ┌───┴─────────────────────────┴───┐
    │  Integration / Smoke Tests      │  tests/integration/
    │  (TestClient, real DB via ORM)  │
┌───┴─────────────────────────────────┴───┐
│         Unit Tests (no DB)              │  tests/unit/
│  Services · Models · Endpoints · Core  │
└─────────────────────────────────────────┘
```

| Tier | Location | DB? | Server? | Runtime |
|------|----------|-----|---------|---------|
| Unit | `tests/unit/` | No | No | <2 min |
| Integration (smoke) | `tests/integration/` | Yes (TestClient) | No | ~5 min |
| E2E Blocking Gates | `tests/e2e/integration_critical/` | Yes | Yes (uvicorn) | ~10 min each |
| Cypress | `cypress/` | Yes | Yes (uvicorn) | ~15 min |

---

## CI Gates (Blocking)

All gates live in `.github/workflows/test-baseline-check.yml`.
Every gate runs after `unit-tests` succeeds. All must be **green** before merge.

| Gate Job | Tests | What It Validates |
|----------|-------|-------------------|
| `unit-tests` | ~6000 unit + tournament | 0 failures, stmt ≥ 87%, branch ≥ 78% |
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
| `booking-lifecycle-gate` | 3 E2E tests | Confirm → waitlist → cancel → auto-promote |
| `auth-lifecycle-gate` | 6 E2E tests | Login → token → refresh → protected endpoint |
| `enrollment-workflow-gate` | 3 E2E tests | Enroll → auto-approve → duplicate rejected |

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

| Metric | CI Threshold | Sprint 38 Actual |
|--------|-------------|-----------------|
| Statement | ≥ 75% | 87.7% |
| Branch (pure) | ≥ 78% | 78.6% |
| Combined | ≥ 75% | ~86% |

Coverage is measured by `python .github/scripts/check_coverage.py` in the `unit-tests` CI job.

**Scope:** `tests/unit/` + `tests/integration/tournament/` + `tests/integration/api_smoke/`
**App scope:** all files under `app/` (via `--cov=app`)

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
| Coverage script | `.github/scripts/check_coverage.py` |
| CI gates workflow | `.github/workflows/test-baseline-check.yml` |
