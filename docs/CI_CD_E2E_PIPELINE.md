# CI/CD E2E Test Pipeline — Comprehensive Guide

> **Last Updated:** 2026-02-20
> **Pipeline Version:** 1.0 (Comprehensive Admin + Instructor + Student Coverage)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Test Coverage](#test-coverage)
- [Running Tests Locally](#running-tests-locally)
- [CI/CD Workflows](#cicd-workflows)
- [Cypress Cloud Integration (Optional)](#cypress-cloud-integration-optional)
- [Interpreting Test Results](#interpreting-test-results)
- [Maintenance & Troubleshooting](#maintenance--troubleshooting)
- [Best Practices](#best-practices)

---

## 🎯 Overview

The **E2E Comprehensive Pipeline** provides automated end-to-end testing for the entire LFA Education Center system across all user roles:

- **Admin** (9 modules, 420+ tests): User/Financial/Session/Tournament/Location/Semester/GamePresets/Events management
- **Instructor** (4 modules, 67+ tests): Dashboard/Session Check-in/Tournament Workflow/Applications
- **Student** (4 modules, 38+ tests): Dashboard/Onboarding/Credits/Specialization

**Total Coverage:** ~525+ tests across 17 modules

---

## 🏗️ Pipeline Architecture

### **GitHub Actions Workflow:** `.github/workflows/e2e-comprehensive.yml`

```
┌─────────────────────────────────────────────────────────────┐
│                     E2E Comprehensive Pipeline               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─── Job 1: Smoke Suite (PR Gate, ~5 min)
                              │    ├─ @smoke tagged tests only
                              │    ├─ Fast feedback for PRs
                              │    └─ Blocking: YES
                              │
                              ├─── Job 2: Critical Suite (Blocking, ~20 min)
                              │    ├─ @critical tagged tests
                              │    ├─ Parallel by role: admin/instructor/student
                              │    └─ Blocking: YES
                              │
                              ├─── Job 3: Full Suite (Nightly, ~60 min)
                              │    ├─ All 525+ tests
                              │    ├─ Parallel by role: admin/instructor/player/auth/system
                              │    ├─ Cypress Cloud recording (if enabled)
                              │    └─ Blocking: NO (nightly only)
                              │
                              └─── Job 4: Test Summary & Coverage Report
                                   ├─ GitHub Step Summary
                                   ├─ PR Comment (if PR event)
                                   └─ Pass/Fail gate
```

---

## 📊 Test Coverage

### **Admin E2E Tests** (9 Modules, ~420 Tests)

| Module | File | Tests | Critical |
|--------|------|-------|----------|
| User Management | `user_management.cy.js` | 50+ | ✅ |
| Financial Management | `financial_management.cy.js` | 40+ | ✅ |
| Session Management | `session_management.cy.js` | 60+ | ✅ |
| Tournament Editing | `tournament_editing.cy.js` | 50+ | ✅ |
| Location Management | `location_management.cy.js` | 40+ | - |
| Semester Management | `semester_management.cy.js` | 40+ | - |
| Game Presets Management | `game_presets_management.cy.js` | 40+ | - |
| Events Calendar | `events_calendar.cy.js` | 40+ | - |
| Tournament Lifecycle | `tournament_lifecycle_complete.cy.js` | 60+ | ✅ |

### **Instructor E2E Tests** (4 Modules, ~67 Tests)

| Module | File | Tests | Critical |
|--------|------|-------|----------|
| Dashboard | `dashboard.cy.js` | 15+ | ✅ |
| Session Check-in | `session_checkin.cy.js` | 12+ | - |
| Tournament Workflow | `tournament_workflow.cy.js` | 30+ | ✅ |
| Tournament Applications | `tournament_applications.cy.js` | 10+ | - |

### **Student E2E Tests** (4 Modules, ~38 Tests)

| Module | File | Tests | Critical |
|--------|------|-------|----------|
| Dashboard | `dashboard.cy.js` | 10+ | ✅ |
| Onboarding | `onboarding.cy.js` | 10+ | ✅ |
| Credits | `credits.cy.js` | 8+ | - |
| Specialization Hub | `specialization_hub.cy.js` | 10+ | - |

### **Test Tags**

- `@smoke`: Fast, essential tests for PR gate (~30 tests, ~5 min)
- `@critical`: Blocking tests for merge (~150 tests, ~20 min)
- All tests: Full suite for nightly runs (~525 tests, ~60 min)

---

## 💻 Running Tests Locally

### **Prerequisites**

1. **Install dependencies:**
   ```bash
   cd tests_cypress
   npm install
   ```

2. **Start services:**
   ```bash
   # Terminal 1: FastAPI backend
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_test \
     uvicorn app.main:app --reload --port 8000

   # Terminal 2: Streamlit frontend
   streamlit run streamlit_app/Home.py --server.port 8501
   ```

### **Run Tests**

#### **Interactive Mode (Cypress UI)**
```bash
cd tests_cypress
npm run cy:open
```

#### **Headless Mode (CLI)**

**All tests:**
```bash
npm run cy:run
```

**By role:**
```bash
npm run cy:run:admin          # All admin tests
npm run cy:run:instructor     # All instructor tests
npm run cy:run:player         # All student tests
```

**By tag:**
```bash
npm run cy:run:smoke          # Smoke tests only (@smoke)
npm run cy:run:critical       # Critical tests only (@critical)
```

**By role + tag:**
```bash
npm run cy:run:admin:critical      # Admin critical tests
npm run cy:run:instructor:critical # Instructor critical tests
npm run cy:run:student:critical    # Student critical tests
```

### **Environment Variables**

Override default test credentials:

```bash
CYPRESS_ADMIN_EMAIL=admin@lfa.com \
CYPRESS_ADMIN_PASSWORD=AdminPass123! \
CYPRESS_INSTRUCTOR_EMAIL=grandmaster@lfa.com \
CYPRESS_INSTRUCTOR_PASSWORD=TestInstructor2026 \
CYPRESS_PLAYER_EMAIL=rdias@manchestercity.com \
CYPRESS_PLAYER_PASSWORD=TestPlayer2026 \
  npm run cy:run:smoke
```

---

## 🚀 CI/CD Workflows

### **Trigger Events**

| Event | Trigger | Suite | Duration | Blocking |
|-------|---------|-------|----------|----------|
| **Pull Request** | On PR to `main`/`develop` | Smoke + Critical | ~25 min | ✅ YES |
| **Nightly** | 03:00 UTC daily (cron) | Full suite (all 525 tests) | ~60 min | ❌ NO |
| **Manual** | `workflow_dispatch` | Configurable (smoke/critical/full/role-specific) | Varies | ❌ NO |

### **PR Gate Workflow**

**Goal:** Fast feedback for pull requests

1. **Smoke Suite** runs first (~5 min)
   - Only @smoke tagged tests
   - If fails → PR blocked immediately

2. **Critical Suite** runs in parallel (~20 min)
   - @critical tests split by role (admin/instructor/student)
   - Parallel execution via matrix strategy
   - If ANY role fails → PR blocked

3. **Test Summary** job
   - Generates GitHub Step Summary
   - Posts PR comment with pass/fail status
   - Fails workflow if smoke OR critical failed

**Example PR Comment:**
```
✅ **E2E Tests Passed** — Safe to merge!

- 🚀 Smoke: PASSED
- 🛡️ Critical: PASSED

**Coverage:** 525+ tests across admin/instructor/student workflows
```

### **Nightly Full Suite**

**Goal:** Comprehensive regression testing

- Runs ALL 525+ tests
- Parallel execution by role (5 parallel jobs):
  - Admin (~420 tests)
  - Instructor (~67 tests)
  - Player (~38 tests)
  - Auth (~15 tests)
  - System (~20 tests)
- Uploads screenshots, videos, and test results
- Records to Cypress Cloud (if configured)

### **Manual Workflow Dispatch**

**Goal:** On-demand test execution

```yaml
inputs:
  suite:
    - smoke
    - critical
    - full
    - admin-only
    - instructor-only
    - student-only
  record:
    - true (record to Cypress Cloud)
    - false (no recording)
```

**Usage:**
1. Go to GitHub Actions → E2E Comprehensive workflow
2. Click "Run workflow"
3. Select suite and record option
4. Click "Run workflow"

---

## ☁️ Cypress Cloud Integration (Optional)

### **Benefits**

- **Test Analytics:** Failure trends, flaky test detection, performance metrics
- **Parallelization:** Automatic load balancing across CI machines
- **Test Replay:** Debug failures with video/screenshot replay
- **Dashboard:** https://cloud.cypress.io/projects/{project-id}

### **Setup**

1. **Create Cypress Cloud project:**
   - Go to https://cloud.cypress.io
   - Create new project
   - Get Project ID (e.g., `abc123`)

2. **Get Record Key:**
   - In Cypress Cloud project settings → Record Keys
   - Copy key (e.g., `a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6`)

3. **Add GitHub Secrets:**
   ```
   Repository Settings → Secrets and variables → Actions → New repository secret

   Name:  CYPRESS_PROJECT_ID
   Value: abc123

   Name:  CYPRESS_RECORD_KEY
   Value: a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6
   ```

4. **Trigger workflow with recording:**
   - Manual dispatch with `record: true`
   - Or modify `e2e-comprehensive.yml` to always record:
     ```yaml
     # Line ~400, change condition:
     if [ -n "${{ secrets.CYPRESS_RECORD_KEY }}" ]; then
       RECORD_FLAG="--record ..."
     fi
     ```

### **Parallel Execution with Cypress Cloud**

When recording enabled, the pipeline automatically uses `--parallel` flag:

```bash
--record --parallel --group ${{ matrix.role }} --ci-build-id ${{ github.run_id }}
```

This distributes tests across multiple machines for faster execution.

---

## 📈 Interpreting Test Results

### **GitHub Actions UI**

**Workflow Run View:**
```
🚀 Smoke Suite (PR Gate)              ✅ 5m 23s
🛡️ Critical Suite - admin             ✅ 18m 45s
🛡️ Critical Suite - instructor        ✅ 12m 34s
🛡️ Critical Suite - student           ✅ 10m 12s
📊 Test Summary & Coverage Report      ✅ 0m 15s
```

**Artifacts (if failure):**
- `smoke-screenshots-{run-id}.zip`
- `critical-admin-screenshots-{run-id}.zip`
- `critical-instructor-screenshots-{run-id}.zip`
- `critical-student-screenshots-{run-id}.zip`

### **GitHub Step Summary**

Automatically generated summary with:
- Test suite status table
- Pass/Fail verdict
- Coverage breakdown
- Total test count

**Example:**
```
## E2E Comprehensive Test Results

| Suite | Status |
|-------|--------|
| 🚀 Smoke (PR Gate) | success |
| 🛡️ Critical (Admin) | success |

### ✅ All E2E tests passed — safe to merge

**Coverage validated:**
- Admin E2E: 9 modules (User/Financial/Session/Tournament/Location/Semester/GamePresets/Events)
- Instructor E2E: 4 modules (Dashboard/Session Check-in/Tournament Workflow/Applications)
- Student E2E: 4 modules (Dashboard/Onboarding/Credits/Specialization)

**Total E2E Test Count: ~525+ tests**
- Admin: ~420 tests
- Instructor: ~67 tests
- Student: ~38 tests
```

### **Test Artifacts**

**Screenshots (on failure only):**
- Location: `tests_cypress/cypress/screenshots/{spec-name}/{test-name}.png`
- Retention: 7-14 days (configurable)
- Download: GitHub Actions → Run → Artifacts

**Videos (nightly full suite only):**
- Location: `tests_cypress/cypress/videos/{spec-name}.mp4`
- Retention: 14 days
- Download: GitHub Actions → Run → Artifacts

**Test Results JSON:**
- Location: `tests_cypress/cypress-results-{role}.json`
- Retention: 30 days
- Format: Cypress JSON reporter output

---

## 🔧 Maintenance & Troubleshooting

### **Common Issues**

#### **1. Smoke/Critical Tests Failing on PR**

**Diagnosis:**
- Check GitHub Actions logs for specific test failures
- Download screenshot artifacts to see UI state at failure

**Resolution:**
```bash
# Run failing tests locally
cd tests_cypress
npm run cy:open  # Interactive mode to debug

# Check specific role tests
npm run cy:run:admin:critical
npm run cy:run:instructor:critical
npm run cy:run:student:critical
```

#### **2. Flaky Tests (Intermittent Failures)**

**Diagnosis:**
- Test passes locally but fails in CI
- Test fails intermittently (not every run)

**Resolution:**
1. **Check timeouts:** Cypress config has generous timeouts for Streamlit
   ```javascript
   // tests_cypress/cypress.config.js
   defaultCommandTimeout: 15000  // May need increase
   pageLoadTimeout: 60000
   ```

2. **Add explicit waits:**
   ```javascript
   cy.get('[data-testid="stButton"]').should('be.visible');
   cy.wait(500);  // Give Streamlit time to settle
   cy.get('[data-testid="stButton"]').click();
   ```

3. **Use retry policy:**
   ```javascript
   // cypress.config.js already has retries configured
   retries: {
     runMode: 2,   // CI retries 2 times
     openMode: 0,
   }
   ```

#### **3. Database Seeding Failures**

**Diagnosis:**
- Tests fail with "user not found" or "test data missing"

**Resolution:**
```bash
# Check seed script locally
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_test \
  python scripts/seed_test_data.py

# Verify test users exist
psql postgresql://postgres:postgres@localhost:5432/lfa_test \
  -c "SELECT email FROM users WHERE email IN ('admin@lfa.com', 'grandmaster@lfa.com', 'rdias@manchestercity.com');"
```

#### **4. Cypress Cloud Recording Failures**

**Diagnosis:**
- Tests run but not uploaded to Cypress Cloud
- Error: "Recording not allowed"

**Resolution:**
1. Verify secrets are set correctly:
   - `CYPRESS_PROJECT_ID` (not prefixed with `CYPRESS_`)
   - `CYPRESS_RECORD_KEY` (not prefixed with `CYPRESS_`)

2. Check Cypress Cloud project settings:
   - Record key is active (not revoked)
   - Project ID matches

3. Test locally:
   ```bash
   CYPRESS_RECORD_KEY=your-key \
   CYPRESS_PROJECT_ID=your-id \
     npx cypress run --record
   ```

### **Updating Test Suite**

#### **Adding New Tests**

1. **Create test file:**
   ```bash
   cd tests_cypress/cypress/e2e/admin
   touch new_feature.cy.js
   ```

2. **Add @smoke or @critical tags:**
   ```javascript
   it('@critical admin can perform critical action', () => {
     // ...
   });

   it('@smoke admin dashboard loads', () => {
     // ...
   });
   ```

3. **Test locally:**
   ```bash
   npm run cy:run:smoke     # Verify smoke tag works
   npm run cy:run:critical  # Verify critical tag works
   ```

4. **Commit and push:**
   - CI/CD will automatically pick up new tests based on tags

#### **Updating Test Credentials**

**Local:**
Update `cypress.config.js` `env` section

**CI/CD:**
Update workflow environment variables in `.github/workflows/e2e-comprehensive.yml`

---

## ✅ Best Practices

### **Test Organization**

```
tests_cypress/cypress/e2e/
├── admin/              # Admin-only tests (9 modules)
├── instructor/         # Instructor-only tests (4 modules)
├── player/             # Student tests (4 modules)
├── auth/               # Authentication tests
├── system/             # Cross-role integration
└── error_states/       # Error handling tests
```

### **Tagging Strategy**

- **@smoke:** Essential tests for PR gate
  - Must run in < 5 minutes
  - Cover critical user paths (login, navigation, basic CRUD)
  - Example: Dashboard loads, user can login, tournament creation smoke test

- **@critical:** Blocking tests for merge
  - Must run in < 20 minutes (per role)
  - Cover business logic and workflows
  - Example: Full tournament lifecycle, payment processing, refund logic

- **No tag:** Full regression suite
  - All tests (including edge cases, error states, validation)
  - Runs nightly only

### **Writing Maintainable Tests**

**1. Use graceful degradation:**
```javascript
cy.get('body').then(($body) => {
  if ($body.text().includes('No data')) {
    cy.log('⚠️ No data available — skipping test');
    return;
  }
  // Continue test
});
```

**2. Add descriptive logs:**
```javascript
cy.log('✓ User balance updated successfully');
cy.log(`⚠️ Test data dependent: requires ${minPlayers} players`);
```

**3. Use data-testid selectors:**
```javascript
// Preferred
cy.get('[data-testid="stButton"]').contains('Submit').click();

// Avoid (fragile)
cy.get('.css-12345').first().click();
```

**4. Session preservation:**
```javascript
// After navigation, verify session still active
cy.assertAuthenticated();
cy.get('[data-testid="stSidebar"]').should('be.visible');
```

### **CI/CD Best Practices**

1. **Keep PR gate fast (<30 min total)**
   - Only @smoke and @critical tests
   - Parallel execution by role
   - Fail fast on smoke failure

2. **Use nightly for comprehensive coverage**
   - All tests (including slow/edge cases)
   - Record to Cypress Cloud for analytics
   - Allow failures (warnings only)

3. **Monitor flaky tests**
   - Cypress Cloud flaky test detection
   - Review failure screenshots/videos
   - Add explicit waits or retry logic

4. **Maintain test data independence**
   - Each test should be self-contained
   - Use unique identifiers (timestamps) for test data
   - Clean up after tests (or use DB transactions)

---

## 🎯 Summary

**CI/CD E2E Pipeline Status:**

| Component | Status | Notes |
|-----------|--------|-------|
| **Admin E2E Coverage** | ✅ 100% | 9 modules, 420+ tests |
| **Instructor E2E Coverage** | ✅ Comprehensive | 4 modules, 67+ tests |
| **Student E2E Coverage** | ✅ Core Features | 4 modules, 38+ tests |
| **PR Gate (Smoke)** | ✅ Configured | ~5 min, blocking |
| **PR Gate (Critical)** | ✅ Configured | ~20 min, blocking, parallel |
| **Nightly Full Suite** | ✅ Configured | ~60 min, parallel by role |
| **Cypress Cloud** | ⚠️ Optional | Requires CYPRESS_RECORD_KEY secret |
| **Test Artifacts** | ✅ Configured | Screenshots, videos, JSON results |
| **GitHub Step Summary** | ✅ Configured | Auto-generated pass/fail report |
| **PR Comments** | ✅ Configured | Auto-posted on PR completion |

**Total E2E Test Count: ~525+ tests**
- Admin: ~420 tests (9 modules)
- Instructor: ~67 tests (4 modules)
- Student: ~38 tests (4 modules)

---

**For questions or issues, contact the QA team or refer to:**
- Cypress Documentation: https://docs.cypress.io
- Cypress Cloud: https://cloud.cypress.io
- GitHub Actions Documentation: https://docs.github.com/actions
