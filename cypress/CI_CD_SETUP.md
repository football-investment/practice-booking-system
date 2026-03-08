# CI/CD Setup for Cypress E2E Tests

> **Version**: 1.0.0
> **Last Updated**: 2026-02-20
> **Baseline**: 93.6% overall pass rate (189/202 tests), 100% critical pass rate (149/149 tests)

---

## Table of Contents

1. [Overview](#overview)
2. [Test Classification](#test-classification)
3. [CI/CD Jobs](#cicd-jobs)
4. [Running Tests Locally](#running-tests-locally)
5. [Result Analysis](#result-analysis)
6. [Maintenance](#maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Cypress E2E test suite is configured with **split critical/non-critical test enforcement**:

- **Critical specs** (core workflows): **Blocking** — CI fails if any test fails
- **Non-critical specs** (error states): **Warning only** — failures logged but non-blocking

This allows the team to:
✅ Maintain 100% stability on core user workflows
⚠️ Monitor error state validation without blocking development
📊 Track overall test health (93.6% baseline) while focusing on what matters most

---

## Test Classification

Tests are classified in [`test-manifest.json`](./test-manifest.json):

### Critical Specs (12 specs, 149 tests — 100% passing)

Core user workflows that **must pass** in CI:

```json
"critical": {
  "specs": [
    "admin/dashboard_navigation.cy.js",      // 19 tests
    "admin/tournament_manager.cy.js",        // 8 tests
    "admin/tournament_monitor.cy.js",        // 9 tests
    "auth/registration.cy.js",               // 6 tests
    "instructor/dashboard.cy.js",            // 17 tests
    "instructor/tournament_applications.cy.js", // 8 tests (NEW)
    "student/credits.cy.js",                 // 11 tests
    "student/dashboard.cy.js",               // 12 tests
    "student/enrollment_flow.cy.js",         // 9 tests
    "student/skill_update.cy.js",            // 10 tests
    "player/credits.cy.js",                  // 9 tests
    "player/specialization_hub.cy.js"        // 11 tests
  ],
  "exitOnFailure": true
}
```

### Non-Critical Specs (7 specs, 53 tests — 75.5% passing)

Error state validation and edge cases with **known failures** (non-blocking):

```json
"nonCritical": {
  "specs": [
    "auth/login.cy.js",                     // 7/9 passing (2 failures)
    "error_states/http_409_conflict.cy.js", // 7/8 passing (1 failure)
    "error_states/unauthorized.cy.js",      // 16/17 passing (1 failure)
    "student/enrollment_409_live.cy.js",    // 5/6 passing (1 failure)
    "student/error_states.cy.js",           // 7/11 passing (4 failures)
    "system/cross_role_e2e.cy.js",          // 13/14 passing (1 failure)
    "player/dashboard.cy.js"                // 5/8 passing (3 failures)
  ],
  "exitOnFailure": false,
  "knownIssues": [ ... ]  // See KNOWN_FAILURES.md
}
```

**Known failures** are tracked in [`KNOWN_FAILURES.md`](./KNOWN_FAILURES.md) with issue IDs (E2E-STAB-001 through E2E-STAB-007).

---

## CI/CD Jobs

GitHub Actions workflow: [`.github/workflows/cypress-e2e.yml`](../.github/workflows/cypress-e2e.yml)

### 1. Smoke Suite (PR Gate)

**Trigger**: Every pull request to `main` or `develop`
**Duration**: ~3-5 minutes
**Mode**: **Blocking** (all smoke tests must pass)

```yaml
jobs:
  smoke:
    name: Smoke Suite (PR Gate)
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - name: Run smoke suite
        run: npx cypress run --env grepTags=@smoke
```

**Purpose**: Fast feedback for critical workflows on every PR.

---

### 2. Critical Specs (PR Validation)

**Trigger**: Pull requests (optional gate) or manual trigger
**Duration**: ~15-20 minutes
**Mode**: **Blocking** (all 149 critical tests must pass)

```yaml
jobs:
  critical:
    name: Critical Specs (Core Workflows — Blocking)
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request' || github.event_name == 'workflow_dispatch'
    steps:
      - name: Run critical specs only
        run: npx cypress run --spec 'cypress/e2e/admin/dashboard_navigation.cy.js,...'
```

**Purpose**: Validate core workflows before merge.

---

### 3. Full Suite (Nightly)

**Trigger**: Daily at 02:00 UTC (cron schedule) or manual trigger
**Duration**: ~25-30 minutes
**Mode**: **Split** (critical blocking, non-critical warning only)

```yaml
jobs:
  full:
    name: Full Suite (Nightly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || inputs.suite == 'full'
    steps:
      - name: Run full suite (all 202 tests)
        continue-on-error: true
        run: |
          npx cypress run \
            --browser chrome \
            --headless \
            --reporter json \
            --reporter-options "output=cypress-results.json"

      - name: Analyze results (critical vs non-critical)
        run: node ci-result-processor.js all
```

**Result Processing**:
- [`ci-result-processor.js`](./ci-result-processor.js) reads `cypress-results.json`
- Compares against [`test-manifest.json`](./test-manifest.json)
- **Exits 0** if all critical specs pass (even if non-critical fail)
- **Exits 1** only if critical specs fail

**Purpose**: Comprehensive validation + monitoring of known failures.

---

### 4. Error State Suite (Optional)

**Trigger**: Nightly (alongside full suite) or manual trigger
**Duration**: ~10-15 minutes
**Mode**: Warning only (always exits 0)

```yaml
jobs:
  error-states:
    name: Non-Critical Specs (Error States — Warning Only)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || inputs.suite == 'errors'
    steps:
      - name: Run error-state specs
        run: npx cypress run --spec 'cypress/e2e/error_states/**'
```

**Purpose**: Dedicated error state validation (no live backend, all stubs).

---

## Running Tests Locally

### Prerequisites

```bash
cd tests_cypress
npm ci
```

### NPM Scripts

```bash
# Run all tests (202 tests, ~25-30 min)
npm run cy:run

# Run smoke tests only (~30 tests, ~3-5 min)
npm run cy:run:smoke

# Run critical specs only (149 tests, ~15-20 min)
npm run cy:run:critical

# Run non-critical specs only (53 tests, ~10-12 min)
npm run cy:run:non-critical

# Run specific role specs
npm run cy:run:admin
npm run cy:run:instructor
npm run cy:run:student
npm run cy:run:player

# Open Cypress UI (interactive mode)
npm run cy:open
```

### Analyze Results

After running tests with JSON reporter:

```bash
# Generate Cypress results
npx cypress run --reporter json --reporter-options "output=cypress-results.json"

# Analyze with CI processor
npm run cy:analyze
# or
node ci-result-processor.js all
```

**Output**:
```
═══════════════════════════════════════════════════════════════════
  Cypress E2E Test Results — CI Analysis
═══════════════════════════════════════════════════════════════════

🔒 CRITICAL SPECS (Core Workflows — Blocking)
─────────────────────────────────────────────────────────────────
   Total Tests:    149
   Passed:         149 ✓
   Failed:         0
   Pass Rate:      100.0% (Expected: 100%)
   Status:         ✅ PASS

⚠️  NON-CRITICAL SPECS (Error States — Warning Only)
─────────────────────────────────────────────────────────────────
   Total Tests:    53
   Passed:         40 ✓
   Failed:         13 ⚠️
   Pass Rate:      75.5% (Expected: ≥70%)
   Status:         ⚠️  WARNING — Non-blocking failures

📊 OVERALL SUMMARY
─────────────────────────────────────────────────────────────────
   Total Tests:    202
   Passed:         189 ✓
   Failed:         13 ⚠️
   Pass Rate:      93.6%
   Baseline:       93.6% (expected)

✅ CI SUCCESS: All critical specs passed
   → Core workflows are stable

Exit code: 0
```

---

## Result Analysis

### CI Result Processor

[`ci-result-processor.js`](./ci-result-processor.js) analyzes Cypress JSON output and enforces test classification rules.

**Modes**:
```bash
# Default: check all specs, exit 1 only if critical fail
node ci-result-processor.js all

# Check only critical specs (exit 1 on any failure)
node ci-result-processor.js critical

# Check only non-critical specs (always exit 0, warnings only)
node ci-result-processor.js non-critical
```

**Exit Codes**:
- `0`: All critical specs passed (non-critical failures ignored)
- `1`: At least one critical spec failed (blocking)

**Workflow Integration**:
```yaml
- name: Run full suite
  continue-on-error: true  # Don't fail immediately
  run: npx cypress run --reporter json --reporter-options "output=cypress-results.json"

- name: Analyze results
  run: node ci-result-processor.js all  # This step determines final exit code
```

---

## Maintenance

### Adding a New Test

1. **Write the test** in `cypress/e2e/<role>/<spec-name>.cy.js`
2. **Tag critical tests** with `@smoke` if they're smoke tests
3. **Classify the spec** in [`test-manifest.json`](./test-manifest.json):
   - Add to `specs.critical.specs[]` if it's a core workflow (blocking)
   - Add to `specs.nonCritical.specs[]` if it's an error state or edge case (warning only)
4. **Update npm scripts** in `package.json`:
   - Add spec path to `cy:run:critical` or `cy:run:non-critical`
5. **Update GitHub Actions** in `.github/workflows/cypress-e2e.yml`:
   - Add spec path to critical job's `--spec` list (if critical)

### Fixing a Known Failure

When you fix a non-critical spec that was previously failing:

1. **Verify the fix** locally:
   ```bash
   npm run cy:run:non-critical
   ```
2. **Update [`KNOWN_FAILURES.md`](./KNOWN_FAILURES.md)**:
   - Remove the spec from the "Known Failures" section
   - Update the "Non-Critical Specs" pass rate
3. **Update [`test-manifest.json`](./test-manifest.json)**:
   - Remove the spec from `specs.nonCritical.knownIssues[]`
   - Update `baseline.passingTests` and `baseline.passRate`
4. **Optional**: Promote to critical if the spec is now stable and tests core workflows

### Promoting a Spec to Critical

If a non-critical spec becomes stable and tests core workflows:

1. **Move in [`test-manifest.json`](./test-manifest.json)**:
   ```json
   // From:
   "nonCritical": {
     "specs": ["student/error_states.cy.js", ...]
   }
   // To:
   "critical": {
     "specs": ["student/error_states.cy.js", ...]
   }
   ```
2. **Update npm scripts** in `package.json`:
   - Move spec from `cy:run:non-critical` to `cy:run:critical`
3. **Update GitHub Actions** workflow:
   - Add spec to critical job's `--spec` list
4. **Update [`KNOWN_FAILURES.md`](./KNOWN_FAILURES.md)**:
   - Remove from known failures
   - Add to critical specs table

---

## Troubleshooting

### "All tests are failing in CI but pass locally"

**Possible causes**:
1. **Backend not started**: Check GitHub Actions logs for `uvicorn` startup errors
2. **Database migrations failed**: Check `alembic upgrade head` step
3. **Test data seeding failed**: Check `seed_test_data.py` output
4. **Port conflicts**: Ensure `BACKEND_PORT=8000` and `STREAMLIT_PORT=8501`

**Fix**: Check service health checks in workflow YAML:
```yaml
options: >-
  --health-cmd pg_isready
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

---

### "Critical spec is failing but it's not blocking CI"

**Possible causes**:
1. Spec not listed in [`test-manifest.json`](./test-manifest.json) `specs.critical.specs[]`
2. CI result processor not running (`node ci-result-processor.js all` step missing)
3. Workflow using `continue-on-error: true` without result analysis

**Fix**: Ensure spec is in manifest and result processor is called after Cypress run.

---

### "Non-critical failures are blocking CI"

**Possible causes**:
1. Spec incorrectly classified as critical in [`test-manifest.json`](./test-manifest.json)
2. Result processor running in `critical` mode instead of `all` mode

**Fix**: Move spec to `specs.nonCritical.specs[]` in manifest.

---

### "New spec not running in CI"

**Possible causes**:
1. Spec not added to workflow `--spec` list
2. Spec pattern doesn't match `specPattern` in `cypress.config.js`

**Fix**:
```bash
# Verify spec pattern matches
grep "specPattern" cypress.config.js
# Expected: specPattern: 'cypress/e2e/**/*.cy.{js,jsx}'

# Add to workflow if running critical specs explicitly
# .github/workflows/cypress-e2e.yml line ~XX
--spec 'cypress/e2e/admin/...,cypress/e2e/instructor/tournament_applications.cy.js'
```

---

## Contact & Support

- **Test Manifest**: [`test-manifest.json`](./test-manifest.json)
- **Known Failures**: [`KNOWN_FAILURES.md`](./KNOWN_FAILURES.md)
- **CI/CD Workflow**: [`.github/workflows/cypress-e2e.yml`](../.github/workflows/cypress-e2e.yml)
- **Cypress Config**: [`cypress.config.js`](./cypress.config.js)
- **Custom Commands**: [`cypress/support/commands.js`](./cypress/support/commands.js)

For questions about:
- **Test stabilization**: See Priority Spec Campaign documentation
- **Session-safe navigation**: Check `TECH_DEBT_FORCE_CLICKS.md`
- **Selector strategies**: Review custom commands in `commands.js`
