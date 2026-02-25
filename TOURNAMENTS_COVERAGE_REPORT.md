# Tournaments Domain - Valódi Coverage és Success Rate Jelentés

**Dátum:** 2026-02-24
**Cél:** ≥95% valódi működési validáció CI-ben
**Jelenlegi állapot:** 📊 Mérési baseline elkészült

---

## Executive Summary

A Tournaments domain (72 endpoint) valódi működési validációját mértük. A Phase 1 enhancement után **a false green állapot megszűnt**, és most látjuk a valódi problémákat.

### Kritikus Eredmények

| Metrika | Érték | Cél | Gap |
|---------|-------|-----|-----|
| **Kód Lefedettség** | **24%** | 95% | -71% |
| **200/201 Success Rate** | **~0%** | 95% | -95% |
| **Auth Test Success** | **58%** (42/72) | 100% | -42% |
| **Total Non-Skipped Tests** | 132 | 144 | -12 |

**Következtetés:** A Tournaments domain **FAR FROM ≥95% target**. Minőségi mélység építés most kezdődik.

---

## Részletes Code Coverage (--cov=app/api/api_v1/endpoints/tournaments)

### Összesített Coverage

```
TOTAL: 3849 statements, 2928 missed → 24% coverage
```

### Fájl-szintű Breakdown (kritikus fájlok)

| Fájl | Statements | Missed | Coverage | Prioritás |
|------|------------|--------|----------|-----------|
| **detail.py** | 29 | 4 | **86%** ✅ | LOW (majdnem kész) |
| **campus_schedule.py** | 74 | 35 | **53%** | MEDIUM |
| **schedule_config.py** | 57 | 29 | **49%** | MEDIUM |
| **cancellation.py** | 86 | 50 | **42%** | HIGH |
| **generator.py** | 266 | 158 | **41%** | HIGH |
| **results/round_management.py** | 32 | 19 | **41%** | MEDIUM |
| **create.py** | 121 | 75 | **38%** | HIGH |
| **admin_enroll.py** | 86 | 53 | **38%** | HIGH |
| **lifecycle.py** | 175 | 111 | **37%** | HIGH |
| **lifecycle_instructor.py** | 79 | 50 | **37%** | HIGH |
| **checkin.py** | 35 | 23 | **34%** | MEDIUM |
| **results/submission.py** | 136 | 94 | **31%** | HIGH |
| **rewards_v2.py** | 86 | 62 | **28%** | HIGH |
| **generate_sessions.py** | 230 | 171 | **26%** | HIGH |
| **available.py** | 65 | 50 | **23%** | MEDIUM |
| **reward_config.py** | 97 | 75 | **23%** | MEDIUM |
| **instructor_assignment.py** | 192 | 152 | **21%** | HIGH |
| **lifecycle_updates.py** | 162 | 130 | **20%** | HIGH |
| **rewards.py** | 348 | 289 | **17%** | CRITICAL |
| **enroll.py** | 182 | 153 | **16%** | CRITICAL |
| **calculate_rankings.py** | 151 | 133 | **12%** | CRITICAL |
| **ops_scenario.py** | 663 | 607 | **8%** | CRITICAL |
| **instructor.py** | 393 | 374 | **5%** | CRITICAL |

### Top 5 Kritikus Fájlok (Legrosszabb Coverage)

1. **instructor.py** — 5% (374/393 sorok végrehajtás nélkül)
2. **ops_scenario.py** — 8% (607/663 sorok végrehajtás nélkül)
3. **calculate_rankings.py** — 12% (133/151 sorok végrehajtás nélkül)
4. **enroll.py** — 16% (153/182 sorok végrehajtás nélkül)
5. **rewards.py** — 17% (289/348 sorok végrehajtás nélkül)

**Összesen hiányzó sorok a Top 5-ből:** 2,556 sorok (66% of total missed lines)

---

## Test Success Rate Részletes Breakdown

### Test Execution Summary

```
Total Tests:     216 (72 endpoints × 3 tests each)
                 ├─ Happy Path:     72 tests
                 ├─ Auth Required:  72 tests
                 └─ Input Validation: 72 tests

Executed:        140 tests (skipped 70 input validation, error 8)
  ├─ PASSED:     42 tests  (30%)
  ├─ FAILED:     90 tests  (64%)
  └─ ERROR:      8 tests   (6%)
```

### Success Rate Analysis

#### 1. Auth-Required Tests (401/403 validation)

**Goal:** Validate that endpoints require authentication
**Expected:** 401 Unauthorized or 403 Forbidden
**Result:** **58% success rate** (42/72 passed)

```
PASSED: 42 auth tests
FAILED: 30 auth tests (endpoints returned 404 instead of 401/403)
```

