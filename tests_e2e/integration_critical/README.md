# Integration Critical Suite

> **Purpose:** Complex multi-role E2E workflows (NON-BLOCKING)
> **Marker:** `@pytest.mark.integration_critical`
> **CI Policy:** Nightly run, does NOT block PR merges
> **Separation:** Isolated from Fast Suite to maintain stability

---

## 🎯 Philosophy

**Fast Suite (52 tests) = BLOCKING:**
- Deterministic
- Fast (<5 min)
- API/lifecycle critical path
- Flake-free
- 100% PASS required for PR merge

**Integration Critical Suite = NON-BLOCKING:**
- Complex multi-role flows
- Longer runtime (10-30s per test)
- System integration validation
- Nightly execution
- Failures do NOT block PR merge

**Key Principle:**
> CI gate stability > maximum coverage

---

## 📊 Test Coverage

### Included Workflows (Priority Order)

| # | Workflow | Priority | Est. Runtime | Status |
|---|----------|----------|--------------|--------|
| 1 | **Multi-Role Integration** | HIGH | ~30s | Planned |
| 2 | **Student Full Enrollment** | HIGH | ~20s | Planned |
| 3 | **Instructor Full Workflow** | HIGH | ~25s | Planned |

---

## 🏗️ Architecture

### Directory Structure
```
tests_e2e/
├── integration_critical/          ← NEW SUITE (non-blocking)
│   ├── __init__.py
│   ├── README.md                  ← This file
│   ├── test_multi_role_integration.py
│   ├── test_student_enrollment_flow.py
│   └── test_instructor_workflow.py
├── test_game_presets_admin.py     ← Fast Suite (blocking)
├── test_instructor_dashboard.py   ← Fast Suite (blocking)
├── test_tournament_lifecycle.py   ← Fast Suite (blocking)
└── ...
```

### Marker Usage
```python
@pytest.mark.e2e
@pytest.mark.integration_critical  # NON-BLOCKING
@pytest.mark.ops_seed              # Requires 64 @lfa-seed.hu players
def test_multi_role_tournament_integration(api_url, test_admin, test_students, test_instructor):
    """
    Full multi-role tournament lifecycle:
    - Admin creates tournament
    - Students enroll
    - Instructor assigned
    - Sessions generated
    - Instructor check-in + results
    - Admin finalizes
    - Students receive rewards + badges
    """
```

---

## 🚀 Execution

### Local Development
```bash
# Run Integration Critical Suite only
pytest tests_e2e/integration_critical/ -v

# Or with marker
pytest tests_e2e/ -m integration_critical -v

# Exclude from Fast Suite
pytest tests_e2e/ -m "not scale_suite and not integration_critical" -v
```

### CI Workflows

**Fast Suite (BLOCKING - mandatory):**
```yaml
# .github/workflows/e2e-fast-suite.yml
pytest tests_e2e/ -m "not scale_suite and not integration_critical"
```

**Integration Critical Suite (NON-BLOCKING - nightly):**
```yaml
# .github/workflows/e2e-integration-critical.yml (NEW)
on:
  schedule:
    - cron: '0 2 * * *'  # Daily 2 AM UTC
  workflow_dispatch:

pytest tests_e2e/ -m integration_critical
```

### Marker Policy Validation

**Verification (run before PR merge):**
```bash
# Verify integration_critical tests are EXCLUDED from Fast Suite
pytest tests_e2e/ -m "not scale_suite and not integration_critical" --collect-only -q | grep -c "test_multi_role\|test_student_full\|test_instructor_full"
# Expected output: 0 (zero integration_critical tests collected)

# Verify integration_critical tests are INCLUDED in their own suite
pytest tests_e2e/ -m integration_critical --collect-only -q | grep -c "test_multi_role\|test_student_full\|test_instructor_full"
# Expected output: 3 (all integration_critical tests collected)
```

**Policy Enforcement:**
- ✅ Fast Suite NEVER collects `@pytest.mark.integration_critical` tests
- ✅ PR pipeline runs ONLY Fast Suite (52/52 PASS required)
- ✅ Integration Critical Suite runs nightly (failures non-blocking)

---

## 📋 Implementation Order

### Phase 1: Multi-Role Integration (Week 1)

