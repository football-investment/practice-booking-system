# CI Testing Setup — Practice Booking System

> Last updated: 2026-03-05
> Branch: `feature/api-tests-stabilization`
> CI status: 15/15 jobs green, 1501 tests passing (unit+integration+api_smoke)

---

## 1. How Tests Are Integrated Into GitHub Actions

All test types run automatically on every push and pull request via GitHub Actions.
There are **13 workflow files** in `.github/workflows/`. The primary gate is
`test-baseline-check.yml`, which blocks merges if any assertion fails.

### Trigger matrix

| Workflow file | Triggers on push | Triggers on PR |
|---|---|---|
| `test-baseline-check.yml` | `main`, `develop` | `main`, `develop`, `feature/*` |
| `api-smoke-tests.yml` | `main` | `main`, `develop` |
| `e2e-fast-suite.yml` | `main`, `develop` | `main`, `develop` |
| `e2e-wizard-coverage.yml` | `main`, `develop` | `main`, `develop`, `feature/*` |
| `e2e-comprehensive.yml` | scheduled (03:00 UTC) | `main`, `develop` |
| `e2e-live-suite.yml` | `main`, `develop` | `main`, `develop` |
| `e2e-integration-critical.yml` | `main`, `develop` | `main`, `develop` |
| `cypress-e2e.yml` | `main`, `develop` | `main`, `develop` |
| `cypress-tests.yml` | `main`, `develop` | `main`, `develop` |
| `cross-platform-testing.yml` | `workflow_dispatch` only | — |

**Concurrency control**: `test-baseline-check.yml` uses `group: ci-baseline-${{ github.ref }}`
with `cancel-in-progress: true` — only one baseline pipeline runs per branch at a time.

---

## 2. All Test Types and Their CI Jobs

### `test-baseline-check.yml` — Primary Gate (14 jobs)

| Job | What it runs | DB |
|---|---|---|
| `unit-tests` | `tests/unit/` + `tests/integration/tournament/` + `tests/integration/api_smoke/` | Real PostgreSQL 15 |
| `api-tests` | `tests/integration/api/` | Real PostgreSQL 15 |
| `api-module-integrity` | Import check + route count validation | Real PostgreSQL 15 |
| `hardcoded-id-guard` | Lint: no `user_id=1` in unit/service tests | None (grep only) |
| `smoke-tests` | E2E smoke via Playwright + FastAPI server | Real PostgreSQL 15 |
| `payment-workflow-gate` | Payment E2E (BLOCKING) | Real PostgreSQL 15 |
| `core-access-gate` | Core access & state sanity (BLOCKING) | Real PostgreSQL 15 |
| `student-lifecycle-gate` | Student lifecycle E2E (BLOCKING) | Real PostgreSQL 15 |
| `instructor-lifecycle-gate` | Instructor lifecycle E2E (BLOCKING) | Real PostgreSQL 15 |
| `refund-workflow-gate` | Refund workflow E2E (BLOCKING) | Real PostgreSQL 15 |
| `multi-campus-gate` | Multi-campus round-robin E2E (BLOCKING) | Real PostgreSQL 15 |
| `session-management-gate` | Session management E2E (BLOCKING) | Real PostgreSQL 15 |
| `skill-assessment-lifecycle-gate` | Skill assessment E2E (BLOCKING) | Real PostgreSQL 15 |
| `baseline-report` | Summary artifact (runs after all gates) | None |

### Additional standalone workflows

| Workflow | Test type | Notes |
|---|---|---|
| `api-smoke-tests.yml` | API smoke (standalone run) | Separate from baseline |
| `e2e-fast-suite.yml` | Playwright E2E fast (8 tests) | Green ✅ |
| `e2e-wizard-coverage.yml` | Playwright wizard tests (5 jobs) | Green ✅ |
| `e2e-comprehensive.yml` | Cypress E2E (parallel by role) | Nightly + on-push |
| `cypress-e2e.yml` | Cypress E2E | Green ✅ |
| `e2e-live-suite.yml` | Live E2E suite | On push to main/develop |
| `e2e-integration-critical.yml` | Critical integration paths | On push to main/develop |

---

## 3. Database Setup — Real PostgreSQL, Not Mocks

**CI uses a real PostgreSQL 15 database, not mocks or SQLite.**

### CI database configuration

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: lfa_intern_system_test
    ports:
      - 5432:5432

env:
  DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
  SECRET_KEY: test-secret-key-for-ci-only-not-production
```

Migrations run before tests: `alembic upgrade head`

### Local development configuration

```
DATABASE_URL=postgresql://...@localhost:5432/lfa_intern_system
```

Local uses `lfa_intern_system` (no `_test` suffix).
CI uses `lfa_intern_system_test`.

**Both use real PostgreSQL** — there is no SQLite or in-memory database in use for
the main test suite (two legacy files `test_lfa_coach_service.py` and `_simple.py`
use SQLite; these are isolated and do not affect coverage or gate jobs).

### Test isolation mechanism

Unit and integration tests use **SAVEPOINT-based isolation** via the `test_db` fixture:

- `postgres_db` fixture: session-scoped, data persists within a test session
- `test_db` fixture: function-scoped, wraps each test in a SAVEPOINT that is rolled
  back at teardown — no data leaks between tests

The `test_db` fixture reads `settings.DATABASE_URL`, so it automatically connects
to `lfa_intern_system_test` in CI and `lfa_intern_system` locally.

---

## 4. Coverage Thresholds and Enforcement

Coverage is measured across the full test run using `pytest-cov` with branch coverage.

### How coverage is measured in CI (`unit-tests` job, 3 steps)

```
Step 1: pytest tests/unit/ tests/integration/tournament/
        --cov=app --cov-branch --cov-fail-under=44