**Interpretation:** 42 endpoints have working auth validation. 30 endpoints either don't exist or have wrong paths.

#### 2. Happy Path Tests (200/201 validation)

**Goal:** Validate that endpoints return success with valid data
**Expected:** 200 OK or 201 Created
**Result:** **~0% success rate** (0/72 passed, 90 failed)

```
FAILED: 90 happy path tests
  ├─ 404 Not Found:        ~60 tests (endpoint doesn't exist or wrong path)
  ├─ 422 Validation Error: ~25 tests (empty payload for POST/PUT)
  └─ 500 Server Error:     ~5 tests (missing dependencies, state issues)
```

**Interpretation:** NONE of the happy path tests are passing with 200/201. This is the **critical gap**.

#### 3. Input Validation Tests (422 validation)

**Goal:** Validate that endpoints reject invalid payloads
**Status:** **100% skipped** (intentionally, waiting for Phase 2)

---

## Gap Analysis: Path to ≥95%

### Current State

```
Baseline Coverage:  24%
Success Rate:       ~0% (200/201 responses)
Auth Success:       58% (42/72 endpoints)
```

### Target State (≥95%)

```
Target Coverage:    ≥95%
Success Rate:       ≥95% (200/201 responses)
Auth Success:       100% (72/72 endpoints)
```

### Gap Breakdown

| Category | Current | Target | Gap | Effort Estimate |
|----------|---------|--------|-----|-----------------|
| **Code Coverage** | 24% | 95% | **-71%** | 40-60 hours |
| **200/201 Success** | 0% | 95% | **-95%** | 30-40 hours |
| **Auth Success** | 58% | 100% | **-42%** | 8-12 hours |
| **TOTAL** | - | - | - | **78-112 hours** |

---

## Prioritás Szerinti Cselekvési Terv

### Priority P0: Fix 404 Endpoints (Immediate, 8-12 hours)

**Problem:** 30 auth tests + 60 happy path tests failing with 404

**Root Causes:**
1. Wrong endpoint paths in auto-generated tests
2. Endpoints genuinely don't exist (removed or never implemented)
3. Router registration issues

**Action Plan:**
1. Cross-reference failing tests with actual endpoint inventory
2. Fix test paths for misconfigured tests
3. Remove tests for non-existent endpoints
4. Document endpoint gaps

**Files to Review:**
- `tools/endpoint_inventory.py` output
- `app/api/api_v1/endpoints/tournaments/__init__.py` (router registration)
- Test paths in `test_tournaments_smoke.py`

**Target:** Reduce 404 errors from ~90 to <10

---

### Priority P1: Generate Valid Payloads (Critical, 20-30 hours)

**Problem:** 25 happy path tests failing with 422 (empty payloads for POST/PUT)

**Root Cause:** Auto-generated tests send `json={}` for all POST/PUT/PATCH requests

**Action Plan:**
1. Extract OpenAPI schemas from FastAPI
2. Generate valid payloads per endpoint based on schema
3. Create payload factories for common entities (Tournament, Enrollment, etc.)
4. Update test generation tool to use payload factories

**Example Implementation:**

```python
# tournaments_payload_factory.py
def generate_create_tournament_payload():
    return {
        "name": "Generated Test Tournament",
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "enrollment_cost": 500,
        "age_group": "PRO",
        "tournament_type_id": 1,
        "max_players": 16,
        # ... all required fields
    }

def generate_enroll_payload(tournament_id: int, user_id: int):
    return {
        "tournament_id": tournament_id,
        "user_id": user_id,
        # ... enrollment-specific fields
    }
```

**Target:** Reduce 422 errors from 25 to 0, increase 200/201 success rate to ~40%

---

### Priority P2: State-Aware Fixtures (High, 15-20 hours)

**Problem:** Some endpoints require specific state (e.g., tournament with sessions, enrolled students)

**Root Cause:** Current fixtures create minimal test data (empty tournament, no sessions, no enrollments)

**Action Plan:**
1. Create tiered fixture hierarchy:
   - `test_tournament_minimal` — Current implementation
   - `test_tournament_with_sessions` — Tournament + generated sessions
   - `test_tournament_with_enrollments` — Tournament + enrolled students
   - `test_tournament_complete` — Full state (sessions + enrollments + results)

2. Update tests to use appropriate fixture level

**Example:**

```python
@pytest.fixture(scope="module")
def test_tournament_with_sessions(test_db, test_tournament, test_campus_id):
    """Tournament with 4 generated sessions (knockout bracket)."""
    # Generate sessions for tournament
    # ... session generation logic
    return {
        "tournament_id": test_tournament["tournament_id"],
        "session_ids": [s.id for s in sessions]
    }

def test_get_tournament_sessions_happy_path(
    api_client,
    admin_token,
    test_tournament_with_sessions  # Use richer fixture
):
    response = api_client.get(
        f"/{test_tournament_with_sessions['tournament_id']}/sessions",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code in [200, 201, 204]
```