**Implementation Principles (API-Driven):**
```python
# test_multi_role_integration.py

# ✅ DO: API-driven workflow
def test_multi_role_tournament_integration(api_url, test_admin, test_students, test_instructor):
    # Step 1: Admin creates tournament via API (NOT UI)
    response = requests.post(f"{api_url}/tournaments", json={...}, headers=admin_auth)
    tournament_id = response.json()["id"]

    # Step 2: Students enroll via API (NOT UI)
    for student in test_students[:3]:
        requests.post(f"{api_url}/tournaments/{tournament_id}/enroll", headers=student_auth)

    # Step 3: Verify enrollments via API assertion
    enrollments = requests.get(f"{api_url}/tournaments/{tournament_id}/enrollments").json()
    assert len(enrollments) == 3

    # ... (API-driven steps continue)

# ❌ DON'T: UI-heavy navigation
# page.goto(f"{base_url}/admin/tournaments")
# page.locator("button:has-text('Create Tournament')").click()
# page.fill("input[name='tournament_name']", "...")  # TOO SLOW, FLAKY
```

**Workflow Coverage:**
- Admin creates tournament → IN_PROGRESS (API POST)
- 3 Students enroll (API POST × 3)
- Instructor assigned (API PATCH)
- Sessions auto-generated (API lifecycle transition)
- Instructor check-in + submit results (API POST)
- Admin finalizes tournament (API PATCH)
- Students receive XP/rewards (API GET validation)
- Champion badge assigned (API GET assertion)

**Hard Constraints:**
- NO Playwright page.goto() unless absolutely necessary
- NO UI navigation for setup/teardown
- API assertions only (deterministic JSON responses)
- Max runtime: 30s HARD CAP

---

### Week 1 Implementation Guide (Scope Control)

> **Senior Irány: Ez egy stabil referencia integrációs gerinc, nem exhaustive teszt**

**1️⃣ Scope Kontroll (MANDATORY):**
```python
# ✅ DO: Maximum 1 happy-path flow
def test_multi_role_tournament_integration(api_url, test_admin, test_students, test_instructor):
    """
    Single happy-path integration flow (NO edge cases, NO branches).

    Purpose: Validate core multi-role integration workflow only.
    NOT an exhaustive test suite.
    """
    # Linear flow: create → enroll → assign → finalize → validate
    # NO if/else branches
    # NO parametrize
    # NO edge-case logic

# ❌ DON'T: Multiple scenarios, parametrization
@pytest.mark.parametrize("player_count", [4, 8, 16])  # TILOS
def test_multi_role_various_sizes(...):  # TILOS - ez exhaustive coverage
```

**2️⃣ State Isolation Enforcement (MANDATORY):**
```python
import time

def test_multi_role_tournament_integration(api_url, test_admin, ...):
    # KÖTELEZŐ: Unique namespace prefix
    timestamp = int(time.time() * 1000)
    tournament_name = f"INT_TEST_MULTI_ROLE_{timestamp}"

    # Step 1: Create tournament
    response = requests.post(f"{api_url}/tournaments", json={
        "name": tournament_name,  # UNIQUE name
        "tournament_type_id": 1,
        # ...
    }, headers=admin_auth)
    tournament_id = response.json()["id"]

    try:
        # ... test workflow ...

    finally:
        # KÖTELEZŐ: Explicit cleanup (NE implicit rollback)
        # Step 1: Delete tournament
        requests.delete(f"{api_url}/tournaments/{tournament_id}", headers=admin_auth)

        # Step 2: Verify cleanup (MANDATORY assertion)
        list_response = requests.get(f"{api_url}/tournaments", headers=admin_auth)
        tournaments = list_response.json()
        assert tournament_id not in [t["id"] for t in tournaments], \
            f"Tournament {tournament_id} still exists after cleanup"

        # Step 3: Verify enrollments deleted
        enrollments_response = requests.get(
            f"{api_url}/tournaments/{tournament_id}/enrollments",
            headers=admin_auth
        )
        assert enrollments_response.status_code == 404 or len(enrollments_response.json()) == 0, \
            "Enrollments not cleaned up"
```

