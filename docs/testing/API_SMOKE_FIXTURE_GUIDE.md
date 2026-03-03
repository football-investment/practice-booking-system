# API Smoke Test — Fixture & Seeding Guide

**Last updated**: 2026-03-03
**Branch**: `feature/api-tests-stabilization`
**CI run**: `22619716615` — 1376 passed, 0 failed

---

## Overview

`tests/integration/api_smoke/` uses module-scoped fixtures with a plain `get_db()` session
(no SAVEPOINT rollback). Data written by fixtures **persists** within the CI test run.
Tests are idempotent: they use "get or create" patterns to avoid duplicate key errors.

---

## Required Seed Data

### 1. Tournament Types (`_seed_tournament_types_once`)

**Why**: The `/api/v1/tournaments/ops/run-scenario` endpoint looks up
`TournamentType` by `code` at runtime and raises HTTP 500 if missing.

**Where**: `tests/integration/api_smoke/conftest.py` — `session`-scoped, `autouse=True`

**What it does**: Loads `app/tournament_types/{league,knockout,group_knockout,swiss}.json`
and inserts them into `tournament_types` if the table is empty.

**Bug history**: `755d84e` — "Tournament type 'knockout' not found in DB" → 500 in CI

```python
@pytest.fixture(scope="session", autouse=True)
def _seed_tournament_types_once():
    # idempotent: only seeds if count == 0
```

---

## Required Model Fields in Fixtures

### `Location` — `country` NOT NULL

```python
# ❌ Fails with IntegrityError
location = Location(name="...", city="Budapest", is_active=True)

# ✅ Correct
location = Location(name="...", city="Budapest", country="Hungary", is_active=True)
```

**Bug history**: `6b7ffe7` — `IntegrityError: null value in column "country"`
at `TestTournamentsSmoke.test_delete_tournament_happy_path` setup.

### `UserLicense` — `started_at` NOT NULL, no default

```python
# ✅ Always set explicitly
license = UserLicense(..., started_at=datetime.now(timezone.utc))
```

### `Semester` — `code` required (UNIQUE), no `is_active` / `specialization_type`

```python
# ✅ Correct
semester = Semester(code="SPRING-2025-X", name="...", start_date=..., end_date=...,
                    status=SemesterStatus.ONGOING)
```

---

## Common NameError / AttributeError Patterns

These were found during api_smoke CI stabilization (commit `0d968dc`):

| Pattern | Wrong | Correct |
|---|---|---|
| Session field | `session.mode` | `session.session_type` |
| Session field | `session.name` | `session.title` |
| Session field | `session.max_participants` | `session.capacity` |
| Enum case | `AttendanceStatus.PRESENT` | `AttendanceStatus.present` |
| Enum case | `role="student"` | `role=UserRole.STUDENT` |
| Enum assignment | `specialization_type=SpecializationType.LFA_COACH` | `specialization_type=SpecializationType.LFA_COACH.value` |
| Raw SQL | `db.execute("SELECT ...")` | `db.execute(text("SELECT ..."))` |

See also: `MEMORY.md` → "Key Model Field Names" and "Enum Values".

---

## Known 500 Errors Fixed

| Test | Root cause | Fix commit |
|---|---|---|
| `test_get_learning_analytics_happy_path` | `KeyError: 'total_attempts'` — missing key in empty analytics dict | `e7b421c` |
| `test_delete_tournament_happy_path` (setup) | `IntegrityError: country NOT NULL` | `6b7ffe7` |
| `test_run_ops_scenario_happy_path` | `TournamentType 'knockout' not found in DB` | `755d84e` |
| `test_get_my_license_happy_path` | `NameError: LFACoachService` — missing import | `0d968dc` |

---

## Fixture Hierarchy

```
tests/integration/conftest.py          ← SAVEPOINT-isolated test_db (function-scoped)
tests/integration/api_smoke/conftest.py ← plain get_db() test_db (module-scoped, OVERRIDES parent)
```

The api_smoke `test_db` overrides the parent's SAVEPOINT fixture intentionally —
api_smoke tests need persistent state within a module (e.g. create user → use token).

---

## CI Step Structure

```yaml
# Step 1: unit + integration/tournament — blocking, floor guard
pytest tests/unit/ tests/integration/tournament/ --cov=app --cov-fail-under=40

# Step 2: api_smoke — blocking (continue-on-error removed 2026-03-03)
pytest tests/integration/api_smoke/ --cov=app --cov-append

# Step 3: combined report — blocking threshold
python -m coverage report --fail-under=43
```

**Coverage baseline**: 51% combined (2026-03-03).
Target progression: 51% → 55% (payload enrichment) → 60% (new API paths).