**Target:** Fix state-dependent endpoints, increase coverage to ~60%

---

### Priority P3: Deep Coverage for Critical Files (High, 20-30 hours)

**Problem:** 5 critical files have <20% coverage (instructor.py, ops_scenario.py, etc.)

**Action Plan:**
1. Manual E2E tests for complex workflows (not smoke tests)
2. Unit tests for business logic functions
3. Integration tests for multi-step operations

**Scope:** NOT part of smoke tests. Requires separate E2E test suite (Phase 1 E2E from plan)

**Files:**
- `instructor.py` (5% → target 80%)
- `ops_scenario.py` (8% → target 50%, mostly admin-only)
- `calculate_rankings.py` (12% → target 80%)
- `enroll.py` (16% → target 90%)
- `rewards.py` (17% → target 80%)

**Target:** Achieve 80%+ coverage on critical revenue-impacting files

---

## Recommended Next Steps (Immediate Focus)

### Week 1: Fix 404 Endpoints (P0)

**Goal:** Reduce false failures from path issues

**Tasks:**
1. Run endpoint inventory tool again
2. Compare inventory with test paths
3. Fix mismatched paths
4. Remove tests for non-existent endpoints
5. Verify in CI

**Success Criteria:** <10 404 errors remaining

### Week 2: Generate Valid Payloads (P1)

**Goal:** Eliminate 422 validation errors

**Tasks:**
1. Extract OpenAPI schemas
2. Build payload factory system
3. Integrate with test generator tool
4. Regenerate enhanced tests
5. Verify in CI

**Success Criteria:** 0 422 errors, 40%+ success rate

### Week 3-4: State-Aware Fixtures (P2)

**Goal:** Support complex endpoint workflows

**Tasks:**
1. Design fixture hierarchy
2. Implement tiered fixtures
3. Update tests to use appropriate fixtures
4. Verify in CI

**Success Criteria:** 60%+ success rate, 50%+ code coverage

---

## Metrics Dashboard (To Be Updated Weekly)

| Week | Code Coverage | 200/201 Success Rate | Auth Success | Total Passing | Target Gap |
|------|---------------|----------------------|--------------|---------------|------------|
| **Baseline (Week 0)** | 24% | ~0% | 58% | 42/216 (19%) | -76% |
| Week 1 (P0) | TBD | TBD | TBD | TBD | TBD |
| Week 2 (P1) | TBD | TBD | TBD | TBD | TBD |
| Week 3-4 (P2) | TBD | TBD | TBD | TBD | TBD |
| **Target** | ≥95% | ≥95% | 100% | 205/216 (95%) | 0% |

---

## Tool Development Needs

### 1. Endpoint Path Validator

**Purpose:** Cross-check test paths against actual router registration

**Implementation:**
```python
# tools/validate_test_paths.py
def validate_test_paths():
    """Compare test URLs with actual registered routes."""
    # 1. Extract routes from FastAPI app
    # 2. Extract test URLs from test files
    # 3. Report mismatches
```

### 2. Payload Generator

**Purpose:** Generate valid request payloads from OpenAPI schema

**Implementation:**
```python
# tools/generate_payloads_from_schema.py
def generate_payload(endpoint_path, method):
    """Generate valid payload from OpenAPI schema."""
    schema = extract_schema(endpoint_path, method)
    return build_payload_from_schema(schema)
```

### 3. Coverage Tracker

**Purpose:** Track coverage progress week-over-week

**Implementation:**
```bash
# tools/track_coverage.sh
pytest tests/integration/api_smoke/test_tournaments_smoke.py \
  --cov=app/api/api_v1/endpoints/tournaments \
  --cov-report=json:coverage_week_$WEEK.json
```

---

## References

- **Phase 1 Report:** [PHASE_1_TOURNAMENTS_ENHANCEMENT_REPORT.md](PHASE_1_TOURNAMENTS_ENHANCEMENT_REPORT.md)
- **API Coverage Status:** [API_TEST_COVERAGE_STATUS.md](API_TEST_COVERAGE_STATUS.md)
- **Enhanced Tests:** [tests/integration/api_smoke/test_tournaments_smoke.py](tests/integration/api_smoke/test_tournaments_smoke.py)
- **Enhancement Tool:** [tools/enhance_tournaments_smoke_tests_v2.py](tools/enhance_tournaments_smoke_tests_v2.py)

---

**Állapot:** Baseline méréses Complete ✅ | P0 Work Ready to Start 🚀
**Következő lépés:** Fix 404 endpoints (8-12 hours, Week 1 focus)