**3️⃣ Stability Validation Szigorítás:**
```bash
# Nem elég 20 consecutive runs

# KÖTELEZŐ: Sequential stability
for i in {1..20}; do
    pytest tests_e2e/integration_critical/test_multi_role_integration.py::test_multi_role_tournament_integration -v
done

# KÖTELEZŐ: Parallel stability (state isolation validation)
pytest -n auto tests_e2e/integration_critical/test_multi_role_integration.py::test_multi_role_tournament_integration -v

# Ha párhuzamosan flake-el → STATE ISOLATION HIBA
# → Unique namespace nem elég izolált
# → Shared mutable state létezik
# → STOP: Ne patch, szétbontás
```

**4️⃣ Observability (MANDATORY):**
```python
import logging
import time

logger = logging.getLogger(__name__)

def test_multi_role_tournament_integration(api_url, test_admin, ...):
    step_timings = {}

    # Step 1: Admin creates tournament
    step_start = time.time()
    logger.info("STEP 1: Admin creating tournament...")
    response = requests.post(...)
    tournament_id = response.json()["id"]
    step_timings["step1_create_tournament"] = time.time() - step_start
    logger.info(f"✓ STEP 1 completed in {step_timings['step1_create_tournament']:.2f}s")

    # Step 2: Students enroll
    step_start = time.time()
    logger.info("STEP 2: Students enrolling...")
    for i, student in enumerate(test_students[:3], 1):
        requests.post(...)
        logger.info(f"  → Student {i}/3 enrolled")
    step_timings["step2_enrollments"] = time.time() - step_start
    logger.info(f"✓ STEP 2 completed in {step_timings['step2_enrollments']:.2f}s")

    # ... (minden lépés hasonlóan)

    # Final timing validation
    total_runtime = sum(step_timings.values())
    logger.info(f"Total runtime: {total_runtime:.2f}s")

    # HARD CAP enforcement
    if total_runtime > 25.0:  # 25s warning threshold (30s hard cap)
        logger.warning(f"⚠️  Runtime approaching 30s limit: {total_runtime:.2f}s")
        logger.warning("🔧 BREAKDOWN KÖTELEZŐ if exceeds 30s")

    assert total_runtime < 30.0, \
        f"Runtime exceeded 30s HARD CAP: {total_runtime:.2f}s — BREAKDOWN REQUIRED"
```

**5️⃣ Stop Condition (CRITICAL):**
```
IF test shows ANY of:
   ❌ Runtime > 30s
   ❌ Flaky (sequential OR parallel)
   ❌ Cleanup not deterministic

THEN:
   🚫 DO NOT patch/workaround
   ✅ BREAK DOWN into smaller integration units

Example breakdown:
   - test_multi_role_tournament_integration (original)
   →
   - test_tournament_creation_and_enrollment (isolated)
   - test_instructor_assignment_and_sessions (isolated)
   - test_tournament_finalization_and_rewards (isolated)
```

**Philosophy:**
> Integration Critical Suite ≠ második Fast Suite
> Kontrollált integrációs validáció, NEM teljes E2E duplikáció

---

### Phase 2: Student Enrollment Flow (Week 2)
```python
# test_student_enrollment_flow.py
- Student login
- Browse tournaments (filter, search)
- View tournament details
- Enroll (credit check, deduction)
- Enrollment confirmation
- "My Tournaments" shows enrollment
- Session schedule visible
- Assertions: enrollment created, credits deducted, sessions visible
```

### Phase 3: Instructor Workflow (Week 3)
```python
# test_instructor_workflow.py
- Instructor applies to tournament
- Admin approves assignment
- Instructor check-in (session start)
- Instructor submit results (scoring)
- Tournament finalization
- Results visible to students
- Assertions: assignment, check-in, results, student visibility
```

---

## 🎯 Definition of Done (DoD)

> **Senior Kontroll: Szigorú stabilitási kritériumok**

**Per-Test Requirements (MANDATORY):**
- ✅ **0 flake in 20 consecutive local runs** (not 10, but **20**)
- ✅ **0 flake in parallel runs** (`pytest -n auto`) — validates state isolation
- ✅ **API-driven** (NOT UI-heavy Playwright flows)
- ✅ **Deterministic fixture isolation** (fixture = authority)
- ✅ **Idempotent cleanup** (no state leakage) + explicit cleanup assertions
- ✅ **Unique namespace prefix** (e.g., `INT_TEST_`) + timestamp for isolation
- ✅ **NO sleep()** calls (use explicit waits, API polling)
- ✅ **NO random data** (deterministic test data only)
- ✅ **Runtime < 30s HARD CAP** (enforced, not aspirational)
- ✅ **Step-level timing + structured logging** (observability mandatory)
- ✅ **Clear failure messages** (actionable errors)
- ✅ **Scope: 1 happy-path only** (NO edge cases, NO parametrize, NO branches)