Step 2: pytest tests/integration/api_smoke/
        --cov=app --cov-branch --cov-append   (appends to step 1)

Step 3: coverage xml -o coverage.xml
        coverage report --fail-under=57       (combined threshold)
        python .github/scripts/check_coverage.py  (stmt >= 63%)
```

### Coverage thresholds

| Threshold | Value | Enforced by |
|---|---|---|
| Unit+tournament only (step 1) | ≥ 44% | `--cov-fail-under=44` |
| Combined (unit+tournament+api_smoke) | ≥ 57% | `coverage report --fail-under=57` |
| Statement coverage (stmt) | ≥ 63% | `check_coverage.py` (STMT_THRESHOLD=63.0) |

Current measured coverage (2026-03-05): **63.4% stmt** (21348/31355 lines)

### Coverage artifact

`coverage.xml` is uploaded as a CI artifact (`coverage-report-combined`) with
30-day retention. Download from the GitHub Actions run summary page.

---

## 5. Local vs CI Parity — Same Logic, Same DB Engine

The local test suite and the CI pipeline run **identical test logic** using the
same pytest configuration and the same PostgreSQL engine.

### What is identical

| Aspect | Local | CI |
|---|---|---|
| Test framework | pytest 3.12 | pytest 3.12 |
| Database engine | PostgreSQL (real) | PostgreSQL 15 (Docker service) |
| ORM | SQLAlchemy (same `app/database.py`) | Same |
| Migrations | `alembic upgrade head` | `alembic upgrade head` |
| Coverage tool | `pytest-cov` | `pytest-cov` |
| Fixtures | Same conftest.py | Same conftest.py |
| Test isolation | SAVEPOINT (`test_db`) | SAVEPOINT (`test_db`) |

### What differs

| Aspect | Local | CI |
|---|---|---|
| DB name | `lfa_intern_system` | `lfa_intern_system_test` |
| `DATABASE_URL` | From `.env` / shell | `postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test` |
| `SECRET_KEY` | From `.env` | `test-secret-key-for-ci-only-not-production` |
| Parallelism | Single-process | Single-process (no `-n auto` yet) |

### Running locally with CI-equivalent settings

```bash
# Match CI environment exactly (requires local postgres running with lfa_intern_system_test DB)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test \
SECRET_KEY=test-secret-key-for-ci-only-not-production \
pytest tests/unit/ tests/integration/tournament/ -q --cov=app --cov-branch --cov-fail-under=44

# Then append api_smoke
DATABASE_URL=... pytest tests/integration/api_smoke/ -q --cov=app --cov-branch --cov-append

# Then check thresholds
coverage report --fail-under=57
python .github/scripts/check_coverage.py
```

---

## 6. Monitoring CI Outputs

### Where to check

- **GitHub Actions tab**: Repository → Actions → "Test Baseline Check"
- **Coverage artifact**: Download `coverage-report-combined` (coverage.xml) from any run
- **Baseline report**: The `baseline-report` job generates a summary after all gates

### What to watch for

| Signal | Meaning | Action |
|---|---|---|
| Any job red | Test failure or threshold violation | Fix before merging |
| Coverage drops below 57% combined | New code not tested | Add tests for new module |
| Coverage drops below 63% stmt | Regression in coverage | Identify which module lost coverage |
| `hardcoded-id-guard` fails | `user_id=1` found in unit tests | Change to `user_id=42` |
| `api-module-integrity` fails | Route count changed unexpectedly | Verify intended endpoint change |

### Monitoring cadence recommendation

- **On every PR**: review CI status before requesting review
- **On every merge to main**: confirm all 14 jobs green before closing PR
- **Weekly**: download coverage artifact and check for modules below 60% stmt
- **After adding a new service/endpoint**: verify coverage did not drop

---

## 7. Hardcoded FK ID Guard

CI enforces that unit tests do not use `user_id=1` as a hardcoded value (FK
collision risk with auto-inserted seed data).

**Pattern checked** (`.github/workflows/test-baseline-check.yml`, `hardcoded-id-guard` job):
- `user_id=1[^0-9]` in `tests/unit/services/` and `tests/unit/tournament/`
- `user_license_id=1[^0-9]` in `tests/unit/` (excluding concurrency files)

**Rule**: Always use `user_id=42` (or any value ≥ 100) in new unit/service tests.

---

## Appendix: Key File Paths

| File | Purpose |
|---|---|
| `.github/workflows/test-baseline-check.yml` | Primary CI gate (14 jobs) |
| `.github/scripts/check_coverage.py` | Enforces STMT_THRESHOLD=63.0% |
| `pytest.ini` | pytest configuration (markers, addopts) |
| `conftest.py` | Shared fixtures: `test_db`, `postgres_db`, `postgres_admin_user` |
| `tests/unit/` | Unit tests (mock-based, no real DB for most) |
| `tests/integration/tournament/` | Tournament integration tests (real DB, test_db fixture) |
| `tests/integration/api_smoke/` | API smoke tests (real DB, real HTTP calls) |
| `tests/integration/api/` | API integration tests |
| `app/database.py` | SQLAlchemy engine — reads `settings.DATABASE_URL` |
| `alembic.ini` + `alembic/` | Migration configuration |
