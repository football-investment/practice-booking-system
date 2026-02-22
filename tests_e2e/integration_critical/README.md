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
- ✅ **API-driven** (NOT UI-heavy Playwright flows)
- ✅ **Deterministic fixture isolation** (fixture = authority)
- ✅ **Idempotent cleanup** (no state leakage)
- ✅ **NO sleep()** calls (use explicit waits, API polling)
- ✅ **NO random data** (deterministic test data only)
- ✅ **Runtime < 30s HARD CAP** (enforced, not aspirational)
- ✅ **Clear failure messages** (actionable errors)

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

- [ ] Test covers multi-role integration (not single-role)
- [ ] Test is NOT duplicate of Fast Suite coverage
- [ ] Test is deterministic (100% pass in 10 runs)
- [ ] Test runtime < 30s
- [ ] Test has clear failure messages
- [ ] Test uses fixture = authority (no manual setup)
- [ ] Test cleanup is complete (no state leakage)
- [ ] Test marked with `@pytest.mark.integration_critical`
- [ ] Test documented in this README

---

**Maintained by:** E2E Team
**Last updated:** 2026-02-22
**Baseline:** e2e-fast-suite-stable-v2
