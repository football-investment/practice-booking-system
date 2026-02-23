# pytest.ini Consolidation Plan

> **Issue**: 2 separate pytest.ini files causing confusion
> **Impact**: Different marker sets, different test paths
> **Priority**: Medium (doesn't block production, but causes confusion)

---

## Current State

### File 1: `pytest.ini` (ROOT)

**Location**: `/pytest.ini`
**Purpose**: Root-level tests (tests/, app/tests/)
**Test Paths**: `testpaths = tests`

**Markers** (43 total):
- E2E markers: `e2e`, `golden_path`, `smoke`, `regression`, `critical`
- User lifecycle: `user_lifecycle`, `registration`, `onboarding`, `ui`, `invitation_ui`
- Business workflow: `business_workflow`, `instructor`, `admin`
- Tournament formats: `h2h`, `individual_ranking`, `group_knockout`, `group_stage`
- Component markers: `tournament`, `validation`, `unit`, `integration`, `requires_worker`

---

### File 2: `tests_e2e/pytest.ini`

**Location**: `/tests_e2e/pytest.ini`
**Purpose**: E2E tests (tests_e2e/)
**Test Paths**: `testpaths = .`

**Markers** (27 total):
- Core: `golden_path`, `e2e`, `smoke`, `regression`, `critical`, `requires_worker`, `skip`
- Lifecycle phases: `lifecycle`, `phase_0` through `phase_6`
- Specialized: `skill_progression`, `edge_cardinality`, `nondestructive`, `scale_structural`
- Production: `production_flow`, `concurrency`, `large_field_monitor`, `tournament_monitor`
- Scale: `ops_seed`, `scale_suite`
- **Integration Critical**: `integration_critical` (unique to this config)
- Performance: `slow`

**Key Difference**: Has `integration_critical` marker (used by Production Gate tests)

---

## Problem Analysis

### Conflicts

1. **Different test paths**: `tests/` vs `.` (current directory)
2. **Marker overlap**: Both define `e2e`, `smoke`, `critical`, etc.
3. **Marker divergence**: tests_e2e/ has specialized markers not in root config
4. **Configuration**: tests_e2e/ has logging, strict-markers, maxfail settings

### Why 2 Configs Exist

**Hypothesis**: tests_e2e/ was created as a separate E2E test suite with different requirements:
- Different execution context (Playwright, lifecycle phases)
- Different markers (integration_critical, phase markers)
- Different logging needs (CLI logging for E2E)

---

## Solution Options

### Option A: Merge into Single Config (Recommended)

**Consolidate all markers into root `pytest.ini`**

**Benefits**:
- Single source of truth
- No confusion about which config is used
- Easier to maintain

**Drawbacks**:
- Larger config file
- Need to update test paths to include both `tests/` and `tests_e2e/`

**Implementation**:
```ini
[pytest]
# Consolidated test configuration
testpaths = tests tests_e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Logging (from tests_e2e config)
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Failure behavior (from tests_e2e config)
addopts =
    --strict-markers
    --tb=short
    --maxfail=1
    -ra

# Custom markers - CONSOLIDATED (all markers from both configs)
markers =
    # E2E Test Markers
    e2e: End-to-end tests with Playwright or Selenium
    golden_path: Production critical Golden Path tests (DO NOT SKIP)
    smoke: Fast smoke tests for CI regression checks
    regression: Regression protection tests
    critical: Build blocker tests - must pass before deployment

    # Integration Critical (Production Gate)
    integration_critical: Critical multi-role integration flows (BLOCKING)

    # User Lifecycle
    user_lifecycle: User activation tests
    registration: User registration flows
    onboarding: User onboarding workflows
    ui: UI-based test (Streamlit/Playwright)
    invitation_ui: Invitation code UI tests

    # Business Workflows
    business_workflow: Business logic workflows
    instructor: Instructor workflow tests
    admin: Admin workflow tests

    # Tournament Formats
    h2h: HEAD_TO_HEAD tournament tests
    individual_ranking: INDIVIDUAL_RANKING tournament tests
    group_knockout: GROUP_AND_KNOCKOUT tournament tests
    group_stage: GROUP_STAGE_ONLY tests

    # Test Levels
    unit: Unit tests for isolated component testing
    integration: Integration tests for multi-component interactions
    requires_worker: Tests requiring background worker

    # Lifecycle Phases (from tests_e2e)
    lifecycle: Lifecycle phase tests (ordered, state-dependent)
    phase_0: Phase 0 — Clean DB setup
    phase_1: Phase 1 — User registration
    phase_2: Phase 2 — Onboarding
    phase_3: Phase 3 — Enrollment/license
    phase_4: Phase 4 — Tournament lifecycle
    phase_5: Phase 5 — Skill progression coverage
    phase_6: Phase 6 — Edge cardinality system-safety tests

    # Performance & Scale (from tests_e2e)
    skill_progression: Skill-level assertions
    edge_cardinality: Edge player-count tests
    nondestructive: Tests that do not modify state
    scale_structural: Structural tests for large-cardinality tournaments
    production_flow: Live server + real DB + Celery required
    concurrency: Parallel tournament generation stress test
    large_field_monitor: 1024-player knockout + UI validation
    tournament_monitor: Headless Playwright tests for OPS Tournament Monitor
    ops_seed: Tests requiring 64 @lfa-seed.hu seed players
    scale_suite: Tests requiring 128-1024 players
    slow: Tests with long runtime (>30s)

    # Component Markers
    tournament: Tournament-related tests
    validation: Business logic validation tests
    skip: Tests to skip (for debugging/manual runs only)

# pytest-selenium: only treat production domains as sensitive
sensitive_url = (https?://(www\.)?lfa\.(com|hu|io))
```

**Then DELETE**: `tests_e2e/pytest.ini`

---

### Option B: Keep Separate, Document Clearly (Pragmatic)

**Keep both configs but add clear documentation**

**Benefits**:
- No risk of breaking existing tests
- Clear separation of concerns
- Easier rollback if issues arise

**Drawbacks**:
- Still confusing for developers
- Need to maintain 2 configs

**Implementation**:

**1. Add to root pytest.ini**:
```ini
[pytest]
# ROOT CONFIG - for tests/ and app/tests/
# For tests_e2e/ tests, use tests_e2e/pytest.ini instead
# See: docs/TESTING_STRATEGY.md for details

testpaths = tests
# ... rest of config
```

**2. Add to tests_e2e/pytest.ini**:
```ini
[pytest]
# E2E CONFIG - for tests_e2e/ only
# For root tests, use /pytest.ini instead
# This config has specialized markers for E2E tests
# See: docs/TESTING_STRATEGY.md for details

testpaths = .
# ... rest of config
```

**3. Create TESTING_STRATEGY.md** documenting when to use each config

---

### Option C: Hybrid (Best of Both)

**Merge common markers, keep specialized configs**

**Root pytest.ini**: Common markers only
**tests_e2e/pytest.ini**: E2E-specific markers (inherits from root)

**Not possible**: pytest doesn't support config inheritance

---

## Recommendation

### ✅ Option A: Merge into Single Config

**Why**:
1. Eliminates confusion
2. Single source of truth
3. Easier to maintain
4. pytest resolves markers correctly

**Risk**: Low (just need to update testpaths)

**Timeline**: 1 hour

---

## Implementation Steps

### Step 1: Backup

```bash
cp pytest.ini pytest.ini.backup
cp tests_e2e/pytest.ini tests_e2e/pytest.ini.backup
```

### Step 2: Create Consolidated Config

```bash
# Edit pytest.ini (root)
# Add:
# - testpaths = tests tests_e2e
# - All markers from both configs
# - Logging settings from tests_e2e/
# - addopts from tests_e2e/
```

### Step 3: Delete Old Config

```bash
rm tests_e2e/pytest.ini
```

### Step 4: Verify

```bash
# Test discovery from root
pytest --collect-only -q | tail -5

# Test discovery from tests_e2e/
cd tests_e2e && pytest --collect-only -q | tail -5

# Run integration critical tests
pytest tests_e2e/integration_critical/ -v

# Run unit tests
pytest app/tests/ --ignore=app/tests/.archive -q
```

---

## Validation

**Success Criteria**:
- ✅ All tests discoverable from root
- ✅ All tests discoverable from tests_e2e/
- ✅ integration_critical marker works
- ✅ No marker warnings
- ✅ All existing tests pass

---

**Status**: READY TO EXECUTE
**Priority**: Medium
**Effort**: 1 hour
**Risk**: Low