**Suite-Level Requirements:**
- ✅ Total runtime < 2 minutes (3 tests × ~30s)
- ✅ Independent execution (no test order dependencies)
- ✅ Does NOT increase Fast Suite runtime (0% impact)
- ✅ No shared mutable state between tests

**Stability Policy (CRITICAL):**
- 🚨 **If test flakes → DO NOT fix ad-hoc**
- 🔧 **Instead: Break down into smaller, more stable units**
- ✅ **Principle: Controlled coverage growth, stability above all**

**Failure Policy:**
- ❌ Failures do NOT block PR merge
- 📊 Failures reported in nightly summary
- 🔧 Iterative fixes (no rush, separate branch)

---

## 🚫 What NOT to Include

**DO NOT add to Integration Critical Suite:**
- ❌ Duplicate Fast Suite coverage (API tests, boundary tests)
- ❌ UI navigation smoke tests (belongs in separate UI suite)
- ❌ Error handling edge cases (LOW priority)
- ❌ Performance benchmarks (Scale Suite)
- ❌ Single-role workflows already covered (Fast Suite)

**Rationale:**
Keep Integration Critical Suite focused on **CRITICAL multi-role workflows** that aren't covered by Fast Suite.

---

## 📊 CI Impact Analysis

**Before (Fast Suite only):**
```
Fast Suite: 52 tests, ~3-5 min
CI gate: BLOCKING
Coverage: API + single-role lifecycle
```

**After (Fast Suite + Integration Critical):**
```
Fast Suite: 52 tests, ~3-5 min (UNCHANGED)
CI gate: BLOCKING (UNCHANGED)

Integration Critical: 3 tests, ~2 min
CI gate: NON-BLOCKING (nightly)
Coverage: Multi-role integration flows
```

**Fast Suite Impact:**
- ✅ Runtime: NO CHANGE (0% growth)
- ✅ Test count: NO CHANGE (52 tests)
- ✅ Stability: PROTECTED (no complex flows added)

---

## 🔄 Maintenance

**Documentation Updates:**
- Update E2E_STABILITY_BASELINE.md when tests added
- Document CI workflow in .github/CI_ENFORCEMENT.md
- Tag stable versions: `e2e-integration-critical-v1`

**Debugging:**
- Integration Critical failures → separate branch
- No rush, iterative fixes
- Does NOT block main development

---

## ✅ Approval Checklist

Before adding a test to Integration Critical Suite:

**Scope Control:**
- [ ] Test covers multi-role integration (not single-role)
- [ ] Test is NOT duplicate of Fast Suite coverage
- [ ] **Maximum 1 happy-path flow** (NO edge cases, NO branches, NO parametrize)
- [ ] Test documented in this README

**Stability:**
- [ ] **0 flake in 20 consecutive runs** (`for i in {1..20}; do pytest ...; done`)
- [ ] **0 flake in parallel runs** (`pytest -n auto` validates state isolation)
- [ ] Test runtime < 30s HARD CAP (measured, not estimated)

**Implementation:**
- [ ] **API-driven** (NOT UI-heavy Playwright navigation)
- [ ] Test uses fixture = authority (no manual setup)
- [ ] **Unique namespace prefix** (e.g., `INT_TEST_` + timestamp)
- [ ] **Explicit cleanup** (DELETE API calls, NOT implicit rollback)
- [ ] **Cleanup assertions** (verify tournament deleted, enrollments = 0)

**Observability:**
- [ ] **Step-level timing measurement** (logged per step)
- [ ] **Structured logging** (info logs at each major step)
- [ ] Test has clear failure messages (actionable errors)

**CI Integration:**
- [ ] Test marked with `@pytest.mark.integration_critical`
- [ ] Test does NOT increase Fast Suite runtime (verified: Fast Suite still 52/52, ~3-5 min)

---

**Maintained by:** E2E Team
**Last updated:** 2026-02-22
**Baseline:** e2e-fast-suite-stable-v2
